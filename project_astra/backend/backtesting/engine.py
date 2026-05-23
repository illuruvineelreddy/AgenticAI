"""
Historical Backtesting Engine for Project Astra
Runs strategies against historical candle data with transaction cost simulation.
"""

from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sqlalchemy import select
from typing import Dict, List, Any, Optional
import structlog

from database.connection import async_session_factory
from database.models import Candle
from backtesting.charges import IndianBrokerageCalculator
from feature_engine.calculator import FeatureCalculator

logger = structlog.get_logger()

class MockBacktestRedis:
    """Mock Redis stream manager to capture strategy signals during backtesting."""
    def __init__(self):
        self.signals = []
        self.STREAMS = {
            'STRATEGY_SIGNALS': 'strategy_signals',
            'CANDLES_5M': 'candles_5m',
            'CANDLES_1M': 'candles_1m'
        }

    async def connect(self):
        pass

    async def publish(self, stream_name: str, event_type: str, data: dict, source_agent: str) -> str:
        if stream_name == 'strategy_signals':
            self.signals.append(data)
        return "mock_msg_id"

    async def subscribe(self, *args, **kwargs):
        pass

class BacktestEngine:
    """Runs strategy simulations over historical candle data."""
    
    def __init__(self):
        self.calculator = FeatureCalculator()

    async def run(
        self,
        strategy_name: str,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 100000.0,
        is_delivery: bool = False
    ) -> Dict[str, Any]:
        """
        Executes a backtest simulation.
        Returns a dict of metrics, trades list, and equity curve.
        """
        logger.info(
            "Running backtest",
            strategy=strategy_name,
            symbol=symbol,
            start=start_date.isoformat(),
            end=end_date.isoformat()
        )
        
        # 1. Fetch historical candles
        candles = await self._fetch_historical_candles(symbol, start_date, end_date)
        if not candles:
            return {"error": f"No historical candle data found for {symbol} in date range."}

        logger.info("Fetched candles for backtest", count=len(candles))

        # 2. Instantiate strategy agent
        agent = self._instantiate_agent(strategy_name)
        if not agent:
            return {"error": f"Strategy {strategy_name} not recognized."}

        # Mock stream manager to capture signals
        mock_redis = MockBacktestRedis()
        agent.redis = mock_redis
        
        # 3. Replay loop
        capital = initial_capital
        equity_curve = []
        trades = []
        active_position = None  # Dict of: entry_price, qty, direction, stop_loss, target, entry_time
        
        candle_history = []
        
        for idx, candle in enumerate(candles):
            candle_history.append(candle)
            if len(candle_history) > 100:
                candle_history.pop(0)

            # Check if active position should be exited (Stop Loss or Target hit)
            if active_position:
                exit_triggered = False
                exit_price = 0.0
                exit_reason = ""
                
                high = candle['high']
                low = candle['low']
                close = candle['close']
                
                sl = active_position['stop_loss']
                tp = active_position['target']
                
                if active_position['direction'] == 'LONG':
                    if low <= sl:
                        exit_triggered = True
                        exit_price = sl
                        exit_reason = "Stop Loss"
                    elif high >= tp:
                        exit_triggered = True
                        exit_price = tp
                        exit_reason = "Target"
                else:  # SHORT
                    if high >= sl:
                        exit_triggered = True
                        exit_price = sl
                        exit_reason = "Stop Loss"
                    elif low <= tp:
                        exit_triggered = True
                        exit_price = tp
                        exit_reason = "Target"
                
                if exit_triggered:
                    # Calculate transaction costs
                    charges = IndianBrokerageCalculator.calculate_charges(
                        quantity=active_position['qty'],
                        price=exit_price,
                        side='SELL' if active_position['direction'] == 'LONG' else 'BUY',
                        is_delivery=is_delivery
                    )
                    
                    # Calculate gross P&L
                    if active_position['direction'] == 'LONG':
                        gross_pnl = (exit_price - active_position['entry_price']) * active_position['qty']
                    else:
                        gross_pnl = (active_position['entry_price'] - exit_price) * active_position['qty']
                        
                    net_pnl = gross_pnl - charges['total_charges']
                    capital += net_pnl
                    
                    trades.append({
                        'symbol': symbol,
                        'direction': active_position['direction'],
                        'qty': active_position['qty'],
                        'entry_price': active_position['entry_price'],
                        'exit_price': exit_price,
                        'entry_time': active_position['entry_time'],
                        'exit_time': candle['timestamp'].isoformat() if isinstance(candle['timestamp'], datetime) else str(candle['timestamp']),
                        'pnl': float(net_pnl),
                        'charges': float(charges['total_charges']),
                        'exit_reason': exit_reason
                    })
                    
                    active_position = None

            # Feed candle to strategy agent to see if it generates a new signal
            # We mock the envelope Redis structure
            mock_message = {
                'event_type': 'candle_complete',
                'data': {
                    'symbol': symbol,
                    'exchange': candle['exchange'],
                    'interval': candle['interval'],
                    'open': candle['open'],
                    'high': candle['high'],
                    'low': candle['low'],
                    'close': candle['close'],
                    'volume': candle['volume'],
                    'timestamp': candle['timestamp'].isoformat() if isinstance(candle['timestamp'], datetime) else str(candle['timestamp'])
                }
            }
            
            # Setup buffer inside agent
            agent.candle_buffers[symbol] = candle_history
            
            # Trigger callback
            await agent._on_candle(mock_message)
            
            # Process any newly generated signals
            if mock_redis.signals:
                sig = mock_redis.signals.pop(0)
                
                # If we don't have an active position, enter trade
                if not active_position:
                    entry_price = float(sig['entry_price'])
                    stop_loss = float(sig['stop_loss'])
                    target = float(sig['target'])
                    direction = sig['direction']
                    
                    # Size trade: risk 1% of current capital
                    risk_amount = capital * 0.01
                    risk_per_share = abs(entry_price - stop_loss)
                    
                    if risk_per_share > 0:
                        qty = int(risk_amount / risk_per_share)
                        qty = max(1, qty)  # Min 1 share
                    else:
                        qty = 1

                    # Apply transaction costs on entry
                    entry_charges = IndianBrokerageCalculator.calculate_charges(
                        quantity=qty,
                        price=entry_price,
                        side='BUY' if direction == 'LONG' else 'SELL',
                        is_delivery=is_delivery
                    )
                    
                    capital -= entry_charges['total_charges']
                    
                    active_position = {
                        'direction': direction,
                        'entry_price': entry_price,
                        'qty': qty,
                        'stop_loss': stop_loss,
                        'target': target,
                        'entry_time': sig['timestamp']
                    }
                    
            equity_curve.append({
                'time': candle['timestamp'].isoformat() if isinstance(candle['timestamp'], datetime) else str(candle['timestamp']),
                'equity': float(capital)
            })

        # Calculate metrics
        metrics = self._calculate_performance_metrics(initial_capital, capital, trades, equity_curve)
        
        return {
            'metrics': metrics,
            'trades': trades,
            'equity_curve': equity_curve
        }

    async def _fetch_historical_candles(self, symbol: str, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        """Queries historical candles from DB."""
        try:
            async with async_session_factory() as session:
                stmt = (
                    select(Candle)
                    .where(
                        Candle.symbol == symbol,
                        Candle.interval == '5m',
                        Candle.timestamp >= start,
                        Candle.timestamp <= end
                    )
                    .order_by(Candle.timestamp.asc())
                )
                res = await session.execute(stmt)
                db_candles = res.scalars().all()
                
                candles_list = []
                for c in db_candles:
                    candles_list.append({
                        'symbol': c.symbol,
                        'exchange': c.exchange,
                        'interval': c.interval,
                        'open': float(c.open),
                        'high': float(c.high),
                        'low': float(c.low),
                        'close': float(c.close),
                        'volume': int(c.volume),
                        'timestamp': c.timestamp
                    })
                return candles_list
        except Exception as e:
            logger.error("Failed to query historical candles for backtesting", symbol=symbol, error=str(e))
            return []

    def _instantiate_agent(self, strategy_name: str) -> Optional[Any]:
        """Maps strategy names to their agent classes."""
        from agents.strategy_agents import (
            TrendStrategyAgent, BreakoutStrategyAgent, VwapStrategyAgent,
            OptionsStrategyAgent, ScalpingStrategyAgent
        )
        if strategy_name == 'trend_strategy':
            return TrendStrategyAgent()
        elif strategy_name == 'breakout_strategy':
            return BreakoutStrategyAgent()
        elif strategy_name == 'vwap_strategy':
            return VwapStrategyAgent()
        elif strategy_name == 'options_strategy':
            return OptionsStrategyAgent()
        elif strategy_name == 'scalping_strategy':
            return ScalpingStrategyAgent()
        return None

    def _calculate_performance_metrics(
        self,
        initial_capital: float,
        final_capital: float,
        trades: List[Dict[str, Any]],
        equity_curve: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Computes trading ratios and performance metrics from the simulation."""
        total_pnl = final_capital - initial_capital
        total_return = (total_pnl / initial_capital) * 100.0
        
        total_trades = len(trades)
        if total_trades == 0:
            return {
                'total_return_pct': 0.0,
                'total_pnl': 0.0,
                'total_trades': 0,
                'win_rate': 0.0,
                'max_drawdown_pct': 0.0,
                'sharpe_ratio': 0.0,
                'profit_factor': 0.0,
            }

        pnls = [t['pnl'] for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        win_rate = (len(wins) / total_trades) * 100.0
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0
        
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Calculate Max Drawdown
        equities = [e['equity'] for e in equity_curve]
        peak = equities[0]
        max_dd = 0.0
        for eq in equities:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak
            if dd > max_dd:
                max_dd = dd
        
        # Calculate Sharpe Ratio (simplified)
        returns = pd.Series(equities).pct_change().dropna()
        if len(returns) > 1 and returns.std() > 0:
            # Assuming daily-like returns in standard deviation, annualized
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe = 0.0

        return {
            'total_return_pct': float(total_return),
            'total_pnl': float(total_pnl),
            'total_trades': int(total_trades),
            'win_rate': float(win_rate),
            'max_drawdown_pct': float(max_dd * 100.0),
            'sharpe_ratio': float(sharpe),
            'profit_factor': float(profit_factor) if profit_factor != float('inf') else 999.0,
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'expectancy': float((win_rate/100.0)*avg_win - (1 - win_rate/100.0)*abs(avg_loss))
        }
