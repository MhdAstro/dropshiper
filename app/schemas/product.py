from pydantic import BaseModel, Field, validator
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
import uuid


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    category: Optional[str] = Field(None, max_length=255, description="Product category")
    brand: Optional[str] = Field(None, max_length=255, description="Product brand")
    partner_id: uuid.UUID = Field(..., description="Partner (supplier) ID - required")
    images: Optional[List[str]] = Field([], description="List of image URLs/paths")
    is_active: bool = Field(True, description="Whether product is active")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=255)
    brand: Optional[str] = Field(None, max_length=255)
    partner_id: Optional[uuid.UUID] = None
    images: Optional[List[str]] = None
    is_active: Optional[bool] = None


class Product(ProductBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductResponse(Product):
    partner_name: Optional[str] = Field(None, description="Partner name")
    variants_count: int = Field(0, description="Number of variants")
    skus_count: int = Field(0, description="Number of SKUs")

    class Config:
        from_attributes = True


class BatchUpdateProduct(BaseModel):
    """Schema for batch updating products"""
    ids: List[uuid.UUID] = Field(..., description="List of product IDs to update")
    update_data: ProductUpdate = Field(..., description="Data to update for all selected products")


class BatchUpdateResponse(BaseModel):
    """Response for batch update operations"""
    updated_count: int = Field(..., description="Number of products successfully updated")
    failed_ids: List[uuid.UUID] = Field([], description="IDs of products that failed to update")
    errors: List[str] = Field([], description="List of error messages")