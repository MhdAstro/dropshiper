from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional
from decimal import Decimal
from datetime import datetime
import uuid


class PartnerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Partner name")
    type: str = Field(..., description="Partner type")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Contact phone")
    address: Optional[str] = Field(None, description="Partner address")
    description: Optional[str] = Field(None, description="Partner description")
    
    # Platform and business information
    platform: Optional[str] = Field(None, max_length=100, description="Platform type (telegram, instagram, basalam, website, etc.)")
    platform_address: Optional[str] = Field(None, max_length=500, description="Seller address on the platform")
    
    # Financial fields
    credit_limit: Optional[Decimal] = Field(0, ge=0, description="Credit limit in Toman")
    payment_terms: Optional[str] = Field(None, max_length=100, description="Payment terms")
    settlement_period_days: Optional[int] = Field(30, ge=1, description="Settlement period in days")
    
    # Pricing configuration
    profit_percentage: Optional[Decimal] = Field(0, ge=0, description="Profit percentage (e.g., 20 for 20%)")
    fixed_amount: Optional[Decimal] = Field(0, ge=0, description="Fixed amount to add to base price")
    price_ending_digit: Optional[int] = Field(0, ge=0, description="Last digit for final prices (e.g., 5000 makes prices end with 5000)")
    
    # API integration
    api_endpoint: Optional[str] = Field(None, max_length=500, description="API endpoint for integration")
    api_key: Optional[str] = Field(None, max_length=255, description="API key for authentication")
    is_active: bool = Field(True, description="Whether partner is active")

    @validator('type')
    def validate_partner_type(cls, v):
        allowed_types = ['supplier', 'distributor', 'retailer', 'manufacturer', 'wholesaler']
        if v.lower() not in allowed_types:
            raise ValueError(f'Partner type must be one of: {", ".join(allowed_types)}')
        return v.lower()

    @validator('contact_phone')
    def validate_phone(cls, v):
        if v is not None:
            # Basic phone validation - remove spaces and check if it's numeric
            clean_phone = v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if not clean_phone.replace('+', '').isdigit():
                raise ValueError('Phone number must contain only digits, spaces, hyphens, parentheses, and plus sign')
        return v


class PartnerCreate(PartnerBase):
    pass


class PartnerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    description: Optional[str] = None
    platform: Optional[str] = Field(None, max_length=100)
    platform_address: Optional[str] = Field(None, max_length=500)
    credit_limit: Optional[Decimal] = Field(None, ge=0)
    current_debt: Optional[Decimal] = Field(None)
    payment_terms: Optional[str] = Field(None, max_length=100)
    settlement_period_days: Optional[int] = Field(None, ge=1)
    profit_percentage: Optional[Decimal] = Field(None, ge=0)
    fixed_amount: Optional[Decimal] = Field(None, ge=0)
    price_ending_digit: Optional[int] = Field(None, ge=0)
    api_endpoint: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None

    @validator('type')
    def validate_partner_type(cls, v):
        if v is not None:
            allowed_types = ['supplier', 'distributor', 'retailer', 'manufacturer', 'wholesaler']
            if v.lower() not in allowed_types:
                raise ValueError(f'Partner type must be one of: {", ".join(allowed_types)}')
            return v.lower()
        return v

    @validator('contact_phone')
    def validate_phone(cls, v):
        if v is not None:
            clean_phone = v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if not clean_phone.replace('+', '').isdigit():
                raise ValueError('Phone number must contain only digits, spaces, hyphens, parentheses, and plus sign')
        return v


class Partner(PartnerBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PartnerResponse(Partner):
    # Platform and business information
    platform: Optional[str] = Field(None, description="Platform type")
    platform_address: Optional[str] = Field(None, description="Platform address")
    
    # Financial information  
    settlement_period_days: Optional[int] = Field(30, description="Settlement period in days")
    
    # Pricing configuration
    profit_percentage: Optional[Decimal] = Field(0, description="Profit percentage")
    fixed_amount: Optional[Decimal] = Field(0, description="Fixed amount to add")
    price_ending_digit: Optional[int] = Field(0, description="Price ending digit")
    
    # Statistics
    products_count: int = Field(0, description="Number of products from this partner")
    total_orders: int = Field(0, description="Total number of orders")
    pending_orders: int = Field(0, description="Number of pending orders")
    completed_orders: int = Field(0, description="Number of completed orders")
    total_order_value: Optional[Decimal] = Field(0, description="Total value of all orders")
    current_debt: Optional[Decimal] = Field(0, description="Current debt amount")
    
    class Config:
        from_attributes = True


class PartnerDetailResponse(PartnerResponse):
    """Detailed partner response with additional financial info"""
    platform: Optional[str] = Field(None, description="Platform type")
    platform_address: Optional[str] = Field(None, description="Platform address")
    credit_limit: Optional[Decimal] = Field(0, description="Credit limit in Toman")
    payment_terms: Optional[str] = Field(None, description="Payment terms")
    settlement_period_days: Optional[int] = Field(30, description="Settlement period in days")
    profit_percentage: Optional[Decimal] = Field(0, description="Profit percentage")
    fixed_amount: Optional[Decimal] = Field(0, description="Fixed amount to add")
    price_ending_digit: Optional[int] = Field(0, description="Price ending digit")
    last_order_date: Optional[datetime] = Field(None, description="Date of last order")
    average_order_value: Optional[Decimal] = Field(0, description="Average order value")
    
    class Config:
        from_attributes = True