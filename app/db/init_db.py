from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import engine, Base
from app.models import *  # Import all models


async def init_db() -> None:
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)