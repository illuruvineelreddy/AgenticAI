"""
VWAP Reversion Strategy Agent
Implements VWAP mean reversion with Bollinger Bands and RSI filter
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

class VwapStrategyAgent:
    """
    VWAP Mean Reversion Strategy.
    
    Logic:
    - BUY when: Close < lower BB AND Close < VWAP * 0.985 AND RSI < 35
    - SELL when: Close > upper BB AND Close > VWAP * 1.015 AND RSI > 65
    - Stop-loss: 1.5 * ATR
    - Target: VWAP
    """
    
    def __init__(self):
        self.running = False
        self.calculator = FeatureCalculator()
        self.candle_buffers: Dict[str, List[Dict[str, Any]]] = {}
        self.max_buffer_size = 100
        
    async def run(self):
        """Start the VWAP strategy agent."""
        self.running = True
        logger.info("VWAP Strategy Agent starting")
        
        await stream_manager.connect()
        
        # Subscribe to candle stream
        await stream_manager.subscribe(
            stream_name=stream_manager.STREAMS['CANDLES_5M'],
            callback=self._on_candle,
            consumer_group='vwap_strategy',
            consumer_name='vwap_agent_1',
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
            if len(self.candle_buffers[symbol]) >= 20:
                # Calculate features
                features = self.calculator.calculate_all(self.candle_buffers[symbol])
                if not features:
                    return

                close = candle['close']
                vwap = features.get('vwap', close)
                bb_lower = features.get('bb_lower', close * 0.98)
                bb_upper = features.get('bb_upper', close * 1.02)
                rsi = features.get('rsi_14', 50.0)
                atr = features.get('atr_14', close * 0.01)

                # Strategy conditions
                oversold_reversion = (close <= bb_lower) and (close < vwap * 0.985) and (rsi < 35)
                overbought_reversion = (close >= bb_upper) and (close > vwap * 1.015) and (rsi > 65)

                direction = None
                stop_loss = 0.0
                target = 0.0
                rationale = ""
                confidence = 0.0

                if oversold_reversion:
                    direction = "LONG"
                    stop_loss = close - (1.5 * atr)
                    target = vwap  # Mean reversion to VWAP
                    confidence = float(min(1.0, 0.5 + (35 - rsi) / 70.0))
                    rationale = f"Oversold mean reversion buy: Close ({close:.2f}) below lower BB ({bb_lower:.2f}) and VWAP ({vwap:.2f}) with RSI: {rsi:.1f}"
                elif overbought_reversion:
                    direction = "SHORT"
                    stop_loss = close + (1.5 * atr)
                    target = vwap  # Mean reversion to VWAP
                    confidence = float(min(1.0, 0.5 + (rsi - 65) / 70.0))
                    rationale = f"Overbought mean reversion sell: Close ({close:.2f}) above upper BB ({bb_upper:.2f}) and VWAP ({vwap:.2f}) with RSI: {rsi:.1f}"

                # Double check risk/reward
                if direction:
                    # If target is too close, reject signal
                    if direction == "LONG" and target <= close + atr:
                        return
                    if direction == "SHORT" and target >= close - atr:
                        return

                    # Save to DB first
                    signal_id = await self._save_signal_to_db(symbol, direction, close, stop_loss, target, confidence, rationale)
                    
                    if signal_id:
                        # Publish signal to Redis stream
                        signal_payload = {
                            'id': signal_id,
                            'strategy': 'vwap_strategy',
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
                            source_agent='vwap_strategy_agent'
                        )
                        logger.info("VWAP signal published", symbol=symbol, direction=direction, entry=close, id=signal_id)

        except Exception as e:
            logger.error("Error running VWAP Strategy callback", error=str(e))

    async def _save_signal_to_db(self, symbol: str, direction: str, entry: float, sl: float, tp: float, confidence: float, rationale: str) -> int:
        """Persist generated signal to strategy_signals database table."""
        try:
            async with async_session_factory() as session:
                sig = StrategySignal(
                    strategy_name='vwap_strategy',
                    symbol=symbol,
                    direction=direction,
                    entry_price=entry,
                    stop_loss=sl,
                    target=tp,
                    confidence=confidence,
                    rationale=rationale,
                    regime='SIDEWAYS',
                    status='PENDING'
                )
                session.add(sig)
                await session.commit()
                await session.refresh(sig)
                return sig.id
        except Exception as e:
            logger.error("Failed to save VWAP signal to DB", symbol=symbol, error=str(e))
            return 0

    async def stop(self):
        """Stop the agent."""
        self.running = False
        logger.info("VWAP Strategy Agent stopped")

vwap_agent = VwapStrategyAgent()
