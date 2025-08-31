from typing import List, Optional, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import selectinload
import uuid

from app.crud.base import CRUDBase
from app.models.order import Order, OrderItem
from app.schemas.order import OrderCreate, OrderUpdate


class OrderCRUD(CRUDBase[Order, OrderCreate, OrderUpdate]):
    async def get_all(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        platform_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Order]:
        query = select(self.model)
        
        filters = []
        
        if status:
            filters.append(Order.status == status)
        if platform_id:
            filters.append(Order.platform_id == platform_id)
        if date_from:
            filters.append(Order.created_at >= date_from)
        if date_to:
            filters.append(Order.created_at <= date_to)
        
        if filters:
            query = query.filter(and_(*filters))
        
        query = query.order_by(desc(Order.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_by_id(self, db: AsyncSession, id: Union[str, uuid.UUID]) -> Optional[Order]:
        if isinstance(id, str):
            id = uuid.UUID(id)
        query = select(self.model).filter(Order.id == id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_order_number(self, db: AsyncSession, order_number: str) -> Optional[Order]:
        query = select(self.model).filter(Order.order_number == order_number)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def update_status(self, db: AsyncSession, *, id: Union[str, uuid.UUID], status: str) -> Optional[Order]:
        order = await self.get_by_id(db, id=id)
        if order:
            order.status = status
            db.add(order)
            await db.commit()
            await db.refresh(order)
        return order


order_crud = OrderCRUD(Order)