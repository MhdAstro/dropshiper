from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import asyncio
import httpx

from app.models.sku import SKU
from app.models.sku_mapping import SKUMapping
from app.models.output_platform import OutputPlatform
from app.models.platform import Platform
from app.models.sync_log import SyncLog


class InventorySyncService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def sync_all_platforms(self) -> Dict[str, Any]:
        """Sync inventory across all active output platforms"""
        
        # Get all active output platforms
        stmt = (
            select(OutputPlatform)
            .options(selectinload(OutputPlatform.platform))
            .where(OutputPlatform.is_active == True)
        )
        
        result = await self.db.execute(stmt)
        output_platforms = result.scalars().all()

        sync_results = {
            "total_platforms": len(output_platforms),
            "successful_syncs": 0,
            "failed_syncs": 0,
            "platform_results": []
        }

        # Sync each platform concurrently
        tasks = []
        for platform in output_platforms:
            task = self._sync_platform(platform)
            tasks.append(task)

        platform_results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(platform_results):
            platform = output_platforms[i]
            
            if isinstance(result, Exception):
                sync_results["failed_syncs"] += 1
                sync_results["platform_results"].append({
                    "platform_id": str(platform.id),
                    "platform_name": platform.platform.name,
                    "status": "error",
                    "error": str(result)
                })
            else:
                sync_results["successful_syncs"] += 1
                sync_results["platform_results"].append({
                    "platform_id": str(platform.id),
                    "platform_name": platform.platform.name,
                    "status": "success",
                    **result
                })

        return sync_results

    async def _sync_platform(self, output_platform: OutputPlatform) -> Dict[str, Any]:
        """Sync inventory for a specific platform"""
        
        start_time = datetime.utcnow()
        sync_log = SyncLog(
            platform_id=output_platform.platform_id,
            sync_type="inventory",
            status="running",
            started_at=start_time
        )
        self.db.add(sync_log)
        await self.db.flush()

        try:
            # Get SKU mappings for this platform
            stmt = (
                select(SKUMapping)
                .options(selectinload(SKUMapping.sku))
                .where(
                    SKUMapping.platform_id == output_platform.platform_id,
                    SKUMapping.is_active == True
                )
            )
            
            result = await self.db.execute(stmt)
            sku_mappings = result.scalars().all()

            sync_result = await self._perform_platform_sync(
                output_platform,
                sku_mappings
            )

            # Update sync log
            sync_log.status = "success"
            sync_log.records_processed = len(sku_mappings)
            sync_log.completed_at = datetime.utcnow()

            # Update platform last sync time
            output_platform.last_sync = datetime.utcnow()

            await self.db.commit()

            return sync_result

        except Exception as e:
            # Update sync log with error
            sync_log.status = "error"
            sync_log.error_message = str(e)
            sync_log.completed_at = datetime.utcnow()
            await self.db.commit()
            raise e

    async def _perform_platform_sync(
        self,
        output_platform: OutputPlatform,
        sku_mappings: List[SKUMapping]
    ) -> Dict[str, Any]:
        """Perform the actual sync with the external platform"""
        
        platform_name = output_platform.platform.name.lower()
        
        if platform_name == "basalam":
            return await self._sync_basalam(output_platform, sku_mappings)
        elif platform_name == "telegram":
            return await self._sync_telegram(output_platform, sku_mappings)
        else:
            return await self._sync_generic_platform(output_platform, sku_mappings)

    async def _sync_basalam(
        self,
        output_platform: OutputPlatform,
        sku_mappings: List[SKUMapping]
    ) -> Dict[str, Any]:
        """Sync inventory with Basalam platform"""
        
        api_endpoint = output_platform.platform.api_endpoint
        if not api_endpoint:
            raise ValueError("Basalam API endpoint not configured")

        # Prepare inventory data for Basalam API
        inventory_updates = []
        
        for mapping in sku_mappings:
            if mapping.sku and mapping.sku.is_active:
                # Calculate final price based on mapping rules
                final_price = self._calculate_mapped_price(mapping)
                
                inventory_updates.append({
                    "external_product_id": mapping.external_product_id,
                    "external_sku": mapping.external_sku,
                    "quantity": mapping.sku.quantity,
                    "price": final_price
                })

        # Send updates to Basalam API
        headers = {
            "Authorization": f"Bearer {output_platform.token}",
            "Content-Type": "application/json"
        }

        response = await self.http_client.post(
            f"{api_endpoint}/inventory/bulk-update",
            json={"items": inventory_updates},
            headers=headers
        )

        if response.status_code != 200:
            raise Exception(f"Basalam sync failed: {response.text}")

        return {
            "updated_items": len(inventory_updates),
            "api_response": response.json()
        }

    async def _sync_telegram(
        self,
        output_platform: OutputPlatform,
        sku_mappings: List[SKUMapping]
    ) -> Dict[str, Any]:
        """Sync inventory with Telegram bot"""
        
        # For Telegram, we might send notifications about stock changes
        # or update a channel with current inventory status
        
        low_stock_items = [
            mapping for mapping in sku_mappings
            if mapping.sku and mapping.sku.quantity < 10
        ]

        if low_stock_items:
            await self._send_telegram_notification(
                output_platform,
                f"Low stock alert: {len(low_stock_items)} items below threshold"
            )

        return {
            "processed_items": len(sku_mappings),
            "low_stock_alerts": len(low_stock_items)
        }

    async def _sync_generic_platform(
        self,
        output_platform: OutputPlatform,
        sku_mappings: List[SKUMapping]
    ) -> Dict[str, Any]:
        """Generic sync for other platforms"""
        
        # Implement generic webhook-based sync
        webhook_url = output_platform.platform.webhook_endpoint
        
        if webhook_url:
            inventory_data = [
                {
                    "sku_code": mapping.sku.sku_code,
                    "external_sku": mapping.external_sku,
                    "quantity": mapping.sku.quantity,
                    "price": self._calculate_mapped_price(mapping)
                }
                for mapping in sku_mappings
                if mapping.sku and mapping.sku.is_active
            ]

            response = await self.http_client.post(
                webhook_url,
                json={"type": "inventory_update", "data": inventory_data}
            )

            return {
                "webhook_sent": True,
                "status_code": response.status_code,
                "items_sent": len(inventory_data)
            }

        return {"message": "No sync method configured for this platform"}

    def _calculate_mapped_price(self, mapping: SKUMapping) -> float:
        """Calculate the final price for a mapped SKU"""
        
        base_price = mapping.sku.price or 0
        
        if mapping.custom_price:
            return float(mapping.custom_price)
        
        if mapping.price_multiplier and mapping.price_multiplier != 1.0:
            return float(base_price * mapping.price_multiplier)
        
        return float(base_price)

    async def _send_telegram_notification(
        self,
        output_platform: OutputPlatform,
        message: str
    ):
        """Send notification via Telegram bot"""
        
        from app.core.config import settings
        
        if not settings.TELEGRAM_BOT_TOKEN:
            return

        # Get chat ID from platform configuration
        chat_id = output_platform.configuration.get("chat_id") if output_platform.configuration else None
        
        if not chat_id:
            return

        telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        
        await self.http_client.post(
            telegram_url,
            json={
                "chat_id": chat_id,
                "text": message
            }
        )

    async def sync_specific_sku(
        self,
        sku_id: str,
        platform_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Sync a specific SKU across platforms"""
        
        sku = await self.db.get(SKU, sku_id)
        if not sku:
            raise ValueError(f"SKU {sku_id} not found")

        # Get mappings for this SKU
        stmt = (
            select(SKUMapping)
            .options(selectinload(SKUMapping.platform))
            .where(SKUMapping.sku_id == sku_id, SKUMapping.is_active == True)
        )
        
        if platform_ids:
            stmt = stmt.where(SKUMapping.platform_id.in_(platform_ids))
        
        result = await self.db.execute(stmt)
        mappings = result.scalars().all()

        sync_results = []
        
        for mapping in mappings:
            try:
                # Get output platform configuration
                output_platform_stmt = (
                    select(OutputPlatform)
                    .where(OutputPlatform.platform_id == mapping.platform_id)
                )
                result = await self.db.execute(output_platform_stmt)
                output_platform = result.scalar_one_or_none()
                
                if output_platform:
                    result = await self._perform_platform_sync(
                        output_platform,
                        [mapping]
                    )
                    sync_results.append({
                        "platform_id": str(mapping.platform_id),
                        "status": "success",
                        **result
                    })

            except Exception as e:
                sync_results.append({
                    "platform_id": str(mapping.platform_id),
                    "status": "error",
                    "error": str(e)
                })

        return {
            "sku_id": sku_id,
            "synced_platforms": len(sync_results),
            "results": sync_results
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()