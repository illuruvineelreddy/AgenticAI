"""
Historical Market Data Replay Engine
Replays database candle/tick records into Redis Streams at variable speeds.
"""

import asyncio
from datetime import datetime
from sqlalchemy import select
from typing import Dict, List, Any, Optional
import structlog

from database.connection import async_session_factory
from database.models import Candle
from utils.redis_streams import stream_manager

logger = structlog.get_logger()

class ReplayEngine:
    """
    Replays historical candles from database into Redis streams.
    Supports speed control (1x - 100x), pause, resume, and stop.
    """
    
    def __init__(self):
        self.running = False
        self.paused = False
        self.speed = 1.0  # Speed multiplier
        self.symbol = ""
        self.start_date = None
        self.end_date = None
        self.replay_task = None
        
    async def start_replay(self, symbol: str, start: datetime, end: datetime, speed: float = 1.0) -> bool:
        """Starts a replay thread in the background."""
        if self.running:
            logger.info("Replay already running. Stopping previous run.")
            await self.stop_replay()
            
        self.symbol = symbol
        self.start_date = start
        self.end_date = end
        self.speed = speed
        self.running = True
        self.paused = False
        
        self.replay_task = asyncio.create_task(self._replay_loop())
        logger.info("Replay engine task started", symbol=symbol, speed=speed)
        return True
        
    async def pause_replay(self):
        """Pauses the replay loop."""
        self.paused = True
        logger.info("Replay engine paused")
        
    async def resume_replay(self):
        """Resumes the replay loop."""
        self.paused = False
        logger.info("Replay engine resumed")
        
    async def stop_replay(self):
        """Stops the replay loop."""
        self.running = False
        self.paused = False
        if self.replay_task:
            self.replay_task.cancel()
            try:
                await self.replay_task
            except asyncio.CancelledError:
                pass
            self.replay_task = None
        logger.info("Replay engine stopped")

    async def get_status(self) -> Dict[str, Any]:
        """Returns the current state of the replay engine."""
        return {
            'running': self.running,
            'paused': self.paused,
            'speed': self.speed,
            'symbol': self.symbol,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None
        }

    async def _replay_loop(self):
        """Internal loop to fetch and stream candles."""
        try:
            # 1. Fetch candles
            async with async_session_factory() as session:
                stmt = (
                    select(Candle)
                    .where(
                        Candle.symbol == self.symbol,
                        Candle.interval == '5m',
                        Candle.timestamp >= self.start_date,
                        Candle.timestamp <= self.end_date
                    )
                    .order_by(Candle.timestamp.asc())
                )
                res = await session.execute(stmt)
                db_candles = res.scalars().all()

            if not db_candles:
                logger.warn("Replay engine found no candles to stream", symbol=self.symbol)
                self.running = False
                return

            logger.info("Replay engine loaded candles for streaming", count=len(db_candles))

            # Base delay between 5m candles (e.g. 5 seconds in real simulation)
            # 5 seconds at 1x speed, 0.5s at 10x, 0.05s at 100x
            base_delay = 2.0

            for idx, c in enumerate(db_candles):
                # Handle stop / cancel
                if not self.running:
                    break

                # Handle pause
                while self.paused:
                    await asyncio.sleep(0.5)
                    if not self.running:
                        break

                # Stream current candle
                candle_dict = {
                    'symbol': c.symbol,
                    'exchange': c.exchange,
                    'interval': c.interval,
                    'open': float(c.open),
                    'high': float(c.high),
                    'low': float(c.low),
                    'close': float(c.close),
                    'volume': int(c.volume),
                    'timestamp': c.timestamp.isoformat()
                }

                # Publish to CANDLES_5M stream (as if from CandleEngine)
                await stream_manager.publish(
                    stream_name=stream_manager.STREAMS['CANDLES_5M'],
                    event_type='candle_complete',
                    data=candle_dict,
                    source_agent='replay_engine'
                )

                # Send update to WebSockets
                from websocket.manager import ws_manager
                await ws_manager.send_candle_update(
                    symbol=c.symbol,
                    interval=c.interval,
                    data=candle_dict
                )

                # Sleep adjusted by speed
                delay = base_delay / self.speed
                await asyncio.sleep(delay)

            logger.info("Replay engine completed streaming all records")
            self.running = False
            
        except asyncio.CancelledError:
            logger.info("Replay engine task cancelled")
        except Exception as e:
            logger.error("Error in replay engine loop", error=str(e))
            self.running = False

# Global instance
replay_engine = ReplayEngine()
