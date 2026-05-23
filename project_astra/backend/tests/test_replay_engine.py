import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from replay_engine.engine import ReplayEngine

@pytest.mark.asyncio
async def test_replay_engine_controls(db_session, mock_stream_manager):
    """Test start, pause, resume, and stop controls of the ReplayEngine."""
    engine = ReplayEngine()
    
    # Verify default state
    status = await engine.get_status()
    assert status["running"] is False
    assert status["paused"] is False
    
    # Prepare mock candles
    from database.models import Candle
    mock_candles = [
        Candle(
            symbol="TCS",
            exchange="NSE",
            interval="5m",
            open=3000.0,
            high=3020.0,
            low=2990.0,
            close=3010.0,
            volume=5000,
            timestamp=datetime(2026, 5, 20, 9, 15)
        )
    ]
    
    # Mock DB query and websocket calls to run cleanly
    with patch("replay_engine.engine.async_session_factory") as mock_db, \
         patch("websocket.manager.ws_manager.send_candle_update", new_callable=AsyncMock):
        
        # Configure mock DB session execute
        mock_sess = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = mock_candles
        mock_sess.execute.return_value = mock_res
        mock_db.return_value.__aenter__.return_value = mock_sess
        
        # Start Replay
        start_time = datetime(2026, 5, 20, 9, 15)
        end_time = datetime(2026, 5, 20, 9, 20)
        
        # Use high speed to run the loop quickly
        await engine.start_replay("TCS", start_time, end_time, speed=100.0)
        
        status = await engine.get_status()
        assert status["running"] is True
        assert status["paused"] is False
        assert status["speed"] == 100.0
        
        # Pause
        await engine.pause_replay()
        status = await engine.get_status()
        assert status["paused"] is True
        
        # Resume
        await engine.resume_replay()
        status = await engine.get_status()
        assert status["paused"] is False
        
        # Stop
        await engine.stop_replay()
        status = await engine.get_status()
        assert status["running"] is False
