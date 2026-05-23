# Local Development Setup Guide - Agentic AI Trading Platform

## Prerequisites

Ensure you have the following installed on your machine:

- **Docker Desktop** (Windows/Mac) or **Docker + Docker Compose** (Linux)
- **Python 3.12** (optional, for local development outside Docker)
- **Node.js 18+** (optional, for frontend development)
- **Git**
- **VS Code** (recommended)

## Quick Start (5 Minutes)

### Step 1: Navigate to Project Directory

```bash
cd /workspace/project_astra
```

### Step 2: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials (optional for paper trading)
# For initial testing, default values work fine
nano .env  # or use your preferred editor
```

**Important:** For paper trading mode, you don't need real broker credentials. The system will run in simulation mode by default.

### Step 3: Start All Services

```bash
# Build and start all containers
docker-compose up -d --build
```

This will start:
- PostgreSQL + TimescaleDB
- Redis
- Backend (FastAPI with hot reload)
- Frontend (Next.js)
- Prometheus
- Grafana

### Step 4: Verify Services Are Running

```bash
# Check all containers are healthy
docker-compose ps

# View logs if needed
docker-compose logs -f
```

Expected output should show all services as "healthy" or "running".

### Step 5: Initialize Database

```bash
# Run database migrations
docker-compose exec backend python -m database.init_db
```

### Step 6: Load Sample Data (Optional)

```bash
# Load historical data for replay testing
docker-compose exec backend python scripts/load_sample_data.py
```

## Access Points

Once everything is running, access the following URLs:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend Dashboard** | http://localhost:3000 | No login required (dev mode) |
| **Backend API** | http://localhost:8000 | - |
| **API Docs (Swagger)** | http://localhost:8000/docs | - |
| **Grafana** | http://localhost:3001 | admin / admin |
| **Prometheus** | http://localhost:9090 | - |
| **Redis Insight** (if installed) | localhost:6379 | - |

## Testing the System

### Test 1: Check API Health

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{"status": "healthy", "services": {"database": "ok", "redis": "ok"}}
```

### Test 2: Start Market Data Replay

```bash
# Start replay engine at 10x speed
docker-compose exec backend python -m replay_engine.start_replay --speed 10x --symbol NIFTY
```

### Test 3: View Active Strategies

```bash
curl http://localhost:8000/api/strategies/active
```

### Test 4: Check Current Regime

```bash
curl http://localhost:8000/api/market/regime
```

### Test 5: View Open Positions (Paper Trading)

```bash
curl http://localhost:8000/api/trading/positions
```

## Common Operations

### Start Paper Trading Mode

```bash
docker-compose exec backend python -m paper_trading.start_engine
```

### Start Specific Agent

```bash
# Example: Start only the regime agent
docker-compose exec backend python -m backend.agents.regime_agent.main
```

### Run Backtest

```bash
docker-compose exec backend python -m backtesting.run_backtest \
  --strategy trend_following \
  --symbol NIFTY \
  --start-date 2024-01-01 \
  --end-date 2024-12-31
```

### View Logs

```bash
# All logs
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f redis

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
docker-compose restart frontend
```

### Stop Everything

```bash
docker-compose down
```

### Stop and Remove All Data

```bash
# WARNING: This deletes all data
docker-compose down -v
```

## Development Workflow

### Hot Reload (Backend)

The backend automatically reloads when you modify Python files:

```bash
# Edit files in /workspace/project_astra/backend/
# Changes are detected automatically
```

### Hot Reload (Frontend)

```bash
# Edit files in /workspace/project_astra/frontend/
# Next.js automatically rebuilds
```

### Run Tests

```bash
# Backend tests
docker-compose exec backend pytest

# Frontend tests
docker-compose exec frontend npm test
```

### Debug Mode

```bash
# Start with verbose logging
docker-compose up -d --build
docker-compose exec backend python -m debugpy --listen 0.0.0.0:5678 -m backend.main
```

Then attach VS Code debugger to localhost:5678

## Troubleshooting

### Issue: Port Already in Use

```bash
# Check what's using the port
netstat -ano | findstr :8000  # Windows
lsof -i :8000  # Linux/Mac

# Change port in docker-compose.yml or stop the conflicting service
```

### Issue: Database Connection Failed

```bash
# Check if postgres is running
docker-compose ps postgres

# View postgres logs
docker-compose logs postgres

# Restart postgres
docker-compose restart postgres

# Reinitialize database
docker-compose exec backend python -m database.init_db
```

### Issue: Redis Connection Failed

```bash
# Check redis status
docker-compose ps redis

# Test redis connection
docker-compose exec redis redis-cli ping
# Should return: PONG
```

### Issue: Backend Won't Start

```bash
# Check logs
docker-compose logs backend

# Common fixes:
# 1. Ensure .env file exists
# 2. Check if ports 8000 is free
# 3. Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Issue: High Memory Usage

```bash
# Limit container resources in docker-compose.yml
# Or reduce replay speed
docker-compose exec backend python -m replay_engine.start_replay --speed 1x
```

## VS Code Setup

### Recommended Extensions

1. Python (Microsoft)
2. Pylance
3. Docker
4. ESLint (for frontend)
5. Prettier
6. Thunder Client (API testing)
7. Grafana

### Launch Configurations (.vscode/launch.json)

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Remote Attach",
      "type": "python",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}/backend",
          "remoteRoot": "/app/backend"
        }
      ]
    }
  ]
}
```

## Monitoring & Observability

### Grafana Dashboards

Access Grafana at http://localhost:3001 (admin/admin)

Pre-configured dashboards:
- System Overview
- Agent Performance
- Trade Analytics
- Risk Metrics
- Market Data Quality

### Prometheus Metrics

Access at http://localhost:9090

Key metrics:
- `agent_signals_total` - Strategy signals generated
- `trade_executions_total` - Paper trades executed
- `pnl_cumulative` - Cumulative P&L
- `redis_stream_lag` - Stream processing lag
- `api_request_duration_seconds` - API latency

## Next Steps

1. **Explore the Dashboard**: http://localhost:3000
2. **Run a Replay**: Test with historical data
3. **Configure Strategies**: Edit YAML configs in `backend/configs/strategies/`
4. **Set Up Alerts**: Configure Telegram in `.env`
5. **Develop Custom Strategies**: Add new agents in `backend/agents/strategy_agents/`

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Verify health: `curl http://localhost:8000/api/health`
3. Review documentation in `/workspace/project_astra/README.md`

---

**Remember**: This is PAPER TRADING MODE ONLY. No real orders will be placed.
