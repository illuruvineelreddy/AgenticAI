"""
Candle Engine - Builds candles from ticks
Supports multiple timeframes: 1m, 5m, 15m, 1h, 1d
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import structlog

from utils.redis_streams import stream_manager
from utils.config import settings

logger = structlog.get_logger()


@dataclass
class Candle:
    """OHLCV Candle structure."""
    symbol: str
    exchange: str
    interval: str
    open: float = 0.0
    high: float = 0.0
    low: float = float('inf')
    close: float = 0.0
    volume: int = 0
    oi: int = 0
    timestamp: float = 0.0
    trades: int = 0
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'exchange': self.exchange,
            'interval': self.interval,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'oi': self.oi,
            'timestamp': self.timestamp,
            'trades': self.trades,
        }


@dataclass
class CandleBuilder:
    """Builds a single candle from ticks."""
    symbol: str
    exchange: str
    interval: str
    interval_seconds: int
    current_candle: Optional[Candle] = None
    last_close_time: float = 0.0
    
    def _get_candle_open_time(self, timestamp: float) -> float:
        """Get the open time for the candle containing this timestamp."""
        dt = datetime.fromtimestamp(timestamp)
        open_time = dt.replace(
            minute=(dt.minute // (self.interval_seconds // 60)) * (self.interval_seconds // 60),
            second=0,
            microsecond=0,
        )
        return open_time.timestamp()
    
    def add_tick(self, tick: dict) -> Optional[Candle]:
        """
        Add a tick to the candle builder.
        Returns completed candle if a new candle started.
        """
        tick_time = tick.get('timestamp', asyncio.get_event_loop().time())
        price = tick.get('price', 0.0)
        volume = tick.get('volume', 0)
        
        candle_open_time = self._get_candle_open_time(tick_time)
        
        # Check if we need to close the current candle
        completed_candle = None
        if self.current_candle and candle_open_time > self.last_close_time:
            completed_candle = self.current_candle
            self.current_candle = None
        
        # Start new candle if needed
        if not self.current_candle:
            self.current_candle = Candle(
                symbol=self.symbol,
                exchange=self.exchange,
                interval=self.interval,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=volume,
                timestamp=candle_open_time,
                trades=1,
            )
            self.last_close_time = candle_open_time
        else:
            # Update existing candle
            self.current_candle.high = max(self.current_candle.high, price)
            self.current_candle.low = min(self.current_candle.low, price)
            self.current_candle.close = price
            self.current_candle.volume += volume
            self.current_candle.trades += 1
        
        return completed_candle
    
    def get_current_candle(self) -> Optional[Candle]:
        """Get the current incomplete candle."""
        return self.current_candle


class CandleEngine:
    """
    Candle Engine - Builds candles from tick data.
    
    Responsibilities:
    - Subscribe to tick stream
    - Build candles for multiple timeframes
    - Publish completed candles to Redis Streams
    - Maintain candle state in memory
    """
    
    SUPPORTED_INTERVALS = {
        '1m': 60,
        '5m': 300,
        '15m': 900,
        '30m': 1800,
        '1h': 3600,
        '1d': 86400,
    }
    
    def __init__(self):
        self.running = False
        self.builders: Dict[str, Dict[str, CandleBuilder]] = {}  # symbol -> interval -> builder
        self.candle_callbacks = []
        
    async def run(self):
        """Main engine loop."""
        self.running = True
        logger.info("Candle Engine starting")
        
        # Connect to Redis
        await stream_manager.connect()
        
        # Subscribe to tick stream
        await stream_manager.subscribe(
            stream_name=stream_manager.STREAMS['MARKET_TICKS'],
            callback=self._on_tick,
            consumer_group='candle_engine',
            consumer_name='candle_builder_1',
        )
        
        # Keep running
        while self.running:
            await asyncio.sleep(1)
    
    async def _on_tick(self, message: dict):
        """Process incoming tick message."""
        try:
            tick_data = message.get('data', {})
            symbol = tick_data.get('symbol')
            
            if not symbol:
                return
            
            # Initialize builders for symbol if needed
            if symbol not in self.builders:
                self.builders[symbol] = {}
                for interval, seconds in self.SUPPORTED_INTERVALS.items():
                    self.builders[symbol][interval] = CandleBuilder(
                        symbol=symbol,
                        exchange=tick_data.get('exchange', 'NSE'),
                        interval=interval,
                        interval_seconds=seconds,
                    )
            
            # Process tick for each interval
            for interval, builder in self.builders[symbol].items():
                completed_candle = builder.add_tick(tick_data)
                
                if completed_candle:
                    # Publish completed candle
                    await self._publish_candle(completed_candle)
                    
                    # Update current candle to frontend
                    current = builder.get_current_candle()
                    if current:
                        await self._send_candle_update(current)
                        
        except Exception as e:
            logger.error("Error processing tick", error=str(e))
    
    async def _publish_candle(self, candle: Candle):
        """Publish completed candle to Redis Stream."""
        stream_map = {
            '1m': stream_manager.STREAMS['CANDLES_1M'],
            '5m': stream_manager.STREAMS['CANDLES_5M'],
        }
        
        stream_name = stream_map.get(candle.interval)
        if stream_name:
            try:
                await stream_manager.publish(
                    stream_name=stream_name,
                    event_type='candle_complete',
                    data=candle.to_dict(),
                    source_agent='candle_engine',
                )
                logger.debug(
                    "Published candle",
                    symbol=candle.symbol,
                    interval=candle.interval,
                    close=candle.close,
                )
            except Exception as e:
                logger.error("Failed to publish candle", error=str(e))
    
    async def _send_candle_update(self, candle: Candle):
        """Send candle update to WebSocket clients."""
        from websocket.manager import ws_manager
        
        try:
            await ws_manager.send_candle_update(
                symbol=candle.symbol,
                interval=candle.interval,
                data=candle.to_dict(),
            )
        except Exception as e:
            logger.error("Failed to send candle update", error=str(e))
    
    def register_callback(self, callback):
        """Register callback for candle updates."""
        self.candle_callbacks.append(callback)
    
    async def stop(self):
        """Stop the candle engine."""
        self.running = False
        logger.info("Candle Engine stopping")


# Global instance
candle_engine = CandleEngine()
