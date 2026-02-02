"""
Phase 3.5: High-Recall Reset Test

Test the loosened fuzzy logic to verify we're generating 300-500 candidates.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from test_phase3_backtest import run_integrated_backtest
from src.utils.logger import get_logger

logger = get_logger(__name__)

logger.info("=" * 80)
logger.info("PHASE 3.5: HIGH-RECALL RESET")
logger.info("Goal: Generate 300-500 fuzzy candidates, let ML filter to 100+ trades")
logger.info("=" * 80)

# Test with loosened fuzzy logic
print("\n" + "="*80)
print("THRESHOLD COMPARISON (With Loosened Fuzzy Layer)")
print("="*80)
print(f"{'Threshold':<12} {'Trades':<8} {'Win Rate':<12} {'Return':<12} {'Sharpe':<10} {'Fuzzy→ML→Final'}")
print("-"*80)

for threshold in [0.20, 0.25, 0.30]:
    result = run_integrated_backtest("RELIANCE.NS", threshold=threshold)
    if result:
        fuzzy = result['ml_stats']['fuzzy_candidates']
        ml_approved = result['ml_stats']['ml_approved']
        trades = result['total_trades']
        print(f"{threshold:<12.2f} {trades:<8} {result['win_rate']:<12.2f}% {result['total_return']:<12.2f}% {result['sharpe_ratio']:<10.2f} {fuzzy}→{ml_approved}→{trades}")

print("-"*80)
print("TARGET: 300-500 fuzzy candidates → ML filters to 100+ trades")
print("BASELINE: 32 trades, 51.88% WR, 9.10% return, 0.92 Sharpe")
print("="*80)

# Test on HDFC (best performer)
print("\n" + "="*80)
print("HDFC VALIDATION (Best Mean-Reversion Performer)")
print("="*80)

result = run_integrated_backtest("HDFCBANK.NS", threshold=0.25)
if result:
    print(f"\nResults:")
    print(f"  Trades: {result['total_trades']}")
    print(f"  Win Rate: {result['win_rate']:.2f}%")
    print(f"  Return: {result['total_return']:.2f}%")
    print(f"  Sharpe: {result['sharpe_ratio']:.2f}")
    print(f"  Fuzzy Candidates: {result['ml_stats']['fuzzy_candidates']}")
    print(f"  ML Approved: {result['ml_stats']['ml_approved']}")

print("="*80)
