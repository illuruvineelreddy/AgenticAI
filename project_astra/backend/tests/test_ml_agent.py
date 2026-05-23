import pytest
import os
import tempfile
import joblib
from unittest.mock import MagicMock, patch, AsyncMock
from agents.ml_agent.trainer import MLModelTrainer
from agents.ml_agent.service import MLService

def test_generate_synthetic_data():
    """Test that MLModelTrainer can generate a synthetic training dataset."""
    trainer = MLModelTrainer()
    df = trainer._generate_synthetic_data()
    
    assert not df.empty
    assert len(df) == 200
    assert "is_win" in df.columns
    assert "pnl" in df.columns
    # Ensure all expected feature columns are present
    from agents.ml_agent.features import FEATURE_COLUMNS
    for col in FEATURE_COLUMNS:
        assert col in df.columns

@pytest.mark.asyncio
async def test_train_and_register_pipeline(db_session):
    """Test that training pipeline runs and logs version to database."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Patch settings.model_path to temp dir
        with patch("utils.config.settings.model_path", tmp_dir), \
             patch("agents.ml_agent.trainer.HAS_ML_LIBS", True):
            
            trainer = MLModelTrainer()
            success = await trainer.train_and_register()
            
            assert success is True
            # Verify models saved to disk
            assert os.path.exists(os.path.join(tmp_dir, "xgboost_classifier.joblib"))
            assert os.path.exists(os.path.join(tmp_dir, "lightgbm_regressor.joblib"))

@pytest.mark.asyncio
async def test_ml_service_fallback_scoring(db_session, mock_stream_manager):
    """Test that MLService falls back to default scores when no models are loaded."""
    service = MLService()
    service.models_loaded = False
    
    # Setup database with a strategy signal
    from database.models import StrategySignal
    from datetime import datetime
    
    signal = StrategySignal(
        strategy_name='trend_strategy',
        symbol='RELIANCE',
        direction='LONG',
        entry_price=2500.0,
        stop_loss=2480.0,
        target=2540.0,
        confidence=0.8,
        rationale='Test rationale',
        regime='BULL',
        status='PENDING',
        created_at=datetime.utcnow()
    )
    db_session.add(signal)
    await db_session.commit()
    await db_session.refresh(signal)
    
    # Trigger callback
    message = {
        "event_type": "trade_approved",
        "data": {
            "signal_id": signal.id,
            "approved_quantity": 10,
            "risk_amount": 200.0,
            "risk_reward_ratio": 2.0
        }
    }
    
    # Mock features retrieval to avoid empty dataframe warnings
    with patch("agents.ml_agent.service.get_features_for_signal", return_value={}):
        await service._on_trade_approved(message)
        
        # Query candidate from database
        from database.models import TradeCandidate
        from sqlalchemy import select
        
        stmt = select(TradeCandidate).where(TradeCandidate.signal_id == signal.id)
        res = await db_session.execute(stmt)
        candidate = res.scalar_one_or_none()
        
        assert candidate is not None
        # In fallback mode win_prob=0.5, expected_pnl=0.0, confidence=0.8
        # Composite score is win_prob * (pnl if pnl > 0 else 10) * confidence = 0.5 * 10 * 0.8 = 4.0
        assert candidate.ml_score == 4.0
        assert candidate.ml_explanation["mode"] == "fallback"
