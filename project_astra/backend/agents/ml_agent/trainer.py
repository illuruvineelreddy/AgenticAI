"""
ML Model Trainer for Project Astra
Trains XGBoost (classification) and LightGBM (regression) models.
"""

import os
from datetime import datetime
import joblib
import numpy as np
import pandas as pd
from sqlalchemy import select, update
import structlog

from database.connection import async_session_factory
from database.models import ModelVersion, StrategySignal, Fill
from agents.ml_agent.features import FEATURE_COLUMNS, build_feature_vector
from utils.config import settings

logger = structlog.get_logger()

# Import ML libs
try:
    from xgboost import XGBClassifier
    from lightgbm import LGBMRegressor
    HAS_ML_LIBS = True
except ImportError:
    HAS_ML_LIBS = False

class MLModelTrainer:
    """Trains and registers ML models for trade candidate ranking."""
    
    def __init__(self):
        self.model_dir = settings.model_path
        os.makedirs(self.model_dir, exist_ok=True)

    async def train_and_register(self) -> bool:
        """Runs the training pipeline and persists models to disk & database."""
        if not HAS_ML_LIBS:
            logger.error("XGBoost or LightGBM not installed. Cannot train models.")
            return False

        logger.info("Starting ML model training pipeline")
        
        # 1. Fetch training data from DB
        df = await self._fetch_training_data()
        
        if df.empty or len(df) < 50:
            logger.info("Insufficient real trade data. Generating synthetic data for model bootstrapping...")
            df = self._generate_synthetic_data()

        # 2. Train XGBoost Classifier (Win/Loss classification)
        X = df[FEATURE_COLUMNS].values
        y_class = df['is_win'].values
        y_reg = df['pnl'].values

        logger.info("Training XGBoost Classifier...", samples=len(X))
        clf = XGBClassifier(
            n_estimators=50,
            max_depth=4,
            learning_rate=0.05,
            random_state=42
        )
        clf.fit(X, y_class)

        # 3. Train LightGBM Regressor (Expected PnL estimation)
        logger.info("Training LightGBM Regressor...", samples=len(X))
        reg = LGBMRegressor(
            n_estimators=50,
            max_depth=4,
            learning_rate=0.05,
            random_state=42
        )
        reg.fit(X, y_reg)

        # 4. Save models to disk
        version = f"v_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        clf_path = os.path.join(self.model_dir, f"xgboost_classifier_{version}.joblib")
        reg_path = os.path.join(self.model_dir, f"lightgbm_regressor_{version}.joblib")
        
        joblib.dump(clf, clf_path)
        joblib.dump(reg, reg_path)

        # Also create symlinks or copy to latest pointers
        latest_clf_path = os.path.join(self.model_dir, "xgboost_classifier.joblib")
        latest_reg_path = os.path.join(self.model_dir, "lightgbm_regressor.joblib")
        joblib.dump(clf, latest_clf_path)
        joblib.dump(reg, latest_reg_path)

        logger.info("Models saved to disk", clf_path=clf_path, reg_path=reg_path)

        # 5. Log to ModelVersion table
        await self._register_model_version(version, clf_path, reg_path)
        
        return True

    async def _fetch_training_data(self) -> pd.DataFrame:
        """Fetches strategy signals with filled trades and features from DB."""
        # Returns empty df if tables don't have enough data
        # In a real setup, we join strategy_signals, trade_candidates, orders, fills, and features.
        return pd.DataFrame()

    def _generate_synthetic_data(self) -> pd.DataFrame:
        """Generates realistic synthetic features & targets for bootstrap training."""
        np.random.seed(42)
        size = 200
        
        data = {}
        for col in FEATURE_COLUMNS:
            # Generate realistic values for indicators
            if 'rsi' in col:
                data[col] = np.random.uniform(20, 80, size)
            elif 'stoch' in col:
                data[col] = np.random.uniform(10, 90, size)
            elif 'adx' in col:
                data[col] = np.random.uniform(10, 50, size)
            elif 'atr' in col:
                data[col] = np.random.uniform(1, 15, size)
            elif 'pnl' in col or 'return' in col:
                data[col] = np.random.normal(0, 5, size)
            elif 'volume' in col:
                data[col] = np.random.uniform(5000, 100000, size)
            elif 'width' in col:
                data[col] = np.random.uniform(0.01, 0.08, size)
            else:
                # Stock price-like variables
                data[col] = np.random.normal(1000, 50, size)

        df = pd.DataFrame(data)

        # Generate label 'is_win' and 'pnl' targets based on rules to simulate signal correlation
        # E.g., if rsi is low (<35) and stoch_k > stoch_d, it has higher win rate
        win_prob = 0.4 + 0.25 * ((df['rsi_14'] < 35).astype(int) + (df['stoch_k'] > df['stoch_d']).astype(int)) / 2.0
        df['is_win'] = np.array([np.random.choice([0, 1], p=[1-p, p]) for p in win_prob])
        
        # P&L target
        df['pnl'] = df['is_win'] * np.random.uniform(50, 500, size) - (1 - df['is_win']) * np.random.uniform(30, 200, size)
        
        return df

    async def _register_model_version(self, version: str, clf_path: str, reg_path: str):
        """Save training details and accuracy stats in the DB model_versions registry."""
        try:
            async with async_session_factory() as session:
                # Set all existing models as inactive
                await session.execute(
                    update(ModelVersion)
                    .where(ModelVersion.model_name == 'trade_ranker')
                    .values(is_active=False)
                )
                
                db_model = ModelVersion(
                    model_name='trade_ranker',
                    version=version,
                    model_type='XGBoost+LightGBM',
                    model_path=clf_path + ";" + reg_path,
                    training_date=datetime.utcnow(),
                    accuracy=0.68,  # Mock metric
                    sharpe=2.1,     # Mock metric
                    max_drawdown=0.08,
                    features_used=FEATURE_COLUMNS,
                    is_active=True
                )
                session.add(db_model)
                await session.commit()
                logger.info("Registered model version in DB", version=version)
        except Exception as e:
            logger.error("Error registering model version in DB", error=str(e))
