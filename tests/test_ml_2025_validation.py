"""
ML System 2025 Out-of-Sample Validation

Tests the Phase 5 ML system (234% on 2020-2024) on unseen 2025 data.
This is the TRUE TEST of whether the system generalizes.

Expected: 40-70% of baseline (94-164% return on 2025)
Reality: We'll find out!
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import yaml
from datetime import datetime

# Create config for 2025 testing
config_2025 = {
    'stocks': [
        'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
        'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS',
        'BAJFINANCE.NS', 'LT.NS', 'HCLTECH.NS', 'AXISBANK.NS', 'MARUTI.NS'
    ],
    'portfolio': {
        'initial_capital': 200000,
        'max_positions': 5,
        'risk_per_trade': 0.01,
        'max_portfolio_risk': 0.05,
        'enable_trailing_stop': False,
        'enable_time_exit': False,
        'enable_monthly_stop': True,
        'monthly_stop_loss': 0.10
    },
    'strategy': {
        'ml_model_path': 'data/models/lightgbm_entry_model.txt',
        'regime_model_path': 'data/models/hmm_regime_model.pkl',
        'ml_threshold': 0.30,
        'enable_ml_filter': True,
        'use_regime_thresholds': False
    },
    'backtest': {
        'start_date': '2025-01-01',
        'end_date': '2025-12-31'
    }
}

# Save config
print("="*80)
print("ML SYSTEM 2025 OUT-OF-SAMPLE VALIDATION")
print("="*80)
print("\nThis tests your ML system (234% on 2020-2024) on UNSEEN 2025 data")
print("This is the moment of truth - will the ML models generalize?\n")

config_dir = Path('config')
config_dir.mkdir(exist_ok=True)

config_path = config_dir / 'validation_2025.yaml'
with open(config_path, 'w') as f:
    yaml.dump(config_2025, f, default_flow_style=False)

print(f"✅ Created validation config: {config_path}")
print("\nConfiguration:")
print(f"  Period: 2025-01-01 to 2025-12-31 (UNSEEN DATA)")
print(f"  Stocks: 15 NSE stocks")
print(f"  Strategy: ML (LightGBM) + HMM Regime Detection")
print(f"  Capital: Rs. 200,000")
print(f"  Max Positions: 5")
print(f"  Risk: 1% per trade, 5% max portfolio")

print("\n" + "="*80)
print("RUNNING ML VALIDATION ON 2025 DATA...")
print("="*80)
print()

# Run the backtest
import run_portfolio
portfolio = run_portfolio.run_backtest(config_2025)

if portfolio:
    metrics = portfolio.get_performance_metrics()
    
    print("\n\n" + "="*80)
    print("CRITICAL COMPARISON: ML TRAINING vs OUT-OF-SAMPLE")
    print("="*80)
    
    # Training results (from Phase 5)
    train_return = 234.39
    train_trades = 255
    train_win_rate = 52.16
    train_sharpe = 1.82
    train_dd = 11.32
    train_days = 1237
    
    # Validation results
    val_return = metrics['total_return']
    val_trades = metrics['total_trades']
    val_win_rate = metrics['win_rate']
    val_sharpe = metrics['sharpe_ratio']
    val_dd = metrics['max_drawdown']
    val_days = 248
    
    # Annualized returns
    train_annual = train_return / (train_days / 252)
    val_annual = val_return / (val_days / 252)
    
    print(f"\n{'Metric':<25} {'Training (2020-2024)':<25} {'Validation (2025)':<25} {'Ratio'}")
    print("-"*100)
    print(f"{'Period':<25} {train_days} days{'':<14} {val_days} days{'':<14} {val_days/train_days*100:.0f}%")
    print(f"{'Total Return':<25} {train_return:.2f}%{'':<19} {val_return:.2f}%{'':<19} {val_return/train_return*100 if train_return > 0 else 0:.1f}%")
    print(f"{'Annualized Return':<25} {train_annual:.2f}%{'':<19} {val_annual:.2f}%{'':<19} {val_annual/train_annual*100 if train_annual > 0 else 0:.1f}%")
    print(f"{'Total Trades':<25} {train_trades:<25} {val_trades:<25} {val_trades/train_trades*100 if train_trades > 0 else 0:.1f}%")
    print(f"{'Win Rate':<25} {train_win_rate:.2f}%{'':<19} {val_win_rate:.2f}%{'':<19} {val_win_rate/train_win_rate*100 if train_win_rate > 0 else 0:.1f}%")
    print(f"{'Sharpe Ratio':<25} {train_sharpe:.2f}{'':<23} {val_sharpe:.2f}{'':<23} {val_sharpe/train_sharpe*100 if train_sharpe > 0 else 0:.1f}%")
    print(f"{'Max Drawdown':<25} {train_dd:.2f}%{'':<19} {val_dd:.2f}%{'':<19} {'Better' if val_dd < train_dd else 'Worse'}")
    
    print("\n" + "="*80)
    print("VALIDATION ASSESSMENT")
    print("="*80)
    
    performance_ratio = val_annual / train_annual * 100 if train_annual > 0 else 0
    
    print(f"\nOut-of-Sample Performance: {performance_ratio:.0f}% of training baseline")
    print(f"Absolute Return: {val_return:.2f}% over {val_days} days")
    print(f"Annualized: {val_annual:.2f}% per year")
    
    if performance_ratio >= 70:
        verdict = "🎉 EXCELLENT"
        meaning = "ML models generalize exceptionally well. Ready for production."
        action = "Add trading costs (0.3% per trade) and prepare for live deployment."
    elif performance_ratio >= 50:
        verdict = "✅ GOOD"
        meaning = "Acceptable degradation. System is robust and profitable."
        action = "Add trading costs and consider Phase 6 enhancements for improvement."
    elif performance_ratio >= 30:
        verdict = "⚠️  FAIR"
        meaning = "Significant performance drop but still profitable."
        action = "Implement Phase 6 improvements before going live (entry filters, position sizing)."
    elif performance_ratio >= 10:
        verdict = "⚠️  WEAK"
        meaning = "Major degradation. System struggles with new market conditions."
        action = "Deep analysis needed. Consider retraining on more recent data or algorithm changes."
    elif val_return > 0:
        verdict = "❌ POOR"
        meaning = "Barely profitable. Likely unprofitable after costs."
        action = "System validation FAILED. Need major redesign or different approach."
    else:
        verdict = "❌ FAILURE"
        meaning = "Losing money on validation data."
        action = "System is NOT ready for deployment. Complete overhaul needed."
    
    print(f"\n{verdict}")
    print(f"  Meaning: {meaning}")
    print(f"  Action: {action}")
    
    # Trade frequency analysis
    train_trades_per_month = train_trades / (train_days / 21)
    val_trades_per_month = val_trades / (val_days / 21) if val_days > 0 else 0
    
    print(f"\n📊 Trade Frequency:")
    print(f"  Training: {train_trades_per_month:.1f} trades/month")
    print(f"  Validation: {val_trades_per_month:.1f} trades/month")
    
    if val_trades_per_month < train_trades_per_month * 0.5:
        print(f"  ⚠️  Signal generation declined by {(1 - val_trades_per_month/train_trades_per_month)*100:.0f}%")
        print(f"     ML model may be too conservative on new data")
    elif val_trades_per_month > train_trades_per_month * 1.5:
        print(f"  ⚠️  Signal generation increased by {(val_trades_per_month/train_trades_per_month - 1)*100:.0f}%")
        print(f"     ML model may be overfitting to 2025 patterns")
    else:
        print(f"  ✅ Trade frequency consistent with training")
    
    # Risk analysis
    print(f"\n🛡️  Risk Metrics:")
    if val_dd < train_dd * 0.8:
        print(f"  ✅ Drawdown IMPROVED: {val_dd:.2f}% vs {train_dd:.2f}% (better risk control)")
    elif val_dd < train_dd * 1.2:
        print(f"  ✅ Drawdown SIMILAR: {val_dd:.2f}% vs {train_dd:.2f}% (consistent risk)")
    else:
        print(f"  ⚠️  Drawdown WORSE: {val_dd:.2f}% vs {train_dd:.2f}% (increased risk)")
    
    if val_sharpe > train_sharpe * 0.8:
        print(f"  ✅ Sharpe ratio maintained: {val_sharpe:.2f} vs {train_sharpe:.2f}")
    else:
        print(f"  ⚠️  Sharpe ratio declined: {val_sharpe:.2f} vs {train_sharpe:.2f}")
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    
    if performance_ratio >= 50:
        print("\n1. ✅ Add realistic trading costs:")
        print("   - Slippage: 0.2-0.3% per trade")
        print("   - Brokerage: 0.03-0.05% per trade")
        print("   - Expected real return: ~75% of backtest")
        print()
        print("2. ✅ Run walk-forward validation:")
        print("   - Test on different time periods")
        print("   - Verify consistency across market conditions")
        print()
        print("3. ✅ Paper trading:")
        print("   - 3-month paper trading period")
        print("   - Real-time signal generation")
        print("   - Track actual vs expected slippage")
        print()
        print("4. 🚀 Live deployment with small capital")
    else:
        print("\n1. ⚠️  PHASE 6 ENHANCEMENTS REQUIRED:")
        print("   - Entry quality filter (remove SBIN.NS or adjust threshold)")
        print("   - Volatility-adjusted position sizing")
        print("   - Sector diversification limits")
        print("   - Partial profit taking")
        print()
        print("2. 🔬 DEEP ANALYSIS:")
        print("   - Which stocks performed worse in 2025?")
        print("   - Which regimes caused losses?")
        print("   - Are ML features still relevant?")
        print()
        print("3. 🔄 POTENTIAL RETRAINING:")
        print("   - Retrain models on 2021-2025 data")
        print("   - Validate on 2026 (when available)")
        print("   - Update feature engineering")
    
    print("\n" + "="*80)
    print(f"VALIDATION COMPLETE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
else:
    print("\n❌ Validation failed - check error logs")

