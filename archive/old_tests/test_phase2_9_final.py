"""
Phase 2.9 FINAL: Aggressively Loosened Fuzzy Scoring

Last attempt before Phase 3. Changes:
1. Threshold: 1.2 → 0.8 (27% average strength)
2. RSI: (RSI - 30) / 30 (widened from 40/20)
3. Trend: (Price - EMA) / ATR (reduced from ATR × 2)
4. ADX: (ADX - 10) / 20 (lowered from 15/15)
5. BB: width × 0.3 (loosened from 0.5)

Target: 100+ trades with 55-58% win rate
If this fails: Phase 3 LightGBM is mandatory
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from test_phase2_backtest import run_comparison_test
from src.utils.logger import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("PHASE 2.9 FINAL: AGGRESSIVELY LOOSENED FUZZY SCORING")
    logger.info("=" * 80)
    logger.info("\nFinal Rule-Based Attempt (20% success probability):")
    logger.info("  Threshold: 1.2 -> 0.8 (27% avg strength)")
    logger.info("  RSI: (RSI - 30) / 30 [widened]")
    logger.info("  Trend: (Price - EMA) / ATR [halved strictness]")
    logger.info("  ADX: (ADX - 10) / 20 [lowered baseline]")
    logger.info("")
    logger.info("SUCCESS CRITERIA: 80+ trades, 54%+ win rate, beat 9.10% baseline")
    logger.info("FAILURE CRITERIA: <50 trades OR <52% win rate -> Phase 3 LightGBM")
    logger.info("=" * 80 + "\n")
    
    run_comparison_test()
