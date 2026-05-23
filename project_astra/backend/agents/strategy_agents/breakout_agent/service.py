"""
Breakout Strategy Agent
Implements price breakout of support/resistance with volume confirmation
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

class BreakoutStrategyAgent:
    """
    Price Breakout Strategy.
    
    Logic:
    - BUY when: Close breaks above 20-candle high AND Volume > 1.5 * 20-candle Volume SMA AND ADX > 20
    - SELL when: Close breaks below 20-candle low AND Volume > 1.5 * 20-candle Volume SMA AND ADX > 20
    - Stop-loss: Last candle low/high or 1.5 * ATR
    - Target: Entry + 3 * ATR
    """
    
    def __init__(self):
        self.running = False
        self.calculator = FeatureCalculator()
        self.candle_buffers: Dict[str, List[Dict[str, Any]]] = {}
        self.max_buffer_size = 100
        
    async def run(self):
        """Start the breakout strategy agent."""
        self.running = True
        logger.info("Breakout Strategy Agent starting")
        
        await stream_manager.connect()
        
        # Subscribe to candle stream
        await stream_manager.subscribe(
            stream_name=stream_manager.STREAMS['CANDLES_5M'],
            callback=self._on_candle,
            consumer_group='breakout_strategy',
            consumer_name='breakout_agent_1',
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

            # Check if buffer has enough candles
            if len(self.candle_buffers[symbol]) >= 21:
                # Calculate features
                features = self.calculator.calculate_all(self.candle_buffers[symbol])
                if not features:
                    return

                close = candle['close']
                volume = candle['volume']
                adx = features.get('adx', 0.0)
                atr = features.get('atr_14', close * 0.01)
                vol_sma = features.get('volume_sma_20', volume)

                # Get previous 20 candles to calculate highest high / lowest low
                prev_candles = self.candle_buffers[symbol][-21:-1]
                highs = [c['high'] for c in prev_candles]
                lows = [c['low'] for c in prev_candles]
                
                prev_high_20 = max(highs)
                prev_low_20 = min(lows)

                # Breakout conditions
                upside_breakout = (close > prev_high_20) and (volume > 1.5 * vol_sma)
                downside_breakout = (close < prev_low_20) and (volume > 1.5 * vol_sma)

                direction = None
                stop_loss = 0.0
                target = 0.0
                rationale = ""
                confidence = 0.0

                if upside_breakout and adx > 20:
                    direction = "LONG"
                    stop_loss = close - (1.5 * atr)
                    target = close + (3.0 * atr)
                    confidence = float(min(1.0, 0.5 + (volume / (vol_sma * 3.0)) / 2.0))
                    rationale = f"Upside Breakout above 20-candle high ({prev_high_20:.2f}) with volume surge ({volume}/{int(vol_sma)}) and ADX: {adx:.1f}"
                elif downside_breakout and adx > 20:
                    direction = "SHORT"
                    stop_loss = close + (1.5 * atr)
                    target = close - (3.0 * atr)
                    confidence = float(min(1.0, 0.5 + (volume / (vol_sma * 3.0)) / 2.0))
                    rationale = f"Downside Breakout below 20-candle low ({prev_low_20:.2f}) with volume surge ({volume}/{int(vol_sma)}) and ADX: {adx:.1f}"

                if direction:
                    # Save to DB first
                    signal_id = await self._save_signal_to_db(symbol, direction, close, stop_loss, target, confidence, rationale)
                    
                    if signal_id:
                        # Publish signal to Redis stream
                        signal_payload = {
                            'id': signal_id,
                            'strategy': 'breakout_strategy',
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
                            source_agent='breakout_strategy_agent'
                        )
                        logger.info("Breakout signal published", symbol=symbol, direction=direction, entry=close, id=signal_id)

        except Exception as e:
            logger.error("Error running Breakout Strategy callback", error=str(e))

    async def _save_signal_to_db(self, symbol: str, direction: str, entry: float, sl: float, tp: float, confidence: float, rationale: str) -> int:
        """Persist generated signal to strategy_signals database table."""
        try:
            async with async_session_factory() as session:
                sig = StrategySignal(
                    strategy_name='breakout_strategy',
                    symbol=symbol,
                    direction=direction,
                    entry_price=entry,
                    stop_loss=sl,
                    target=tp,
                    confidence=confidence,
                    rationale=rationale,
                    regime='HIGH_VOL',
                    status='PENDING'
                )
                session.add(sig)
                await session.commit()
                await session.refresh(sig)
                return sig.id
        except Exception as e:
            logger.error("Failed to save Breakout signal to DB", symbol=symbol, error=str(e))
            return 0

    async def stop(self):
        """Stop the agent."""
        self.running = False
        logger.info("Breakout Strategy Agent stopped")

breakout_agent = BreakoutStrategyAgent()
