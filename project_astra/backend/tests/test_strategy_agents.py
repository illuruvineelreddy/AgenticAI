import pytest
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime

from agents.strategy_agents.trend_agent.service import TrendStrategyAgent
from agents.strategy_agents.breakout_agent.service import BreakoutStrategyAgent
from agents.strategy_agents.vwap_agent.service import VwapStrategyAgent
from agents.strategy_agents.options_agent.service import OptionsStrategyAgent
from agents.strategy_agents.scalping_agent.service import ScalpingStrategyAgent

@pytest.mark.asyncio
async def test_trend_strategy_agent_long(db_session, mock_stream_manager):
    """Test that TrendStrategyAgent generates a LONG signal on a bullish crossover."""
    agent = TrendStrategyAgent()
    
    # We mock calculate_all to return values triggering a LONG signal
    # Call 1 (current features): adx > 25, ema_9 > ema_21, close > ema_50
    # Call 2 (prev features): ema_9 <= ema_21
    mock_features = {
        "ema_9": 105.0,
        "ema_21": 102.0,
        "ema_50": 98.0,
        "adx": 30.0,
        "atr_14": 2.0
    }
    mock_prev_features = {
        "ema_9": 101.0,
        "ema_21": 102.0,
        "ema_50": 98.0,
        "adx": 30.0,
        "atr_14": 2.0
    }
    
    with patch.object(agent.calculator, "calculate_all") as mock_calc:
        mock_calc.side_effect = [mock_features, mock_prev_features]
        
        # Populate buffer with 26 candles so calculation is triggered
        agent.candle_buffers["RELIANCE"] = [
            {"close": 100.0, "open": 99.0, "high": 101.0, "low": 98.0, "volume": 1000, "timestamp": datetime.utcnow().isoformat()}
            for _ in range(26)
        ]
        
        # Update the last candle close to be above ema_50
        agent.candle_buffers["RELIANCE"][-1]["close"] = 106.0
        
        # Trigger candle complete callback
        message = {
            "event_type": "candle_complete",
            "data": {
                "symbol": "RELIANCE",
                "open": 99.0,
                "high": 108.0,
                "low": 98.0,
                "close": 106.0,
                "volume": 2000,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await agent._on_candle(message)
        
        # Verify a signal was published
        assert len(mock_stream_manager.published) == 1
        published_msg = mock_stream_manager.published[0]
        assert published_msg["stream_name"] == "strategy_signals"
        assert published_msg["event_type"] == "signal_generated"
        assert published_msg["data"]["direction"] == "LONG"
        assert published_msg["data"]["symbol"] == "RELIANCE"
        assert published_msg["data"]["entry_price"] == 106.0


@pytest.mark.asyncio
async def test_breakout_strategy_agent(db_session, mock_stream_manager):
    """Test that BreakoutStrategyAgent registers candles and calculates features correctly."""
    agent = BreakoutStrategyAgent()
    
    # Simple check that it initializes
    assert agent.calculator is not None
    assert agent.running is False
    
    # Send a mock message (no signal should trigger on short history)
    message = {
        "event_type": "candle_complete",
        "data": {
            "symbol": "RELIANCE",
            "open": 100.0,
            "high": 105.0,
            "low": 95.0,
            "close": 101.0,
            "volume": 1000,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    await agent._on_candle(message)
    assert len(agent.candle_buffers["RELIANCE"]) == 1


@pytest.mark.asyncio
async def test_vwap_strategy_agent(db_session, mock_stream_manager):
    """Test that VwapStrategyAgent handles candle messages."""
    agent = VwapStrategyAgent()
    assert agent.running is False
    
    message = {
        "event_type": "candle_complete",
        "data": {
            "symbol": "TCS",
            "open": 3000.0,
            "high": 3050.0,
            "low": 2980.0,
            "close": 3020.0,
            "volume": 1500,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    await agent._on_candle(message)
    assert len(agent.candle_buffers["TCS"]) == 1


@pytest.mark.asyncio
async def test_options_strategy_agent(db_session, mock_stream_manager):
    """Test that OptionsStrategyAgent handles candle messages."""
    agent = OptionsStrategyAgent()
    assert agent.running is False
    
    message = {
        "event_type": "candle_complete",
        "data": {
            "symbol": "INFY",
            "open": 1400.0,
            "high": 1420.0,
            "low": 1390.0,
            "close": 1410.0,
            "volume": 5000,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    await agent._on_candle(message)
    assert len(agent.candle_buffers["INFY"]) == 1


@pytest.mark.asyncio
async def test_scalping_strategy_agent(db_session, mock_stream_manager):
    """Test that ScalpingStrategyAgent handles candle messages."""
    agent = ScalpingStrategyAgent()
    assert agent.running is False
    
    message = {
        "event_type": "candle_complete",
        "data": {
            "symbol": "HDFCBANK",
            "open": 1600.0,
            "high": 1610.0,
            "low": 1590.0,
            "close": 1605.0,
            "volume": 10000,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    await agent._on_candle(message)
    assert len(agent.candle_buffers["HDFCBANK"]) == 1
