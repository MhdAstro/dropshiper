from sqlalchemy import Column, String, DateTime, DECIMAL, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    order_number = Column(String(255), unique=True, nullable=False)
    platform_id = Column(String(36), ForeignKey("platforms.id"))
    customer_info = Column(JSON)
    total_amount = Column(DECIMAL(10, 2))
    status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    platform = relationship("Platform")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"))
    sku_id = Column(String(36), ForeignKey("sku.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(10, 2))
    total_price = Column(DECIMAL(10, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="items")
    sku = relationship("SKU", back_populates="order_items")