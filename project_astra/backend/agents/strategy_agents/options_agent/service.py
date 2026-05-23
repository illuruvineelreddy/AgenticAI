"""
Options Strategy Agent
Implements volatility-adjusted options-informed strategy using VIX, Stochastic oscillator, and OBV
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

class OptionsStrategyAgent:
    """
    Options Volatility-Based Directional Strategy.
    
    Logic:
    - BUY when: VIX < 18 (low vol expansion potential) AND Stoch %K crosses above %D AND OBV is rising
    - SELL when: VIX > 25 (high vol contraction potential) AND Stoch %K crosses below %D AND OBV is falling
    - Stop-loss: 2.0 * ATR (wider to allow vol room)
    - Target: 4.0 * ATR
    """
    
    def __init__(self):
        self.running = False
        self.calculator = FeatureCalculator()
        self.candle_buffers: Dict[str, List[Dict[str, Any]]] = {}
        self.max_buffer_size = 100
        
    async def run(self):
        """Start the options strategy agent."""
        self.running = True
        logger.info("Options Strategy Agent starting")
        
        await stream_manager.connect()
        
        # Subscribe to candle stream
        await stream_manager.subscribe(
            stream_name=stream_manager.STREAMS['CANDLES_5M'],
            callback=self._on_candle,
            consumer_group='options_strategy',
            consumer_name='options_agent_1',
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
            if len(self.candle_buffers[symbol]) >= 15:
                # Calculate features
                features = self.calculator.calculate_all(self.candle_buffers[symbol])
                if not features:
                    return

                close = candle['close']
                stoch_k = features.get('stoch_k', 50.0)
                stoch_d = features.get('stoch_d', 50.0)
                obv = features.get('obv', 0.0)
                atr = features.get('atr_14', close * 0.01)
                
                # Retrieve VIX level (mock VIX from configuration/regime state or fallback to 15.0)
                from agents.regime_agent.service import regime_service
                regime = regime_service.get_current_regime()
                vix = regime.vix_level if regime else 15.0

                # Check previous stochastic values for crossover
                prev_candles = self.candle_buffers[symbol][:-1]
                prev_features = self.calculator.calculate_all(prev_candles)
                if not prev_features:
                    return
                
                prev_k = prev_features.get('stoch_k', 50.0)
                prev_d = prev_features.get('stoch_d', 50.0)
                prev_obv = prev_features.get('obv', 0.0)

                bullish_crossover = (prev_k <= prev_d) and (stoch_k > stoch_d)
                bearish_crossover = (prev_k >= prev_d) and (stoch_k < stoch_d)
                obv_rising = obv > prev_obv

                direction = None
                stop_loss = 0.0
                target = 0.0
                rationale = ""
                confidence = 0.0

                if bullish_crossover and obv_rising and vix < 18:
                    direction = "LONG"
                    stop_loss = close - (2.0 * atr)
                    target = close + (4.0 * atr)
                    confidence = float(min(1.0, 0.6 + (18 - vix) / 36.0))
                    rationale = f"Options buying setup: VIX ({vix:.1f}) is low, Stochastic crossover, OBV rising"
                elif bearish_crossover and not obv_rising and vix > 22:
                    direction = "SHORT"
                    stop_loss = close + (2.0 * atr)
                    target = close - (4.0 * atr)
                    confidence = float(min(1.0, 0.6 + (vix - 22) / 36.0))
                    rationale = f"Options selling setup: VIX ({vix:.1f}) is elevated, Stochastic breakdown, OBV falling"

                if direction:
                    # Save to DB first
                    signal_id = await self._save_signal_to_db(symbol, direction, close, stop_loss, target, confidence, rationale)
                    
                    if signal_id:
                        # Publish signal to Redis stream
                        signal_payload = {
                            'id': signal_id,
                            'strategy': 'options_strategy',
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
                            source_agent='options_strategy_agent'
                        )
                        logger.info("Options signal published", symbol=symbol, direction=direction, entry=close, id=signal_id)

        except Exception as e:
            logger.error("Error running Options Strategy callback", error=str(e))

    async def _save_signal_to_db(self, symbol: str, direction: str, entry: float, sl: float, tp: float, confidence: float, rationale: str) -> int:
        """Persist generated signal to strategy_signals database table."""
        try:
            async with async_session_factory() as session:
                sig = StrategySignal(
                    strategy_name='options_strategy',
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
            logger.error("Failed to save Options signal to DB", symbol=symbol, error=str(e))
            return 0

    async def stop(self):
        """Stop the agent."""
        self.running = False
        logger.info("Options Strategy Agent stopped")

options_agent = OptionsStrategyAgent()
