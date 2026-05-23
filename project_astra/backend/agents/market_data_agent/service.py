"""
Market Data Agent - Connects to broker WebSocket and streams market data
Handles: Zerodha Kite, Upstox, Fyers, Dhan
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
import structlog
import json

from utils.config import settings
from utils.redis_streams import stream_manager

logger = structlog.get_logger()


@dataclass
class Tick:
    """Market tick data structure."""
    symbol: str
    exchange: str
    price: float
    volume: int
    bid_price: float
    ask_price: float
    bid_qty: int
    ask_qty: int
    total_buy_qty: int
    total_sell_qty: int
    timestamp: float
    ltp: float
    ohlc: Dict[str, float]


class MarketDataService:
    """
    Market Data Agent - Manages WebSocket connections to brokers.
    
    Responsibilities:
    - Connect to broker WebSocket
    - Subscribe to instruments
    - Receive and validate ticks
    - Publish to Redis Streams
    - Handle reconnections
    - Maintain local symbol state
    """
    
    def __init__(self):
        self.running = False
        self.connected = False
        self.subscribed_symbols: List[str] = []
        self.tick_callbacks: List[Callable] = []
        self.reconnect_delay = 5  # seconds
        self.max_reconnect_attempts = 10
        self.last_tick_time: Dict[str, float] = {}
        
        # Mock mode for development without broker credentials
        self.mock_mode = not settings.broker_api_key
        
    async def run(self):
        """Main service loop."""
        self.running = True
        logger.info("Market Data Service starting", mock_mode=self.mock_mode)
        
        attempt = 0
        while self.running and attempt < self.max_reconnect_attempts:
            try:
                if self.mock_mode:
                    await self._run_mock_mode()
                else:
                    await self._connect_to_broker()
                    
            except asyncio.CancelledError:
                logger.info("Market Data Service cancelled")
                break
            except Exception as e:
                attempt += 1
                logger.error(
                    "Market Data Service error",
                    error=str(e),
                    attempt=attempt,
                    max_attempts=self.max_reconnect_attempts,
                )
                
                if attempt < self.max_reconnect_attempts:
                    logger.info(f"Reconnecting in {self.reconnect_delay}s...")
                    await asyncio.sleep(self.reconnect_delay)
                else:
                    logger.error("Max reconnect attempts reached")
                    if self.running:
                        # Continue in mock mode if broker connection fails
                        logger.warning("Switching to mock mode")
                        self.mock_mode = True
                        await self._run_mock_mode()
    
    async def _connect_to_broker(self):
        """Connect to actual broker WebSocket."""
        logger.info("Connecting to broker WebSocket", broker=settings.broker_name)
        
        # TODO: Implement actual broker WebSocket connections
        # For now, this is a placeholder for future implementation
        
        if settings.broker_name == "zerodha":
            await self._connect_zerodha()
        elif settings.broker_name == "upstox":
            await self._connect_upstox()
        elif settings.broker_name == "fyers":
            await self._connect_fyers()
        elif settings.broker_name == "dhan":
            await self._connect_dhan()
        else:
            raise ValueError(f"Unsupported broker: {settings.broker_name}")
    
    async def _connect_zerodha(self):
        """Connect to Zerodha Kite WebSocket."""
        # Placeholder for Zerodha implementation
        logger.warning("Zerodha WebSocket not yet implemented - using mock mode")
        self.mock_mode = True
    
    async def _connect_upstox(self):
        """Connect to Upstox WebSocket."""
        logger.warning("Upstox WebSocket not yet implemented - using mock mode")
        self.mock_mode = True
    
    async def _connect_fyers(self):
        """Connect to Fyers WebSocket."""
        logger.warning("Fyers WebSocket not yet implemented - using mock mode")
        self.mock_mode = True
    
    async def _connect_dhan(self):
        """Connect to Dhan WebSocket."""
        logger.warning("Dhan WebSocket not yet implemented - using mock mode")
        self.mock_mode = True
    
    async def _run_mock_mode(self):
        """Run in mock/simulation mode for development."""
        logger.info("Running in MOCK MODE - simulating market data")
        self.connected = True
        
        # Use default watchlist
        symbols = settings.watchlist_nifty50[:5]  # Start with 5 symbols
        
        while self.running:
            # Generate simulated ticks for each symbol
            for symbol in symbols:
                if not self.running:
                    break
                    
                tick = self._generate_mock_tick(symbol)
                await self._process_tick(tick)
            
            # Simulate tick frequency (every 500ms)
            await asyncio.sleep(0.5)
    
    def _generate_mock_tick(self, symbol: str) -> Tick:
        """Generate realistic mock tick data."""
        import random
        
        # Base prices for common stocks (approximate)
        base_prices = {
            "RELIANCE": 2500.0,
            "TCS": 3600.0,
            "HDFCBANK": 1600.0,
            "INFY": 1450.0,
            "ICICIBANK": 950.0,
        }
        
        base_price = base_prices.get(symbol, 100.0 + random.random() * 900)
        
        # Add some randomness
        price_change = (random.random() - 0.5) * 2  # -1 to +1
        price = base_price + price_change
        
        return Tick(
            symbol=symbol,
            exchange="NSE",
            price=price,
            volume=random.randint(100, 10000),
            bid_price=price - 0.05,
            ask_price=price + 0.05,
            bid_qty=random.randint(100, 5000),
            ask_qty=random.randint(100, 5000),
            total_buy_qty=random.randint(10000, 100000),
            total_sell_qty=random.randint(10000, 100000),
            timestamp=time.time(),
            ltp=price,
            ohlc={
                'open': base_price,
                'high': base_price + abs(price_change),
                'low': base_price - abs(price_change),
                'close': price,
            }
        )
    
    async def _process_tick(self, tick: Tick):
        """Process and publish tick to Redis Stream."""
        # Validate tick
        if not self._validate_tick(tick):
            logger.warning("Invalid tick received", symbol=tick.symbol)
            return
        
        # Check for stale ticks
        if self._is_stale_tick(tick):
            logger.warning("Stale tick detected", symbol=tick.symbol)
        
        # Update last tick time
        self.last_tick_time[tick.symbol] = tick.timestamp
        
        # Convert to dict
        tick_data = {
            'symbol': tick.symbol,
            'exchange': tick.exchange,
            'price': tick.price,
            'volume': tick.volume,
            'bid_price': tick.bid_price,
            'ask_price': tick.ask_price,
            'bid_qty': tick.bid_qty,
            'ask_qty': tick.ask_qty,
            'total_buy_qty': tick.total_buy_qty,
            'total_sell_qty': tick.total_sell_qty,
            'timestamp': tick.timestamp,
            'ltp': tick.ltp,
            'ohlc': tick.ohlc,
        }
        
        # Publish to Redis Stream
        try:
            await stream_manager.publish(
                stream_name=stream_manager.STREAMS['MARKET_TICKS'],
                event_type='tick',
                data=tick_data,
                source_agent='market_data_agent',
            )
        except Exception as e:
            logger.error("Failed to publish tick", symbol=tick.symbol, error=str(e))
        
        # Call registered callbacks
        for callback in self.tick_callbacks:
            try:
                await callback(tick)
            except Exception as e:
                logger.error("Tick callback error", error=str(e))
    
    def _validate_tick(self, tick: Tick) -> bool:
        """Validate tick data."""
        if tick.price <= 0:
            return False
        if tick.symbol not in self.subscribed_symbols and not self.mock_mode:
            return False
        return True
    
    def _is_stale_tick(self, tick: Tick) -> bool:
        """Check if tick is stale (older than 5 seconds)."""
        last_time = self.last_tick_time.get(tick.symbol, 0)
        return (tick.timestamp - last_time) > 5 if last_time > 0 else False
    
    async def subscribe(self, symbols: List[str]):
        """Subscribe to market data for symbols."""
        self.subscribed_symbols = list(set(self.subscribed_symbols + symbols))
        logger.info(f"Subscribed to {len(symbols)} symbols", symbols=symbols)
    
    async def unsubscribe(self, symbols: List[str]):
        """Unsubscribe from market data for symbols."""
        self.subscribed_symbols = [s for s in self.subscribed_symbols if s not in symbols]
        logger.info(f"Unsubscribed from {len(symbols)} symbols", symbols=symbols)
    
    def register_tick_callback(self, callback: Callable):
        """Register callback for tick updates."""
        self.tick_callbacks.append(callback)
        logger.info("Registered tick callback")
    
    async def stop(self):
        """Stop the market data service."""
        self.running = False
        logger.info("Market Data Service stopping")
