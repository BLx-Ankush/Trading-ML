"""
Hidden Markov Model for Market Regime Detection

Detects market regimes:
- Trending Up: High returns, low volatility, directional movement
- Trending Down: Negative returns, increasing volatility
- Ranging: Low returns, moderate volatility, choppy
- High Volatility: Extreme volatility, unpredictable moves
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from hmmlearn import hmm
from sklearn.preprocessing import StandardScaler
import pickle
from pathlib import Path

from ..utils.logger import get_logger

logger = get_logger(__name__)


class RegimeDetector:
    """
    HMM-based market regime detector.
    
    Uses 3-state HMM to classify market conditions:
    - State 0: Trending (use momentum strategies)
    - State 1: Ranging (use mean-reversion strategies)
    - State 2: High Volatility (avoid trading or reduce exposure)
    """
    
    def __init__(
        self,
        n_states: int = 3,
        n_iter: int = 100,
        random_state: int = 42
    ):
        """
        Initialize regime detector.
        
        Args:
            n_states: Number of hidden states (default: 3)
            n_iter: Maximum iterations for EM algorithm
            random_state: Random seed for reproducibility
        """
        self.n_states = n_states
        self.n_iter = n_iter
        self.random_state = random_state
        
        # Initialize HMM with Gaussian emissions
        self.model = hmm.GaussianHMM(
            n_components=n_states,
            covariance_type="full",
            n_iter=n_iter,
            random_state=random_state
        )
        
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.state_mapping = {}  # Maps HMM states to regime names
        
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Extract features for regime detection.
        
        Features:
        - Returns (log returns)
        - Volatility (rolling std of returns)
        - Volume change (normalized)
        - ADX (trend strength)
        - Price momentum (rate of change)
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            DataFrame with features
        """
        df = data.copy()
        
        # Calculate returns
        df['returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Rolling volatility (20-day)
        df['volatility'] = df['returns'].rolling(window=20).std()
        
        # Volume change
        df['volume_change'] = df['volume'].pct_change()
        
        # ADX (Average Directional Index) - trend strength
        # Using simplified calculation
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift(1))
        low_close = np.abs(df['low'] - df['close'].shift(1))
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        atr = true_range.rolling(window=14).mean()
        plus_di = 100 * (plus_dm.rolling(window=14).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=14).mean() / atr)
        
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        df['adx'] = dx.rolling(window=14).mean()
        
        # Price momentum (10-day ROC)
        df['momentum'] = df['close'].pct_change(periods=10)
        
        # Select feature columns
        feature_cols = ['returns', 'volatility', 'volume_change', 'adx', 'momentum']
        features = df[feature_cols].copy()
        
        # Forward fill then backward fill to handle NaN
        features = features.ffill().bfill()
        
        return features
    
    def fit(self, data: pd.DataFrame) -> 'RegimeDetector':
        """
        Fit HMM model on historical data.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            self
        """
        logger.info("Extracting features for HMM training...")
        features = self.extract_features(data)
        
        # Remove any remaining NaN
        features = features.dropna()
        
        if len(features) < 100:
            raise ValueError("Insufficient data for HMM training (need at least 100 samples)")
        
        logger.info(f"Training HMM with {len(features)} samples...")
        
        # Scale features
        X = self.scaler.fit_transform(features)
        
        # Fit HMM
        self.model.fit(X)
        
        # Predict states on training data to map states to regimes
        states = self.model.predict(X)
        
        # Analyze each state to determine regime type
        self._identify_regimes(features, states)
        
        self.is_fitted = True
        logger.info("HMM training complete")
        logger.info(f"State mapping: {self.state_mapping}")
        
        return self
    
    def _identify_regimes(self, features: pd.DataFrame, states: np.ndarray) -> None:
        """
        Identify which HMM state corresponds to which regime.
        
        Logic:
        - High ADX + positive returns = Trending Up
        - High ADX + negative returns = Trending Down  
        - Low ADX + low volatility = Ranging
        - High volatility = High Volatility
        
        Args:
            features: Feature DataFrame
            states: Predicted states
        """
        features['state'] = states
        
        state_profiles = {}
        for state in range(self.n_states):
            mask = features['state'] == state
            profile = {
                'avg_return': features.loc[mask, 'returns'].mean(),
                'avg_volatility': features.loc[mask, 'volatility'].mean(),
                'avg_adx': features.loc[mask, 'adx'].mean(),
                'avg_momentum': features.loc[mask, 'momentum'].mean(),
                'count': mask.sum()
            }
            state_profiles[state] = profile
        
        # Map states to regimes based on characteristics
        # State with highest volatility = High Volatility regime
        vol_state = max(state_profiles.items(), key=lambda x: x[1]['avg_volatility'])[0]
        self.state_mapping[vol_state] = 'high_volatility'
        
        # Among remaining states, high ADX = Trending
        remaining = [s for s in range(self.n_states) if s != vol_state]
        adx_values = [(s, state_profiles[s]['avg_adx']) for s in remaining]
        trend_state = max(adx_values, key=lambda x: x[1])[0]
        
        # Check if trending up or down based on returns
        if state_profiles[trend_state]['avg_return'] > 0:
            self.state_mapping[trend_state] = 'trending'
        else:
            self.state_mapping[trend_state] = 'trending'  # Still use momentum
        
        # Remaining state = Ranging
        range_state = [s for s in remaining if s != trend_state][0]
        self.state_mapping[range_state] = 'ranging'
        
        logger.info("\nRegime Profiles:")
        for state, regime in self.state_mapping.items():
            prof = state_profiles[state]
            logger.info(f"  {regime.upper()} (State {state}):")
            logger.info(f"    Avg Return: {prof['avg_return']:.4f}")
            logger.info(f"    Avg Volatility: {prof['avg_volatility']:.4f}")
            logger.info(f"    Avg ADX: {prof['avg_adx']:.2f}")
            logger.info(f"    Occurrences: {prof['count']}")
    
    def predict(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict regime for new data.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Tuple of (states, regime_names)
        """
        if not self.is_fitted:
            logger.warning("Model not fitted, using default regime (TRENDING)")
            # Fallback: return default regime
            default_states = np.ones(len(data), dtype=int)
            default_regimes = np.array(['TRENDING'] * len(data))
            return default_states, default_regimes
        
        try:
            features = self.extract_features(data)
            features = features.dropna()
            
            # Replace infinity with NaN, then drop
            features = features.replace([np.inf, -np.inf], np.nan)
            features = features.dropna()
            
            if len(features) == 0:
                logger.warning("No valid features after cleaning, using default regime")
                default_states = np.ones(len(data), dtype=int)
                default_regimes = np.array(['TRENDING'] * len(data))
                return default_states, default_regimes
            
            # Clip extreme values before scaling
            features = features.clip(lower=-1e10, upper=1e10)
            
            X = self.scaler.transform(features)
            
            # Check for NaN/inf after scaling
            if np.any(np.isnan(X)) or np.any(np.isinf(X)):
                logger.warning("Invalid values after scaling, using default regime")
                default_states = np.ones(len(data), dtype=int)
                default_regimes = np.array(['TRENDING'] * len(data))
                return default_states, default_regimes
            
            states = self.model.predict(X)
            
            # Map states to regime names
            regimes = np.array([self.state_mapping[s] for s in states])
            
            # If results are shorter than input, pad with last value
            if len(regimes) < len(data):
                padding = np.full(len(data) - len(regimes), regimes[-1] if len(regimes) > 0 else 'TRENDING')
                regimes = np.concatenate([regimes, padding])
                states = np.concatenate([states, np.full(len(padding), states[-1] if len(states) > 0 else 1)])
            
            return states, regimes
            
        except Exception as e:
            logger.error(f"Regime prediction failed: {str(e)}, using default regime")
            # Fallback: return default regime
            default_states = np.ones(len(data), dtype=int)
            default_regimes = np.array(['TRENDING'] * len(data))
            return default_states, default_regimes
    
    def predict_latest(self, data: pd.DataFrame) -> str:
        """
        Predict current regime based on latest data.
        
        Args:
            data: DataFrame with OHLCV data (at least 50 days)
            
        Returns:
            Current regime name
        """
        states, regimes = self.predict(data)
        return regimes[-1]
    
    def get_regime_probabilities(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Get probability distribution over regimes for each time point.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            DataFrame with probabilities for each regime
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        features = self.extract_features(data)
        features = features.dropna()
        
        X = self.scaler.transform(features)
        
        # Get posterior probabilities
        posteriors = self.model.predict_proba(X)
        
        # Create DataFrame with regime names as columns
        prob_df = pd.DataFrame(posteriors, index=features.index)
        prob_df.columns = [self.state_mapping[i] for i in range(self.n_states)]
        
        return prob_df
    
    def save(self, filepath: str) -> None:
        """Save model to disk."""
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'state_mapping': self.state_mapping,
            'n_states': self.n_states,
            'is_fitted': self.is_fitted
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {filepath}")
    
    def load(self, filepath: str) -> 'RegimeDetector':
        """Load model from disk."""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.state_mapping = model_data['state_mapping']
        self.n_states = model_data['n_states']
        self.is_fitted = model_data['is_fitted']
        
        logger.info(f"Model loaded from {filepath}")
        return self
