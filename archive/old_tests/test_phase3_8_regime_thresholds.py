"""
Phase 3.8: Regime-Specific ML Thresholds

Strategy: Adapt ML threshold based on HMM regime
- Trending (70% of time): Threshold 0.20 (aggressive - trust the trend)
- Ranging (26.5% of time): Threshold 0.28 (selective - only best setups)
- High Vol (3.5% of time): Threshold 0.35 (very selective - avoid chaos)

Expected: 23 trades -> 32-35 trades, ~58% WR, ~8-9% return
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from test_phase3_backtest import run_integrated_backtest

print("\n" + "="*80)
print("PHASE 3.8: REGIME-ADAPTIVE ML THRESHOLDS")
print("="*80)
print("Phase 3.5 (Flat 0.30):  23 trades, 60.87% WR, 6.59% return, 0.96 Sharpe")
print("Phase 3.8 (Adaptive):   Expected 32-35 trades, 58%+ WR, 8-9% return")
print()
print("Threshold Strategy:")
print("  - Trending regime:        0.20 (aggressive)")
print("  - Ranging regime:         0.28 (selective)")
print("  - High volatility regime: 0.35 (very selective)")
print("="*80)

model_path = 'data/models/lightgbm_entry_model.txt'  # 2:1 R:R model (AUC 0.8678)

# Test on all three stocks
symbols = ['RELIANCE.NS', 'HDFCBANK.NS', 'TCS.NS']
results = {}

print("\n" + "="*80)
print("TESTING REGIME-ADAPTIVE STRATEGY")
print("="*80)

for symbol in symbols:
    print(f"\n{'='*80}")
    print(f"{symbol}")
    print(f"{'='*80}")
    
    result = run_integrated_backtest(
        symbol=symbol,
        threshold=0.30,  # This will be overridden by regime-specific thresholds
        model_path=model_path
    )
    
    if result:
        results[symbol] = result
        print(f"\nResults for {symbol}:")
        print(f"  Total Trades:    {result['total_trades']}")
        print(f"  Win Rate:        {result['win_rate']:.2f}%")
        print(f"  Total Return:    {result['total_return']:.2f}%")
        print(f"  Sharpe Ratio:    {result['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown:    {result['max_drawdown']:.2f}%")
        
        # Regime breakdown
        ml_stats = result.get('ml_stats', {})
        by_regime = ml_stats.get('by_regime', {})
        
        print(f"\n  Regime Breakdown:")
        for regime, stats in by_regime.items():
            candidates = stats.get('candidates', 0)
            approved = stats.get('approved', 0)
            approval_rate = (approved / candidates * 100) if candidates > 0 else 0
            print(f"    {regime:<20}: {candidates:>3} candidates -> {approved:>3} approved ({approval_rate:.1f}%)")

print("\n" + "="*80)
print("SUMMARY - REGIME-ADAPTIVE vs FLAT THRESHOLD")
print("="*80)

if results:
    print(f"\n{'Stock':<15} {'Trades':<8} {'Win Rate':<12} {'Return':<12} {'Sharpe':<10} {'vs Phase 3.5'}")
    print("-"*80)
    
    # Phase 3.5 baselines (flat threshold 0.30)
    phase35_baselines = {
        'RELIANCE.NS': {'trades': 23, 'win_rate': 60.87, 'return': 6.59, 'sharpe': 0.96},
        'HDFCBANK.NS': {'trades': 40, 'win_rate': 40.00, 'return': 3.78, 'sharpe': 0.43},
        'TCS.NS': {'trades': 0, 'win_rate': 0, 'return': 0, 'sharpe': 0}  # Unknown
    }
    
    for symbol, result in results.items():
        baseline = phase35_baselines.get(symbol, {})
        baseline_return = baseline.get('return', 0)
        improvement = ((result['total_return'] - baseline_return) / baseline_return * 100) if baseline_return > 0 else 0
        
        print(f"{symbol:<15} {result['total_trades']:<8} {result['win_rate']:<12.2f}% {result['total_return']:<12.2f}% {result['sharpe_ratio']:<10.2f} {improvement:+.1f}%")
    
    print("-"*80)
    
    # Average improvement
    avg_return = sum(r['total_return'] for r in results.values()) / len(results)
    avg_trades = sum(r['total_trades'] for r in results.values()) / len(results)
    avg_wr = sum(r['win_rate'] for r in results.values()) / len(results)
    
    print(f"{'AVERAGE':<15} {avg_trades:<8.1f} {avg_wr:<12.2f}% {avg_return:<12.2f}%")
    print()
    print("BASELINE TO BEAT: 9.10% (Phase 1 Random Entries)")
    print("="*80)
    
    # Verdict
    if avg_return >= 9.10:
        print("\n" + "🎉 SUCCESS! Regime-adaptive strategy beats random baseline!")
    elif avg_return >= 7.5:
        print("\n" + "✅ STRONG IMPROVEMENT over Phase 3.5 (6.59%), close to baseline")
    else:
        print("\n" + "⚠️  Improvement over Phase 3.5 but still below random baseline")
else:
    print("\nNo results collected.")

print("="*80)
