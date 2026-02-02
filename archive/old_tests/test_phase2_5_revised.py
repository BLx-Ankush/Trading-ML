"""
Phase 2.5: REVISED - High Recall System

Fixes from Phase 2 failure:
1. ✓ Removed 30% randomness (engineer, not gambler)
2. ✓ Scoring-based entry (2/3 conditions instead of 3/3)
3. ✓ Loosened thresholds (ADX 20, RSI 42)
4. ✓ Near-miss tracking for Phase 3

Goal: 100+ trades with 60%+ win rate
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

# Re-use the existing backtest script but with updated strategy selector
from test_phase2_backtest import run_comparison_test
from src.utils.logger import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("PHASE 2.5: REVISED BACKTEST - HIGH RECALL SYSTEM")
    logger.info("=" * 80)
    logger.info("\nChanges from Phase 2:")
    logger.info("  1. Removed 30% randomness filter")
    logger.info("  2. Scoring-based entry (2/3 conditions)")
    logger.info("  3. Loosened ADX: 25 → 20")
    logger.info("  4. Loosened RSI: 35 → 42")
    logger.info("  5. Near-miss tracking enabled")
    logger.info("\nExpected: 100+ trades, 60%+ win rate, 8-12% annual return")
    logger.info("=" * 80 + "\n")
    
    run_comparison_test()
