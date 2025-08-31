from typing import List, Optional, Dict, Any
from pydantic import BaseModel, UUID4, ConfigDict
from datetime import datetime
from decimal import Decimal


class OrderItemBase(BaseModel):
    sku_id: UUID4
    quantity: int
    unit_price: Decimal
    total_price: Decimal


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemUpdate(BaseModel):
    quantity: Optional[int] = None
    unit_price: Optional[Decimal] = None
    total_price: Optional[Decimal] = None


class OrderItem(OrderItemBase):
    id: UUID4
    order_id: UUID4
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class OrderBase(BaseModel):
    order_number: str
    platform_id: Optional[UUID4] = None
    customer_info: Optional[Dict[str, Any]] = None
    total_amount: Decimal
    status: Optional[str] = "pending"


class OrderCreate(OrderBase):
    items: List[OrderItemCreate] = []


class OrderUpdate(BaseModel):
    order_number: Optional[str] = None
    platform_id: Optional[UUID4] = None
    customer_info: Optional[Dict[str, Any]] = None
    total_amount: Optional[Decimal] = None
    status: Optional[str] = None


class OrderItemResponse(OrderItemBase):
    id: UUID4
    order_id: UUID4
    created_at: datetime
    # Additional fields for frontend display
    sku_code: Optional[str] = None
    product_name: Optional[str] = None
    product_id: Optional[UUID4] = None
    partner_name: Optional[str] = None
    partner_id: Optional[UUID4] = None
    
    model_config = ConfigDict(from_attributes=True)


class Order(OrderBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class OrderResponse(OrderBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []
    
    model_config = ConfigDict(from_attributes=True)