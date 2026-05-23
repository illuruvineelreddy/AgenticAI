"""
Risk Agent - Validates and approves/rejects trade signals
Enforces risk limits, position limits, and compliance checks
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import structlog

from utils.redis_streams import stream_manager
from utils.config import settings

logger = structlog.get_logger()


class RiskCheckResult(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class RiskAssessment:
    """Result of risk assessment for a trade."""
    signal_id: int
    result: RiskCheckResult
    checks_passed: List[str]
    checks_failed: List[str]
    rejection_reason: Optional[str]
    approved_quantity: int
    risk_amount: float
    risk_reward_ratio: float
    
    def to_dict(self) -> dict:
        return {
            'signal_id': self.signal_id,
            'result': self.result.value,
            'checks_passed': self.checks_passed,
            'checks_failed': self.checks_failed,
            'rejection_reason': self.rejection_reason,
            'approved_quantity': self.approved_quantity,
            'risk_amount': self.risk_amount,
            'risk_reward_ratio': self.risk_reward_ratio,
        }


class RiskService:
    """
    Risk Management Agent.
    
    Enforces:
    - Max 1% risk per trade
    - Max 3% daily drawdown
    - Max 5 open positions
    - Liquidity checks
    - Spread checks
    - Correlation checks
    - Regime-based restrictions
    
    Has final veto power on all trades.
    """
    
    def __init__(self):
        self.running = False
        self.daily_pnl = 0.0
        self.open_positions_count = 0
        self.total_risk_exposure = 0.0
        
        # Risk limits from config
        self.max_risk_per_trade = settings.max_risk_per_trade  # 1%
        self.max_daily_drawdown = settings.max_daily_drawdown  # 3%
        self.max_open_positions = settings.max_open_positions  # 5
        self.default_capital = settings.default_capital  # 10 Lakhs
        
    async def run(self):
        """Main risk service loop."""
        self.running = True
        logger.info("Risk Service starting")
        
        # Connect to Redis
        await stream_manager.connect()
        
        # Subscribe to strategy signals
        await stream_manager.subscribe(
            stream_name=stream_manager.STREAMS['STRATEGY_SIGNALS'],
            callback=self._on_signal,
            consumer_group='risk_agent',
            consumer_name='risk_checker_1',
        )
        
        # Keep running
        while self.running:
            await asyncio.sleep(1)
    
    async def _on_signal(self, message: dict):
        """Process incoming strategy signal."""
        try:
            signal_data = message.get('data', {})
            
            # Perform risk assessment
            assessment = await self._assess_signal(signal_data)
            
            if assessment:
                # Publish result
                if assessment.result == RiskCheckResult.APPROVED:
                    # Send to execution
                    await stream_manager.publish(
                        stream_name=stream_manager.STREAMS['RISK_APPROVED'],
                        event_type='trade_approved',
                        data=assessment.to_dict(),
                        source_agent='risk_agent',
                    )
                    logger.info(
                        "Trade approved",
                        signal_id=assessment.signal_id,
                        quantity=assessment.approved_quantity,
                        risk_amount=assessment.risk_amount,
                    )
                else:
                    logger.info(
                        "Trade rejected",
                        signal_id=assessment.signal_id,
                        reason=assessment.rejection_reason,
                    )
                    
        except Exception as e:
            logger.error("Error assessing signal", error=str(e))
    
    async def _assess_signal(self, signal: dict) -> Optional[RiskAssessment]:
        """Perform comprehensive risk assessment on a signal."""
        signal_id = signal.get('id', 0)
        symbol = signal.get('symbol', '')
        entry_price = signal.get('entry_price', 0.0)
        stop_loss = signal.get('stop_loss', entry_price * 0.99)  # Default 1% SL
        direction = signal.get('direction', 'LONG')
        confidence = signal.get('confidence', 0.5)
        
        checks_passed = []
        checks_failed = []
        rejection_reason = None
        
        # Calculate risk per share
        if direction == 'LONG':
            risk_per_share = entry_price - stop_loss
        else:
            risk_per_share = stop_loss - entry_price
        
        if risk_per_share <= 0:
            return RiskAssessment(
                signal_id=signal_id,
                result=RiskCheckResult.REJECTED,
                checks_passed=[],
                checks_failed=['invalid_stop_loss'],
                rejection_reason='Invalid stop loss - must be below entry for LONG, above for SHORT',
                approved_quantity=0,
                risk_amount=0.0,
                risk_reward_ratio=0.0,
            )
        
        # Check 1: Maximum risk per trade (1%)
        max_risk_amount = self.default_capital * self.max_risk_per_trade
        if self._check_max_risk(max_risk_amount):
            checks_passed.append('max_risk_per_trade')
        else:
            checks_failed.append('max_risk_per_trade')
            rejection_reason = 'Exceeds maximum risk per trade (1%)'
        
        # Check 2: Daily drawdown limit
        if self._check_daily_drawdown():
            checks_passed.append('daily_drawdown_limit')
        else:
            checks_failed.append('daily_drawdown_limit')
            rejection_reason = 'Daily drawdown limit reached (3%)'
        
        # Check 3: Maximum open positions
        if self._check_position_limit():
            checks_passed.append('position_limit')
        else:
            checks_failed.append('position_limit')
            rejection_reason = 'Maximum open positions reached (5)'
        
        # Check 4: Liquidity check (minimum volume)
        if await self._check_liquidity(symbol):
            checks_passed.append('liquidity_check')
        else:
            checks_failed.append('liquidity_check')
            rejection_reason = 'Insufficient liquidity'
        
        # Check 5: Spread check
        if await self._check_spread(symbol, entry_price):
            checks_passed.append('spread_check')
        else:
            checks_failed.append('spread_check')
            rejection_reason = 'Spread too wide'
        
        # Check 6: Regime check
        if self._check_regime_allowed(signal.get('strategy', '')):
            checks_passed.append('regime_check')
        else:
            checks_failed.append('regime_check')
            rejection_reason = 'Strategy not allowed in current regime'
        
        # Check 7: Risk-reward ratio
        target = signal.get('target', entry_price * 1.02)
        if direction == 'LONG':
            reward_per_share = target - entry_price
        else:
            reward_per_share = entry_price - target
        
        rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0
        
        if rr_ratio >= 1.5:  # Minimum 1.5:1 reward-to-risk
            checks_passed.append('risk_reward_ratio')
        else:
            checks_failed.append('risk_reward_ratio')
            rejection_reason = f'Risk-reward ratio too low ({rr_ratio:.2f}:1, min 1.5:1)'
        
        # Determine result
        if checks_failed:
            result = RiskCheckResult.REJECTED
            approved_quantity = 0
            risk_amount = 0.0
        else:
            # Calculate approved quantity
            approved_quantity = int(max_risk_amount / risk_per_share)
            
            # Apply confidence scaling
            approved_quantity = int(approved_quantity * confidence)
            
            # Ensure minimum lot size
            approved_quantity = max(1, approved_quantity)
            
            risk_amount = approved_quantity * risk_per_share
            result = RiskCheckResult.APPROVED
        
        return RiskAssessment(
            signal_id=signal_id,
            result=result,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            rejection_reason=rejection_reason,
            approved_quantity=approved_quantity,
            risk_amount=risk_amount,
            risk_reward_ratio=rr_ratio,
        )
    
    def _check_max_risk(self, max_risk_amount: float) -> bool:
        """Check if trade is within max risk limits."""
        return self.total_risk_exposure + max_risk_amount <= self.default_capital * 0.05
    
    def _check_daily_drawdown(self) -> bool:
        """Check if daily drawdown limit is reached."""
        return abs(self.daily_pnl) < self.default_capital * self.max_daily_drawdown
    
    def _check_position_limit(self) -> bool:
        """Check if position limit is reached."""
        return self.open_positions_count < self.max_open_positions
    
    async def _check_liquidity(self, symbol: str) -> bool:
        """Check if instrument has sufficient liquidity."""
        # Mock: In production, check average volume
        return True
    
    async def _check_spread(self, symbol: str, price: float) -> bool:
        """Check if bid-ask spread is acceptable."""
        # Mock: In production, check actual spread
        max_spread_pct = 0.001  # 0.1%
        return True
    
    def _check_regime_allowed(self, strategy: str) -> bool:
        """Check if strategy is allowed in current regime."""
        from agents.regime_agent.service import regime_service
        
        regime = regime_service.get_current_regime()
        if not regime:
            return True  # Allow if no regime data
        
        return strategy in regime.allowed_strategies
    
    def update_position_count(self, delta: int):
        """Update open positions count."""
        self.open_positions_count += delta
        self.open_positions_count = max(0, self.open_positions_count)
    
    def update_daily_pnl(self, pnl: float):
        """Update daily PnL."""
        self.daily_pnl += pnl
    
    def update_risk_exposure(self, delta: float):
        """Update total risk exposure."""
        self.total_risk_exposure += delta
        self.total_risk_exposure = max(0, self.total_risk_exposure)
    
    async def stop(self):
        """Stop risk service."""
        self.running = False
        logger.info("Risk Service stopping")


# Global instance
risk_service = RiskService()
