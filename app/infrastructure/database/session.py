import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.infrastructure.database.models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5432/job_radar_db"
)

if "sslmode=" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("sslmode=", "ssl=")

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

if "&channel_binding=require" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("&channel_binding=require", "")
elif "?channel_binding=require" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("?channel_binding=require", "")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)