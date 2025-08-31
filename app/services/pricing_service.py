from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.models.pricing_rule import PricingRule
from app.models.product import Product
from app.models.partner import Partner


class PricingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_price(
        self,
        sku_id: str,
        cost_price: float,
        quantity: int = 1
    ) -> float:
        """Calculate final selling price based on cost price and partner pricing rules"""
        
        # Import SKU here to avoid circular import
        from app.models.sku import SKU
        
        # Get SKU with product and partner information
        stmt = (
            select(SKU)
            .options(selectinload(SKU.product).selectinload(Product.partner))
            .where(SKU.id == sku_id)
        )
        result = await self.db.execute(stmt)
        sku = result.scalar_one_or_none()

        if not sku or not sku.product or not sku.product.partner:
            return cost_price

        # Get applicable pricing rules
        pricing_rules = await self._get_applicable_pricing_rules(
            sku.product.partner_id,
            sku.product.category,
            quantity
        )

        # Apply pricing rules in order of priority
        final_price = Decimal(str(cost_price))
        
        for rule in pricing_rules:
            final_price = self._apply_pricing_rule(final_price, rule, quantity)

        return float(final_price)
        
    async def calculate_price_for_product(
        self,
        product_id: str, 
        cost_price: float,
        quantity: int = 1
    ) -> float:
        """Calculate price based on product (for when SKU doesn't exist yet)"""
        
        # Get product with partner information
        stmt = (
            select(Product)
            .options(selectinload(Product.partner))
            .where(Product.id == product_id)
        )
        result = await self.db.execute(stmt)
        product = result.scalar_one_or_none()

        if not product or not product.partner:
            return cost_price

        # Get applicable pricing rules
        pricing_rules = await self._get_applicable_pricing_rules(
            product.partner_id,
            product.category,
            quantity
        )

        # Apply pricing rules in order of priority
        final_price = Decimal(str(cost_price))
        
        for rule in pricing_rules:
            final_price = self._apply_pricing_rule(final_price, rule, quantity)

        return float(final_price)

    async def _get_applicable_pricing_rules(
        self,
        partner_id: str,
        category: Optional[str],
        quantity: int
    ) -> List[PricingRule]:
        """Get pricing rules applicable to the given parameters"""
        
        now = datetime.utcnow()
        
        stmt = (
            select(PricingRule)
            .where(
                and_(
                    PricingRule.partner_id == partner_id,
                    PricingRule.is_active == True,
                    PricingRule.valid_from <= now,
                    PricingRule.min_quantity <= quantity,
                    or_(
                        PricingRule.valid_until.is_(None),
                        PricingRule.valid_until >= now
                    ),
                    or_(
                        PricingRule.max_quantity.is_(None),
                        PricingRule.max_quantity >= quantity
                    ),
                    or_(
                        PricingRule.category_filter.is_(None),
                        PricingRule.category_filter == category
                    )
                )
            )
            .order_by(PricingRule.priority.desc())
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()

    def _apply_pricing_rule(
        self,
        current_price: Decimal,
        rule: PricingRule,
        quantity: int
    ) -> Decimal:
        """Apply a single pricing rule to the current price"""
        
        if rule.rule_type == "percentage":
            # Apply percentage markup/discount
            multiplier = Decimal("1") + (Decimal(str(rule.rule_value)) / Decimal("100"))
            return current_price * multiplier
            
        elif rule.rule_type == "fixed_amount":
            # Add/subtract fixed amount
            return current_price + Decimal(str(rule.rule_value))
            
        elif rule.rule_type == "custom":
            # Custom pricing logic can be implemented here
            # For now, return the current price unchanged
            return current_price
            
        return current_price

    async def create_pricing_rule(
        self,
        partner_id: str,
        rule_data: Dict[str, Any]
    ) -> PricingRule:
        """Create a new pricing rule"""
        
        pricing_rule = PricingRule(
            partner_id=partner_id,
            rule_name=rule_data["rule_name"],
            rule_type=rule_data["rule_type"],
            rule_value=rule_data.get("rule_value"),
            min_quantity=rule_data.get("min_quantity", 1),
            max_quantity=rule_data.get("max_quantity"),
            category_filter=rule_data.get("category_filter"),
            product_filter=rule_data.get("product_filter"),
            priority=rule_data.get("priority", 0),
            valid_from=rule_data.get("valid_from", datetime.utcnow()),
            valid_until=rule_data.get("valid_until")
        )
        
        self.db.add(pricing_rule)
        await self.db.commit()
        await self.db.refresh(pricing_rule)
        
        return pricing_rule

    async def update_pricing_rule(
        self,
        rule_id: str,
        rule_data: Dict[str, Any]
    ) -> Optional[PricingRule]:
        """Update an existing pricing rule"""
        
        pricing_rule = await self.db.get(PricingRule, rule_id)
        if not pricing_rule:
            return None

        for field, value in rule_data.items():
            if hasattr(pricing_rule, field) and field != "id":
                setattr(pricing_rule, field, value)

        pricing_rule.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(pricing_rule)
        
        return pricing_rule

    async def delete_pricing_rule(self, rule_id: str) -> bool:
        """Delete a pricing rule"""
        
        pricing_rule = await self.db.get(PricingRule, rule_id)
        if not pricing_rule:
            return False

        pricing_rule.is_active = False
        pricing_rule.updated_at = datetime.utcnow()
        await self.db.commit()
        
        return True

    async def get_partner_pricing_rules(
        self,
        partner_id: str,
        active_only: bool = True
    ) -> List[PricingRule]:
        """Get all pricing rules for a specific partner"""
        
        stmt = select(PricingRule).where(PricingRule.partner_id == partner_id)
        
        if active_only:
            stmt = stmt.where(PricingRule.is_active == True)
        
        stmt = stmt.order_by(PricingRule.priority.desc(), PricingRule.created_at.desc())
        
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def calculate_bulk_pricing(
        self,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate pricing for multiple items at once"""
        
        results = {
            "items": [],
            "total_base_price": Decimal("0"),
            "total_final_price": Decimal("0"),
            "total_discount": Decimal("0")
        }

        for item in items:
            product_id = item["product_id"]
            base_price = Decimal(str(item["base_price"]))
            quantity = item.get("quantity", 1)

            final_price = await self.calculate_price(
                product_id,
                float(base_price),
                quantity=quantity
            )
            
            final_price_decimal = Decimal(str(final_price))
            discount = base_price - final_price_decimal

            item_result = {
                "product_id": product_id,
                "base_price": float(base_price),
                "final_price": float(final_price_decimal),
                "discount": float(discount),
                "quantity": quantity,
                "line_total": float(final_price_decimal * quantity)
            }

            results["items"].append(item_result)
            results["total_base_price"] += base_price * quantity
            results["total_final_price"] += final_price_decimal * quantity
            results["total_discount"] += discount * quantity

        # Convert Decimal to float for JSON serialization
        results["total_base_price"] = float(results["total_base_price"])
        results["total_final_price"] = float(results["total_final_price"])
        results["total_discount"] = float(results["total_discount"])

        return results

    async def calculate_final_price_with_formula(
        self, 
        base_price: Decimal, 
        partner_id: str,
        quantity: int = 1
    ) -> Decimal:
        """
        Calculate final price based on base price and partner's pricing formula
        
        Args:
            base_price: The base price from supplier
            partner_id: Partner ID to get pricing formula
            quantity: Quantity for bulk pricing (if applicable)
            
        Returns:
            Calculated final price
        """
        if not base_price or base_price <= 0:
            return Decimal('0')
        
        # Get partner and their pricing formula
        partner_query = select(Partner).where(Partner.id == partner_id)
        partner_result = await self.db.execute(partner_query)
        partner = partner_result.scalar_one_or_none()
        
        if not partner:
            return base_price
        
        # Calculate price using profit percentage and fixed amount
        calculated_price = self._calculate_price_with_profit(
            base_price,
            partner.profit_percentage or Decimal('0'),
            partner.fixed_amount or Decimal('0')
        )
        
        # Apply price ending digit rounding
        final_price = self._apply_price_ending(
            calculated_price, 
            partner.price_ending_digit or 0
        )
        
        return final_price
    
    def _calculate_price_with_profit(
        self, 
        base_price: Decimal, 
        profit_percentage: Decimal,
        fixed_amount: Decimal
    ) -> Decimal:
        """
        Calculate final price using profit percentage and fixed amount
        
        Args:
            base_price: The base price from supplier
            profit_percentage: Profit percentage (e.g., 20 for 20%)
            fixed_amount: Fixed amount to add to base price
            
        Returns:
            Calculated price with profit and fixed amount added
        """
        if not base_price or base_price <= 0:
            return Decimal('0')
        
        try:
            # Calculate profit amount: base_price * (profit_percentage / 100)
            profit_amount = base_price * (profit_percentage / Decimal('100'))
            
            # Calculate final price: base_price + profit_amount + fixed_amount
            calculated_price = base_price + profit_amount + fixed_amount
            
            return calculated_price
            
        except Exception as e:
            print(f"Price calculation error: {e}")
            return base_price
    
    def _is_safe_formula(self, formula: str) -> bool:
        """
        Check if the formula contains only safe mathematical operations
        """
        # Only allow numbers, basic math operators, and parentheses
        allowed_pattern = r'^[\d\s\+\-\*\/\.\(\)]+$'
        return bool(re.match(allowed_pattern, formula))
    
    def _apply_price_ending(self, price: Decimal, ending_digit: int) -> Decimal:
        """
        Apply price ending digit rounding
        
        Args:
            price: The calculated price
            ending_digit: Last digit for prices (e.g., 5000 makes all prices end with 5000)
            
        Returns:
            Price rounded to end with specified digit
        """
        if ending_digit <= 0:
            return price
        
        try:
            price_float = float(price)
            
            # Find how much to add to make price end with ending_digit
            remainder = price_float % ending_digit
            if remainder == 0:
                return price
            
            # Calculate adjustment needed
            adjustment = ending_digit - remainder
            
            # If adjustment is more than 3, round up to next ending_digit cycle
            if adjustment > 3:
                adjusted_price = price_float + adjustment
            else:
                adjusted_price = price_float + adjustment
            
            return Decimal(str(int(adjusted_price)))
            
        except Exception as e:
            print(f"Price ending calculation error: {e}")
            return price
    
    async def update_sku_final_prices(self, product_id: Optional[str] = None):
        """
        Update final prices for all SKUs, optionally filtered by product
        """
        # Import SKU here to avoid circular import
        from app.models.sku import SKU
        
        query = select(SKU).options(selectinload(SKU.product))
        if product_id:
            query = query.where(SKU.product_id == product_id)
        
        result = await self.db.execute(query)
        skus = result.scalars().all()
        
        updated_count = 0
        for sku in skus:
            if sku.base_price and sku.product and sku.product.partner_id:
                try:
                    new_final_price = await self.calculate_final_price_with_formula(
                        sku.base_price,
                        str(sku.product.partner_id)
                    )
                    
                    if new_final_price != sku.final_price:
                        sku.final_price = new_final_price
                        updated_count += 1
                        
                except Exception as e:
                    print(f"Error updating SKU {sku.id} final price: {e}")
        
        if updated_count > 0:
            await self.db.commit()
        
        return updated_count