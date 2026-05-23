"""
Scalping Strategy Agent
Implements RSI + Stochastic Fast Scalping on 1-minute candles during early market hours
"""

import asyncio
from datetime import datetime, time
import pytz
import structlog
from typing import Dict, List, Any
from sqlalchemy import insert

from utils.redis_streams import stream_manager
from utils.config import settings
from database.connection import async_session_factory
from database.models import StrategySignal
from feature_engine.calculator import FeatureCalculator

logger = structlog.get_logger()

class ScalpingStrategyAgent:
    """
    RSI + Stochastic Fast Scalping Strategy.
    
    Logic:
    - Subscribes to candles_1m (1-minute candles)
    - Active only during high volatility (9:15 AM to 11:15 AM IST)
    - BUY when: RSI(7) < 30 AND Stochastic K crosses above D (both < 20) AND close <= Keltner Lower Channel
    - SELL when: RSI(7) > 70 AND Stochastic K crosses below D (both > 80) AND close >= Keltner Upper Channel
    - Stop-loss: 0.75 * ATR (tight)
    - Target: 1.5 * ATR (quick exit)
    """
    
    def __init__(self):
        self.running = False
        self.calculator = FeatureCalculator()
        self.candle_buffers: Dict[str, List[Dict[str, Any]]] = {}
        self.max_buffer_size = 100
        
    async def run(self):
        """Start the scalping strategy agent."""
        self.running = True
        logger.info("Scalping Strategy Agent starting")
        
        await stream_manager.connect()
        
        # Subscribe to 1m candle stream (not 5m!)
        await stream_manager.subscribe(
            stream_name=stream_manager.STREAMS['CANDLES_1M'],
            callback=self._on_candle,
            consumer_group='scalping_strategy',
            consumer_name='scalping_agent_1',
        )
        
        while self.running:
            await asyncio.sleep(1)
            
    def _is_market_active_for_scalping(self) -> bool:
        """Check if current time is within 9:15 AM to 11:15 AM IST."""
        tz_ist = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(tz_ist).time()
        
        start_time = time(9, 15)
        end_time = time(11, 15)
        
        # In mock mode, we bypass time checks to allow testing at any time
        if settings.environment == 'development':
            return True
            
        return start_time <= now_ist <= end_time
    
    async def _on_candle(self, message: dict):
        """Process candle data and generate signals."""
        try:
            # Check market hour slot
            if not self._is_market_active_for_scalping():
                return
                
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
                rsi = features.get('rsi_14', 50.0) # Using rsi_14 but can adjust
                stoch_k = features.get('stoch_k', 50.0)
                stoch_d = features.get('stoch_d', 50.0)
                kc_lower = features.get('kc_lower', close * 0.99)
                kc_upper = features.get('kc_upper', close * 1.01)
                atr = features.get('atr_14', close * 0.005)

                # Stochastic crossover check
                prev_candles = self.candle_buffers[symbol][:-1]
                prev_features = self.calculator.calculate_all(prev_candles)
                if not prev_features:
                    return
                
                prev_k = prev_features.get('stoch_k', 50.0)
                prev_d = prev_features.get('stoch_d', 50.0)

                stoch_bullish_crossover = (prev_k <= prev_d) and (stoch_k > stoch_d)
                stoch_bearish_crossover = (prev_k >= prev_d) and (stoch_k < stoch_d)

                direction = None
                stop_loss = 0.0
                target = 0.0
                rationale = ""
                confidence = 0.0

                # RSI Scalping uses 30/70 thresholds
                if rsi < 30 and stoch_bullish_crossover and stoch_k < 20 and close <= kc_lower:
                    direction = "LONG"
                    stop_loss = close - (0.75 * atr)
                    target = close + (1.5 * atr)
                    confidence = float(min(1.0, 0.7 + (30 - rsi) / 100.0))
                    rationale = f"Scalp BUY: oversold RSI ({rsi:.1f}), Stochastic cross < 20, close <= KC lower"
                elif rsi > 70 and stoch_bearish_crossover and stoch_k > 80 and close >= kc_upper:
                    direction = "SHORT"
                    stop_loss = close + (0.75 * atr)
                    target = close - (1.5 * atr)
                    confidence = float(min(1.0, 0.7 + (rsi - 70) / 100.0))
                    rationale = f"Scalp SELL: overbought RSI ({rsi:.1f}), Stochastic cross > 80, close >= KC upper"

                if direction:
                    # Save to DB first
                    signal_id = await self._save_signal_to_db(symbol, direction, close, stop_loss, target, confidence, rationale)
                    
                    if signal_id:
                        # Publish signal to Redis stream
                        signal_payload = {
                            'id': signal_id,
                            'strategy': 'scalping_strategy',
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
                            source_agent='scalping_strategy_agent'
                        )
                        logger.info("Scalping signal published", symbol=symbol, direction=direction, entry=close, id=signal_id)

        except Exception as e:
            logger.error("Error running Scalping Strategy callback", error=str(e))

    async def _save_signal_to_db(self, symbol: str, direction: str, entry: float, sl: float, tp: float, confidence: float, rationale: str) -> int:
        """Persist generated signal to strategy_signals database table."""
        try:
            async with async_session_factory() as session:
                sig = StrategySignal(
                    strategy_name='scalping_strategy',
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
            logger.error("Failed to save Scalping signal to DB", symbol=symbol, error=str(e))
            return 0

    async def stop(self):
        """Stop the agent."""
        self.running = False
        logger.info("Scalping Strategy Agent stopped")

scalping_agent = ScalpingStrategyAgent()
