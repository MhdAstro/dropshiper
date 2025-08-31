from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime
import uuid


class SKUBase(BaseModel):
    product_id: uuid.UUID = Field(..., description="Product ID this SKU belongs to")
    sku_code: Optional[str] = Field(None, min_length=1, max_length=255, description="Unique SKU code (auto-generated if not provided)")
    
    # New fields from requirements
    size: Optional[str] = Field(None, max_length=100, description="Size variant (e.g., L, XL, 38, 42)")
    color: Optional[str] = Field(None, max_length=100, description="Color variant (e.g., آبی, قرمز, سفید)")
    base_price: Optional[Decimal] = Field(None, gt=0, description="Base price from supplier")
    final_price: Optional[Decimal] = Field(None, gt=0, description="Final calculated price")
    inventory: int = Field(0, ge=0, description="Stock quantity")
    link: Optional[str] = Field(None, max_length=500, description="Product link URL")
    
    # Legacy fields (keeping for backward compatibility)
    quantity: Optional[int] = Field(None, ge=0, description="Available quantity (alias for inventory)")
    price: Optional[Decimal] = Field(None, gt=0, description="SKU price (legacy)")
    cost_price: Optional[Decimal] = Field(None, gt=0, description="Cost price from supplier (alias for base_price)")
    weight: Optional[Decimal] = Field(None, gt=0, description="Weight in kg")
    dimensions: Optional[Dict[str, float]] = Field(None, description="Dimensions (length, width, height) in cm")
    is_active: bool = Field(True, description="Whether SKU is active")

    @validator('dimensions')
    def validate_dimensions(cls, v):
        if v is not None:
            required_keys = ['length', 'width', 'height']
            if not all(key in v for key in required_keys):
                raise ValueError('Dimensions must include length, width, and height')
            if not all(isinstance(v[key], (int, float)) and v[key] > 0 for key in required_keys):
                raise ValueError('All dimensions must be positive numbers')
        return v


class SKUCreate(SKUBase):
    pass


class SKUUpdate(BaseModel):
    product_id: Optional[uuid.UUID] = None
    sku_code: Optional[str] = Field(None, min_length=1, max_length=255)
    
    # New fields from requirements
    size: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, max_length=100)
    base_price: Optional[Decimal] = Field(None, gt=0)
    final_price: Optional[Decimal] = Field(None, gt=0)
    inventory: Optional[int] = Field(None, ge=0)
    link: Optional[str] = Field(None, max_length=500)
    
    # Legacy fields
    quantity: Optional[int] = Field(None, ge=0)
    price: Optional[Decimal] = Field(None, gt=0)
    cost_price: Optional[Decimal] = Field(None, gt=0)
    weight: Optional[Decimal] = Field(None, gt=0)
    dimensions: Optional[Dict[str, float]] = None
    is_active: Optional[bool] = None

    @validator('dimensions')
    def validate_dimensions(cls, v):
        if v is not None:
            required_keys = ['length', 'width', 'height']
            if not all(key in v for key in required_keys):
                raise ValueError('Dimensions must include length, width, and height')
            if not all(isinstance(v[key], (int, float)) and v[key] > 0 for key in required_keys):
                raise ValueError('All dimensions must be positive numbers')
        return v


class SKU(SKUBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VariantInfo(BaseModel):
    id: uuid.UUID
    type: str
    value: str
    
    class Config:
        from_attributes = True


class SKUResponse(SKU):
    product_name: Optional[str] = Field(None, description="Product name")
    partner_name: Optional[str] = Field(None, description="Partner name")
    variants: List[VariantInfo] = Field([], description="List of variants that make up this SKU")
    low_stock: bool = Field(False, description="Whether this SKU has low stock")
    calculated_selling_price: Optional[Decimal] = Field(None, description="Calculated selling price based on pricing rules")
    
    class Config:
        from_attributes = True