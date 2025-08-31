from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.database import Base


class OutputPlatform(Base):
    __tablename__ = "output_platforms"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    platform_id = Column(String(36), ForeignKey("platforms.id"))
    token = Column(String(500))
    refresh_token = Column(String(500))
    last_sync = Column(DateTime(timezone=True))
    sync_interval = Column(Integer, default=1800)  # seconds
    configuration = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")
    platform = relationship("Platform")