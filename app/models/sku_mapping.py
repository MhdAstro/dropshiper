from sqlalchemy import Column, String, Boolean, DateTime, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.database import Base


class SKUMapping(Base):
    __tablename__ = "sku_mapping"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    sku_id = Column(String(36), ForeignKey("sku.id", ondelete="CASCADE"))
    platform_id = Column(String(36), ForeignKey("platforms.id"))
    external_sku = Column(String(255))
    external_product_id = Column(String(255))
    price_multiplier = Column(DECIMAL(5, 2), default=1.0)
    custom_price = Column(DECIMAL(10, 2))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    sku = relationship("SKU", back_populates="mappings")
    platform = relationship("Platform")