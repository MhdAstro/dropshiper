from sqlalchemy import Column, String, Text, Boolean, DateTime, DECIMAL, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.database import Base
from app.core.types import UUID


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(255))
    brand = Column(String(255))
    partner_id = Column(UUID(), ForeignKey("partners.id"))
    images = Column(JSON)  # Array of image URLs/paths
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    partner = relationship("Partner")
    variants = relationship("Variant", back_populates="product", cascade="all, delete-orphan")
    skus = relationship("SKU", back_populates="product", cascade="all, delete-orphan")