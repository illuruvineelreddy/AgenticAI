import pytest
import asyncio
import time
import os
from typing import Dict, Any, List, Callable
from unittest.mock import MagicMock, AsyncMock, patch

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base
from utils.config import settings

# --- MOCK REDIS STREAM MANAGER ---
class MockRedisStreamManager:
    """Mock RedisStreamManager that runs in-memory without Redis connection."""
    STREAMS = {
        'MARKET_TICKS': 'market_ticks',
        'CANDLES_1M': 'candles_1m',
        'CANDLES_5M': 'candles_5m',
        'FEATURES': 'features_stream',
        'REGIME': 'regime_stream',
        'STRATEGY_SIGNALS': 'strategy_signals',
        'RISK_APPROVED': 'risk_approved_signals',
        'EXECUTION_ORDERS': 'execution_orders',
        'EXECUTION_UPDATES': 'execution_updates',
        'ALERTS': 'alerts_stream',
    }

    def __init__(self):
        self.published = []
        self.callbacks = {}
        self.running = True

    async def connect(self):
        return True

    async def disconnect(self):
        self.running = False
        return True

    async def publish(self, stream_name: str, event_type: str, data: Dict[str, Any], source_agent: str) -> str:
        msg_id = f"MOCK_MSG_{int(time.time() * 1000)}"
        message = {
            "stream_name": stream_name,
            "event_type": event_type,
            "timestamp": time.time(),
            "data": data,
            "source_agent": source_agent,
            "message_id": msg_id
        }
        self.published.append(message)
        
        # Trigger subscription callbacks asynchronously
        if stream_name in self.callbacks:
            for cb in self.callbacks[stream_name]:
                asyncio.create_task(cb(message))
        
        return msg_id

    async def subscribe(self, stream_name: str, callback: Callable, consumer_group=None, consumer_name=None, batch_size=1):
        if stream_name not in self.callbacks:
            self.callbacks[stream_name] = []
        self.callbacks[stream_name].append(callback)


# Instantiate and patch stream_manager globally at the top level
global_mock_stream_manager = MockRedisStreamManager()
import utils.redis_streams
utils.redis_streams.stream_manager = global_mock_stream_manager

# Setup a shared file-based SQLite database for tests
DB_FILE = "test_astra.db"
if os.path.exists(DB_FILE):
    try:
        os.remove(DB_FILE)
    except Exception:
        pass

sqlite_async_url = f"sqlite+aiosqlite:///{DB_FILE}"
sqlite_sync_url = f"sqlite:///{DB_FILE}"

async_engine_instance = create_async_engine(sqlite_async_url, echo=False)
sync_engine_instance = create_engine(sqlite_sync_url, echo=False)

# Create all tables at module scope synchronously
Base.metadata.create_all(sync_engine_instance)

# Bind the global database.connection objects at startup (before strategy agents get imported)
import database.connection
database.connection.engine = async_engine_instance
database.connection.sync_engine = sync_engine_instance

test_async_session_factory = async_sessionmaker(
    async_engine_instance,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)
test_sync_session_factory = sessionmaker(
    bind=sync_engine_instance,
    autocommit=False,
    autoflush=False
)

database.connection.async_session_factory = test_async_session_factory
database.connection.sync_session_factory = test_sync_session_factory


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    res_loop = policy.new_event_loop()
    yield res_loop
    res_loop.close()


@pytest.fixture(scope="session")
def test_engine():
    """Session-wide async engine for testing database."""
    yield async_engine_instance


@pytest.fixture
async def db_session() -> AsyncSession:
    """Fixture that yields an async database session for a test case."""
    async with test_async_session_factory() as session:
        yield session
        # Rollback changes to keep tests isolated
        await session.rollback()


@pytest.fixture
def mock_stream_manager():
    """Fixture that yields the global MockRedisStreamManager."""
    global_mock_stream_manager.published.clear()
    global_mock_stream_manager.callbacks.clear()
    return global_mock_stream_manager


@pytest.fixture
def sample_candles() -> List[Dict[str, Any]]:
    """Yield a list of mock candles for testing indicators."""
    from datetime import datetime, timedelta
    base_time = datetime.utcnow() - timedelta(hours=10)
    candles = []
    
    # Generate 100 candles of 5-minute intervals
    for i in range(100):
        # Sine wave price with noise
        import math
        price = 100.0 + 10.0 * math.sin(i / 10.0) + (i % 3 - 1) * 0.5
        candles.append({
            "symbol": "RELIANCE",
            "timestamp": (base_time + timedelta(minutes=5 * i)).isoformat(),
            "open": price - 0.2,
            "high": price + 1.0,
            "low": price - 0.9,
            "close": price,
            "volume": 1000 + i * 10
        })
    return candles


# Cleanup database file after all tests complete
@pytest.fixture(scope="session", autouse=True)
def cleanup_db(request):
    def remove_file():
        # Close engines first
        asyncio.run(async_engine_instance.dispose())
        sync_engine_instance.dispose()
        if os.path.exists(DB_FILE):
            try:
                os.remove(DB_FILE)
            except Exception:
                pass
    request.addfinalizer(remove_file)
