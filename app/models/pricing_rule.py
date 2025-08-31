from sqlalchemy import Column, String, Boolean, DateTime, DECIMAL, Integer, ForeignKey, Text
from sqlalchemy import JSON
from app.core.types import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.database import Base


class PricingRule(Base):
    __tablename__ = "pricing_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    partner_id = Column(String(36), ForeignKey("partners.id"))
    rule_name = Column(String(255), nullable=False)
    rule_type = Column(String(50), nullable=False)  # 'percentage', 'fixed_amount', 'custom'
    rule_value = Column(DECIMAL(10, 4))  # percentage or fixed amount
    min_quantity = Column(Integer, default=1)
    max_quantity = Column(Integer)
    category_filter = Column(String(255))
    product_filter = Column(JSON)
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    valid_from = Column(DateTime(timezone=True), server_default=func.now())
    valid_until = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    partner = relationship("Partner")