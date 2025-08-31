from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime
import uuid


class SettlementBase(BaseModel):
    partner_id: uuid.UUID = Field(..., description="Partner ID for settlement")
    amount: Decimal = Field(..., gt=0, description="Settlement amount")
    reason: Optional[str] = Field(None, description="Reason for settlement")
    settled_by: Optional[str] = Field(None, description="Who performed the settlement")
    notes: Optional[str] = Field(None, description="Additional notes")


class SettlementCreate(SettlementBase):
    previous_debt: Decimal = Field(..., description="Debt before settlement")
    remaining_debt: Decimal = Field(..., description="Debt after settlement")


class SettlementResponse(SettlementBase):
    id: uuid.UUID
    previous_debt: Decimal
    remaining_debt: Decimal
    created_at: datetime
    partner_name: Optional[str] = Field(None, description="Partner name")

    class Config:
        from_attributes = True