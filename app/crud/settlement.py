from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
import uuid

from app.crud.base import CRUDBase
from app.models.settlement import Settlement
from app.models.partner import Partner
from app.schemas.settlement import SettlementCreate, SettlementResponse


class CRUDSettlement(CRUDBase[Settlement, SettlementCreate, dict]):
    
    async def get_by_partner(
        self,
        db: AsyncSession,
        *,
        partner_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Settlement]:
        """Get settlements for a specific partner"""
        result = await db.execute(
            select(Settlement)
            .where(Settlement.partner_id == partner_id)
            .order_by(desc(Settlement.created_at))
            .offset(skip)
            .limit(limit)
            .options(selectinload(Settlement.partner))
        )
        return result.scalars().all()
    
    async def get_with_partner_details(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Settlement]:
        """Get settlements with partner details"""
        result = await db.execute(
            select(Settlement)
            .order_by(desc(Settlement.created_at))
            .offset(skip)
            .limit(limit)
            .options(selectinload(Settlement.partner))
        )
        return result.scalars().all()
    
    async def create_settlement_record(
        self,
        db: AsyncSession,
        *,
        partner_id: uuid.UUID,
        amount: float,
        previous_debt: float,
        remaining_debt: float,
        reason: Optional[str] = None,
        settled_by: str = "system"
    ) -> Settlement:
        """Create a settlement record"""
        settlement_data = SettlementCreate(
            partner_id=partner_id,
            amount=amount,
            previous_debt=previous_debt,
            remaining_debt=remaining_debt,
            reason=reason,
            settled_by=settled_by
        )
        
        db_obj = Settlement(**settlement_data.dict())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        
        # Load the partner relationship
        await db.refresh(db_obj, ["partner"])
        
        return db_obj


settlement_crud = CRUDSettlement(Settlement)