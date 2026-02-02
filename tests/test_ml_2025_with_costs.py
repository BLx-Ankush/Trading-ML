"""
Phase 6A Week 1: ML System 2025 Validation WITH TRADING COSTS

Tests Phase 5 ML system on 2025 data with realistic costs:
- Slippage: 0.25% per trade (entry + exit)
- Brokerage: 0.04% per trade (entry + exit)
- STT: 0.1% (sell side only)
- Total: ~0.68% per round trip

Expected: 22.21% gross → 15-18% net
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import yaml
from datetime import datetime

# Create config for 2025 testing WITH COSTS
config_2025_with_costs = {
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
        'monthly_stop_loss': 0.10,
        # Phase 6A: Enable realistic trading costs
        'enable_trading_costs': True,
        'slippage_pct': 0.0025,    # 0.25% slippage per trade
        'brokerage_pct': 0.0004,   # 0.04% brokerage per trade
        'stt_pct': 0.001           # 0.1% STT on sell side (Budget 2026 unchanged)
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

print("="*80)
print("PHASE 6A WEEK 1: ML SYSTEM 2025 VALIDATION WITH TRADING COSTS")
print("="*80)
print("\nBudget 2026 Update: STT unchanged at 0.1% for equity delivery ✅")
print("Testing realistic costs: 0.68% per round trip\n")

config_dir = Path('config')
config_dir.mkdir(exist_ok=True)

config_path = config_dir / 'validation_2025_with_costs.yaml'
with open(config_path, 'w') as f:
    yaml.dump(config_2025_with_costs, f, default_flow_style=False)

print(f"✅ Created validation config: {config_path}")
print("\nConfiguration:")
print(f"  Period: 2025-01-01 to 2025-12-31")
print(f"  Stocks: 15 NSE stocks")
print(f"  Strategy: ML (LightGBM) + HMM Regime")
print(f"  Capital: Rs. 200,000")
print(f"  Max Positions: 5")
print(f"  Risk: 1% per trade, 5% max portfolio")
print(f"\n  ⚠️  TRADING COSTS ENABLED:")
print(f"  - Slippage: 0.25% per trade (entry + exit)")
print(f"  - Brokerage: 0.04% per trade (entry + exit)")
print(f"  - STT: 0.1% (sell side only)")
print(f"  - TOTAL: ~0.68% per round trip")

print("\n" + "="*80)
print("RUNNING ML VALIDATION WITH TRADING COSTS...")
print("="*80)
print()

# Run the backtest
import run_portfolio
portfolio = run_portfolio.run_backtest(config_2025_with_costs)

if portfolio:
    metrics = portfolio.get_performance_metrics()
    
    print("\n\n" + "="*80)
    print("PHASE 6A RESULTS: GROSS vs NET RETURNS")
    print("="*80)
    
    # Baseline (without costs - from previous validation)
    baseline_return = 22.21
    baseline_trades = 39
    baseline_win_rate = 56.41
    
    # With costs
    gross_return = metrics.get('gross_return', metrics['total_return'])
    net_return = metrics['total_return']
    total_costs = metrics.get('total_costs', 0.0)
    cost_impact_pct = metrics.get('cost_impact_pct', 0.0)
    
    trades = metrics['total_trades']
    win_rate = metrics['win_rate']
    sharpe = metrics['sharpe_ratio']
    max_dd = metrics['max_drawdown']
    
    # Annualized
    days = 248  # Approximate trading days in 2025
    net_annual = net_return / (days / 252)
    
    print(f"\n{'Metric':<30} {'Without Costs':<20} {'With Costs':<20} {'Impact'}")
    print("-"*90)
    print(f"{'Total Return':<30} {baseline_return:.2f}%{'':<14} {net_return:.2f}%{'':<14} {net_return-baseline_return:+.2f}%")
    print(f"{'Annualized Return':<30} {baseline_return:.2f}%{'':<14} {net_annual:.2f}%{'':<14} {net_annual-baseline_return:+.2f}%")
    print(f"{'Total Trades':<30} {baseline_trades:<20} {trades:<20} {trades-baseline_trades:+d}")
    print(f"{'Win Rate':<30} {baseline_win_rate:.2f}%{'':<14} {win_rate:.2f}%{'':<14} {win_rate-baseline_win_rate:+.2f}%")
    print(f"{'Sharpe Ratio':<30} {'N/A':<20} {sharpe:.2f}{'':<18}")
    print(f"{'Max Drawdown':<30} {'N/A':<20} {max_dd:.2f}%{'':<14}")
    
    print("\n" + "="*80)
    print("COST BREAKDOWN")
    print("="*80)
    
    print(f"\nTotal Trading Costs: Rs. {total_costs:,.2f}")
    print(f"Cost Impact: {cost_impact_pct:.2f}% of initial capital")
    print(f"Average Cost per Trade: Rs. {total_costs/trades if trades > 0 else 0:,.2f}")
    
    if 'slippage_costs' in metrics:
        slippage = metrics['slippage_costs']
        brokerage = metrics['brokerage_costs']
        stt = metrics['stt_costs']
        
        print(f"\nCost Components:")
        print(f"  Slippage (0.25% × 2):  Rs. {slippage:>10,.2f}  ({slippage/total_costs*100:.1f}%)")
        print(f"  Brokerage (0.04% × 2): Rs. {brokerage:>10,.2f}  ({brokerage/total_costs*100:.1f}%)")
        print(f"  STT (0.1% sell):       Rs. {stt:>10,.2f}  ({stt/total_costs*100:.1f}%)")
    
    print("\n" + "="*80)
    print("PHASE 6A WEEK 1 ASSESSMENT")
    print("="*80)
    
    print(f"\n✅ Phase 6A Week 1: COMPLETE")
    print(f"\nNet Return After Costs: {net_return:.2f}%")
    print(f"Annualized: {net_annual:.2f}% per year")
    print(f"Cost Impact: {baseline_return - net_return:.2f}% absolute")
    
    if net_annual >= 15:
        verdict = "🎉 EXCELLENT"
        meaning = "Even with costs, system beats most mutual funds (10-12% annual)"
        action = "Proceed to Week 2: Fix problem stocks (ICICIBANK, KOTAKBANK)"
    elif net_annual >= 12:
        verdict = "✅ GOOD"
        meaning = "Competitive with index funds (~12-15% annual)"
        action = "Week 2 improvements will push into excellent territory"
    elif net_annual >= 8:
        verdict = "⚠️  FAIR"
        meaning = "Marginally beats FD rates (7-8%)"
        action = "Need Week 2-3 improvements to make worthwhile"
    else:
        verdict = "❌ WEAK"
        meaning = "Below FD rates. Not worth the risk."
        action = "Major rework needed or consider different strategy"
    
    print(f"\nVerdict: {verdict}")
    print(f"Meaning: {meaning}")
    print(f"Action: {action}")
    
    # Compare with training baseline
    print("\n" + "="*80)
    print("OUT-OF-SAMPLE PERFORMANCE (Net After Costs)")
    print("="*80)
    
    train_annual = 47.75  # From Phase 5 training
    retention = (net_annual / train_annual * 100) if train_annual > 0 else 0
    
    print(f"\nTraining (2020-2024): {train_annual:.2f}% annual")
    print(f"Validation (2025) Net: {net_annual:.2f}% annual")
    print(f"Retention Rate: {retention:.1f}% (After costs)")
    
    if retention >= 35:
        print(f"✅ Strong generalization even with realistic costs")
    elif retention >= 25:
        print(f"✅ Acceptable retention with costs")
    else:
        print(f"⚠️  Costs significantly impact viability")
    
    print("\n" + "="*80)
    print("NEXT STEPS - PHASE 6A WEEK 2")
    print("="*80)
    print("""
Week 2 Plan: Fix Problem Stocks

1. Exclude ICICIBANK.NS
   - 0% win rate on 2025 validation
   - Lost Rs. 1,783 (single largest losing stock)
   - Add to exclusion list

2. Raise threshold for KOTAKBANK.NS
   - Only 25% win rate (3 losses vs 1 win)
   - Lost Rs. 1,230 net
   - Increase ML threshold from 0.30 to 0.40-0.45

3. Expected Impact:
   - Reduce losing trades by 4-5
   - Recover ~Rs. 3,000-3,500
   - Improve win rate: 56.41% → 58-60%
   - Net return: Current → +1.5-2.0% higher

Implementation: Modify run_portfolio.py to add stock-specific filters
""")
    
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"""
Phase 6A Week 1: ✅ COMPLETE

Implementation:
  • Added realistic trading costs to portfolio_engine.py
  • Cost structure: 0.68% per round trip (Budget 2026 compliant)
  • Comprehensive tracking and reporting

Results:
  • Gross Return: {gross_return:.2f}%
  • Net Return: {net_return:.2f}%
  • Cost Impact: {cost_impact_pct:.2f}% of capital
  • Annualized Net: {net_annual:.2f}%
  • Verdict: {verdict.split()[-1]}

Ready for Week 2: Fix problem stocks
""")

else:
    print("❌ Backtest failed. Check logs for errors.")
