"""
Phase 3.6: Backtest with 1.5:1 R:R Model

Test thresholds 0.20-0.30, focus on HDFC validation
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from test_phase3_backtest import run_integrated_backtest

print("\n" + "="*80)
print("PHASE 3.6: BACKTEST WITH 1.5:1 R:R MODEL")
print("="*80)
print("Model: lightgbm_entry_model_1_5_rr.txt")
print("Baseline: 37.14% label win rate (vs 23.6% with 2:1 R:R)")
print("Target: 40+ trades, 55%+ WR, >9.10% return")
print("="*80)

model_path = 'data/models/lightgbm_entry_model_1_5_rr.txt'

# RELIANCE threshold sweep
print("\n" + "="*80)
print("RELIANCE.NS - THRESHOLD SWEEP (0.20-0.30)")
print("="*80)
print(f"{'Threshold':<12} {'Trades':<8} {'Win Rate':<12} {'Return':<12} {'Sharpe':<10} {'Fuzzy->ML'}")
print("-"*80)

reliance_results = []
for threshold in [0.20, 0.22, 0.25, 0.27, 0.30]:
    result = run_integrated_backtest("RELIANCE.NS", threshold=threshold, model_path=model_path)
    if result:
        fuzzy = result['ml_stats']['fuzzy_candidates']
        ml_approved = result['ml_stats']['ml_approved']
        print(f"{threshold:<12.2f} {result['total_trades']:<8} {result['win_rate']:<12.2f}% {result['total_return']:<12.2f}% {result['sharpe_ratio']:<10.2f} {fuzzy}->{ml_approved}")
        reliance_results.append(result)

print("-"*80)
print("BASELINE (2:1 R:R, Phase 3.5): 23 trades, 60.87% WR, 6.59% return, 0.96 Sharpe")
print("TARGET (1.5:1 R:R): 40+ trades, 55%+ WR, >9.10% return")
print("="*80)

# HDFC validation (best performer)
print("\n" + "="*80)
print("HDFCBANK.NS - VALIDATION (Threshold 0.22-0.25)")
print("="*80)

hdfc_results = []
for threshold in [0.22, 0.25]:
    result = run_integrated_backtest("HDFCBANK.NS", threshold=threshold, model_path=model_path)
    if result:
        print(f"\nThreshold {threshold}:")
        print(f"  Trades: {result['total_trades']}")
        print(f"  Win Rate: {result['win_rate']:.2f}%")
        print(f"  Return: {result['total_return']:.2f}%")
        print(f"  Sharpe: {result['sharpe_ratio']:.2f}")
        print(f"  Fuzzy: {result['ml_stats']['fuzzy_candidates']} -> ML: {result['ml_stats']['ml_approved']}")
        hdfc_results.append(result)

print("="*80)

# Summary
print("\n" + "="*80)
print("FINAL VERDICT")
print("="*80)

best_reliance = max(reliance_results, key=lambda x: x['total_return']) if reliance_results else None
best_hdfc = max(hdfc_results, key=lambda x: x['total_return']) if hdfc_results else None

if best_reliance:
    print(f"\nBest RELIANCE:")
    print(f"  {best_reliance['total_trades']} trades, {best_reliance['win_rate']:.2f}% WR, {best_reliance['total_return']:.2f}% return")
    
if best_hdfc:
    print(f"\nBest HDFC:")
    print(f"  {best_hdfc['total_trades']} trades, {best_hdfc['win_rate']:.2f}% WR, {best_hdfc['total_return']:.2f}% return")

print(f"\nBaseline to beat: 9.10% return (Phase 1 Random)")
print("="*80)
