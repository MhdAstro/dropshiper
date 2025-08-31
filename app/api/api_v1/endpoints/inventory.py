from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.db.database import get_db
from app.services.inventory_update_service import InventoryUpdateService
from app.services.inventory_sync_service import InventorySyncService

router = APIRouter()


@router.post("/update")
async def update_inventory(
    source_platform_id: str,
    inventory_data: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db)
):
    """Update inventory from supplier data"""
    
    service = InventoryUpdateService(db)
    
    try:
        result = await service.update_inventory_from_supplier(
            source_platform_id,
            inventory_data
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_inventory(
    background_tasks: BackgroundTasks,
    platform_ids: List[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Sync inventory across platforms"""
    
    async def sync_task():
        async with InventorySyncService(db) as service:
            await service.sync_all_platforms()
    
    background_tasks.add_task(sync_task)
    
    return {"message": "Inventory sync started"}


@router.post("/sync/{sku_id}")
async def sync_sku(
    sku_id: str,
    platform_ids: List[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Sync specific SKU across platforms"""
    
    async with InventorySyncService(db) as service:
        try:
            result = await service.sync_specific_sku(sku_id, platform_ids)
            return result
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{sku_id}")
async def manual_inventory_update(
    sku_id: str,
    new_quantity: int,
    reason: str,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Manually update inventory for specific SKU"""
    
    service = InventoryUpdateService(db)
    
    try:
        result = await service.manual_inventory_update(
            sku_id,
            new_quantity,
            reason,
            user_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/low-stock")
async def get_low_stock_items(
    threshold: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get items with low stock"""
    
    service = InventoryUpdateService(db)
    
    try:
        result = await service.get_low_stock_items(threshold)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))