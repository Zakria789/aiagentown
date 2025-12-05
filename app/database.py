"""
Database connection aur session management
SQLAlchemy async engine ke saath
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Database URL ko async format me convert karo
# postgresql:// -> postgresql+asyncpg://
# sqlite:// -> sqlite+aiosqlite://
database_url = settings.DATABASE_URL
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif database_url.startswith("sqlite://"):
    database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

# Async engine banao
engine = create_async_engine(
    database_url,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,  # Connection health check
    pool_recycle=3600,   # 1 hour me connections recycle karo
)

# Alias for backward compatibility
async_engine = engine

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Alias for scheduler service
async_session_maker = AsyncSessionLocal

# Base class for all models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Database session dependency
    FastAPI routes me use karne ke liye
    
    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise
        finally:
            await session.close()


async def init_db():
    """
    Database tables create karta hai
    Production me Alembic use karo, yeh sirf development ke liye hai
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def close_db():
    """
    Database connections ko gracefully close karta hai
    """
    await engine.dispose()
    logger.info("Database connections closed")
