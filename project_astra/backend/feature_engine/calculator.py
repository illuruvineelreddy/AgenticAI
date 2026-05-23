"""
Technical Indicator Calculator for Project Astra
Includes a robust fallback to pure Python/Pandas/Numpy if TA-Lib is not installed.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Union

try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False

class FeatureCalculator:
    """
    Calculates technical indicators on candle data.
    Falls back to pure pandas/numpy calculations if TA-Lib is not available.
    """
    
    def __init__(self):
        pass

    def calculate_all(self, candles: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculates all technical indicators from the list of candles.
        Returns a dictionary of feature names and their latest values.
        """
        if not candles or len(candles) < 2:
            return {}

        # Convert candles list to DataFrame
        # Expects: open, high, low, close, volume, timestamp
        df = pd.DataFrame(candles)
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        # Sort by timestamp ascending
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)

        features = {}
        
        try:
            # Calculate groups
            trend = self._calculate_trend(df)
            momentum = self._calculate_momentum(df)
            volatility = self._calculate_volatility(df)
            volume = self._calculate_volume(df)
            
            # Merge all features
            features.update(trend)
            features.update(momentum)
            features.update(volatility)
            features.update(volume)
        except Exception as e:
            # Avoid crashing, log and return whatever we can
            import structlog
            logger = structlog.get_logger()
            logger.error("Error calculating features", error=str(e))
            
        return features

    def _calculate_trend(self, df: pd.DataFrame) -> Dict[str, float]:
        features = {}
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        # 1. EMA (9, 21, 50, 200)
        for period in [9, 21, 50, 200]:
            if len(close) >= period:
                if HAS_TALIB:
                    features[f'ema_{period}'] = float(talib.EMA(close, timeperiod=period)[-1])
                else:
                    features[f'ema_{period}'] = float(df['close'].ewm(span=period, adjust=False).mean().iloc[-1])
            else:
                features[f'ema_{period}'] = float(close[-1])

        # 2. MACD (12, 26, 9)
        if len(close) >= 26:
            if HAS_TALIB:
                macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
                features['macd'] = float(macd[-1])
                features['macd_signal'] = float(macdsignal[-1])
                features['macd_hist'] = float(macdhist[-1])
            else:
                ema_12 = df['close'].ewm(span=12, adjust=False).mean()
                ema_26 = df['close'].ewm(span=26, adjust=False).mean()
                macd = ema_12 - ema_26
                signal = macd.ewm(span=9, adjust=False).mean()
                hist = macd - signal
                features['macd'] = float(macd.iloc[-1])
                features['macd_signal'] = float(signal.iloc[-1])
                features['macd_hist'] = float(hist.iloc[-1])
        else:
            features['macd'] = 0.0
            features['macd_signal'] = 0.0
            features['macd_hist'] = 0.0

        # 3. ADX (14)
        if len(df) >= 14:
            if HAS_TALIB:
                features['adx'] = float(talib.ADX(high, low, close, timeperiod=14)[-1])
            else:
                # Pure pandas ADX implementation
                plus_dm = df['high'].diff()
                minus_dm = df['low'].diff()
                plus_dm[plus_dm < 0] = 0
                minus_dm[minus_dm > 0] = 0
                minus_dm = -minus_dm
                
                tr1 = df['high'] - df['low']
                tr2 = (df['high'] - df['close'].shift()).abs()
                tr3 = (df['low'] - df['close'].shift()).abs()
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                
                atr = tr.rolling(14).mean() # simplified
                plus_di = 100 * (plus_dm.rolling(14).mean() / atr)
                minus_di = 100 * (minus_dm.rolling(14).mean() / atr)
                dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
                adx = dx.rolling(14).mean()
                features['adx'] = float(adx.fillna(50).iloc[-1])
        else:
            features['adx'] = 25.0

        # 4. Parabolic SAR
        if len(df) >= 2:
            if HAS_TALIB:
                features['sar'] = float(talib.SAR(high, low, acceleration=0.02, maximum=0.2)[-1])
            else:
                # Simplified SAR placeholder for pure pandas
                features['sar'] = float(close[-1] * 0.98 if close[-1] > close[-2] else close[-1] * 1.02)
        else:
            features['sar'] = float(close[-1])

        # 5. Ichimoku Cloud
        if len(df) >= 52:
            high_9 = df['high'].rolling(window=9).max()
            low_9 = df['low'].rolling(window=9).min()
            tenkan_sen = (high_9 + low_9) / 2
            
            high_26 = df['high'].rolling(window=26).max()
            low_26 = df['low'].rolling(window=26).min()
            kijun_sen = (high_26 + low_26) / 2
            
            senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
            
            high_52 = df['high'].rolling(window=52).max()
            low_52 = df['low'].rolling(window=52).min()
            senkou_span_b = ((high_52 + low_52) / 2).shift(26)
            
            features['ichimoku_tenkan'] = float(tenkan_sen.iloc[-1])
            features['ichimoku_kijun'] = float(kijun_sen.iloc[-1])
            features['ichimoku_span_a'] = float(senkou_span_a.fillna(close[-1]).iloc[-1])
            features['ichimoku_span_b'] = float(senkou_span_b.fillna(close[-1]).iloc[-1])
        else:
            features['ichimoku_tenkan'] = float(close[-1])
            features['ichimoku_kijun'] = float(close[-1])
            features['ichimoku_span_a'] = float(close[-1])
            features['ichimoku_span_b'] = float(close[-1])

        # 6. SuperTrend (10, 3)
        if len(df) >= 10:
            # Calculate ATR (10)
            if HAS_TALIB:
                atr_10 = talib.ATR(high, low, close, timeperiod=10)
            else:
                tr1 = df['high'] - df['low']
                tr2 = (df['high'] - df['close'].shift()).abs()
                tr3 = (df['low'] - df['close'].shift()).abs()
                atr_10 = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(10).mean().values
                
            hl2 = (df['high'] + df['low']) / 2
            basic_ub = hl2 + 3 * atr_10
            basic_lb = hl2 - 3 * atr_10
            
            final_ub = basic_ub.copy()
            final_lb = basic_lb.copy()
            
            for i in range(1, len(df)):
                if basic_ub[i] < final_ub[i-1] or close[i-1] > final_ub[i-1]:
                    final_ub[i] = basic_ub[i]
                else:
                    final_ub[i] = final_ub[i-1]
                    
                if basic_lb[i] > final_lb[i-1] or close[i-1] < final_lb[i-1]:
                    final_lb[i] = basic_lb[i]
                else:
                    final_lb[i] = final_lb[i-1]
            
            supertrend = np.zeros(len(df))
            for i in range(1, len(df)):
                if supertrend[i-1] == final_ub[i-1]:
                    supertrend[i] = final_ub[i] if close[i] <= final_ub[i] else final_lb[i]
                else:
                    supertrend[i] = final_lb[i] if close[i] >= final_lb[i] else final_ub[i]
            
            features['supertrend'] = float(supertrend[-1])
        else:
            features['supertrend'] = float(close[-1])
            
        return features

    def _calculate_momentum(self, df: pd.DataFrame) -> Dict[str, float]:
        features = {}
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        # 1. RSI (14)
        if len(close) >= 14:
            if HAS_TALIB:
                features['rsi_14'] = float(talib.RSI(close, timeperiod=14)[-1])
            else:
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                features['rsi_14'] = float(rsi.fillna(50).iloc[-1])
        else:
            features['rsi_14'] = 50.0

        # 2. Stochastic (14, 3, 3)
        if len(df) >= 14:
            if HAS_TALIB:
                slowk, slowd = talib.STOCH(high, low, close, fastk_period=14, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
                features['stoch_k'] = float(slowk[-1])
                features['stoch_d'] = float(slowd[-1])
            else:
                low_14 = df['low'].rolling(14).min()
                high_14 = df['high'].rolling(14).max()
                fast_k = 100 * ((df['close'] - low_14) / (high_14 - low_14))
                slow_k = fast_k.rolling(3).mean()
                slow_d = slow_k.rolling(3).mean()
                features['stoch_k'] = float(slow_k.fillna(50).iloc[-1])
                features['stoch_d'] = float(slow_d.fillna(50).iloc[-1])
        else:
            features['stoch_k'] = 50.0
            features['stoch_d'] = 50.0

        # 3. Williams %R (14)
        if len(df) >= 14:
            if HAS_TALIB:
                features['williams_r'] = float(talib.WILLR(high, low, close, timeperiod=14)[-1])
            else:
                low_14 = df['low'].rolling(14).min()
                high_14 = df['high'].rolling(14).max()
                williams_r = -100 * ((high_14 - df['close']) / (high_14 - low_14))
                features['williams_r'] = float(williams_r.fillna(-50).iloc[-1])
        else:
            features['williams_r'] = -50.0

        # 4. CCI (20)
        if len(df) >= 20:
            if HAS_TALIB:
                features['cci_20'] = float(talib.CCI(high, low, close, timeperiod=20)[-1])
            else:
                tp = (df['high'] + df['low'] + df['close']) / 3
                sma = tp.rolling(20).mean()
                mad = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
                cci = (tp - sma) / (0.015 * mad)
                features['cci_20'] = float(cci.fillna(0).iloc[-1])
        else:
            features['cci_20'] = 0.0

        # 5. ROC (Rate of Change) - 10 period
        if len(close) >= 10:
            if HAS_TALIB:
                features['roc_10'] = float(talib.ROC(close, timeperiod=10)[-1])
            else:
                features['roc_10'] = float(((close[-1] - close[-10]) / close[-10]) * 100)
        else:
            features['roc_10'] = 0.0
            
        return features

    def _calculate_volatility(self, df: pd.DataFrame) -> Dict[str, float]:
        features = {}
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        # 1. Bollinger Bands (20, 2)
        if len(close) >= 20:
            if HAS_TALIB:
                upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2.0, nbdevdn=2.0, matype=0)
                features['bb_upper'] = float(upper[-1])
                features['bb_middle'] = float(middle[-1])
                features['bb_lower'] = float(lower[-1])
            else:
                middle = df['close'].rolling(20).mean()
                std = df['close'].rolling(20).std()
                features['bb_upper'] = float((middle + 2 * std).iloc[-1])
                features['bb_middle'] = float(middle.iloc[-1])
                features['bb_lower'] = float((middle - 2 * std).iloc[-1])
        else:
            features['bb_upper'] = float(close[-1] * 1.05)
            features['bb_middle'] = float(close[-1])
            features['bb_lower'] = float(close[-1] * 0.95)

        # 2. ATR (14)
        if len(df) >= 14:
            if HAS_TALIB:
                features['atr_14'] = float(talib.ATR(high, low, close, timeperiod=14)[-1])
            else:
                tr1 = df['high'] - df['low']
                tr2 = (df['high'] - df['close'].shift()).abs()
                tr3 = (df['low'] - df['close'].shift()).abs()
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr = tr.rolling(14).mean()
                features['atr_14'] = float(atr.fillna(close[-1] * 0.01).iloc[-1])
        else:
            features['atr_14'] = float(close[-1] * 0.01)

        # 3. Keltner Channel (20, 1.5)
        if len(df) >= 20:
            # Middle line is 20 EMA, band width is 1.5 ATR
            if HAS_TALIB:
                ema_20 = talib.EMA(close, timeperiod=20)
                atr_20 = talib.ATR(high, low, close, timeperiod=20)
                features['kc_middle'] = float(ema_20[-1])
                features['kc_upper'] = float(ema_20[-1] + 1.5 * atr_20[-1])
                features['kc_lower'] = float(ema_20[-1] - 1.5 * atr_20[-1])
            else:
                ema_20 = df['close'].ewm(span=20, adjust=False).mean()
                tr1 = df['high'] - df['low']
                tr2 = (df['high'] - df['close'].shift()).abs()
                tr3 = (df['low'] - df['close'].shift()).abs()
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr_20 = tr.rolling(20).mean()
                features['kc_middle'] = float(ema_20.iloc[-1])
                features['kc_upper'] = float((ema_20 + 1.5 * atr_20).iloc[-1])
                features['kc_lower'] = float((ema_20 - 1.5 * atr_20).iloc[-1])
        else:
            features['kc_middle'] = float(close[-1])
            features['kc_upper'] = float(close[-1] * 1.03)
            features['kc_lower'] = float(close[-1] * 0.97)

        # 4. Historical Volatility (20-day annualized)
        if len(close) >= 20:
            returns = np.diff(np.log(close))
            features['historical_volatility'] = float(np.std(returns) * np.sqrt(252) * 100)
        else:
            features['historical_volatility'] = 20.0
            
        return features

    def _calculate_volume(self, df: pd.DataFrame) -> Dict[str, float]:
        features = {}
        close = df['close'].values
        volume = df['volume'].values
        
        # 1. OBV (On-Balance Volume)
        if len(df) >= 2:
            if HAS_TALIB:
                features['obv'] = float(talib.OBV(close, volume)[-1])
            else:
                obv = np.zeros(len(df))
                obv[0] = volume[0]
                for i in range(1, len(df)):
                    if close[i] > close[i-1]:
                        obv[i] = obv[i-1] + volume[i]
                    elif close[i] < close[i-1]:
                        obv[i] = obv[i-1] - volume[i]
                    else:
                        obv[i] = obv[i-1]
                features['obv'] = float(obv[-1])
        else:
            features['obv'] = float(volume[-1])

        # 2. VWAP (Volume Weighted Average Price)
        # Note: True VWAP resets intraday. We compute a cumulative VWAP over the buffer.
        pv = (df['close'] * df['volume']).cumsum()
        cum_volume = df['volume'].cumsum()
        vwap = pv / cum_volume
        features['vwap'] = float(vwap.fillna(close[-1]).iloc[-1])

        # 3. Volume SMA (20 period)
        if len(volume) >= 20:
            if HAS_TALIB:
                features['volume_sma_20'] = float(talib.SMA(volume, timeperiod=20)[-1])
            else:
                features['volume_sma_20'] = float(df['volume'].rolling(20).mean().iloc[-1])
        else:
            features['volume_sma_20'] = float(volume[-1])
            
        return features
