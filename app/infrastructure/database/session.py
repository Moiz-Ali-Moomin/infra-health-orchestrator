from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings

# Global async Postgres engine mapping to asyncpg
engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False
)

async def init_db():
    from app.infrastructure.database.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
