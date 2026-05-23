"""
Project Astra - Agentic AI Trading Platform for Indian Markets
Main FastAPI Application Entry Point
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import structlog

from api.routes import router as api_router
from websocket.manager import ConnectionManager
from database.connection import init_db
from agents.market_data_agent.service import MarketDataService
from agents.regime_agent.service import RegimeService
from agents.ml_agent.service import MLService
from agents.risk_agent.service import RiskService
from agents.execution_agent.service import ExecutionService
from agents.monitoring_agent.service import MonitoringService
from candle_engine.engine import CandleEngine
from feature_engine.service import FeatureService
from agents.strategy_agents import (
    TrendStrategyAgent, BreakoutStrategyAgent, VwapStrategyAgent,
    OptionsStrategyAgent, ScalpingStrategyAgent
)
from utils.config import settings
from utils.metrics import setup_metrics

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.log_level)),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger()

# Global connection manager for WebSockets
ws_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    
    logger.info("Starting Project Astra - Agentic AI Trading Platform")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Setup Prometheus metrics
    setup_metrics()
    logger.info("Metrics configured")
    
    # Start background services
    tasks = []
    
    # Start market data service
    market_data_service = MarketDataService()
    tasks.append(asyncio.create_task(market_data_service.run()))
    logger.info("Market data service started")
    
    # Start candle engine
    candle_engine = CandleEngine()
    tasks.append(asyncio.create_task(candle_engine.run()))
    logger.info("Candle engine started")

    # Start feature service
    feature_service = FeatureService()
    tasks.append(asyncio.create_task(feature_service.run()))
    logger.info("Feature service started")

    # Start regime detection service
    regime_service = RegimeService()
    tasks.append(asyncio.create_task(regime_service.run()))
    logger.info("Regime service started")
    
    # Start strategy agents
    trend_agent = TrendStrategyAgent()
    tasks.append(asyncio.create_task(trend_agent.run()))
    breakout_agent = BreakoutStrategyAgent()
    tasks.append(asyncio.create_task(breakout_agent.run()))
    vwap_agent = VwapStrategyAgent()
    tasks.append(asyncio.create_task(vwap_agent.run()))
    options_agent = OptionsStrategyAgent()
    tasks.append(asyncio.create_task(options_agent.run()))
    scalping_agent = ScalpingStrategyAgent()
    tasks.append(asyncio.create_task(scalping_agent.run()))
    logger.info("All strategy agents started")

    # Start ML inference service
    ml_service = MLService()
    tasks.append(asyncio.create_task(ml_service.run()))
    logger.info("ML service started")
    
    # Start risk management service
    risk_service = RiskService()
    tasks.append(asyncio.create_task(risk_service.run()))
    logger.info("Risk service started")
    
    # Start execution service (paper trading)
    execution_service = ExecutionService()
    tasks.append(asyncio.create_task(execution_service.run()))
    logger.info("Execution service started")
    
    # Start monitoring service
    monitoring_service = MonitoringService()
    tasks.append(asyncio.create_task(monitoring_service.run()))
    logger.info("Monitoring service started")
    
    yield
    
    # Shutdown: Cancel all background tasks
    logger.info("Shutting down services...")
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("All services stopped")


# Initialize FastAPI application
app = FastAPI(
    title="Project Astra - Agentic AI Trading Platform",
    description="Multi-agent AI trading system for Indian markets with paper trading support",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "status": "healthy",
        "service": "Project Astra",
        "version": "1.0.0",
        "mode": "paper_trading" if settings.paper_trading_mode else "live",
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "services": {
            "database": "connected",
            "redis": "connected",
            "websocket": "running",
        },
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates to frontend."""
    await ws_manager.connect(websocket)
    logger.info("WebSocket client connected")
    
    try:
        while True:
            # Keep connection alive, receive messages from client if needed
            data = await websocket.receive_text()
            # Process client messages if any
            logger.debug("Received from client", message=data)
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower(),
    )
