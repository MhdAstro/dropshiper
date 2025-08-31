from sqlalchemy import Column, String, Boolean, DateTime, DECIMAL, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.database import Base
from app.core.types import UUID


class Partner(Base):
    __tablename__ = "partners"

    id = Column(UUID(), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(UUID(), ForeignKey("users.id"), nullable=False, index=True)  # Owner of this partner
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # 'supplier', 'distributor', 'retailer', 'manufacturer', 'wholesaler'
    contact_email = Column(String(255))
    contact_phone = Column(String(50))
    address = Column(Text)
    description = Column(Text)
    
    # Platform and business information
    platform = Column(String(100))  # telegram, instagram, basalam, website, etc.
    platform_address = Column(String(500))  # seller address on that platform
    
    # Financial information
    credit_limit = Column(DECIMAL(15, 2), default=0)  # Credit limit in Toman
    current_debt = Column(DECIMAL(15, 2), default=0)  # Current debt amount
    payment_terms = Column(String(100))  # e.g., "30 days", "immediate", etc.
    settlement_period_days = Column(Integer, default=30)  # Settlement period in days
    
    # Pricing configuration
    profit_percentage = Column(DECIMAL(5, 2), default=0)  # Profit percentage (e.g., 20 for 20%)
    fixed_amount = Column(DECIMAL(12, 2), default=0)  # Fixed amount to add to base price
    price_ending_digit = Column(Integer, default=0)  # Last digit for final prices (e.g., 5000 makes all prices end with 5000)
    
    # API integration
    api_endpoint = Column(String(500))
    api_key = Column(String(255))
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")
    products = relationship("Product", back_populates="partner")
    settlements = relationship("Settlement", back_populates="partner", cascade="all, delete-orphan")