from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
import uuid


class PricingRuleBase(BaseModel):
    rule_name: str = Field(..., min_length=1, max_length=255, description="Name of the pricing rule")
    rule_type: str = Field(..., description="Type of rule: percentage, fixed_amount, or custom")
    rule_value: Optional[Decimal] = Field(None, description="Rule value (percentage or fixed amount)")
    min_quantity: int = Field(1, ge=1, description="Minimum quantity for rule to apply")
    max_quantity: Optional[int] = Field(None, description="Maximum quantity for rule to apply")
    category_filter: Optional[str] = Field(None, description="Product category filter (optional)")
    product_filter: Optional[Dict[str, Any]] = Field(None, description="Product filter criteria (JSON)")
    priority: int = Field(0, description="Rule priority (higher number = higher priority)")
    is_active: bool = Field(True, description="Whether the rule is active")
    valid_from: Optional[datetime] = Field(None, description="Rule valid from date")
    valid_until: Optional[datetime] = Field(None, description="Rule valid until date")

    @validator('rule_type')
    def validate_rule_type(cls, v):
        allowed_types = ['percentage', 'fixed_amount', 'custom']
        if v not in allowed_types:
            raise ValueError(f'Rule type must be one of: {", ".join(allowed_types)}')
        return v

    @validator('rule_value')
    def validate_rule_value(cls, v, values):
        rule_type = values.get('rule_type')
        if rule_type in ['percentage', 'fixed_amount'] and v is None:
            raise ValueError(f'Rule value is required for {rule_type} rule type')
        return v

    @validator('max_quantity')
    def validate_max_quantity(cls, v, values):
        min_quantity = values.get('min_quantity', 1)
        if v is not None and v < min_quantity:
            raise ValueError('Maximum quantity must be greater than minimum quantity')
        return v


class PricingRuleCreate(PricingRuleBase):
    partner_id: uuid.UUID = Field(..., description="Partner ID this rule belongs to")


class PricingRuleUpdate(BaseModel):
    rule_name: Optional[str] = Field(None, min_length=1, max_length=255)
    rule_type: Optional[str] = None
    rule_value: Optional[Decimal] = None
    min_quantity: Optional[int] = Field(None, ge=1)
    max_quantity: Optional[int] = None
    category_filter: Optional[str] = None
    product_filter: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    @validator('rule_type')
    def validate_rule_type(cls, v):
        if v is not None:
            allowed_types = ['percentage', 'fixed_amount', 'custom']
            if v not in allowed_types:
                raise ValueError(f'Rule type must be one of: {", ".join(allowed_types)}')
        return v


class PricingRule(PricingRuleBase):
    id: uuid.UUID
    partner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PricingRuleResponse(PricingRule):
    partner_name: Optional[str] = Field(None, description="Partner name")
    
    class Config:
        from_attributes = True


class PriceCalculationRequest(BaseModel):
    sku_id: uuid.UUID = Field(..., description="SKU ID to calculate price for")
    cost_price: Decimal = Field(..., gt=0, description="Cost price")
    quantity: int = Field(1, ge=1, description="Quantity")


class PriceCalculationResponse(BaseModel):
    sku_id: uuid.UUID
    cost_price: Decimal
    calculated_price: Decimal
    applied_rules: list[str] = Field([], description="List of applied rule names")
    markup_percentage: Optional[Decimal] = Field(None, description="Total markup percentage")
    markup_amount: Optional[Decimal] = Field(None, description="Total markup amount")