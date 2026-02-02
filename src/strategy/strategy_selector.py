"""
Strategy Selector based on Market Regime

Selects appropriate trading strategy based on detected market regime:
- Trending: Use momentum strategies (follow the trend)
- Ranging: Use mean-reversion strategies (fade extremes)
- High Volatility: Reduce exposure or stay in cash
"""

from typing import Dict, Optional
import pandas as pd
import numpy as np

from ..utils.logger import get_logger

logger = get_logger(__name__)


class StrategySelector:
    """
    Selects trading strategy based on market regime.
    
    Strategy Rules:
    - TRENDING: Take trades in direction of trend, avoid counter-trend
    - RANGING: Take mean-reversion trades, avoid breakouts
    - HIGH_VOLATILITY: Reduce position size or avoid trading
    """
    
    def __init__(self):
        """Initialize strategy selector."""
        self.current_regime = None
        self.strategy_stats = {
            'trending': {'trades': 0, 'wins': 0, 'total_pnl': 0},
            'ranging': {'trades': 0, 'wins': 0, 'total_pnl': 0},
            'high_volatility': {'trades': 0, 'wins': 0, 'total_pnl': 0}
        }
        # Track near-misses for Phase 3 training
        self.near_misses = []
    
    def should_trade(self, regime: str) -> bool:
        """
        Determine if trading should occur in current regime.
        
        Args:
            regime: Current market regime
            
        Returns:
            True if trading is allowed
        """
        # Avoid trading in high volatility regimes
        if regime == 'high_volatility':
            logger.debug("Skipping trade: High volatility regime")
            return False
        
        return True
    
    def get_position_size_multiplier(self, regime: str) -> float:
        """
        Get position size multiplier based on regime.
        
        Args:
            regime: Current market regime
            
        Returns:
            Multiplier for position size (0.0 to 1.0)
        """
        multipliers = {
            'trending': 1.0,      # Full size in trending markets
            'ranging': 0.7,       # Reduced size in ranging markets
            'high_volatility': 0.3  # Minimal size in volatile markets
        }
        
        return multipliers.get(regime, 0.5)
    
    def get_entry_signal(
        self,
        regime: str,
        price: float,
        indicators: Dict[str, float],
        track_near_miss: bool = True
    ) -> Optional[str]:
        """
        Generate entry signal based on regime and indicators.
        
        Args:
            regime: Current market regime
            price: Current price
            indicators: Dictionary of technical indicators
            track_near_miss: Whether to log near-miss signals
            
        Returns:
            'LONG', 'SHORT', or None
        """
        if not self.should_trade(regime):
            return None
        
        signal = None
        if regime == 'trending':
            signal = self._trending_signal(price, indicators)
        elif regime == 'ranging':
            signal = self._ranging_signal(price, indicators)
        
        # Track near-misses (score = 1 out of 3) for Phase 3
        if track_near_miss and signal is None:
            self._track_near_miss(regime, price, indicators)
        
        return signal
    
    def _track_near_miss(self, regime: str, price: float, indicators: Dict[str, float]):
        """Track signals that almost qualified (for Phase 3 training data)."""
        # Only track if we have valid indicators
        if len([v for v in indicators.values() if v is not None]) < 3:
            return
        
        self.near_misses.append({
            'regime': regime,
            'price': price,
            'indicators': indicators.copy()
        })
    
    def _trending_signal(
        self,
        price: float,
        indicators: Dict[str, float]
    ) -> Optional[str]:
        """
        Momentum strategy for trending markets (PHASE 3.5: HIGH-RECALL).
        
        Logic: VERY LOOSE scoring to generate 300-500 candidates
        - RSI Weight: (RSI - 20) / 60, clamped [0, 1] (20-80 range)
        - Trend Weight: (Price - EMA) / (ATR * 0.5), clamped [0, 1] (0.5x ATR)
        - ADX Weight: (ADX - 5) / 25, clamped [0, 1] (5-30 range)
        
        Entry: If total_score > 0.4 (HIGH RECALL - let ML filter)
        
        Args:
            price: Current price
            indicators: Technical indicators
            
        Returns:
            Signal or None
        """
        ema20 = indicators.get('ema_20')
        rsi = indicators.get('rsi')
        adx = indicators.get('adx')
        atr = indicators.get('atr')
        
        if ema20 is None or rsi is None or adx is None or atr is None:
            return None
        
        # HIGH-RECALL Fuzzy scoring - VERY LOOSE
        score = 0.0
        
        # RSI contribution: (RSI - 20) / 60, clamped [0, 1]
        # RSI 20 = min, RSI 80 = max (EXTREME WIDENING)
        # Captures both oversold snaps and overbought momentum
        rsi_weight = max(0.0, min(1.0, (rsi - 20) / 60))
        score += rsi_weight
        
        # Trend strength: ABS(Price - EMA) / (ATR * 0.5), clamped [0, 1]
        # Just 0.5 ATR away from EMA = full weight (VERY LOOSE)
        # Detects EARLY trend formation in EITHER direction
        trend_weight = max(0.0, min(1.0, abs(price - ema20) / (atr * 0.5)))
        score += trend_weight
        
        # ADX contribution: (ADX - 5) / 25, clamped [0, 1]
        # ADX 5 = barely moving, ADX 30 = strong trend (ULTRA-LOW FLOOR)
        # Catches trends at inception
        adx_weight = max(0.0, min(1.0, (adx - 5) / 25))
        score += adx_weight
        
        # Entry if total score > 0.4 (out of 3.0)
        # Only 13% average strength needed - HIGH RECALL MODE
        # Let LightGBM (0.8678 AUC) do the real filtering
        if score > 0.4:
            return 'LONG'
        
        return None
    
    def _ranging_signal(
        self,
        price: float,
        indicators: Dict[str, float]
    ) -> Optional[str]:
        """
        Mean-reversion strategy for ranging markets (PHASE 3.5: ULTRA HIGH-RECALL).
        
        SPECIAL FOCUS: HDFC result (83% WR, 5.09% return) shows ranging excels
        
        Logic: EXTREMELY LOOSE scoring - widest net for ML
        - RSI Weight: (60 - RSI) / 40, clamped [0, 1] (20-60 range)
        - BB Weight: (BB_lower - Price) / (BB_width * 0.2) (ultra-sensitive)
        - Pullback Weight: (EMA - Price) / (ATR * 0.5) (half ATR)
        
        Entry: If total_score > 0.4 (ULTRA HIGH RECALL)
        
        Args:
            price: Current price
            indicators: Technical indicators
            
        Returns:
            Signal or None
        """
        bb_lower = indicators.get('bb_lower')
        bb_upper = indicators.get('bb_upper')
        rsi = indicators.get('rsi')
        ema20 = indicators.get('ema_20')
        atr = indicators.get('atr')
        
        if bb_lower is None or bb_upper is None or rsi is None or atr is None:
            return None
        
        # ULTRA HIGH-RECALL Fuzzy scoring - WIDEST NET
        score = 0.0
        
        # RSI oversold: (60 - RSI) / 40, clamped [0, 1]
        # RSI 20 = max weight, RSI 60 = min weight (EXTREME WIDTH)
        # Captures deep oversold + mild weakness
        rsi_weight = max(0.0, min(1.0, (60 - rsi) / 40))
        score += rsi_weight
        
        # Distance from lower BB: (BB_lower - Price) / (BB_width * 0.2)
        # ULTRA-SENSITIVE - even approaching BB triggers signal
        # Catches mean-reversion opportunities early
        bb_width = bb_upper - bb_lower
        if bb_width > 0:
            bb_weight = max(0.0, min(1.0, (bb_lower - price) / (bb_width * 0.2)))
            score += bb_weight
        
        # Pullback from EMA: ABS(EMA - Price) / (ATR * 0.5), clamped [0, 1]
        # Just 0.5 ATR pullback = full weight (VERY LOOSE)
        # Detects early pullback reversals in EITHER direction
        if ema20 is not None:
            pullback_weight = max(0.0, min(1.0, abs(ema20 - price) / (atr * 0.5)))
            score += pullback_weight
        
        # Entry if total score > 0.4 (out of 3.0)
        # ULTRA HIGH RECALL - only 13% strength needed
        # Trust LightGBM's 0.8678 AUC to find the gems
        if score > 0.4:
            return 'LONG'
        
        return None
    
    def update_stats(self, regime: str, pnl: float) -> None:
        """
        Update strategy statistics.
        
        Args:
            regime: Regime where trade occurred
            pnl: Trade P&L
        """
        if regime in self.strategy_stats:
            self.strategy_stats[regime]['trades'] += 1
            self.strategy_stats[regime]['total_pnl'] += pnl
            if pnl > 0:
                self.strategy_stats[regime]['wins'] += 1
    
    def get_stats(self) -> Dict:
        """Get strategy performance statistics."""
        stats = {}
        for regime, data in self.strategy_stats.items():
            if data['trades'] > 0:
                stats[regime] = {
                    'trades': data['trades'],
                    'win_rate': data['wins'] / data['trades'],
                    'avg_pnl': data['total_pnl'] / data['trades'],
                    'total_pnl': data['total_pnl']
                }
            else:
                stats[regime] = {
                    'trades': 0,
                    'win_rate': 0,
                    'avg_pnl': 0,
                    'total_pnl': 0
                }
        
        return stats
    
    def print_stats(self) -> None:
        """Print strategy statistics."""
        logger.info("\n" + "=" * 60)
        logger.info("STRATEGY PERFORMANCE BY REGIME")
        logger.info("=" * 60)
        
        stats = self.get_stats()
        for regime, data in stats.items():
            logger.info(f"\n{regime.upper()}:")
            logger.info(f"  Trades: {data['trades']}")
            if data['trades'] > 0:
                logger.info(f"  Win Rate: {data['win_rate']:.2%}")
                logger.info(f"  Avg P&L: Rs.{data['avg_pnl']:.2f}")
                logger.info(f"  Total P&L: Rs.{data['total_pnl']:.2f}")
        
        logger.info("=" * 60)
