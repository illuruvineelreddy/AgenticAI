"""
Feature Engine Service for Project Astra
Calculates and persists technical indicators in real-time.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any
import structlog
from sqlalchemy import select

from utils.redis_streams import stream_manager
from utils.config import settings
from database.connection import async_session_factory
from database.models import Candle, Feature
from feature_engine.calculator import FeatureCalculator

logger = structlog.get_logger()

class FeatureService:
    """
    Service to process 5-minute candles, calculate technical indicators,
    persist them to database, and publish to features_stream.
    """
    
    def __init__(self):
        self.running = False
        self.calculator = FeatureCalculator()
        self.candle_buffers: Dict[str, List[Dict[str, Any]]] = {}
        self.max_buffer_size = 100

    async def run(self):
        """Start the Feature Engine Service."""
        self.running = True
        logger.info("Feature Engine Service starting")
        
        await stream_manager.connect()
        
        # Pre-populate candle buffers from database
        await self._prepopulate_buffers()

        # Subscribe to 5m candle stream
        await stream_manager.subscribe(
            stream_name=stream_manager.STREAMS['CANDLES_5M'],
            callback=self._on_candle,
            consumer_group='feature_engine',
            consumer_name='feature_engine_1',
        )

        while self.running:
            await asyncio.sleep(1)

    async def stop(self):
        """Stop the Feature Engine Service."""
        self.running = False
        logger.info("Feature Engine Service stopped")

    async def _prepopulate_buffers(self):
        """Fetch recent candles from the DB to initialize the rolling buffers."""
        logger.info("Pre-populating candle buffers from database")
        try:
            async with async_session_factory() as session:
                # Query unique symbols in instruments or candles
                symbols = settings.watchlist_nifty50 + settings.watchlist_niftybank
                
                for symbol in symbols:
                    stmt = (
                        select(Candle)
                        .where(Candle.symbol == symbol, Candle.interval == '5m')
                        .order_by(Candle.timestamp.desc())
                        .limit(self.max_buffer_size)
                    )
                    result = await session.execute(stmt)
                    db_candles = result.scalars().all()
                    
                    if db_candles:
                        # Convert to dict format needed by calculator
                        # Sort by timestamp ascending for calculations
                        candles_list = []
                        for c in reversed(db_candles):
                            candles_list.append({
                                'symbol': c.symbol,
                                'exchange': c.exchange,
                                'interval': c.interval,
                                'open': float(c.open),
                                'high': float(c.high),
                                'low': float(c.low),
                                'close': float(c.close),
                                'volume': int(c.volume),
                                'oi': int(c.oi) if c.oi else 0,
                                'timestamp': c.timestamp
                            })
                        self.candle_buffers[symbol] = candles_list
                        logger.debug("Pre-populated buffer", symbol=symbol, count=len(candles_list))
                        
        except Exception as e:
            logger.error("Error pre-populating candle buffers", error=str(e))

    async def _on_candle(self, message: dict):
        """Process an incoming candle from Redis Stream."""
        try:
            event_type = message.get('event_type')
            if event_type != 'candle_complete':
                return
                
            candle_data = message.get('data', {})
            symbol = candle_data.get('symbol')
            if not symbol:
                return

            # Normalize values
            candle = {
                'symbol': symbol,
                'exchange': candle_data.get('exchange', 'NSE'),
                'interval': candle_data.get('interval', '5m'),
                'open': float(candle_data.get('open', 0.0)),
                'high': float(candle_data.get('high', 0.0)),
                'low': float(candle_data.get('low', 0.0)),
                'close': float(candle_data.get('close', 0.0)),
                'volume': int(candle_data.get('volume', 0)),
                'oi': int(candle_data.get('oi', 0)),
                'timestamp': candle_data.get('timestamp')
            }

            # Update rolling buffer
            if symbol not in self.candle_buffers:
                self.candle_buffers[symbol] = []
            
            self.candle_buffers[symbol].append(candle)
            if len(self.candle_buffers[symbol]) > self.max_buffer_size:
                self.candle_buffers[symbol].pop(0)

            # Check if we have enough candles to calculate features
            if len(self.candle_buffers[symbol]) >= 2:
                # Calculate features
                features_dict = self.calculator.calculate_all(self.candle_buffers[symbol])
                
                if features_dict:
                    # Save to DB and publish to Redis Stream
                    timestamp = candle['timestamp']
                    if isinstance(timestamp, (int, float)):
                        dt_timestamp = datetime.fromtimestamp(timestamp)
                    elif isinstance(timestamp, str):
                        try:
                            # Standard ISO format parsing
                            dt_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        except ValueError:
                            dt_timestamp = datetime.utcnow()
                    else:
                        dt_timestamp = timestamp if isinstance(timestamp, datetime) else datetime.utcnow()

                    await self._save_features_to_db(symbol, features_dict, dt_timestamp)
                    
                    # Publish features to stream
                    await stream_manager.publish(
                        stream_name=stream_manager.STREAMS['FEATURES'],
                        event_type='features_calculated',
                        data={
                            'symbol': symbol,
                            'candle_timestamp': dt_timestamp.isoformat(),
                            'features': features_dict
                        },
                        source_agent='feature_engine'
                    )
                    
                    logger.debug("Features calculated and published", symbol=symbol, feature_count=len(features_dict))

        except Exception as e:
            logger.error("Error processing candle in feature service", error=str(e))

    async def _save_features_to_db(self, symbol: str, features: Dict[str, float], timestamp: datetime):
        """Persist calculated features to the DB."""
        try:
            async with async_session_factory() as session:
                db_features = []
                for name, val in features.items():
                    # Determine category
                    category = 'technical'
                    if name in ['stoch_k', 'stoch_d', 'rsi_14', 'williams_r', 'cci_20', 'roc_10']:
                        category = 'momentum'
                    elif name in ['historical_volatility', 'atr_14', 'bb_upper', 'bb_middle', 'bb_lower']:
                        category = 'volatility'
                    elif name in ['obv', 'vwap', 'volume_sma_20']:
                        category = 'volume'
                    
                    feat = Feature(
                        symbol=symbol,
                        feature_name=name,
                        feature_value=float(val) if not np.isnan(val) and not np.isinf(val) else 0.0,
                        feature_category=category,
                        candle_timestamp=timestamp
                    )
                    db_features.append(feat)
                
                session.add_all(db_features)
                await session.commit()
        except Exception as e:
            logger.error("Failed to save features to DB", symbol=symbol, error=str(e))

# Global instance
feature_service = FeatureService()
