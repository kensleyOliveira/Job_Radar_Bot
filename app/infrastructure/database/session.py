import asyncio
import logging
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.infrastructure.database.models import Base

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgrespassword@postgres:5432/job_radar_db"
)

# Motor assíncrono para o PostgreSQL Docker local
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={"timeout": 15}
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db(max_retries: int = 10, delay_seconds: int = 2):
    """Inicializa as tabelas com retentativas até o PostgreSQL local responder."""
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Conectando ao PostgreSQL local (tentativa {attempt}/{max_retries})...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Tabelas criadas com sucesso no PostgreSQL local!")
            return
        except Exception as e:
            logger.warning(f"Tentativa {attempt} falhou: {e}")
            if attempt == max_retries:
                raise
            await asyncio.sleep(delay_seconds)