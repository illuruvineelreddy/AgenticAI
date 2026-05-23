"""
Configuration Management for Project Astra
Loads settings from environment variables and YAML configs
"""

import os
from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # =====================================================================
    # Environment
    # =====================================================================
    environment: str = Field(default="development", description="Environment name")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # =====================================================================
    # Database Configuration
    # =====================================================================
    db_host: str = Field(default="localhost", description="PostgreSQL host")
    db_port: int = Field(default=5432, description="PostgreSQL port")
    db_user: str = Field(default="astra", description="PostgreSQL user")
    db_password: str = Field(default="astra_secure_123", description="PostgreSQL password")
    db_name: str = Field(default="astra_trading", description="PostgreSQL database name")
    
    @property
    def database_url(self) -> str:
        """Construct async PostgreSQL URL."""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def sync_database_url(self) -> str:
        """Construct sync PostgreSQL URL for migrations."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    # =====================================================================
    # Redis Configuration
    # =====================================================================
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    
    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # =====================================================================
    # Broker Configuration
    # =====================================================================
    broker_api_key: Optional[str] = Field(default=None, description="Broker API key")
    broker_api_secret: Optional[str] = Field(default=None, description="Broker API secret")
    broker_name: str = Field(default="zerodha", description="Broker name")
    
    # =====================================================================
    # Trading Configuration
    # =====================================================================
    paper_trading_mode: bool = Field(default=True, description="Enable paper trading mode")
    max_risk_per_trade: float = Field(default=0.01, description="Max risk per trade (1%)")
    max_daily_drawdown: float = Field(default=0.03, description="Max daily drawdown (3%)")
    max_open_positions: int = Field(default=5, description="Maximum open positions")
    default_capital: float = Field(default=1000000, description="Default capital for paper trading")
    
    # =====================================================================
    # Replay Engine Configuration
    # =====================================================================
    replay_speed: str = Field(default="1x", description="Replay speed multiplier")
    replay_start_date: Optional[str] = Field(default=None, description="Replay start date")
    replay_end_date: Optional[str] = Field(default=None, description="Replay end date")
    
    # =====================================================================
    # ML Configuration
    # =====================================================================
    model_path: str = Field(default="/models", description="Path to ML models")
    dataset_path: str = Field(default="/datasets", description="Path to datasets")
    enable_shap: bool = Field(default=True, description="Enable SHAP explanations")
    ml_inference_batch_size: int = Field(default=100, description="ML inference batch size")
    
    # =====================================================================
    # Telegram Notifications
    # =====================================================================
    telegram_bot_token: Optional[str] = Field(default=None, description="Telegram bot token")
    telegram_chat_id: Optional[str] = Field(default=None, description="Telegram chat ID")
    telegram_enabled: bool = Field(default=False, description="Enable Telegram alerts")
    
    # =====================================================================
    # Frontend Configuration
    # =====================================================================
    backend_port: int = Field(default=8000, description="Backend port")
    frontend_port: int = Field(default=3000, description="Frontend port")
    
    # =====================================================================
    # Monitoring Configuration
    # =====================================================================
    prometheus_port: int = Field(default=9090, description="Prometheus port")
    grafana_port: int = Field(default=3001, description="Grafana port")
    
    # =====================================================================
    # Instrument Lists
    # =====================================================================
    watchlist_nifty50: List[str] = Field(
        default=[
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
            "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK",
            "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "SUNPHARMA",
            "TITAN", "BAJFINANCE", "ULTRACEMCO", "NESTLEIND", "WIPRO",
        ],
        description="Nifty 50 stock symbols",
    )
    
    watchlist_niftybank: List[str] = Field(
        default=[
            "HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK",
            "INDUSINDBK", "BANDHANBNK", "FEDERALBNK", "IDFCFIRSTB", "RBLBANK",
        ],
        description="Nifty Bank stock symbols",
    )
    
    indices: List[str] = Field(
        default=["NIFTY 50", "NIFTY BANK", "NIFTY IT", "NIFTY MIDCAP 100"],
        description="Market indices to track",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
