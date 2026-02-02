"""Quick summary of Phase 3 results."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from test_phase3_backtest import run_integrated_backtest

print("\n" + "="*80)
print("PHASE 3: THRESHOLD COMPARISON (RELIANCE.NS)")
print("="*80)
print(f"{'Threshold':<12} {'Trades':<8} {'Win Rate':<12} {'Return':<12} {'Sharpe':<10} {'ML Approved'}")
print("-"*80)

for threshold in [0.20, 0.25, 0.30]:
    result = run_integrated_backtest("RELIANCE.NS", threshold=threshold)
    if result:
        print(f"{threshold:<12.2f} {result['total_trades']:<8} {result['win_rate']:<12.2f}% {result['total_return']:<12.2f}% {result['sharpe_ratio']:<10.2f} {result['ml_stats']['ml_approved']}/{result['ml_stats']['fuzzy_candidates']}")

print("-"*80)
print("BASELINE (Phase 1): 32 trades, 51.88% WR, 9.10% return, 0.92 Sharpe")
print("="*80)

print("\n" + "="*80)
print("CROSS-STOCK VALIDATION (Threshold 0.25)")
print("="*80)
print(f"{'Stock':<15} {'Trades':<8} {'Win Rate':<12} {'Return':<12} {'Sharpe'}")
print("-"*80)

for stock in ["TCS.NS", "HDFCBANK.NS"]:
    result = run_integrated_backtest(stock, threshold=0.25)
    if result:
        print(f"{stock:<15} {result['total_trades']:<8} {result['win_rate']:<12.2f}% {result['total_return']:<12.2f}% {result['sharpe_ratio']:<10.2f}")

print("="*80)
