from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.database import Base


class InventoryUpdate(Base):
    __tablename__ = "inventory_updates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("sku.id"))
    source_platform_id = Column(UUID(as_uuid=True), ForeignKey("source_platforms.id"))
    old_quantity = Column(Integer)
    new_quantity = Column(Integer)
    update_type = Column(String(50))  # 'manual', 'automatic', 'order_placed'
    reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    sku = relationship("SKU", back_populates="inventory_updates")
    source_platform = relationship("SourcePlatform", back_populates="inventory_updates")