import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from agents.risk_agent.service import RiskService, RiskCheckResult

@pytest.mark.asyncio
async def test_assess_signal_approved():
    """Test that a signal passing all checks is approved with a calculated quantity."""
    service = RiskService()
    
    # Mock regime allowed check to keep test simple
    with patch.object(service, "_check_regime_allowed", return_type=bool, return_value=True):
        signal = {
            "id": 1,
            "symbol": "RELIANCE",
            "entry_price": 2500.0,
            "stop_loss": 2480.0,  # Risk is 20
            "target": 2540.0,     # Reward is 40. R-R ratio is 2.0 (>= 1.5)
            "direction": "LONG",
            "confidence": 0.8,
            "strategy": "trend_strategy"
        }
        
        assessment = await service._assess_signal(signal)
        
        assert assessment.result == RiskCheckResult.APPROVED
        assert assessment.risk_reward_ratio == 2.0
        assert assessment.approved_quantity > 0
        assert len(assessment.checks_failed) == 0

@pytest.mark.asyncio
async def test_assess_signal_rejected_invalid_sl():
    """Test that a signal with an invalid stop-loss (e.g. SL above entry for LONG) is rejected."""
    service = RiskService()
    
    signal = {
        "id": 2,
        "symbol": "RELIANCE",
        "entry_price": 2500.0,
        "stop_loss": 2510.0,  # SL is above entry for LONG
        "target": 2600.0,
        "direction": "LONG",
        "confidence": 0.8,
        "strategy": "trend_strategy"
    }
    
    assessment = await service._assess_signal(signal)
    
    assert assessment.result == RiskCheckResult.REJECTED
    assert "invalid_stop_loss" in assessment.checks_failed

@pytest.mark.asyncio
async def test_assess_signal_rejected_low_rr():
    """Test that a signal with a risk-reward ratio less than 1.5 is rejected."""
    service = RiskService()
    
    with patch.object(service, "_check_regime_allowed", return_value=True):
        signal = {
            "id": 3,
            "symbol": "RELIANCE",
            "entry_price": 2500.0,
            "stop_loss": 2480.0,  # Risk is 20
            "target": 2510.0,     # Reward is 10. R-R is 0.5 (< 1.5)
            "direction": "LONG",
            "confidence": 0.8,
            "strategy": "trend_strategy"
        }
        
        assessment = await service._assess_signal(signal)
        
        assert assessment.result == RiskCheckResult.REJECTED
        assert "risk_reward_ratio" in assessment.checks_failed
        assert assessment.approved_quantity == 0

def test_risk_exposure_limit():
    """Test that risk exposure checks block when exceeding maximum limits."""
    service = RiskService()
    service.total_risk_exposure = 0.0
    
    # Capital is 10,000,000. Max risk exposure limit is 5% = 50,000
    assert service._check_max_risk(10000) is True
    
    # Exceeding 5% limits
    assert service._check_max_risk(60000) is False

def test_daily_drawdown_limit():
    """Test that daily drawdown checks block when exceeding 3% daily drawdown."""
    service = RiskService()
    
    # Capital is 1,000,000. 3% drawdown is 30,000.
    service.daily_pnl = -10000
    assert service._check_daily_drawdown() is True
    
    service.daily_pnl = -35000
    assert service._check_daily_drawdown() is False

def test_open_position_limit():
    """Test that open positions limit check blocks when exceeding limit."""
    service = RiskService()
    service.open_positions_count = 3
    assert service._check_position_limit() is True
    
    service.open_positions_count = 5
    assert service._check_position_limit() is False
