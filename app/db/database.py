from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase
import os

from app.core.config import settings


class Base(DeclarativeBase):
    pass


# Debug: Print the DATABASE_URL to see what's being used
database_url = settings.DATABASE_URL
print(f"DATABASE_URL from settings: {database_url}")
print(f"DATABASE_URL from env: {os.getenv('DATABASE_URL', 'Not found')}")

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