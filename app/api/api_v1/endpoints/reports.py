from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, Dict, Any

from app.db.database import get_db
from app.services.reporting_service import ReportingService

router = APIRouter()


@router.get("/inventory")
async def get_inventory_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get inventory summary report"""
    
    service = ReportingService(db)
    
    try:
        df = datetime.fromisoformat(date_from) if date_from else None
        dt = datetime.fromisoformat(date_to) if date_to else None
        
        result = await service.get_inventory_summary(df, dt)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sales")
async def get_sales_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    platform_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get sales report"""
    
    service = ReportingService(db)
    
    try:
        df = datetime.fromisoformat(date_from) if date_from else None
        dt = datetime.fromisoformat(date_to) if date_to else None
        
        result = await service.get_sales_report(df, dt, platform_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/partners")
async def get_partner_performance_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get partner performance report"""
    
    service = ReportingService(db)
    
    try:
        df = datetime.fromisoformat(date_from) if date_from else None
        dt = datetime.fromisoformat(date_to) if date_to else None
        
        result = await service.get_partner_performance_report(df, dt)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync")
async def get_platform_sync_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get platform synchronization report"""
    
    service = ReportingService(db)
    
    try:
        df = datetime.fromisoformat(date_from) if date_from else None
        dt = datetime.fromisoformat(date_to) if date_to else None
        
        result = await service.get_platform_sync_report(df, dt)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/custom")
async def generate_custom_report(
    report_config: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Generate custom report"""
    
    service = ReportingService(db)
    
    try:
        result = await service.get_custom_report(report_config)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_report(
    report_data: Dict[str, Any],
    export_format: str = "json",
    db: AsyncSession = Depends(get_db)
):
    """Export report data"""
    
    service = ReportingService(db)
    
    try:
        exported_data = await service.export_report_data(report_data, export_format)
        
        if export_format.lower() == "csv":
            media_type = "text/csv"
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            media_type = "application/json"
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return Response(
            content=exported_data,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))