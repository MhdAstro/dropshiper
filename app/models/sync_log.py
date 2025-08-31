from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.database import Base


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    platform_id = Column(UUID(as_uuid=True), ForeignKey("platforms.id"))
    sync_type = Column(String(50))  # 'inventory', 'price', 'product'
    status = Column(String(50))  # 'success', 'error', 'partial'
    records_processed = Column(Integer)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    platform = relationship("Platform")