from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.database import get_db
from app.crud.settlement import settlement_crud
from app.schemas.settlement import SettlementResponse

router = APIRouter()


@router.get("/", response_model=List[SettlementResponse])
async def get_settlements(
    skip: int = Query(0, ge=0, description="Number of settlements to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of settlements to retrieve"),
    partner_id: str = Query(None, description="Filter by partner ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get settlement history.
    
    Optional filters:
    - **partner_id**: Show only settlements for specific partner
    """
    if partner_id:
        try:
            partner_uuid = uuid.UUID(partner_id)
            settlements = await settlement_crud.get_by_partner(
                db, 
                partner_id=partner_uuid, 
                skip=skip, 
                limit=limit
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid partner ID format")
    else:
        settlements = await settlement_crud.get_with_partner_details(
            db, skip=skip, limit=limit
        )
    
    # Convert to response format with partner names
    response_settlements = []
    for settlement in settlements:
        response_settlements.append(
            SettlementResponse(
                id=settlement.id,
                partner_id=settlement.partner_id,
                amount=settlement.amount,
                previous_debt=settlement.previous_debt,
                remaining_debt=settlement.remaining_debt,
                reason=settlement.reason,
                settled_by=settlement.settled_by,
                notes=settlement.notes,
                created_at=settlement.created_at,
                partner_name=settlement.partner.name if settlement.partner else None
            )
        )
    
    return response_settlements


@router.get("/partner/{partner_id}", response_model=List[SettlementResponse])
async def get_partner_settlements(
    partner_id: str,
    skip: int = Query(0, ge=0, description="Number of settlements to skip"),
    limit: int = Query(50, ge=1, le=500, description="Number of settlements to retrieve"),
    db: AsyncSession = Depends(get_db)
):
    """Get settlement history for a specific partner."""
    try:
        partner_uuid = uuid.UUID(partner_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid partner ID format")
    
    settlements = await settlement_crud.get_by_partner(
        db, 
        partner_id=partner_uuid, 
        skip=skip, 
        limit=limit
    )
    
    # Convert to response format
    response_settlements = []
    for settlement in settlements:
        response_settlements.append(
            SettlementResponse(
                id=settlement.id,
                partner_id=settlement.partner_id,
                amount=settlement.amount,
                previous_debt=settlement.previous_debt,
                remaining_debt=settlement.remaining_debt,
                reason=settlement.reason,
                settled_by=settlement.settled_by,
                notes=settlement.notes,
                created_at=settlement.created_at,
                partner_name=settlement.partner.name if settlement.partner else None
            )
        )
    
    return response_settlements