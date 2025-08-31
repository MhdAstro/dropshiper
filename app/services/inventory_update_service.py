from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.sku import SKU
from app.models.inventory_update import InventoryUpdate
from app.models.source_platform import SourcePlatform
from app.models.platform import Platform
from app.services.pricing_service import PricingService


class InventoryUpdateService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pricing_service = PricingService(db)

    async def update_inventory_from_supplier(
        self, 
        source_platform_id: str,
        inventory_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Update inventory based on supplier data"""
        
        source_platform = await self.db.get(SourcePlatform, source_platform_id)
        if not source_platform:
            raise ValueError(f"Source platform {source_platform_id} not found")

        results = {
            "updated": 0,
            "created": 0,
            "errors": [],
            "processed": len(inventory_data)
        }

        try:
            for item_data in inventory_data:
                try:
                    await self._process_inventory_item(source_platform, item_data, results)
                except Exception as e:
                    results["errors"].append({
                        "item": item_data,
                        "error": str(e)
                    })

            # Update last sync time
            source_platform.last_sync = datetime.utcnow()
            await self.db.commit()

            # Log the update
            await self._log_inventory_update(
                source_platform_id,
                "automatic",
                f"Updated {results['updated']} items, created {results['created']} items"
            )

        except Exception as e:
            await self.db.rollback()
            raise e

        return results

    async def _process_inventory_item(
        self,
        source_platform: SourcePlatform,
        item_data: Dict[str, Any],
        results: Dict[str, Any]
    ):
        """Process a single inventory item"""
        
        sku_code = item_data.get("sku_code")
        new_quantity = item_data.get("quantity", 0)
        new_price = item_data.get("price")
        
        if not sku_code:
            raise ValueError("SKU code is required")

        # Find existing SKU
        stmt = select(SKU).where(SKU.sku_code == sku_code)
        result = await self.db.execute(stmt)
        sku = result.scalar_one_or_none()

        if sku:
            # Update existing SKU
            old_quantity = sku.quantity
            sku.quantity = new_quantity
            
            if new_price is not None:
                # Apply pricing rules
                final_price = await self.pricing_service.calculate_price(
                    sku.product_id,
                    new_price,
                    source_platform.id
                )
                sku.price = final_price

            sku.updated_at = datetime.utcnow()

            # Log the inventory update
            await self._create_inventory_update_log(
                sku.id,
                source_platform.id,
                old_quantity,
                new_quantity,
                "automatic"
            )

            results["updated"] += 1

        else:
            # Create new SKU if product exists
            product_id = item_data.get("product_id")
            if product_id:
                new_sku = await self._create_new_sku(
                    product_id,
                    sku_code,
                    new_quantity,
                    new_price,
                    item_data
                )
                
                await self._create_inventory_update_log(
                    new_sku.id,
                    source_platform.id,
                    0,
                    new_quantity,
                    "automatic"
                )

                results["created"] += 1

    async def _create_new_sku(
        self,
        product_id: str,
        sku_code: str,
        quantity: int,
        price: Optional[float],
        item_data: Dict[str, Any]
    ) -> SKU:
        """Create a new SKU"""
        
        new_sku = SKU(
            product_id=product_id,
            sku_code=sku_code,
            quantity=quantity,
            price=price,
            variant_combination=item_data.get("variant_combination"),
            weight=item_data.get("weight"),
            dimensions=item_data.get("dimensions")
        )
        
        self.db.add(new_sku)
        await self.db.flush()
        return new_sku

    async def _create_inventory_update_log(
        self,
        sku_id: str,
        source_platform_id: str,
        old_quantity: int,
        new_quantity: int,
        update_type: str,
        reason: Optional[str] = None
    ):
        """Create inventory update log entry"""
        
        log_entry = InventoryUpdate(
            sku_id=sku_id,
            source_platform_id=source_platform_id,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
            update_type=update_type,
            reason=reason
        )
        
        self.db.add(log_entry)

    async def manual_inventory_update(
        self,
        sku_id: str,
        new_quantity: int,
        reason: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Manually update inventory for a specific SKU"""
        
        sku = await self.db.get(SKU, sku_id)
        if not sku:
            raise ValueError(f"SKU {sku_id} not found")

        old_quantity = sku.quantity
        sku.quantity = new_quantity
        sku.updated_at = datetime.utcnow()

        # Log the manual update
        await self._create_inventory_update_log(
            sku_id,
            None,  # No source platform for manual updates
            old_quantity,
            new_quantity,
            "manual",
            f"Manual update by user {user_id}: {reason}"
        )

        await self.db.commit()

        return {
            "sku_id": sku_id,
            "old_quantity": old_quantity,
            "new_quantity": new_quantity,
            "updated_at": sku.updated_at.isoformat()
        }

    async def process_order_inventory_update(
        self,
        order_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Update inventory when an order is placed"""
        
        results = {
            "updated": 0,
            "errors": [],
            "insufficient_stock": []
        }

        try:
            for item in order_items:
                sku_id = item["sku_id"]
                quantity_ordered = item["quantity"]

                sku = await self.db.get(SKU, sku_id)
                if not sku:
                    results["errors"].append({
                        "sku_id": sku_id,
                        "error": "SKU not found"
                    })
                    continue

                if sku.quantity < quantity_ordered:
                    results["insufficient_stock"].append({
                        "sku_id": sku_id,
                        "available": sku.quantity,
                        "requested": quantity_ordered
                    })
                    continue

                # Update inventory
                old_quantity = sku.quantity
                sku.quantity -= quantity_ordered
                sku.updated_at = datetime.utcnow()

                # Log the inventory update
                await self._create_inventory_update_log(
                    sku_id,
                    None,
                    old_quantity,
                    sku.quantity,
                    "order_placed",
                    f"Order placed - reduced by {quantity_ordered}"
                )

                results["updated"] += 1

            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            raise e

        return results

    async def get_low_stock_items(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """Get items with low stock"""
        
        stmt = (
            select(SKU)
            .options(selectinload(SKU.product))
            .where(SKU.quantity <= threshold)
            .where(SKU.is_active == True)
        )
        
        result = await self.db.execute(stmt)
        low_stock_skus = result.scalars().all()

        return [
            {
                "sku_id": str(sku.id),
                "sku_code": sku.sku_code,
                "product_name": sku.product.name if sku.product else None,
                "current_quantity": sku.quantity,
                "price": float(sku.price) if sku.price else None
            }
            for sku in low_stock_skus
        ]

    async def _log_inventory_update(
        self,
        source_platform_id: str,
        update_type: str,
        message: str
    ):
        """Log inventory update operation"""
        
        from app.models.sync_log import SyncLog
        
        log_entry = SyncLog(
            platform_id=source_platform_id,
            sync_type="inventory",
            status="success",
            records_processed=1,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        
        self.db.add(log_entry)