"""
Feature Engineering Pipeline for LightGBM

Creates 20-30 features from price, volume, and indicator data.
Features are designed to capture:
1. Momentum (trends, breakouts)
2. Mean reversion (oversold/overbought)
3. Volatility (expansion/contraction)
4. Volume patterns (accumulation/distribution)
5. Market regime (from HMM)
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FeatureEngineer:
    """
    Create ML features from OHLCV data and indicators.
    
    Features are normalized and engineered to be predictive of
    2:1 R:R trade outcomes.
    """
    
    def __init__(self):
        """Initialize feature engineer."""
        self.feature_names = []
        
    def create_features(
        self,
        data: pd.DataFrame,
        regime: pd.Series = None
    ) -> pd.DataFrame:
        """
        Create all features from input data.
        
        Args:
            data: DataFrame with OHLCV and indicators
            regime: Optional Series with regime labels
            
        Returns:
            DataFrame with all engineered features
        """
        features = pd.DataFrame(index=data.index)
        
        # 1. Price momentum features
        features = pd.concat([features, self._momentum_features(data)], axis=1)
        
        # 2. Mean reversion features
        features = pd.concat([features, self._reversion_features(data)], axis=1)
        
        # 3. Volatility features
        features = pd.concat([features, self._volatility_features(data)], axis=1)
        
        # 4. Volume features
        features = pd.concat([features, self._volume_features(data)], axis=1)
        
        # 5. Regime features (if available)
        if regime is not None:
            features = pd.concat([features, self._regime_features(data, regime)], axis=1)
        
        # Only log feature names once (on first call)
        if not hasattr(self, 'feature_names'):
            self.feature_names = features.columns.tolist()
            logger.info(f"Created {len(self.feature_names)} features for ML model")
        
        return features
    
    def _momentum_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create momentum-based features."""
        features = pd.DataFrame(index=data.index)
        
        # RSI normalized (0-1 range)
        if 'rsi' in data.columns:
            features['rsi_norm'] = data['rsi'] / 100.0
            features['rsi_overbought'] = (data['rsi'] > 70).astype(int)
            features['rsi_oversold'] = (data['rsi'] < 30).astype(int)
        
        # Price vs EMA (trend strength)
        if 'ema_20' in data.columns and 'atr' in data.columns:
            features['price_above_ema'] = (data['close'] > data['ema_20']).astype(int)
            features['price_ema_distance'] = (data['close'] - data['ema_20']) / data['atr']
        
        # ADX (trend strength)
        if 'adx' in data.columns:
            features['adx_norm'] = data['adx'] / 100.0
            features['adx_strong'] = (data['adx'] > 25).astype(int)
        
        # MACD
        if 'macd' in data.columns and 'macd_signal' in data.columns:
            features['macd_histogram'] = data['macd'] - data['macd_signal']
            features['macd_positive'] = (data['macd'] > 0).astype(int)
            features['macd_crossover'] = (
                (data['macd'] > data['macd_signal']) & 
                (data['macd'].shift(1) <= data['macd_signal'].shift(1))
            ).astype(int)
        
        # Momentum (Rate of Change)
        features['momentum_5'] = data['close'].pct_change(5)
        features['momentum_10'] = data['close'].pct_change(10)
        
        return features
    
    def _reversion_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create mean-reversion features."""
        features = pd.DataFrame(index=data.index)
        
        # Bollinger Bands
        if 'bb_lower' in data.columns and 'bb_upper' in data.columns:
            bb_width = data['bb_upper'] - data['bb_lower']
            features['bb_position'] = (data['close'] - data['bb_lower']) / bb_width
            features['bb_near_lower'] = (data['close'] < data['bb_lower'] * 1.02).astype(int)
            features['bb_near_upper'] = (data['close'] > data['bb_upper'] * 0.98).astype(int)
            features['bb_width_norm'] = bb_width / data['close']
        
        # Distance from recent high/low
        features['dist_from_20high'] = (data['close'] - data['high'].rolling(20).max()) / data['close']
        features['dist_from_20low'] = (data['close'] - data['low'].rolling(20).min()) / data['close']
        
        return features
    
    def _volatility_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create volatility features."""
        features = pd.DataFrame(index=data.index)
        
        # ATR normalized
        if 'atr' in data.columns:
            features['atr_norm'] = data['atr'] / data['close']
            features['atr_expanding'] = (
                data['atr'] > data['atr'].rolling(10).mean()
            ).astype(int)
        
        # Rolling volatility
        returns = data['close'].pct_change()
        features['volatility_10'] = returns.rolling(10).std()
        features['volatility_20'] = returns.rolling(20).std()
        
        return features
    
    def _volume_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create volume-based features."""
        features = pd.DataFrame(index=data.index)
        
        if 'volume' in data.columns:
            # Volume vs average
            vol_ma20 = data['volume'].rolling(20).mean()
            features['volume_ratio'] = data['volume'] / vol_ma20
            features['volume_spike'] = (data['volume'] > vol_ma20 * 1.5).astype(int)
            
            # Volume trend
            features['volume_increasing'] = (
                data['volume'] > data['volume'].shift(1)
            ).astype(int)
        
        return features
    
    def _regime_features(self, data: pd.DataFrame, regime: pd.Series) -> pd.DataFrame:
        """Create regime-based features."""
        features = pd.DataFrame(index=data.index)
        
        # One-hot encode regime
        regime_dummies = pd.get_dummies(regime, prefix='regime')
        features = pd.concat([features, regime_dummies], axis=1)
        
        # Ensure all three regime columns exist (even if not present in data)
        for regime_col in ['regime_high_volatility', 'regime_ranging', 'regime_trending']:
            if regime_col not in features.columns:
                features[regime_col] = 0
        
        # Regime duration (how long in current regime)
        regime_changes = (regime != regime.shift(1)).cumsum()
        features['regime_duration'] = regime_changes.groupby(regime_changes).cumcount()
        
        return features
