import pytest
from unittest.mock import patch
from feature_engine.calculator import FeatureCalculator

def test_calculate_all_basic(sample_candles):
    """Test that calculate_all returns a dictionary with all required technical indicators."""
    calculator = FeatureCalculator()
    features = calculator.calculate_all(sample_candles)
    
    # Verify that we got features back
    assert isinstance(features, dict)
    assert len(features) > 0
    
    # Assert existence of key features
    expected_indicators = [
        "ema_9", "ema_21", "ema_50", "ema_200",
        "macd", "macd_signal", "macd_hist",
        "adx", "sar", "ichimoku_tenkan", "ichimoku_kijun",
        "rsi_14", "stoch_k", "stoch_d", "williams_r", "cci_20", "roc_10",
        "bb_upper", "bb_middle", "bb_lower", "atr_14",
        "kc_middle", "kc_upper", "kc_lower", "historical_volatility",
        "obv", "vwap", "volume_sma_20"
    ]
    
    for indicator in expected_indicators:
        assert indicator in features
        assert isinstance(features[indicator], (int, float))

def test_calculate_all_empty():
    """Test that calculate_all handles empty or small lists of candles gracefully."""
    calculator = FeatureCalculator()
    
    assert calculator.calculate_all([]) == {}
    assert calculator.calculate_all([{"close": 100}]) == {}

def test_pure_python_fallback(sample_candles):
    """Test that calculations still succeed and produce reasonable values even without TA-Lib."""
    # Force HAS_TALIB to False to trigger pure Python fallbacks
    with patch("feature_engine.calculator.HAS_TALIB", False):
        calculator = FeatureCalculator()
        features = calculator.calculate_all(sample_candles)
        
        assert isinstance(features, dict)
        assert len(features) > 0
        
        # Verify values are generated and numeric
        assert features["rsi_14"] >= 0 and features["rsi_14"] <= 100
        assert features["stoch_k"] >= 0 and features["stoch_k"] <= 100
        assert features["stoch_d"] >= 0 and features["stoch_d"] <= 100
        assert features["bb_upper"] > features["bb_lower"]
        assert features["atr_14"] > 0
        assert features["vwap"] > 0
