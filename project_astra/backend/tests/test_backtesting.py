import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from backtesting.charges import IndianBrokerageCalculator
from backtesting.engine import BacktestEngine

def test_brokerage_calculator_intraday():
    """Test standard discount broker charges for intraday equity trades."""
    # BUY order: quantity=100, price=1000 (value = 100,000)
    charges = IndianBrokerageCalculator.calculate_charges(100, 1000.0, "BUY", is_delivery=False)
    
    assert charges["trade_value"] == 100000.0
    # Brokerage: 0.03% of 100,000 = 30, capped at 20.0
    assert charges["brokerage"] == 20.0
    # STT: 0 on intraday BUY
    assert charges["stt"] == 0.0
    # Exchange transaction: 0.00325% of 100,000 = 3.25
    assert round(charges["exchange_charges"], 2) == 3.25
    # Stamp duty: 0.003% of 100,000 = 3.0
    assert round(charges["stamp_duty"], 2) == 3.0
    
    # SELL order: quantity=100, price=1000
    charges_sell = IndianBrokerageCalculator.calculate_charges(100, 1000.0, "SELL", is_delivery=False)
    # STT: 0.025% of 100,000 = 25.0
    assert charges_sell["stt"] == 25.0
    # Stamp duty: 0 on intraday SELL
    assert charges_sell["stamp_duty"] == 0.0

def test_brokerage_calculator_delivery():
    """Test charges for delivery trades (zero brokerage model)."""
    # BUY order: quantity=100, price=1000
    charges = IndianBrokerageCalculator.calculate_charges(100, 1000.0, "BUY", is_delivery=True)
    
    assert charges["brokerage"] == 0.0  # Zero brokerage on delivery
    # STT: 0.1% on buy = 100
    assert charges["stt"] == 100.0
    # Stamp duty: 0.015% on buy = 15.0
    assert charges["stamp_duty"] == pytest.approx(15.0)

@pytest.mark.asyncio
async def test_backtest_engine_run(db_session):
    """Test that BacktestEngine executes simulation loop and returns metrics dictionary."""
    engine = BacktestEngine()
    
    # Setup mock historical candles
    mock_candles = [
        {
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "interval": "5m",
            "open": 2500.0,
            "high": 2510.0,
            "low": 2490.0,
            "close": 2505.0,
            "volume": 1000,
            "timestamp": datetime(2026, 5, 20, 9, 15)
        },
        {
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "interval": "5m",
            "open": 2505.0,
            "high": 2520.0,
            "low": 2502.0,
            "close": 2515.0,
            "volume": 1200,
            "timestamp": datetime(2026, 5, 20, 9, 20)
        }
    ]
    
    # Mock database fetch and agent instantiation
    with patch.object(engine, "_fetch_historical_candles", return_value=mock_candles), \
         patch.object(engine, "_instantiate_agent") as mock_inst:
             
        # Mock strategy agent to not generate signals for simplicity
        mock_agent = MagicMock()
        mock_agent.candle_buffers = {}
        mock_agent._on_candle = AsyncMock()
        mock_inst.return_value = mock_agent
        
        result = await engine.run(
            strategy_name="trend_strategy",
            symbol="RELIANCE",
            start_date=datetime(2026, 5, 20, 9, 15),
            end_date=datetime(2026, 5, 20, 9, 20),
            initial_capital=100000.0
        )
        
        assert "metrics" in result
        assert "trades" in result
        assert "equity_curve" in result
        
        metrics = result["metrics"]
        assert metrics["total_trades"] == 0
        assert metrics["total_pnl"] == 0.0
        assert len(result["equity_curve"]) == 2
