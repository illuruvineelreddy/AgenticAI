"""
Prometheus Metrics Configuration
"""

from prometheus_client import Counter, Gauge, Histogram, Summary, start_http_server
from utils.config import settings

# =============================================================================
# METRICS DEFINITIONS
# =============================================================================

# Market Data Metrics
market_ticks_total = Counter(
    'market_ticks_total',
    'Total number of market ticks received',
    ['symbol', 'exchange']
)

tick_latency_seconds = Histogram(
    'tick_latency_seconds',
    'Latency of tick processing',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Candle Metrics
candles_created_total = Counter(
    'candles_created_total',
    'Total number of candles created',
    ['symbol', 'interval']
)

# Strategy Metrics
strategy_signals_total = Counter(
    'strategy_signals_total',
    'Total number of strategy signals generated',
    ['strategy', 'symbol', 'direction']
)

signal_confidence = Gauge(
    'signal_confidence',
    'Confidence score of strategy signals',
    ['strategy', 'symbol']
)

# Risk Metrics
risk_checks_total = Counter(
    'risk_checks_total',
    'Total number of risk checks performed',
    ['result']
)

trades_approved_total = Counter(
    'trades_approved_total',
    'Total number of trades approved',
    ['symbol']
)

trades_rejected_total = Counter(
    'trades_rejected_total',
    'Total number of trades rejected',
    ['reason']
)

# Execution Metrics
orders_total = Counter(
    'orders_total',
    'Total number of orders placed',
    ['symbol', 'side', 'status']
)

order_fill_ratio = Gauge(
    'order_fill_ratio',
    'Ratio of filled quantity to order quantity',
    ['symbol']
)

execution_latency_seconds = Histogram(
    'execution_latency_seconds',
    'Latency of order execution',
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Position Metrics
open_positions = Gauge(
    'open_positions',
    'Number of currently open positions',
    ['symbol']
)

position_pnl = Gauge(
    'position_pnl',
    'Unrealized PnL of positions',
    ['symbol']
)

total_unrealized_pnl = Gauge(
    'total_unrealized_pnl',
    'Total unrealized PnL across all positions'
)

total_realized_pnl = Gauge(
    'total_realized_pnl',
    'Total realized PnL'
)

# System Metrics
system_uptime = Gauge(
    'system_uptime',
    'System uptime in seconds'
)

redis_stream_lag = Gauge(
    'redis_stream_lag',
    'Lag in Redis Stream consumption',
    ['stream_name']
)

agent_status = Gauge(
    'agent_status',
    'Status of agents (1=running, 0=stopped)',
    ['agent_name']
)

# Regime Metrics
current_regime = Gauge(
    'current_regime',
    'Current market regime',
    ['regime']
)

regime_confidence = Gauge(
    'regime_confidence',
    'Confidence in current regime detection'
)


def setup_metrics():
    """Setup and start Prometheus metrics server."""
    # Start Prometheus HTTP server
    start_http_server(settings.prometheus_port)
    print(f"Prometheus metrics available at http://localhost:{settings.prometheus_port}")


def update_system_uptime(start_time: float):
    """Update system uptime metric."""
    import time
    system_uptime.set(time.time() - start_time)


def update_agent_status(agent_name: str, is_running: bool):
    """Update agent status metric."""
    agent_status.labels(agent_name=agent_name).set(1 if is_running else 0)
