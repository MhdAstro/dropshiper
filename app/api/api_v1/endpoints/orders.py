from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.crud.order import order_crud
from app.schemas.order import Order, OrderCreate, OrderUpdate, OrderResponse, OrderItemResponse

router = APIRouter()


@router.get("/", response_model=List[Order])
async def get_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    platform_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all orders with optional filtering"""
    orders = await order_crud.get_all(
        db,
        skip=skip,
        limit=limit,
        status=status,
        platform_id=platform_id,
        date_from=date_from,
        date_to=date_to
    )
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific order by ID with items"""
    # First get the basic order
    order = await order_crud.get_by_id(db, id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # For now, return order without items since we might not have order items in the database yet
    # In a real implementation, this would fetch the order items and enrich them with product/partner info
    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        platform_id=order.platform_id,
        customer_info=order.customer_info,
        total_amount=order.total_amount,
        status=order.status,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=[]  # Empty for now - would be populated with real order items
    )


@router.post("/", response_model=Order)
async def create_order(order_in: OrderCreate, db: AsyncSession = Depends(get_db)):
    """Create a new order"""
    # Check if order_number already exists
    existing_order = await order_crud.get_by_order_number(db, order_number=order_in.order_number)
    if existing_order:
        raise HTTPException(status_code=400, detail="Order number already exists")
    
    order = await order_crud.create(db=db, obj_in=order_in)
    return order


@router.put("/{order_id}", response_model=Order)
async def update_order(order_id: str, order_in: OrderUpdate, db: AsyncSession = Depends(get_db)):
    """Update an existing order"""
    order = await order_crud.get_by_id(db, id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order = await order_crud.update(db=db, db_obj=order, obj_in=order_in)
    return order


@router.patch("/{order_id}/status", response_model=Order)
async def update_order_status(order_id: str, status_update: dict, db: AsyncSession = Depends(get_db)):
    """Update order status"""
    status = status_update.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="Status is required")
    
    order = await order_crud.update_status(db, id=order_id, status=status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.delete("/{order_id}")
async def delete_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an order"""
    order = await order_crud.get_by_id(db, id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    await order_crud.remove(db=db, id=order_id)
    return {"message": "Order deleted successfully"}