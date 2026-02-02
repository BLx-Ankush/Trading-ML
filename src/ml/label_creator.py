"""
Label Creator for LightGBM Training

Creates binary labels by simulating forward-looking 2:1 risk-reward outcomes.
- Label = 1: Price hits 2× ATR profit before 1× ATR stop
- Label = 0: Stop hit first or no clear outcome

This is the MOST CRITICAL component - labels define what the model learns.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LabelCreator:
    """
    Create labels for ML training by simulating 2:1 R:R outcomes.
    
    For each potential entry point:
    1. Calculate entry price, stop (entry - 2×ATR), target (entry + 4×ATR)
    2. Look forward to see which is hit first
    3. Label = 1 if target hit, 0 if stop hit
    """
    
    def __init__(
        self,
        risk_multiplier: float = 2.0,  # Stop = entry - risk_multiplier × ATR
        reward_multiplier: float = 4.0,  # Target = entry + reward_multiplier × ATR
        max_holding_days: int = 20  # Max days to hold before labeling as neutral
    ):
        """
        Initialize label creator.
        
        Args:
            risk_multiplier: ATR multiplier for stop-loss (2.0 = 2× ATR)
            reward_multiplier: ATR multiplier for take-profit (4.0 = 4× ATR for 2:1 R:R)
            max_holding_days: Maximum days to wait for outcome before timeout
        """
        self.risk_multiplier = risk_multiplier
        self.reward_multiplier = reward_multiplier
        self.max_holding_days = max_holding_days
        
    def create_labels(
        self,
        data: pd.DataFrame,
        regime: pd.Series = None
    ) -> Tuple[pd.Series, Dict[str, float]]:
        """
        Create binary labels for each row in data.
        
        Args:
            data: DataFrame with columns ['close', 'high', 'low', 'atr']
            regime: Optional Series with regime labels for filtering
            
        Returns:
            Tuple of (labels Series, statistics dict)
        """
        if 'atr' not in data.columns:
            raise ValueError("Data must contain 'atr' column")
        
        required_cols = ['close', 'high', 'low', 'atr']
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"Data must contain '{col}' column")
        
        labels = pd.Series(np.nan, index=data.index, name='label')
        label_details = []
        
        # For each potential entry point
        for i in range(len(data) - self.max_holding_days - 1):
            entry_price = data['close'].iloc[i]
            atr = data['atr'].iloc[i]
            
            # Skip if ATR is invalid
            if pd.isna(atr) or atr <= 0:
                labels.iloc[i] = 0  # Label as failure if no valid ATR
                continue
            
            # Calculate stop and target
            stop_loss = entry_price - (self.risk_multiplier * atr)
            take_profit = entry_price + (self.reward_multiplier * atr)
            
            # Look forward to see which is hit first
            outcome = self._simulate_forward(
                data=data,
                start_idx=i + 1,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                max_bars=self.max_holding_days
            )
            
            labels.iloc[i] = outcome['label']
            label_details.append({
                'index': i,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'label': outcome['label'],
                'bars_held': outcome['bars_held'],
                'outcome_type': outcome['outcome_type']
            })
        
        # Calculate statistics
        stats = self._calculate_statistics(labels, label_details)
        
        logger.info(f"Created {len(labels)} labels:")
        logger.info(f"  Winners (1): {stats['win_count']} ({stats['win_rate']:.2%})")
        logger.info(f"  Losers (0): {stats['loss_count']} ({stats['loss_rate']:.2%})")
        logger.info(f"  Avg bars to win: {stats['avg_bars_to_win']:.1f}")
        logger.info(f"  Avg bars to loss: {stats['avg_bars_to_loss']:.1f}")
        
        return labels, stats
    
    def _simulate_forward(
        self,
        data: pd.DataFrame,
        start_idx: int,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        max_bars: int
    ) -> Dict:
        """
        Simulate forward price movement to determine outcome.
        
        Returns:
            Dict with keys: label, bars_held, outcome_type
        """
        end_idx = min(start_idx + max_bars, len(data))
        
        for bar_num, i in enumerate(range(start_idx, end_idx), start=1):
            low = data['low'].iloc[i]
            high = data['high'].iloc[i]
            
            # Check if stop hit (low crosses below stop)
            if low <= stop_loss:
                return {
                    'label': 0,
                    'bars_held': bar_num,
                    'outcome_type': 'stop_hit'
                }
            
            # Check if target hit (high crosses above target)
            if high >= take_profit:
                return {
                    'label': 1,
                    'bars_held': bar_num,
                    'outcome_type': 'target_hit'
                }
        
        # Timeout - no clear outcome
        # Label as 0 (failure) to be conservative
        return {
            'label': 0,
            'bars_held': max_bars,
            'outcome_type': 'timeout'
        }
    
    def _calculate_statistics(
        self,
        labels: pd.Series,
        details: list
    ) -> Dict[str, float]:
        """Calculate label statistics."""
        valid_labels = labels[~labels.isna()]
        
        win_count = (valid_labels == 1).sum()
        loss_count = (valid_labels == 0).sum()
        total = len(valid_labels)
        
        # Calculate average bars held
        winners = [d for d in details if d['label'] == 1]
        losers = [d for d in details if d['label'] == 0]
        
        avg_bars_to_win = np.mean([d['bars_held'] for d in winners]) if winners else 0
        avg_bars_to_loss = np.mean([d['bars_held'] for d in losers]) if losers else 0
        
        return {
            'win_count': int(win_count),
            'loss_count': int(loss_count),
            'total_count': total,
            'win_rate': win_count / total if total > 0 else 0,
            'loss_rate': loss_count / total if total > 0 else 0,
            'avg_bars_to_win': avg_bars_to_win,
            'avg_bars_to_loss': avg_bars_to_loss
        }
