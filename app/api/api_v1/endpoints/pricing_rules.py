from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from decimal import Decimal
import uuid

from app.db.database import get_db
from app.models.pricing_rule import PricingRule
from app.models.partner import Partner
from app.schemas.pricing_rule import (
    PricingRuleCreate, 
    PricingRuleUpdate, 
    PricingRuleResponse,
    PriceCalculationRequest,
    PriceCalculationResponse
)
from app.services.pricing_service import PricingService

router = APIRouter()


@router.get("/", response_model=List[PricingRuleResponse])
async def get_pricing_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    partner_id: Optional[str] = Query(None, description="Filter by partner ID"),
    active_only: bool = Query(True, description="Show only active rules"),
    db: AsyncSession = Depends(get_db)
):
    """Get all pricing rules with filtering options"""
    
    query = select(PricingRule).options(selectinload(PricingRule.partner))
    
    conditions = []
    if partner_id:
        conditions.append(PricingRule.partner_id == partner_id)
    if active_only:
        conditions.append(PricingRule.is_active == True)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.offset(skip).limit(limit).order_by(PricingRule.priority.desc(), PricingRule.created_at.desc())
    
    result = await db.execute(query)
    pricing_rules = result.scalars().all()
    
    # Convert to response format
    response_rules = []
    for rule in pricing_rules:
        response_rules.append(
            PricingRuleResponse(
                id=rule.id,
                partner_id=rule.partner_id,
                rule_name=rule.rule_name,
                rule_type=rule.rule_type,
                rule_value=rule.rule_value,
                min_quantity=rule.min_quantity,
                max_quantity=rule.max_quantity,
                category_filter=rule.category_filter,
                product_filter=rule.product_filter,
                priority=rule.priority,
                is_active=rule.is_active,
                valid_from=rule.valid_from,
                valid_until=rule.valid_until,
                created_at=rule.created_at,
                updated_at=rule.updated_at,
                partner_name=rule.partner.name if rule.partner else None
            )
        )
    
    return response_rules


@router.get("/{rule_id}", response_model=PricingRuleResponse)
async def get_pricing_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific pricing rule by ID"""
    
    try:
        rule_uuid = uuid.UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID format")
    
    query = select(PricingRule).options(selectinload(PricingRule.partner)).where(PricingRule.id == rule_uuid)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
    
    return PricingRuleResponse(
        id=rule.id,
        partner_id=rule.partner_id,
        rule_name=rule.rule_name,
        rule_type=rule.rule_type,
        rule_value=rule.rule_value,
        min_quantity=rule.min_quantity,
        max_quantity=rule.max_quantity,
        category_filter=rule.category_filter,
        product_filter=rule.product_filter,
        priority=rule.priority,
        is_active=rule.is_active,
        valid_from=rule.valid_from,
        valid_until=rule.valid_until,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        partner_name=rule.partner.name if rule.partner else None
    )


@router.post("/", response_model=PricingRuleResponse)
async def create_pricing_rule(
    pricing_rule: PricingRuleCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new pricing rule"""
    
    # Verify partner exists
    partner = await db.get(Partner, pricing_rule.partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Create pricing rule
    new_rule = PricingRule(
        partner_id=pricing_rule.partner_id,
        rule_name=pricing_rule.rule_name,
        rule_type=pricing_rule.rule_type,
        rule_value=pricing_rule.rule_value,
        min_quantity=pricing_rule.min_quantity,
        max_quantity=pricing_rule.max_quantity,
        category_filter=pricing_rule.category_filter,
        product_filter=pricing_rule.product_filter,
        priority=pricing_rule.priority,
        is_active=pricing_rule.is_active,
        valid_from=pricing_rule.valid_from,
        valid_until=pricing_rule.valid_until
    )
    
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    
    # Load partner for response
    await db.refresh(new_rule, ["partner"])
    
    return PricingRuleResponse(
        id=new_rule.id,
        partner_id=new_rule.partner_id,
        rule_name=new_rule.rule_name,
        rule_type=new_rule.rule_type,
        rule_value=new_rule.rule_value,
        min_quantity=new_rule.min_quantity,
        max_quantity=new_rule.max_quantity,
        category_filter=new_rule.category_filter,
        product_filter=new_rule.product_filter,
        priority=new_rule.priority,
        is_active=new_rule.is_active,
        valid_from=new_rule.valid_from,
        valid_until=new_rule.valid_until,
        created_at=new_rule.created_at,
        updated_at=new_rule.updated_at,
        partner_name=new_rule.partner.name if new_rule.partner else None
    )


@router.put("/{rule_id}", response_model=PricingRuleResponse)
async def update_pricing_rule(
    rule_id: str,
    pricing_rule_update: PricingRuleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing pricing rule"""
    
    try:
        rule_uuid = uuid.UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID format")
    
    # Get existing rule
    rule = await db.get(PricingRule, rule_uuid)
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
    
    # Update fields
    update_data = pricing_rule_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    await db.commit()
    await db.refresh(rule)
    
    # Load partner for response
    await db.refresh(rule, ["partner"])
    
    return PricingRuleResponse(
        id=rule.id,
        partner_id=rule.partner_id,
        rule_name=rule.rule_name,
        rule_type=rule.rule_type,
        rule_value=rule.rule_value,
        min_quantity=rule.min_quantity,
        max_quantity=rule.max_quantity,
        category_filter=rule.category_filter,
        product_filter=rule.product_filter,
        priority=rule.priority,
        is_active=rule.is_active,
        valid_from=rule.valid_from,
        valid_until=rule.valid_until,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        partner_name=rule.partner.name if rule.partner else None
    )


@router.delete("/{rule_id}")
async def delete_pricing_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete (deactivate) a pricing rule"""
    
    try:
        rule_uuid = uuid.UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID format")
    
    rule = await db.get(PricingRule, rule_uuid)
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
    
    # Soft delete by deactivating
    rule.is_active = False
    await db.commit()
    
    return {"message": "Pricing rule deactivated successfully"}


@router.get("/partner/{partner_id}", response_model=List[PricingRuleResponse])
async def get_partner_pricing_rules(
    partner_id: str,
    active_only: bool = Query(True, description="Show only active rules"),
    db: AsyncSession = Depends(get_db)
):
    """Get all pricing rules for a specific partner"""
    
    try:
        partner_uuid = uuid.UUID(partner_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid partner ID format")
    
    # Verify partner exists
    partner = await db.get(Partner, partner_uuid)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    query = (
        select(PricingRule)
        .options(selectinload(PricingRule.partner))
        .where(PricingRule.partner_id == partner_uuid)
    )
    
    if active_only:
        query = query.where(PricingRule.is_active == True)
    
    query = query.order_by(PricingRule.priority.desc(), PricingRule.created_at.desc())
    
    result = await db.execute(query)
    rules = result.scalars().all()
    
    return [
        PricingRuleResponse(
            id=rule.id,
            partner_id=rule.partner_id,
            rule_name=rule.rule_name,
            rule_type=rule.rule_type,
            rule_value=rule.rule_value,
            min_quantity=rule.min_quantity,
            max_quantity=rule.max_quantity,
            category_filter=rule.category_filter,
            product_filter=rule.product_filter,
            priority=rule.priority,
            is_active=rule.is_active,
            valid_from=rule.valid_from,
            valid_until=rule.valid_until,
            created_at=rule.created_at,
            updated_at=rule.updated_at,
            partner_name=rule.partner.name if rule.partner else None
        ) for rule in rules
    ]


@router.post("/calculate-price", response_model=PriceCalculationResponse)
async def calculate_price(
    request: PriceCalculationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Calculate selling price for a SKU based on pricing rules"""
    
    pricing_service = PricingService(db)
    
    try:
        calculated_price = await pricing_service.calculate_price(
            str(request.sku_id),
            float(request.cost_price),
            request.quantity
        )
        
        markup_amount = Decimal(str(calculated_price)) - request.cost_price
        markup_percentage = None
        if request.cost_price > 0:
            markup_percentage = (markup_amount / request.cost_price) * 100
        
        return PriceCalculationResponse(
            sku_id=request.sku_id,
            cost_price=request.cost_price,
            calculated_price=Decimal(str(calculated_price)),
            markup_amount=markup_amount,
            markup_percentage=markup_percentage,
            applied_rules=[]  # TODO: Track applied rules in pricing service
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error calculating price: {str(e)}")