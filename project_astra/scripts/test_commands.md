# Quick Test Commands - Agentic AI Trading Platform

After running the quick start script, use these commands to test the system.

## 1. Health Check

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T10:00:00Z",
  "services": {
    "database": "connected",
    "redis": "connected",
    "market_data": "running"
  }
}
```

## 2. Check Available Endpoints

Open in browser: http://localhost:8000/docs

This shows the interactive Swagger API documentation.

## 3. Get Market Regime

```bash
curl http://localhost:8000/api/market/regime
```

Expected response:
```json
{
  "current_regime": "SIDEWAYS",
  "confidence": 0.75,
  "vix_level": 15.5,
  "trend_strength": 0.3,
  "volatility": "NORMAL",
  "allowed_strategies": ["mean_reversion", "scalping"],
  "risk_multiplier": 0.8
}
```

## 4. List Active Strategies

```bash
curl http://localhost:8000/api/strategies/active
```

Expected response:
```json
{
  "active_strategies": [
    {
      "name": "trend_following",
      "status": "running",
      "signals_today": 5,
      "win_rate": 0.65
    },
    {
      "name": "vwap_mean_reversion",
      "status": "running",
      "signals_today": 8,
      "win_rate": 0.58
    }
  ]
}
```

## 5. View Open Positions (Paper Trading)

```bash
curl http://localhost:8000/api/trading/positions
```

Expected response:
```json
{
  "positions": [
    {
      "symbol": "RELIANCE",
      "quantity": 100,
      "entry_price": 2450.50,
      "current_price": 2455.00,
      "pnl": 450.00,
      "pnl_percent": 0.18,
      "strategy": "trend_following",
      "entry_time": "2024-01-01T09:30:00Z"
    }
  ],
  "total_pnl": 450.00,
  "total_positions": 1
}
```

## 6. Get Recent Signals

```bash
curl http://localhost:8000/api/signals/recent?limit=10
```

Expected response:
```json
{
  "signals": [
    {
      "timestamp": "2024-01-01T10:15:00Z",
      "symbol": "NIFTY",
      "strategy": "breakout",
      "direction": "BUY",
      "entry": 21500,
      "stop_loss": 21450,
      "target": 21600,
      "confidence": 0.82,
      "status": "pending"
    }
  ]
}
```

## 7. Start Replay Engine

```bash
# Start replay at 10x speed
docker-compose exec backend python -m replay_engine.start_replay \
  --speed 10x \
  --symbol NIFTY \
  --date 2024-01-01

# Or use preset scenarios
docker-compose exec backend python -m replay_engine.start_replay \
  --scenario "high_volatility" \
  --speed 5x
```

## 8. Run Backtest

```bash
docker-compose exec backend python -m backtesting.run_backtest \
  --strategy trend_following \
  --symbol RELIANCE \
  --start-date 2024-01-01 \
  --end-date 2024-03-31 \
  --initial-capital 100000
```

Expected output includes:
- Total Return
- Sharpe Ratio
- Max Drawdown
- Win Rate
- Profit Factor

## 9. Check Redis Streams

```bash
# Connect to Redis CLI
docker-compose exec redis redis-cli

# In Redis CLI:
# List all streams
XINFO STREAMS

# Check market_ticks stream length
XLEN market_ticks

# Read last 5 ticks from market_ticks
XREVRANGE market_ticks + - COUNT 5

# Check strategy_signals stream
XLEN strategy_signals

# Exit Redis CLI
EXIT
```

## 10. Check Database Tables

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d trading_platform

# In PostgreSQL:
# List all tables
\dt

# Count candles
SELECT COUNT(*) FROM candles_1m;

# Count signals
SELECT COUNT(*) FROM strategy_signals;

# View recent positions
SELECT * FROM positions ORDER BY created_at DESC LIMIT 10;

# Exit PostgreSQL
\q
```

## 11. View Agent Logs

```bash
# Real-time logs for all services
docker-compose logs -f

# Only backend logs
docker-compose logs -f backend

# Last 100 lines of backend logs
docker-compose logs --tail=100 backend

# Search for errors
docker-compose logs backend | grep ERROR
```

## 12. Test WebSocket Connection

```bash
# Install wscat if not available
npm install -g wscat

# Connect to WebSocket
wscat -c ws://localhost:8000/ws/market

# You should receive tick data
```

Or use Python:

```python
import websocket
import json

def on_message(ws, message):
    print(f"Received: {json.loads(message)}")

ws = websocket.WebSocketApp(
    "ws://localhost:8000/ws/market",
    on_message=on_message
)
ws.run_forever()
```

## 13. Monitor Prometheus Metrics

Open browser: http://localhost:9090

Try these queries:
- `agent_signals_total` - Total signals generated
- `trade_executions_total` - Total trades executed
- `pnl_cumulative` - Cumulative P&L
- `redis_stream_lag_seconds` - Stream processing lag
- `api_request_duration_seconds` - API latency

## 14. View Grafana Dashboards

Open browser: http://localhost:3001
Login: admin / admin

Pre-configured dashboards:
1. **System Overview** - Overall system health
2. **Agent Performance** - Individual agent metrics
3. **Trade Analytics** - P&L, win rate, drawdown
4. **Risk Metrics** - Exposure, VaR, limits
5. **Market Data Quality** - Tick/candle statistics

## 15. Send Test Alert (Telegram)

```bash
curl -X POST http://localhost:8000/api/alerts/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Test alert from trading platform"}'
```

## 16. Stop Specific Agent

```bash
# Example: Stop the breakout agent
curl -X POST http://localhost:8000/api/agents/breakout_agent/stop
```

## 17. Restart Specific Agent

```bash
# Example: Restart the regime agent
curl -X POST http://localhost:8000/api/agents/regime_agent/restart
```

## 18. Get System Metrics

```bash
curl http://localhost:8000/api/system/metrics
```

Expected response:
```json
{
  "cpu_usage": 45.2,
  "memory_usage_mb": 2048,
  "redis_memory_mb": 128,
  "postgres_connections": 15,
  "active_streams": 10,
  "messages_per_second": 150
}
```

## 19. Export Trade History

```bash
curl http://localhost:8000/api/trading/history/export?format=csv \
  --output trade_history.csv
```

## 20. Validate Configuration

```bash
curl http://localhost:8000/api/config/validate
```

---

## Common Testing Scenarios

### Scenario 1: Full System Test

```bash
# 1. Start replay
docker-compose exec backend python -m replay_engine.start_replay --speed 10x

# 2. Wait 2 minutes for signals

# 3. Check positions
curl http://localhost:8000/api/trading/positions

# 4. View P&L
curl http://localhost:8000/api/trading/pnl

# 5. Stop replay
docker-compose exec backend python -m replay_engine.stop_replay
```

### Scenario 2: Strategy Isolation Test

```bash
# Disable all strategies except one
curl -X POST http://localhost:8000/api/strategies/disable_all

curl -X POST http://localhost:8000/api/strategies/trend_following/enable

# Run test for 5 minutes
# Check only trend_following signals appear
curl http://localhost:8000/api/signals/recent?strategy=trend_following
```

### Scenario 3: Risk Agent Test

```bash
# Try to place a risky trade (should be rejected)
curl -X POST http://localhost:8000/api/trading/test_order \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NIFTY",
    "quantity": 10000,
    "action": "BUY",
    "price": 21500
  }'

# Should receive rejection with reason
```

### Scenario 4: Failover Test

```bash
# Stop one agent
docker-compose stop backend

# Start it again
docker-compose start backend

# Verify system continues running
curl http://localhost:8000/api/health
```

---

## Quick Reference Card

| Action | Command |
|--------|---------|
| Start All | `docker-compose up -d` |
| Stop All | `docker-compose down` |
| View Logs | `docker-compose logs -f` |
| Health Check | `curl localhost:8000/api/health` |
| Frontend | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |
| Grafana | http://localhost:3001 |
| Redis CLI | `docker-compose exec redis redis-cli` |
| Postgres CLI | `docker-compose exec postgres psql -U postgres` |
