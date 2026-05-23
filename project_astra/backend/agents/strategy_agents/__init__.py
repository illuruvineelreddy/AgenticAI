"""
Strategy Agents Package
Exposes all 5 strategy agents
"""

from agents.strategy_agents.trend_agent.service import trend_agent, TrendStrategyAgent
from agents.strategy_agents.breakout_agent.service import breakout_agent, BreakoutStrategyAgent
from agents.strategy_agents.vwap_agent.service import vwap_agent, VwapStrategyAgent
from agents.strategy_agents.options_agent.service import options_agent, OptionsStrategyAgent
from agents.strategy_agents.scalping_agent.service import scalping_agent, ScalpingStrategyAgent

__all__ = [
    "trend_agent", "TrendStrategyAgent",
    "breakout_agent", "BreakoutStrategyAgent",
    "vwap_agent", "VwapStrategyAgent",
    "options_agent", "OptionsStrategyAgent",
    "scalping_agent", "ScalpingStrategyAgent"
]
