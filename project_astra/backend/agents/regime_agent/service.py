"""
Regime Agent - Detects market regime
States: BULL, BEAR, SIDEWAYS, HIGH_VOL, EVENT_MODE
"""

import asyncio
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
import structlog

from utils.redis_streams import stream_manager
from utils.config import settings

logger = structlog.get_logger()


class RegimeType(str, Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOL = "HIGH_VOL"
    EVENT_MODE = "EVENT_MODE"


@dataclass
class RegimeState:
    """Current market regime state."""
    regime: RegimeType
    confidence: float
    vix_level: float
    trend_strength: float
    volatility_level: float
    breadth: float
    allowed_strategies: List[str]
    risk_multiplier: float
    timestamp: float
    
    def to_dict(self) -> dict:
        return {
            'regime': self.regime.value,
            'confidence': self.confidence,
            'vix_level': self.vix_level,
            'trend_strength': self.trend_strength,
            'volatility_level': self.volatility_level,
            'breadth': self.breadth,
            'allowed_strategies': self.allowed_strategies,
            'risk_multiplier': self.risk_multiplier,
            'timestamp': self.timestamp,
        }


class RegimeService:
    """
    Regime Detection Agent.
    
    Determines market state based on multiple factors:
    - VIX levels
    - EMA trend analysis
    - Market breadth
    - ATR/volatility
    - Event calendar
    
    Output:
    - Current regime
    - Allowed strategies for this regime
    - Risk multiplier
    """
    
    # Regime detection thresholds
    VIX_LOW = 12
    VIX_NORMAL = 18
    VIX_HIGH = 25
    VIX_VERY_HIGH = 35
    
    TREND_THRESHOLD = 0.02  # 2% move for trend detection
    
    def __init__(self):
        self.running = False
        self.current_regime: Optional[RegimeState] = None
        self.update_interval = 60  # Update every minute
        
        # Strategy allowances per regime
        self.strategy_allowances = {
            RegimeType.BULL: ['trend', 'breakout', 'scalping'],
            RegimeType.BEAR: ['trend', 'breakout', 'scalping'],
            RegimeType.SIDEWAYS: ['vwap', 'scalping', 'options'],
            RegimeType.HIGH_VOL: ['breakout', 'scalping'],
            RegimeType.EVENT_MODE: [],  # No trading during events
        }
        
        # Risk multipliers per regime
        self.risk_multipliers = {
            RegimeType.BULL: 1.0,
            RegimeType.BEAR: 0.8,
            RegimeType.SIDEWAYS: 0.6,
            RegimeType.HIGH_VOL: 0.5,
            RegimeType.EVENT_MODE: 0.0,
        }
    
    async def run(self):
        """Main regime detection loop."""
        self.running = True
        logger.info("Regime Service starting")
        
        # Connect to Redis
        await stream_manager.connect()
        
        while self.running:
            try:
                # Analyze market conditions
                regime = await self._detect_regime()
                
                if regime:
                    self.current_regime = regime
                    
                    # Publish to Redis Stream
                    await stream_manager.publish(
                        stream_name=stream_manager.STREAMS['REGIME'],
                        event_type='regime_update',
                        data=regime.to_dict(),
                        source_agent='regime_agent',
                    )
                    
                    logger.info(
                        "Regime updated",
                        regime=regime.regime.value,
                        confidence=regime.confidence,
                        risk_multiplier=regime.risk_multiplier,
                    )
                
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Regime detection error", error=str(e))
                await asyncio.sleep(10)
    
    async def _detect_regime(self) -> Optional[RegimeState]:
        """
        Detect current market regime.
        
        In production, this would analyze:
        - Real VIX data from NSE
        - Index price action (NIFTY, BANKNIFTY)
        - Market breadth (advancers/decliners)
        - Volume patterns
        """
        try:
            # Mock regime detection for development
            # In production, replace with actual analysis
            
            # Simulate VIX reading (mock)
            vix_level = await self._get_vix_level()
            
            # Simulate trend strength (mock)
            trend_strength = await self._get_trend_strength()
            
            # Simulate volatility (mock)
            volatility_level = await self._get_volatility_level()
            
            # Simulate market breadth (mock)
            breadth = await self._get_market_breadth()
            
            # Determine regime based on factors
            regime, confidence = self._classify_regime(
                vix=vix_level,
                trend=trend_strength,
                vol=volatility_level,
                breadth=breadth,
            )
            
            # Get allowed strategies and risk multiplier
            allowed_strategies = self.strategy_allowances.get(regime, [])
            risk_multiplier = self.risk_multipliers.get(regime, 0.5)
            
            return RegimeState(
                regime=regime,
                confidence=confidence,
                vix_level=vix_level,
                trend_strength=trend_strength,
                volatility_level=volatility_level,
                breadth=breadth,
                allowed_strategies=allowed_strategies,
                risk_multiplier=risk_multiplier,
                timestamp=asyncio.get_event_loop().time(),
            )
            
        except Exception as e:
            logger.error("Error detecting regime", error=str(e))
            return None
    
    async def _get_vix_level(self) -> float:
        """Get current VIX level."""
        # Mock: Return simulated VIX
        import random
        return 15.0 + random.random() * 10  # 15-25 range
    
    async def _get_trend_strength(self) -> float:
        """Calculate trend strength from index prices."""
        # Mock: Return simulated trend
        import random
        return random.random()  # 0-1
    
    async def _get_volatility_level(self) -> float:
        """Calculate market volatility."""
        # Mock: Return simulated volatility
        import random
        return 0.5 + random.random() * 0.5  # 0.5-1.0
    
    async def _get_market_breadth(self) -> float:
        """Get market breadth (advancers/decliners ratio)."""
        # Mock: Return simulated breadth
        import random
        return 0.3 + random.random() * 0.4  # 0.3-0.7
    
    def _classify_regime(
        self,
        vix: float,
        trend: float,
        vol: float,
        breadth: float,
    ) -> tuple[RegimeType, float]:
        """Classify regime based on indicators."""
        
        # Check for event mode first (would check event calendar in production)
        is_event_day = False  # Mock
        if is_event_day:
            return RegimeType.EVENT_MODE, 0.9
        
        # High volatility regime
        if vix > self.VIX_HIGH or vol > 0.8:
            return RegimeType.HIGH_VOL, min(0.9, (vix / self.VIX_VERY_HIGH))
        
        # Bull regime: Strong trend up, good breadth
        if trend > 0.6 and breadth > 0.6 and vix < self.VIX_NORMAL:
            return RegimeType.BULL, min(0.9, trend * breadth)
        
        # Bear regime: Strong trend down, poor breadth
        if trend > 0.6 and breadth < 0.4 and vix < self.VIX_NORMAL:
            return RegimeType.BEAR, min(0.9, trend * (1 - breadth))
        
        # Sideways: Weak trend
        if trend < 0.3:
            return RegimeType.SIDEWAYS, 1.0 - trend
        
        # Default to sideways with low confidence
        return RegimeType.SIDEWAYS, 0.5
    
    def get_current_regime(self) -> Optional[RegimeState]:
        """Get current regime state."""
        return self.current_regime
    
    def is_strategy_allowed(self, strategy_name: str) -> bool:
        """Check if a strategy is allowed in current regime."""
        if not self.current_regime:
            return False
        
        return strategy_name in self.current_regime.allowed_strategies
    
    def get_risk_multiplier(self) -> float:
        """Get current risk multiplier."""
        if not self.current_regime:
            return 0.5  # Default conservative
        
        return self.current_regime.risk_multiplier
    
    async def stop(self):
        """Stop regime service."""
        self.running = False
        logger.info("Regime Service stopping")


# Global instance
regime_service = RegimeService()
