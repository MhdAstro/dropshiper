from sqlalchemy import Column, String, DECIMAL, DateTime, ForeignKey, Text
from app.core.types import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.database import Base


class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)
    partner_id = Column(UUID(), ForeignKey("partners.id", ondelete="CASCADE"), nullable=False)
    amount = Column(DECIMAL(12, 2), nullable=False)  # Settlement amount
    previous_debt = Column(DECIMAL(12, 2), nullable=False)  # Debt before settlement
    remaining_debt = Column(DECIMAL(12, 2), nullable=False)  # Debt after settlement
    reason = Column(Text)  # Reason for settlement
    settled_by = Column(String(255))  # Who performed the settlement (user/system)
    notes = Column(Text)  # Additional notes
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    partner = relationship("Partner", back_populates="settlements")