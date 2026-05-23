import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from main import app

client = TestClient(app)

def test_api_health():
    """Test the detailed health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data

def test_api_market_status():
    """Test /market/status returns regime data."""
    response = client.get("/api/v1/market/status")
    assert response.status_code == 200
    data = response.json()
    assert "market_open" in data
    assert "regime" in data

def test_api_positions(db_session):
    """Test retrieving open positions."""
    # Patch sync session query to mock returning positions
    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = []
    
    with patch("database.connection.get_sync_db_session") as mock_db:
        mock_db.return_value.query.return_value = mock_query
        
        response = client.get("/api/v1/positions")
        assert response.status_code == 200
        data = response.json()
        assert "positions" in data
        assert data["count"] == 0

def test_api_orders(db_session):
    """Test retrieving order history."""
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value.limit.return_value.all.return_value = []
    
    with patch("database.connection.get_sync_db_session") as mock_db:
        mock_db.return_value.query.return_value = mock_query
        
        response = client.get("/api/v1/orders")
        assert response.status_code == 200
        data = response.json()
        assert "orders" in data
        assert data["count"] == 0

def test_api_signals(db_session):
    """Test retrieving strategy signals."""
    mock_query = MagicMock()
    mock_query.order_by.return_value.limit.return_value.all.return_value = []
    
    with patch("database.connection.get_sync_db_session") as mock_db:
        mock_db.return_value.query.return_value = mock_query
        
        response = client.get("/api/v1/signals")
        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert data["count"] == 0

def test_api_pnl_summary(db_session):
    """Test /pnl/summary calculation logic."""
    with patch("database.connection.get_sync_db_session") as mock_db:
        session_instance = mock_db.return_value
        # Mock func.sum calls
        session_instance.query.return_value.scalar.return_value = 1500.0
        session_instance.query.return_value.filter.return_value.scalar.return_value = 500.0
        
        response = client.get("/api/v1/pnl/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["realized_pnl"] == 1500.0
        assert data["unrealized_pnl"] == 500.0
        assert data["total_pnl"] == 2000.0

def test_api_config():
    """Test retrieving system configurations."""
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    data = response.json()
    assert "watchlist" in data
    assert "paper_trading_mode" in data

def test_api_metrics():
    """Test retrieving monitoring metrics status."""
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["uptime"] == "running"
    assert "services" in data
    assert "redis_streams" in data

@patch("backtesting.engine.BacktestEngine.run", new_callable=AsyncMock)
def test_api_run_backtest(mock_run):
    """Test running a backtest via POST request."""
    mock_run.return_value = {"metrics": {"sharpe_ratio": 2.1}, "trades": []}
    
    payload = {
        "strategy": "trend_strategy",
        "symbol": "RELIANCE",
        "start_date": "2026-05-20T00:00:00Z",
        "end_date": "2026-05-21T00:00:00Z",
        "initial_capital": 50000.0
    }
    
    response = client.post("/api/v1/backtest/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert data["metrics"]["sharpe_ratio"] == 2.1

@patch("replay_engine.engine.replay_engine.start_replay", new_callable=AsyncMock)
def test_api_replay_start(mock_start):
    """Test starting a replay session via POST request."""
    mock_start.return_value = True
    
    payload = {
        "symbol": "INFY",
        "start_date": "2026-05-20T00:00:00Z",
        "end_date": "2026-05-21T00:00:00Z",
        "speed": 5.0
    }
    
    response = client.post("/api/v1/replay/start", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
