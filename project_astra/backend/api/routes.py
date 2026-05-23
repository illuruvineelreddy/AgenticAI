"""
API Routes for Project Astra
RESTful endpoints for frontend and external access
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/market/status")
async def get_market_status():
    """Get current market status."""
    from agents.regime_agent.service import regime_service
    
    regime = regime_service.get_current_regime()
    
    return {
        "market_open": True,  # Would check actual market hours
        "regime": regime.to_dict() if regime else None,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/positions")
async def get_positions():
    """Get current open positions."""
    from database.connection import get_sync_db_session
    from database.models import Position
    
    session = get_sync_db_session()
    try:
        positions = session.query(Position).filter(
            Position.status == 'OPEN'
        ).all()
        
        return {
            "positions": [
                {
                    "id": p.id,
                    "symbol": p.symbol,
                    "side": p.side,
                    "quantity": p.quantity,
                    "average_price": float(p.average_price),
                    "current_price": float(p.current_price) if p.current_price else None,
                    "unrealized_pnl": float(p.unrealized_pnl) if p.unrealized_pnl else None,
                    "entry_time": p.entry_time.isoformat() if p.entry_time else None,
                }
                for p in positions
            ],
            "count": len(positions),
        }
    finally:
        session.close()


@router.get("/orders")
async def get_orders(
    limit: int = Query(default=50, le=500),
    status: Optional[str] = None,
):
    """Get order history."""
    from database.connection import get_sync_db_session
    from database.models import Order
    
    session = get_sync_db_session()
    try:
        query = session.query(Order)
        
        if status:
            query = query.filter(Order.status == status)
        
        orders = query.order_by(Order.created_at.desc()).limit(limit).all()
        
        return {
            "orders": [
                {
                    "id": o.id,
                    "order_id": o.order_id,
                    "symbol": o.symbol,
                    "side": o.side,
                    "quantity": o.quantity,
                    "price": float(o.price) if o.price else None,
                    "status": o.status,
                    "filled_quantity": o.filled_quantity,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                }
                for o in orders
            ],
            "count": len(orders),
        }
    finally:
        session.close()


@router.get("/signals")
async def get_signals(limit: int = Query(default=50, le=500)):
    """Get recent strategy signals."""
    from database.connection import get_sync_db_session
    from database.models import StrategySignal
    
    session = get_sync_db_session()
    try:
        signals = session.query(StrategySignal)\
            .order_by(StrategySignal.created_at.desc())\
            .limit(limit)\
            .all()
        
        return {
            "signals": [
                {
                    "id": s.id,
                    "strategy": s.strategy_name,
                    "symbol": s.symbol,
                    "direction": s.direction,
                    "entry_price": float(s.entry_price),
                    "stop_loss": float(s.stop_loss) if s.stop_loss else None,
                    "target": float(s.target) if s.target else None,
                    "confidence": s.confidence,
                    "status": s.status,
                    "rationale": s.rationale,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in signals
            ],
            "count": len(signals),
        }
    finally:
        session.close()


@router.get("/pnl/summary")
async def get_pnl_summary():
    """Get PnL summary."""
    from database.connection import get_sync_db_session
    from database.models import Fill, Position
    from sqlalchemy import func
    
    session = get_sync_db_session()
    try:
        # Calculate realized PnL from fills
        realized_pnl = session.query(func.sum(Fill.pnl)).scalar() or 0
        
        # Calculate unrealized PnL from open positions
        unrealized_pnl = session.query(func.sum(Position.unrealized_pnl))\
            .filter(Position.status == 'OPEN')\
            .scalar() or 0
        
        return {
            "realized_pnl": float(realized_pnl),
            "unrealized_pnl": float(unrealized_pnl),
            "total_pnl": float(realized_pnl + unrealized_pnl),
            "currency": "INR",
        }
    finally:
        session.close()


@router.get("/alerts")
async def get_alerts(limit: int = Query(default=50, le=500)):
    """Get system alerts."""
    from database.connection import get_sync_db_session
    from database.models import Alert
    
    session = get_sync_db_session()
    try:
        alerts = session.query(Alert)\
            .order_by(Alert.created_at.desc())\
            .limit(limit)\
            .all()
        
        return {
            "alerts": [
                {
                    "id": a.id,
                    "type": a.alert_type,
                    "severity": a.severity,
                    "title": a.title,
                    "message": a.message,
                    "source": a.source,
                    "is_read": a.is_read,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in alerts
            ],
            "count": len(alerts),
        }
    finally:
        session.close()


@router.post("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: int):
    """Mark alert as read."""
    from database.connection import get_sync_db_session
    from database.models import Alert
    
    session = get_sync_db_session()
    try:
        alert = session.query(Alert).filter(Alert.id == alert_id).first()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert.is_read = True
        session.commit()
        
        return {"status": "success", "alert_id": alert_id}
    except HTTPException:
        raise
    finally:
        session.close()


@router.get("/config")
async def get_config():
    """Get system configuration."""
    from utils.config import settings
    
    return {
        "paper_trading_mode": settings.paper_trading_mode,
        "max_risk_per_trade": settings.max_risk_per_trade,
        "max_daily_drawdown": settings.max_daily_drawdown,
        "max_open_positions": settings.max_open_positions,
        "default_capital": settings.default_capital,
        "watchlist": settings.watchlist_nifty50,
        "enabled_strategies": ["trend", "vwap", "breakout", "options", "scalping"],
    }


@router.get("/metrics")
async def get_metrics():
    """Get system metrics."""
    return {
        "uptime": "running",
        "services": {
            "market_data": "active",
            "candle_engine": "active",
            "regime_detection": "active",
            "strategy_agents": "active",
            "risk_agent": "active",
            "execution": "active",
            "monitoring": "active",
        },
        "redis_streams": {
            "market_ticks": "streaming",
            "candles_1m": "streaming",
            "candles_5m": "streaming",
            "strategy_signals": "active",
            "execution_orders": "active",
        },
    }
