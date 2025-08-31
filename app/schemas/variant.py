from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import uuid


class VariantBase(BaseModel):
    product_id: uuid.UUID = Field(..., description="Product ID this variant belongs to")
    type: str = Field(..., min_length=1, max_length=100, description="Variant type (e.g., 'size', 'color', 'material')")
    value: str = Field(..., min_length=1, max_length=255, description="Variant value (e.g., 'Large', 'Red', 'Cotton')")

    @validator('type')
    def validate_type(cls, v):
        allowed_types = ['size', 'color', 'material', 'style', 'pattern', 'weight', 'capacity', 'length']
        if v.lower() not in allowed_types:
            # Allow custom types but provide suggestions
            pass
        return v.lower()


class VariantCreate(VariantBase):
    pass


class VariantUpdate(BaseModel):
    product_id: Optional[uuid.UUID] = None
    type: Optional[str] = Field(None, min_length=1, max_length=100)
    value: Optional[str] = Field(None, min_length=1, max_length=255)

    @validator('type')
    def validate_type(cls, v):
        if v is not None:
            return v.lower()
        return v


class Variant(VariantBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class VariantResponse(Variant):
    product_name: Optional[str] = Field(None, description="Product name")
    
    class Config:
        from_attributes = True


class VariantCombination(BaseModel):
    """For representing variant combinations in SKUs"""
    variants: List[Variant] = Field(..., description="List of variants that make up this combination")
    
    class Config:
        from_attributes = True