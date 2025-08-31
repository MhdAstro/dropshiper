from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase
import os

from app.core.config import settings


class Base(DeclarativeBase):
    pass


# Fix the DATABASE_URL if it's just the hostname
raw_database_url = settings.DATABASE_URL
if raw_database_url == "imp-psql-postgresql-ha.stage-monajjem.svc.cluster.local":
    database_url = "postgresql+asyncpg://imp-psql-postgresql-ha.stage-monajjem.svc.cluster.local:5432/dropshiper_db"
else:
    # Ensure async driver is specified
    if raw_database_url.startswith("postgresql://"):
        database_url = raw_database_url.replace("postgresql://", "postgresql+asyncpg://")
    else:
        database_url = raw_database_url

# Create async engine
engine = create_async_engine(
    database_url,
    echo=settings.DEBUG,
    future=True
)

# Create async session maker
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()