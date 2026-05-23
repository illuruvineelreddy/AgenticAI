"""
Trend Following Strategy Agent
Implements EMA-based trend following strategy with ADX confirmation
"""

import asyncio
from datetime import datetime
import structlog
from typing import Dict, List, Any
from sqlalchemy import insert

from utils.redis_streams import stream_manager
from utils.config import settings
from database.connection import async_session_factory
from database.models import StrategySignal
from feature_engine.calculator import FeatureCalculator

logger = structlog.get_logger()

class TrendStrategyAgent:
    """
    EMA Trend Following Strategy.
    
    Logic:
    - BUY when: Fast EMA (9) crosses above Slow EMA (21) AND ADX > 25 AND Price > EMA (50)
    - SELL when: Fast EMA (9) crosses below Slow EMA (21) AND ADX > 25 AND Price < EMA (50)
    - Stop-loss: 1.5 * ATR from entry
    - Target: 3 * ATR from entry
    """
    
    def __init__(self):
        self.running = False
        self.calculator = FeatureCalculator()
        self.candle_buffers: Dict[str, List[Dict[str, Any]]] = {}
        self.max_buffer_size = 100
        
    async def run(self):
        """Start the trend strategy agent."""
        self.running = True
        logger.info("Trend Strategy Agent starting")
        
        await stream_manager.connect()
        
        # Subscribe to candle stream
        await stream_manager.subscribe(
            stream_name=stream_manager.STREAMS['CANDLES_5M'],
            callback=self._on_candle,
            consumer_group='trend_strategy',
            consumer_name='trend_agent_1',
        )
        
        while self.running:
            await asyncio.sleep(1)
    
    async def _on_candle(self, message: dict):
        """Process candle data and generate signals."""
        try:
            event_type = message.get('event_type')
            if event_type != 'candle_complete':
                return
                
            candle_data = message.get('data', {})
            symbol = candle_data.get('symbol')
            if not symbol:
                return

            # Append to buffer
            candle = {
                'symbol': symbol,
                'open': float(candle_data.get('open', 0.0)),
                'high': float(candle_data.get('high', 0.0)),
                'low': float(candle_data.get('low', 0.0)),
                'close': float(candle_data.get('close', 0.0)),
                'volume': int(candle_data.get('volume', 0)),
                'timestamp': candle_data.get('timestamp')
            }

            if symbol not in self.candle_buffers:
                self.candle_buffers[symbol] = []
            
            self.candle_buffers[symbol].append(candle)
            if len(self.candle_buffers[symbol]) > self.max_buffer_size:
                self.candle_buffers[symbol].pop(0)

            # Check if buffer has enough candles (need at least 26 for calculations)
            if len(self.candle_buffers[symbol]) >= 26:
                # Calculate features
                features = self.calculator.calculate_all(self.candle_buffers[symbol])
                if not features:
                    return

                # Get indicators
                close = candle['close']
                ema_9 = features.get('ema_9', close)
                ema_21 = features.get('ema_21', close)
                ema_50 = features.get('ema_50', close)
                adx = features.get('adx', 0.0)
                atr = features.get('atr_14', close * 0.01)

                # Get previous values to detect crossover
                prev_candles = self.candle_buffers[symbol][:-1]
                prev_features = self.calculator.calculate_all(prev_candles)
                if not prev_features:
                    return
                
                prev_close = prev_candles[-1]['close']
                prev_ema_9 = prev_features.get('ema_9', prev_close)
                prev_ema_21 = prev_features.get('ema_21', prev_close)

                # Detect Crossovers
                bullish_crossover = (prev_ema_9 <= prev_ema_21) and (ema_9 > ema_21)
                bearish_crossover = (prev_ema_9 >= prev_ema_21) and (ema_9 < ema_21)

                # Define signal variables
                direction = None
                stop_loss = 0.0
                target = 0.0
                rationale = ""
                confidence = 0.0

                if bullish_crossover and adx > 25 and close > ema_50:
                    direction = "LONG"
                    stop_loss = close - (1.5 * atr)
                    target = close + (3.0 * atr)
                    confidence = float(min(1.0, 0.5 + (adx - 25) / 50.0))
                    rationale = f"Bullish EMA(9) crossed EMA(21) above EMA(50) with strong trend (ADX: {adx:.1f})"
                elif bearish_crossover and adx > 25 and close < ema_50:
                    direction = "SHORT"
                    stop_loss = close + (1.5 * atr)
                    target = close - (3.0 * atr)
                    confidence = float(min(1.0, 0.5 + (adx - 25) / 50.0))
                    rationale = f"Bearish EMA(9) crossed EMA(21) below EMA(50) with strong trend (ADX: {adx:.1f})"

                if direction:
                    # Save to DB first to get unique ID
                    signal_id = await self._save_signal_to_db(symbol, direction, close, stop_loss, target, confidence, rationale)
                    
                    if signal_id:
                        # Publish signal to Redis stream
                        signal_payload = {
                            'id': signal_id,
                            'strategy': 'trend_strategy',
                            'symbol': symbol,
                            'direction': direction,
                            'entry_price': close,
                            'stop_loss': stop_loss,
                            'target': target,
                            'confidence': confidence,
                            'rationale': rationale,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                        await stream_manager.publish(
                            stream_name=stream_manager.STREAMS['STRATEGY_SIGNALS'],
                            event_type='signal_generated',
                            data=signal_payload,
                            source_agent='trend_strategy_agent'
                        )
                        logger.info("Trend signal published", symbol=symbol, direction=direction, entry=close, id=signal_id)

        except Exception as e:
            logger.error("Error running Trend Strategy callback", error=str(e))

    async def _save_signal_to_db(self, symbol: str, direction: str, entry: float, sl: float, tp: float, confidence: float, rationale: str) -> int:
        """Persist generated signal to strategy_signals database table."""
        try:
            async with async_session_factory() as session:
                sig = StrategySignal(
                    strategy_name='trend_strategy',
                    symbol=symbol,
                    direction=direction,
                    entry_price=entry,
                    stop_loss=sl,
                    target=tp,
                    confidence=confidence,
                    rationale=rationale,
                    regime='BULL' if direction == 'LONG' else 'BEAR',  # Placeholder context
                    status='PENDING'
                )
                session.add(sig)
                await session.commit()
                await session.refresh(sig)
                return sig.id
        except Exception as e:
            logger.error("Failed to save Trend signal to DB", symbol=symbol, error=str(e))
            return 0

    async def stop(self):
        """Stop the agent."""
        self.running = False
        logger.info("Trend Strategy Agent stopped")

trend_agent = TrendStrategyAgent()
