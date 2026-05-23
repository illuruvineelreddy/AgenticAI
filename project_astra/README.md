# Project Astra - Local Development Setup Guide

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker + Docker Compose (Linux)
- Python 3.12 (for local development outside Docker)
- Node.js 18+ (for frontend development)
- Git
- VS Code (recommended)
- 16GB+ RAM recommended

## Quick Start

### 1. Clone and Setup

```bash
cd /workspace/project_astra

# Copy environment file
cp .env.example .env

# Edit .env with your credentials (optional for paper trading)
```

### 2. Start All Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL + TimescaleDB (port 5432)
- Redis (port 6379)
- Backend FastAPI (port 8000)
- Frontend Next.js (port 3000)
- Prometheus (port 9090)
- Grafana (port 3001)

### 3. Verify Services

```bash
# Check all containers are running
docker-compose ps

# View logs
docker-compose logs -f backend

# Test backend health
curl http://localhost:8000/health

# Test API
curl http://localhost:8000/api/v1/market/status
```

### 4. Access Dashboards

- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **Grafana**: http://localhost:3001 (admin/admin123)
- **Prometheus**: http://localhost:9090

## Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Backend API | http://localhost:8000 | - |
| Frontend | http://localhost:3000 | - |
| Grafana | http://localhost:3001 | admin / admin123 |
| Prometheus | http://localhost:9090 | - |
| PostgreSQL | localhost:5432 | astra / astra_secure_123 |
| Redis | localhost:6379 | - |

## Development Workflow

### Hot Reload

The backend supports hot reload. Changes to Python files will automatically restart the server.

```bash
# View live logs
docker-compose logs -f backend
```

### Database Access

```bash
# Connect to PostgreSQL
docker exec -it astra-postgres psql -U astra -d astra_trading

# View tables
\dt

# Query data
SELECT * FROM strategy_signals LIMIT 10;
```

### Redis Access

```bash
# Connect to Redis CLI
docker exec -it astra-redis redis-cli

# View streams
XRANGE market_ticks - +

# Stream info
XINFO STREAM market_ticks
```

### Testing

```bash
# Run tests inside backend container
docker exec -it astra-backend pytest

# Run with coverage
docker exec -it astra-backend pytest --cov=.
```

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

## Troubleshooting

### Port Already in Use

If ports are in use, edit `.env` and change:
```
BACKEND_PORT=8001
FRONTEND_PORT=3001
GRAFANA_PORT=3002
```

### Database Connection Issues

```bash
# Check PostgreSQL is healthy
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

### Redis Connection Issues

```bash
# Check Redis is running
docker exec astra-redis redis-cli ping

# Should return: PONG
```

## Paper Trading Mode

By default, the system runs in PAPER TRADING MODE:
- No real money involved
- Simulated order execution
- Realistic slippage and latency
- Full Indian brokerage charges simulation

To enable live trading (NOT RECOMMENDED initially):
1. Add broker credentials to `.env`
2. Set `PAPER_TRADING_MODE=false`
3. Restart services

## Next Steps

1. Explore the API at http://localhost:8000/docs
2. Check Grafana dashboards for metrics
3. Review logs for system activity
4. Configure Telegram alerts (optional)
5. Add custom strategies in `backend/agents/strategy_agents/`
