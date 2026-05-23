"""
Database Connection and Initialization
Handles PostgreSQL + TimescaleDB connections
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import structlog

from utils.config import settings
from database.models import Base

logger = structlog.get_logger()

# Global engine and session factories
engine = None
async_session_factory = None
sync_engine = None
sync_session_factory = None


async def init_db():
    """Initialize database connection and create tables."""
    global engine, async_session_factory, sync_engine, sync_session_factory
    
    logger.info("Initializing database connection", url=settings.database_url)
    
    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=settings.log_level == "DEBUG",
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
    )
    
    # Create async session factory
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    # Create sync engine for migrations
    sync_engine = create_engine(
        settings.sync_database_url,
        echo=settings.log_level == "DEBUG",
        pool_pre_ping=True,
    )
    
    sync_session_factory = sessionmaker(
        bind=sync_engine,
        autocommit=False,
        autoflush=False,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created successfully")
    
    # Create TimescaleDB hypertables (if extension is available)
    await setup_timescaledb()


async def setup_timescaledb():
    """Setup TimescaleDB hypertables for time-series data."""
    async with engine.begin() as conn:
        try:
            # Enable TimescaleDB extension
            await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE"))
            logger.info("TimescaleDB extension enabled")
            
            # Convert ticks table to hypertable
            await conn.execute(sa.text("""
                SELECT create_hypertable('ticks', 'timestamp', if_not_exists => TRUE)
            """))
            logger.info("Ticks hypertable created")
            
            # Convert candles table to hypertable
            await conn.execute(sa.text("""
                SELECT create_hypertable('candles', 'timestamp', if_not_exists => TRUE)
            """))
            logger.info("Candles hypertable created")
            
            # Add compression policies (optional, for older data)
            # await conn.execute(sa.text("""
            #     ALTER TABLE ticks SET (
            #         timescaledb.compress,
            #         timescaledb.compress_segmentby = 'symbol'
            #     )
            # """))
            
        except Exception as e:
            logger.warning("TimescaleDB setup warning", error=str(e))


async def get_db_session() -> AsyncSession:
    """Get database session for dependency injection."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db_session():
    """Get synchronous database session."""
    return sync_session_factory()


async def close_db():
    """Close database connections."""
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")


# Import sa for text queries
import sqlalchemy as sa
from sqlalchemy import create_engine
