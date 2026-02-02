"""
ML-Enhanced Strategy Selector

Two-layer approach:
- Layer 2 (Fuzzy Logic): Generate candidate trade ideas
- Layer 3 (LightGBM): Final gatekeeper with ML model
"""

from typing import Dict, Optional
import pandas as pd
import numpy as np

from .strategy_selector import StrategySelector
from ..ml.lightgbm_model import LightGBMModel
from ..ml.feature_engineer import FeatureEngineer
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MLStrategySelector:
    """
    ML-enhanced strategy selector with two-layer filtering.
    
    Architecture:
    1. Layer 2 (Fuzzy Logic): Generate candidate trades based on regime + indicators
    2. Layer 3 (ML Gatekeeper): LightGBM filters candidates with probability threshold
    """
    
    def __init__(
        self,
        model_path: str,
        threshold: float = 0.30,
        enable_ml_filter: bool = True,
        use_regime_thresholds: bool = True
    ):
        """
        Initialize ML strategy selector.
        
        Args:
            model_path: Path to trained LightGBM model
            threshold: Default probability threshold (used if use_regime_thresholds=False)
            enable_ml_filter: If False, only use fuzzy logic (for comparison)
            use_regime_thresholds: If True, use regime-specific thresholds (default: True)
        """
        # Layer 2: Fuzzy logic selector
        self.fuzzy_selector = StrategySelector()
        
        # Layer 3: ML gatekeeper
        self.enable_ml_filter = enable_ml_filter
        self.threshold = threshold
        self.use_regime_thresholds = use_regime_thresholds
        
        # Regime-specific thresholds (Phase 3.8)
        # Trending: Lower threshold (trust the trend) -> more trades
        # Ranging: Higher threshold (only best mean-reversion) -> quality over quantity
        # High Vol: Highest threshold (avoid chaos) -> minimal trades
        self.regime_thresholds = {
            'trending': 0.20,      # Aggressive in trends
            'ranging': 0.28,       # Selective in ranges
            'high_volatility': 0.35  # Very selective in chaos
        }
        
        self.ml_model = None
        self.feature_engineer = FeatureEngineer()
        
        if enable_ml_filter:
            try:
                self.ml_model = LightGBMModel()
                self.ml_model.load(model_path)
                if use_regime_thresholds:
                    logger.info(f"Loaded ML model from {model_path} (regime-adaptive thresholds: trending={self.regime_thresholds['trending']}, ranging={self.regime_thresholds['ranging']}, high_vol={self.regime_thresholds['high_volatility']})")
                else:
                    logger.info(f"Loaded ML model from {model_path} (flat threshold={threshold})")
            except Exception as e:
                logger.warning(f"Failed to load ML model: {e}. Falling back to fuzzy logic only.")
                self.enable_ml_filter = False
        
        # Statistics
        self.stats = {
            'fuzzy_candidates': 0,
            'ml_approved': 0,
            'ml_rejected': 0,
            'fuzzy_only': 0,
            'by_regime': {
                'trending': {'candidates': 0, 'approved': 0},
                'ranging': {'candidates': 0, 'approved': 0},
                'high_volatility': {'candidates': 0, 'approved': 0}
            }
        }
    
    def get_entry_signal(
        self,
        regime: str,
        data: pd.DataFrame,
        current_idx: int,
        regime_series: Optional[pd.Series] = None
    ) -> Optional[str]:
        """
        Generate entry signal using two-layer approach.
        
        Args:
            regime: Current market regime
            data: Full historical data with indicators
            current_idx: Current bar index
            regime_series: Series of regime labels (for feature engineering)
            
        Returns:
            'LONG', 'SHORT', or None
        """
        # Get current bar
        current_bar = data.iloc[current_idx]
        
        # Prepare indicators dict for fuzzy logic
        indicators = {
            'ema_20': current_bar.get('ema_21'),  # Using ema_21 from TechnicalIndicators
            'rsi': current_bar.get('rsi'),
            'adx': current_bar.get('adx'),
            'atr': current_bar.get('atr'),
            'macd': current_bar.get('macd'),
            'macd_signal': current_bar.get('macd_signal'),
            'bb_upper': current_bar.get('bb_upper'),
            'bb_lower': current_bar.get('bb_lower'),
            'volume': current_bar.get('volume')
        }
        
        # Layer 2: Fuzzy logic generates candidate
        fuzzy_signal = self.fuzzy_selector.get_entry_signal(
            regime=regime,
            price=current_bar['close'],
            indicators=indicators,
            track_near_miss=False
        )
        
        if fuzzy_signal is None:
            return None
        
        self.stats['fuzzy_candidates'] += 1
        
        # Track regime-specific candidate (Phase 3.8)
        if regime in self.stats['by_regime']:
            self.stats['by_regime'][regime]['candidates'] += 1
        
        # If ML filter disabled, return fuzzy signal directly
        if not self.enable_ml_filter or self.ml_model is None:
            self.stats['fuzzy_only'] += 1
            return fuzzy_signal
        
        # Layer 3: ML gatekeeper evaluates candidate
        try:
            # Create features for current bar
            features = self.feature_engineer.create_features(
                data.iloc[:current_idx+1],  # Only use data up to current point (no lookahead)
                regime=regime_series.iloc[:current_idx+1] if regime_series is not None else None
            )
            
            # Get features for current bar
            current_features = features.iloc[-1:].copy()
            
            # Check for NaN values
            if current_features.isna().any().any():
                logger.debug(f"NaN in features at idx {current_idx}, skipping ML filter")
                self.stats['fuzzy_only'] += 1
                return fuzzy_signal
            
            # Get ML prediction probability
            probability = self.ml_model.predict_proba(current_features)[0]
            
            # Determine threshold based on regime (Phase 3.8)
            if self.use_regime_thresholds and regime in self.regime_thresholds:
                effective_threshold = self.regime_thresholds[regime]
                logger.debug(f"Using regime-specific threshold for {regime}: {effective_threshold}")
            else:
                effective_threshold = self.threshold
            
            # Apply threshold
            if probability >= effective_threshold:
                self.stats['ml_approved'] += 1
                if regime in self.stats['by_regime']:
                    self.stats['by_regime'][regime]['approved'] += 1
                logger.debug(f"ML approved: prob={probability:.3f} >= {effective_threshold} (regime={regime})")
                return fuzzy_signal
            else:
                self.stats['ml_rejected'] += 1
                logger.debug(f"ML rejected: prob={probability:.3f} < {effective_threshold} (regime={regime})")
                return None
        
        except Exception as e:
            logger.warning(f"ML filter error at idx {current_idx}: {e}")
            self.stats['fuzzy_only'] += 1
            return fuzzy_signal
    
    def get_stats(self) -> Dict:
        """Get filtering statistics."""
        total = self.stats['fuzzy_candidates']
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            'approval_rate': self.stats['ml_approved'] / total if total > 0 else 0,
            'rejection_rate': self.stats['ml_rejected'] / total if total > 0 else 0
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            'fuzzy_candidates': 0,
            'ml_approved': 0,
            'ml_rejected': 0,
            'fuzzy_only': 0
        }
