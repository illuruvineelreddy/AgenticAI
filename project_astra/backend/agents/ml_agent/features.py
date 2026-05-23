"""
ML Feature Extraction and Engineering
Extracts and builds feature vectors from database tables.
"""

from datetime import datetime
import pandas as pd
import numpy as np
from sqlalchemy import select
from typing import Dict, List, Any
import structlog

from database.models import Feature

logger = structlog.get_logger()

FEATURE_COLUMNS = [
    'ema_9', 'ema_21', 'ema_50', 'ema_200',
    'macd', 'macd_signal', 'macd_hist',
    'adx', 'sar', 'rsi_14', 'stoch_k', 'stoch_d', 'williams_r', 'cci_20', 'roc_10',
    'bb_upper', 'bb_middle', 'bb_lower', 'atr_14', 'kc_middle', 'kc_upper', 'kc_lower',
    'historical_volatility', 'obv', 'vwap', 'volume_sma_20',
    # Engineered features
    'price_to_ema_9', 'price_to_ema_21', 'price_to_ema_50', 'price_to_ema_200',
    'bb_width', 'kc_width'
]

async def get_features_for_signal(session, symbol: str, timestamp: datetime, entry_price: float) -> Dict[str, float]:
    """
    Fetch calculated features from the DB for a symbol and timestamp.
    Appends engineered features relative to entry_price.
    """
    try:
        # Query features close to the signal timestamp (within 5 minutes)
        stmt = (
            select(Feature)
            .where(Feature.symbol == symbol)
            .order_by(Feature.candle_timestamp.desc())
            .limit(50)
        )
        result = await session.execute(stmt)
        db_features = result.scalars().all()
        
        if not db_features:
            return {}

        # Find features matching the closest timestamp
        # In real-time, features will be saved with the candle's timestamp.
        # Find the set of features with the minimum time difference
        features_by_time = {}
        for f in db_features:
            t = f.candle_timestamp
            if t not in features_by_time:
                features_by_time[t] = {}
            features_by_time[t][f.feature_name] = f.feature_value

        if not features_by_time:
            return {}

        # Find closest timestamp
        closest_time = min(features_by_time.keys(), key=lambda t: abs((t - timestamp).total_seconds()))
        time_diff = abs((closest_time - timestamp).total_seconds())
        
        # Only use features if they are within 10 minutes of the signal
        if time_diff > 600:
            logger.warn("Feature timestamp is too far from signal timestamp", symbol=symbol, diff_sec=time_diff)
            return {}
            
        features = features_by_time[closest_time]
        
        # Add engineered features
        features = add_engineered_features(features, entry_price)
        
        return features
        
    except Exception as e:
        logger.error("Error retrieving features for signal", symbol=symbol, error=str(e))
        return {}

def add_engineered_features(features: Dict[str, float], price: float) -> Dict[str, float]:
    """Adds relative features like price-to-EMA ratio and band widths."""
    res = features.copy()
    
    # Ratios
    for ema in ['ema_9', 'ema_21', 'ema_50', 'ema_200']:
        if ema in res and res[ema] != 0:
            res[f'price_to_{ema}'] = float(price / res[ema])
        else:
            res[f'price_to_{ema}'] = 1.0
            
    # Bollinger Band Width
    if 'bb_upper' in res and 'bb_lower' in res and 'bb_middle' in res and res['bb_middle'] != 0:
        res['bb_width'] = float((res['bb_upper'] - res['bb_lower']) / res['bb_middle'])
    else:
        res['bb_width'] = 0.05
        
    # Keltner Channel Width
    if 'kc_upper' in res and 'kc_lower' in res and 'kc_middle' in res and res['kc_middle'] != 0:
        res['kc_width'] = float((res['kc_upper'] - res['kc_lower']) / res['kc_middle'])
    else:
        res['kc_width'] = 0.05
        
    return res

def build_feature_vector(features: Dict[str, float]) -> List[float]:
    """Builds a flat list of features aligned with FEATURE_COLUMNS."""
    vector = []
    for col in FEATURE_COLUMNS:
        vector.append(features.get(col, 0.0))
    return vector
