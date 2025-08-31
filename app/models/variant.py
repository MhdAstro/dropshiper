from sqlalchemy import Column, String, DateTime, ForeignKey
from app.core.types import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.database import Base


class Variant(Base):
    __tablename__ = "variants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"))
    type = Column(String(100), nullable=False)  # 'size', 'color', 'material', etc.
    value = Column(String(255), nullable=False)  # 'Large', 'Red', 'Cotton', etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="variants")
    skus = relationship("SKU", secondary="sku_variants", back_populates="variants")