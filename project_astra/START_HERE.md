# 🚀 START HERE - Agentic AI Trading Platform Local Setup

Welcome to **Project Astra** - Your local AI-powered multi-agent trading platform for Indian markets.

## ⚡ Quick Start (Choose Your OS)

### Windows Users

```cmd
cd C:\path\to\project_astra
scripts\quick_start.bat
```

### Linux/Mac Users

```bash
cd /workspace/project_astra
chmod +x scripts/quick_start.sh
./scripts/quick_start.sh
```

### Manual Start (All Platforms)

```bash
cd /workspace/project_astra

# Step 1: Copy environment file
cp .env.example .env

# Step 2: Start all services
docker-compose up -d --build

# Step 3: Wait 2 minutes, then initialize database
docker-compose exec backend python -m database.init_db

# Step 4: Open dashboard
# Navigate to: http://localhost:3000
```

---

## 🎯 What You Get

Once running, you'll have access to:

| Service | URL | Purpose |
|---------|-----|---------|
| 📊 **Dashboard** | http://localhost:3000 | Live trading interface |
| 🔌 **API** | http://localhost:8000 | Backend REST API |
| 📖 **API Docs** | http://localhost:8000/docs | Interactive Swagger UI |
| 📈 **Grafana** | http://localhost:3001 | Monitoring dashboards (admin/admin) |
| 📉 **Prometheus** | http://localhost:9090 | Metrics collection |

---

## ✅ Verify Installation

Run these commands to test your setup:

```bash
# Test 1: Check if all containers are running
docker-compose ps

# Test 2: Health check
curl http://localhost:8000/api/health

# Test 3: View current market regime
curl http://localhost:8000/api/market/regime

# Test 4: Check open positions
curl http://localhost:8000/api/trading/positions
```

---

## 🎮 First Steps

### 1. Explore the Dashboard

Open http://localhost:3000 in your browser.

You'll see:
- Live market data (simulated)
- Active strategies
- Open positions
- P&L tracking
- Risk metrics

### 2. Start Market Replay

Simulate historical market data:

```bash
docker-compose exec backend python -m replay_engine.start_replay \
  --speed 10x \
  --symbol NIFTY
```

This will:
- Load historical NIFTY data
- Replay at 10x speed
- Generate strategy signals
- Execute paper trades

### 3. Watch It Work

Monitor the system in real-time:

```bash
# View live logs
docker-compose logs -f backend

# Or watch specific agent
docker-compose logs -f backend | grep "strategy_agent"
```

### 4. Run a Backtest

Test a strategy on historical data:

```bash
docker-compose exec backend python -m backtesting.run_backtest \
  --strategy trend_following \
  --symbol RELIANCE \
  --start-date 2024-01-01 \
  --end-date 2024-03-31
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | Complete setup instructions |
| [scripts/test_commands.md](scripts/test_commands.md) | Testing commands reference |
| [README.md](README.md) | Full project documentation |

---

## 🛠 Common Tasks

### Start Everything
```bash
docker-compose up -d
```

### Stop Everything
```bash
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
```

### Restart Services
```bash
# All services
docker-compose restart

# Specific service
docker-compose restart backend
```

### Reset Everything (WARNING: Deletes Data)
```bash
docker-compose down -v
```

---

## 🐛 Troubleshooting

### Issue: "Port already in use"

**Solution:** Change ports in `docker-compose.yml` or stop the conflicting service.

```bash
# Find what's using port 8000
# Windows:
netstat -ano | findstr :8000

# Linux/Mac:
lsof -i :8000
```

### Issue: "Cannot connect to Docker"

**Solution:** 
- Windows: Ensure Docker Desktop is running
- Linux: `sudo systemctl start docker`
- Mac: Open Docker Desktop application

### Issue: "Database connection failed"

**Solution:**
```bash
# Wait for postgres to be ready
docker-compose logs -f postgres

# Reinitialize database
docker-compose exec backend python -m database.init_db
```

### Issue: "Backend won't start"

**Solution:**
```bash
# Check logs
docker-compose logs backend

# Rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### More Help

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed troubleshooting.

---

## 🎯 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     YOUR BROWSER                            │
│                  http://localhost:3000                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    NEXT.JS FRONTEND                         │
│              Dashboard, Charts, Controls                    │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST/WebSocket
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   FASTAPI BACKEND                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ MULTI-AGENT ORCHESTRATION                            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │   │
│  │  │ Market Data  │→ │   Regime     │→ │ Strategies │ │   │
│  │  │   Agent      │  │    Agent     │  │   Agents   │ │   │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │   │
│  │         ↓                  ↓                ↓        │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │   │
│  │  │     ML       │← │    Risk      │← │ Execution  │ │   │
│  │  │    Agent     │  │    Agent     │  │   Agent    │ │   │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────┬────────────────────┬──────────────────────────────┘
           │                    │
           ▼                    ▼
┌──────────────────┐  ┌──────────────────┐
│   POSTGRESQL     │  │      REDIS       │
│  + TimescaleDB   │  │     Streams      │
│  - Ticks         │  │  - market_ticks  │
│  - Candles       │  │  - candles_1m    │
│  - Features      │  │  - signals       │
│  - Orders        │  │  - orders        │
│  - Positions     │  │  - alerts        │
└──────────────────┘  └──────────────────┘
```

---

## 🧪 Key Features

### ✅ Paper Trading
- Simulated order execution
- Realistic slippage & latency
- Partial fill simulation
- No real money involved

### ✅ Multi-Agent System
- **Market Data Agent**: WebSocket feeds
- **Regime Agent**: Market state detection
- **Strategy Agents**: 5 independent strategies
- **ML Agent**: Trade ranking & scoring
- **Risk Agent**: Safety checks & veto
- **Execution Agent**: Order management
- **Monitoring Agent**: System health

### ✅ Replay Engine
- Historical data replay
- Variable speeds (1x to 50x)
- Full system testing
- Scenario simulation

### ✅ Backtesting
- Walk-forward analysis
- Realistic cost modeling
- Performance metrics
- Strategy comparison

### ✅ Monitoring
- Prometheus metrics
- Grafana dashboards
- Real-time alerts
- System health checks

---

## 📋 Prerequisites

Ensure you have installed:

- ✅ Docker Desktop (Windows/Mac) or Docker + Docker Compose (Linux)
- ✅ 8GB+ RAM (16GB recommended)
- ✅ 10GB free disk space
- ✅ Python 3.12 (optional, for development)
- ✅ Node.js 18+ (optional, for frontend development)

---

## 🎓 Learning Path

### Day 1: Setup & Exploration
1. Run quick start script
2. Explore dashboard
3. View API documentation
4. Check system logs

### Day 2: Understanding the System
1. Read agent documentation
2. Study Redis stream design
3. Review database schema
4. Examine strategy code

### Day 3: Running Tests
1. Start market replay
2. Observe signal generation
3. Monitor paper trades
4. Analyze results in Grafana

### Day 4: Customization
1. Modify strategy parameters
2. Adjust risk limits
3. Create custom alerts
4. Build new indicators

### Day 5: Advanced Usage
1. Run comprehensive backtests
2. Compare strategies
3. Optimize parameters
4. Develop new agents

---

## 🔐 Security Notes

⚠️ **IMPORTANT**: This is a **LOCAL DEVELOPMENT** version only.

- Do NOT expose these services to the internet
- Do NOT use real broker credentials initially
- Do NOT enable live trading without thorough testing
- Change default passwords before any production use

---

## 📞 Support & Resources

### Getting Help

1. Check logs: `docker-compose logs -f`
2. Review documentation in `/docs`
3. Examine example configurations
4. Test with curl commands from `scripts/test_commands.md`

### Useful Commands Reference

```bash
# Quick health check
curl http://localhost:8000/api/health

# View active strategies
curl http://localhost:8000/api/strategies/active

# Check positions
curl http://localhost:8000/api/trading/positions

# Get recent signals
curl http://localhost:8000/api/signals/recent?limit=5

# Access Redis CLI
docker-compose exec redis redis-cli

# Access PostgreSQL
docker-compose exec postgres psql -U postgres -d astra_trading
```

---

## 🎉 Next Steps

1. ✅ **Verify setup is working**
   ```bash
   curl http://localhost:8000/api/health
   ```

2. ✅ **Open the dashboard**
   - Navigate to http://localhost:3000

3. ✅ **Start a replay**
   ```bash
   docker-compose exec backend python -m replay_engine.start_replay --speed 10x
   ```

4. ✅ **Explore Grafana**
   - Navigate to http://localhost:3001
   - Login: admin / admin123

5. ✅ **Read the full documentation**
   - See SETUP_GUIDE.md for details
   - See scripts/test_commands.md for testing

---

## ⚠️ Disclaimer

This platform is for **EDUCATIONAL AND RESEARCH PURPOSES ONLY**.

- Paper trading mode by default
- No real orders placed
- Past performance ≠ future results
- Not financial advice
- Use at your own risk

---

**Ready to start?** Run the quick start script above! 🚀

For detailed instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md)
