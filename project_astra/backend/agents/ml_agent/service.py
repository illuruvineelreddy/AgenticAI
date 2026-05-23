"""
ML Agent - Machine Learning Inference Service
Uses XGBoost/LightGBM for trade candidate ranking and scoring
"""

import asyncio
from datetime import datetime
import os
import joblib
import structlog
from sqlalchemy import select

from utils.redis_streams import stream_manager
from utils.config import settings
from database.connection import async_session_factory
from database.models import TradeCandidate, StrategySignal
from agents.ml_agent.features import get_features_for_signal, build_feature_vector
from agents.ml_agent.trainer import MLModelTrainer

logger = structlog.get_logger()

class MLService:
    """
    ML Inference Agent.
    Loads models on startup (or triggers auto-training if missing).
    Scores approved trade candidates from Risk Agent and persists them.
    """
    
    def __init__(self):
        self.running = False
        self.clf_model = None
        self.reg_model = None
        self.models_loaded = False
        
    async def run(self):
        """Start ML service."""
        self.running = True
        logger.info("ML Service starting")
        
        # Connect to Redis
        await stream_manager.connect()
        
        # Load ML models (trains if missing)
        await self.load_models()
        
        # Subscribe to risk-approved signals for ML scoring
        await stream_manager.subscribe(
            stream_name=stream_manager.STREAMS['RISK_APPROVED'],
            callback=self._on_trade_approved,
            consumer_group='ml_agent',
            consumer_name='ml_scorer_1',
        )
        
        while self.running:
            await asyncio.sleep(1)
            
    async def load_models(self):
        """Load trained ML models from disk. Trains them if they don't exist."""
        clf_path = os.path.join(settings.model_path, "xgboost_classifier.joblib")
        reg_path = os.path.join(settings.model_path, "lightgbm_regressor.joblib")
        
        if not os.path.exists(clf_path) or not os.path.exists(reg_path):
            logger.info("ML models not found on disk. Initiating bootstrapping...")
            trainer = MLModelTrainer()
            success = await trainer.train_and_register()
            if not success:
                logger.warn("Model bootstrapping failed. Running in fallback mode.")
                return

        try:
            self.clf_model = joblib.load(clf_path)
            self.reg_model = joblib.load(reg_path)
            self.models_loaded = True
            logger.info("ML models successfully loaded from disk", clf_path=clf_path, reg_path=reg_path)
        except Exception as e:
            logger.error("Error loading ML models from disk", error=str(e))
            self.models_loaded = False
            
    async def _on_trade_approved(self, message: dict):
        """Score approved trades with ML model and write candidate to DB."""
        try:
            event_type = message.get('event_type')
            if event_type != 'trade_approved':
                return
                
            risk_data = message.get('data', {})
            signal_id = risk_data.get('signal_id')
            if not signal_id:
                return

            logger.info("Scoring risk-approved trade candidate", signal_id=signal_id)

            # Query signal details from DB
            async with async_session_factory() as session:
                stmt = select(StrategySignal).where(StrategySignal.id == signal_id)
                result = await session.execute(stmt)
                signal = result.scalar_one_or_none()
                
                if not signal:
                    logger.error("Signal not found in database", signal_id=signal_id)
                    return
                
                symbol = signal.symbol
                entry_price = float(signal.entry_price)
                direction = signal.direction
                confidence = float(signal.confidence)

                # Fetch features for this signal
                features = await get_features_for_signal(
                    session=session,
                    symbol=symbol,
                    timestamp=signal.created_at,
                    entry_price=entry_price
                )

            # Perform scoring
            win_prob = 0.5
            expected_pnl = 0.0
            explanation = {"mode": "fallback", "message": "No ML models active"}

            if self.models_loaded and features:
                try:
                    feat_vector = build_feature_vector(features)
                    # XGBoost classification: predict win probability [class 0, class 1]
                    win_prob = float(self.clf_model.predict_proba([feat_vector])[0][1])
                    # LightGBM regression: predict PnL
                    expected_pnl = float(self.reg_model.predict([feat_vector])[0])
                    
                    explanation = {
                        "mode": "ml",
                        "win_probability": win_prob,
                        "expected_pnl_inr": expected_pnl,
                        "key_features": {
                            "rsi_14": features.get('rsi_14', 50.0),
                            "adx": features.get('adx', 0.0),
                            "bb_width": features.get('bb_width', 0.0)
                        }
                    }
                except Exception as ex:
                    logger.error("Error running model inference", error=str(ex))
            
            # Compute composite ML score
            ml_score = float(win_prob * (expected_pnl if expected_pnl > 0 else 10.0) * confidence)

            # Save TradeCandidate to database
            async with async_session_factory() as session:
                # First check if candidate exists
                candidate_stmt = select(TradeCandidate).where(TradeCandidate.signal_id == signal_id)
                cand_res = await session.execute(candidate_stmt)
                db_candidate = cand_res.scalar_one_or_none()
                
                if not db_candidate:
                    db_candidate = TradeCandidate(
                        signal_id=signal_id,
                        symbol=symbol,
                        direction=direction,
                        entry_price=entry_price,
                        quantity=risk_data.get('approved_quantity', 1),
                        stop_loss=float(signal.stop_loss) if signal.stop_loss else entry_price * 0.99,
                        target=float(signal.target) if signal.target else entry_price * 1.02,
                        risk_amount=risk_data.get('risk_amount', 0.0),
                        expected_reward=risk_data.get('risk_amount', 0.0) * float(risk_data.get('risk_reward_ratio', 1.5)),
                        risk_reward_ratio=float(risk_data.get('risk_reward_ratio', 1.5)),
                        confidence=confidence,
                        ml_score=ml_score,
                        ml_explanation=explanation,
                        status='APPROVED'
                    )
                    session.add(db_candidate)
                    
                    # Update StrategySignal status to APPROVED
                    signal.status = 'APPROVED'
                    
                    await session.commit()
                    logger.info("Saved trade candidate with ML score", signal_id=signal_id, ml_score=ml_score)

        except Exception as e:
            logger.error("Error in ML Service signal callback", error=str(e))
            
    async def stop(self):
        """Stop ML service."""
        self.running = False
        logger.info("ML Service stopped")

ml_service = MLService()
