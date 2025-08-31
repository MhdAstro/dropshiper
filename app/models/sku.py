from sqlalchemy import Column, String, Integer, Boolean, DateTime, DECIMAL, ForeignKey, Table
from app.core.types import UUID
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.database import Base

# Association table for many-to-many relationship between SKU and Variant
sku_variant_association = Table(
    'sku_variants',
    Base.metadata,
    Column('sku_id', String(36), ForeignKey('sku.id', ondelete="CASCADE"), primary_key=True),
    Column('variant_id', String(36), ForeignKey('variants.id', ondelete="CASCADE"), primary_key=True)
)


class SKU(Base):
    __tablename__ = "sku"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    sku_code = Column(String(255), unique=True, nullable=False)
    
    # New fields from requirements
    size = Column(String(100))  # Size variant (e.g., "L", "XL", "38", "42")
    color = Column(String(100))  # Color variant (e.g., "آبی", "قرمز", "سفید")
    base_price = Column(DECIMAL(12, 2))  # Base price from supplier
    final_price = Column(DECIMAL(12, 2))  # Calculated final price after formulas
    inventory = Column(Integer, default=0)  # Stock quantity
    link = Column(String(500))  # Product link URL
    
    # Existing fields (keeping for backward compatibility)
    quantity = Column(Integer, default=0)  # Alias for inventory
    price = Column(DECIMAL(10, 2))  # Legacy price field
    cost_price = Column(DECIMAL(10, 2))  # Alias for base_price
    weight = Column(DECIMAL(8, 2))
    dimensions = Column(JSON)  # Store length, width, height as JSON
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    product = relationship("Product", back_populates="skus")
    variants = relationship("Variant", secondary=sku_variant_association, back_populates="skus")
    mappings = relationship("SKUMapping", back_populates="sku", cascade="all, delete-orphan")
    inventory_updates = relationship("InventoryUpdate", back_populates="sku")
    order_items = relationship("OrderItem", back_populates="sku")
    
    async def calculate_selling_price(self, db_session, quantity: int = 1) -> float:
        """Calculate selling price based on cost_price and partner pricing rules"""
        from app.services.pricing_service import PricingService
        
        if not self.cost_price:
            return 0.0
            
        pricing_service = PricingService(db_session)
        return await pricing_service.calculate_price(
            sku_id=str(self.id),
            cost_price=float(self.cost_price),
            quantity=quantity
        )