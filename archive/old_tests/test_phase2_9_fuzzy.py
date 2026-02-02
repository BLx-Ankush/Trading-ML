"""
Phase 2.9: FUZZY SCORING - Soft Probabilities

Mathematical Fix:
- Old: P(Trade) = P(Regime) × P(Ind1) × P(Ind2) × P(Ind3) → Probability Leak
- New: Score = W1 + W2 + W3, each weight ∈ [0,1], threshold = 1.2

Key Changes:
1. ✓ Continuous weights instead of binary (0/1)
2. ✓ RSI: (RSI - 40) / 20 → captures partial strength
3. ✓ Trend: (Price - EMA) / (ATR × 2) → volatility-normalized
4. ✓ ADX: (ADX - 15) / 15 → gradual trend strength
5. ✓ Lower threshold: 1.2 / 3.0 (40% average) vs 2/3 (66% average)

Expected: 100+ trades with 58-60% win rate
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from test_phase2_backtest import run_comparison_test
from src.utils.logger import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("PHASE 2.9: FUZZY SCORING - SOFT PROBABILITIES")
    logger.info("=" * 80)
    logger.info("\nMathematical Fix:")
    logger.info("  Old: Binary AND chains = Probability Leak")
    logger.info("  New: Weighted Sum = Smooth Probability")
    logger.info("")
    logger.info("Fuzzy Weights:")
    logger.info("  RSI: (RSI - 40) / 20, clamped [0, 1]")
    logger.info("  Trend: (Price - EMA) / (ATR x 2), clamped [0, 1]")
    logger.info("  ADX: (ADX - 15) / 15, clamped [0, 1]")
    logger.info("")
    logger.info("Entry Threshold: 1.2 / 3.0 (40% average strength)")
    logger.info("")
    logger.info("Expected: 100+ trades, 58-60% win rate, 10-15% total return")
    logger.info("=" * 80 + "\n")
    
    run_comparison_test()
