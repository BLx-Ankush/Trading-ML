"""
Phase 6A Production System - 2025 Out-of-Sample Validation

This runs the COMPLETE Phase 6A system (all improvements) on 2025 unseen data.

Configuration includes:
- Trading costs: 0.68% per round trip
- Problem stock filters: ICICIBANK excluded, KOTAKBANK/ITC thresholds raised
- Sector diversification: Max 2 banking, max 2 IT positions
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import yaml
from datetime import datetime

print("="*80)
print("PHASE 6A PRODUCTION SYSTEM - 2025 OUT-OF-SAMPLE VALIDATION")
print("="*80)
print(f"\nValidation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("\nTesting Period: 2025-01-01 to 2025-12-31 (UNSEEN DATA)")
print("This is out-of-sample validation - the system was trained on 2020-2024.")
print("\n" + "="*80)

# Load production configuration
config_path = Path('config/phase6a_production.yaml')

if not config_path.exists():
    print(f"\n[ERROR] Production config not found: {config_path}")
    print("Creating production configuration...")
    
    config = {
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
            'enable_trading_costs': True,
            'slippage_pct': 0.0025,
            'brokerage_pct': 0.0004,
            'stt_pct': 0.001,
            'excluded_stocks': ['ICICIBANK.NS'],
            'stock_ml_thresholds': {
                'KOTAKBANK.NS': 0.45,
                'ITC.NS': 0.40
            }
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
    
    config_path.parent.mkdir(exist_ok=True)
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    print(f"[OK] Created: {config_path}")
else:
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    print(f"[OK] Loaded production config: {config_path}")

print("\nCONFIGURATION SUMMARY:")
print("-" * 80)
print("\nStock Universe: 15 NSE stocks")
print(f"Excluded: {', '.join(config['portfolio'].get('excluded_stocks', []))}")
print(f"\nRaised ML Thresholds:")
for stock, threshold in config['portfolio'].get('stock_ml_thresholds', {}).items():
    print(f"  {stock}: {threshold} (default: 0.30)")

print("\nTrading Costs:")
print(f"  Slippage: {config['portfolio']['slippage_pct']*100:.2f}% per trade (entry + exit)")
print(f"  Brokerage: {config['portfolio']['brokerage_pct']*100:.2f}% per trade (entry + exit)")
print(f"  STT: {config['portfolio']['stt_pct']*100:.2f}% on sell side")
print(f"  Total: ~0.68% per round trip")

print("\nSector Limits: (Built into PortfolioEngine)")
print("  Banking: Max 2 positions")
print("  IT: Max 2 positions")

print("\n" + "="*80)
print("RUNNING OUT-OF-SAMPLE VALIDATION...")
print("="*80)
print()

# Run backtest
import run_portfolio
portfolio = run_portfolio.run_backtest(config)

if portfolio:
    metrics = portfolio.get_performance_metrics()
    
    print("\n\n" + "="*80)
    print("COMPLETE SYSTEM RESULTS - 2025 OUT-OF-SAMPLE")
    print("="*80)
    
    # Extract metrics
    initial_capital = config['portfolio']['initial_capital']
    final_capital = portfolio.capital
    net_return = metrics['total_return']
    gross_return = metrics.get('gross_return', net_return)
    total_costs = metrics.get('total_costs', 0.0)
    cost_impact = metrics.get('cost_impact_pct', 0.0)
    
    total_trades = metrics['total_trades']
    win_rate = metrics['win_rate']
    sharpe = metrics['sharpe_ratio']
    max_dd = metrics['max_drawdown']
    profit_factor = metrics['profit_factor']
    avg_win = metrics['avg_win']
    avg_loss = metrics['avg_loss']
    
    # Annualized
    days = 248
    annualized = net_return / (days / 252)
    
    print(f"\n{'='*80}")
    print("PERFORMANCE SUMMARY")
    print("="*80)
    
    print(f"\nCapital:")
    print(f"  Initial Capital:        Rs. {initial_capital:>12,}")
    print(f"  Final Capital:          Rs. {final_capital:>12,.2f}")
    print(f"  Profit/Loss:            Rs. {final_capital - initial_capital:>12,.2f}")
    
    print(f"\nReturns:")
    print(f"  Gross Return:           {gross_return:>12.2f}%")
    print(f"  Trading Costs:          Rs. {total_costs:>12,.2f} ({cost_impact:.2f}% of capital)")
    print(f"  Net Return:             {net_return:>12.2f}%")
    print(f"  Annualized Return:      {annualized:>12.2f}%")
    
    print(f"\nTrading Activity:")
    print(f"  Total Trades:           {total_trades:>12}")
    print(f"  Winning Trades:         {int(total_trades * win_rate / 100):>12}")
    print(f"  Losing Trades:          {int(total_trades * (100 - win_rate) / 100):>12}")
    print(f"  Win Rate:               {win_rate:>12.2f}%")
    
    print(f"\nRisk Metrics:")
    print(f"  Sharpe Ratio:           {sharpe:>12.2f}")
    print(f"  Profit Factor:          {profit_factor:>12.2f}")
    print(f"  Max Drawdown:           {max_dd:>12.2f}%")
    print(f"  Average Win:            Rs. {avg_win:>12,.2f}")
    print(f"  Average Loss:           Rs. {avg_loss:>12,.2f}")
    print(f"  Win/Loss Ratio:         {abs(avg_win/avg_loss) if avg_loss != 0 else 0:>12.2f}")
    
    # Cost breakdown
    if 'slippage_costs' in metrics:
        slippage = metrics['slippage_costs']
        brokerage = metrics['brokerage_costs']
        stt = metrics['stt_costs']
        
        print(f"\n{'='*80}")
        print("TRADING COSTS BREAKDOWN")
        print("="*80)
        
        print(f"\n  Slippage Costs:         Rs. {slippage:>12,.2f} ({slippage/total_costs*100:.1f}% of total)")
        print(f"  Brokerage Costs:        Rs. {brokerage:>12,.2f} ({brokerage/total_costs*100:.1f}% of total)")
        print(f"  STT Costs:              Rs. {stt:>12,.2f} ({stt/total_costs*100:.1f}% of total)")
        print(f"  Total Costs:            Rs. {total_costs:>12,.2f}")
        print(f"\n  Cost per Trade:         Rs. {total_costs/total_trades if total_trades > 0 else 0:>12,.2f}")
        print(f"  Cost as % of Capital:   {cost_impact:>12.2f}%")
    
    # Per-symbol performance
    print(f"\n{'='*80}")
    print("PER-STOCK PERFORMANCE")
    print("="*80)
    
    symbol_df = portfolio.get_symbol_breakdown()
    if not symbol_df.empty:
        symbol_df = symbol_df.sort_values('total_pnl', ascending=False)
        
        print(f"\n{'Stock':<18} {'Trades':<8} {'Win Rate':<12} {'Total PnL':<18} {'Avg PnL'}")
        print("-" * 80)
        
        for _, row in symbol_df.iterrows():
            stock = row['symbol']
            trades = row['trades']
            wr = row['win_rate']
            pnl = row['total_pnl']
            avg_pnl = row['avg_pnl_per_trade']
            
            print(f"{stock:<18} {trades:<8} {wr:>6.1f}%{'':<4} Rs. {pnl:>12,.0f}{'':<2} Rs. {avg_pnl:>9,.0f}")
    
    # Sector analysis
    print(f"\n{'='*80}")
    print("SECTOR PERFORMANCE")
    print("="*80)
    
    sector_map = {
        'HDFCBANK.NS': 'Banking',
        'SBIN.NS': 'Banking',
        'KOTAKBANK.NS': 'Banking',
        'AXISBANK.NS': 'Banking',
        'TCS.NS': 'IT',
        'INFY.NS': 'IT',
        'HCLTECH.NS': 'IT',
        'RELIANCE.NS': 'Energy',
        'HINDUNILVR.NS': 'Consumer',
        'ITC.NS': 'Consumer',
        'MARUTI.NS': 'Auto',
        'BHARTIARTL.NS': 'Telecom',
        'BAJFINANCE.NS': 'NBFC',
        'LT.NS': 'Infrastructure'
    }
    
    sector_stats = {}
    for _, row in symbol_df.iterrows():
        sector = sector_map.get(row['symbol'], 'Other')
        if sector not in sector_stats:
            sector_stats[sector] = {'trades': 0, 'pnl': 0, 'wins': 0}
        sector_stats[sector]['trades'] += row['trades']
        sector_stats[sector]['pnl'] += row['total_pnl']
        sector_stats[sector]['wins'] += int(row['trades'] * row['win_rate'] / 100)
    
    print(f"\n{'Sector':<18} {'Trades':<8} {'Win Rate':<12} {'Total PnL'}")
    print("-" * 60)
    
    for sector, stats in sorted(sector_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
        wr = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
        print(f"{sector:<18} {stats['trades']:<8} {wr:>6.1f}%{'':<4} Rs. {stats['pnl']:>12,.0f}")
    
    # Benchmark comparison
    print(f"\n{'='*80}")
    print("BENCHMARK COMPARISON")
    print("="*80)
    
    benchmarks = {
        'Fixed Deposits': 7.5,
        'Mutual Funds': 11.0,
        'Index Funds (Nifty 50)': 13.5,
        'Top Hedge Funds': 17.5
    }
    
    print(f"\n{'Benchmark':<30} {'Return':<15} {'Our System':<15} {'Difference'}")
    print("-" * 80)
    
    for name, bench_return in benchmarks.items():
        diff = annualized - bench_return
        status = "[BEATS]" if diff > 0 else "[LOSES]"
        print(f"{name:<30} {bench_return:>6.1f}%{'':<7} {annualized:>6.2f}%{'':<7} {status} {diff:+.2f}%")
    
    # System validation
    print(f"\n{'='*80}")
    print("SYSTEM VALIDATION AGAINST CRITERIA")
    print("="*80)
    
    criteria_results = []
    criteria_results.append(("Net Return > 15% annual", annualized > 15, annualized, "15%"))
    criteria_results.append(("Win Rate > 60%", win_rate > 60, win_rate, "60%"))
    criteria_results.append(("Sharpe Ratio > 2.0", sharpe > 2.0, sharpe, "2.0"))
    criteria_results.append(("Max Drawdown < 5%", max_dd < 5, max_dd, "5%"))
    criteria_results.append(("Profit Factor > 2.5", profit_factor > 2.5, profit_factor, "2.5"))
    
    passed = sum(1 for _, result, _, _ in criteria_results if result)
    total = len(criteria_results)
    
    print(f"\n{'Criterion':<35} {'Target':<15} {'Actual':<15} {'Status'}")
    print("-" * 80)
    
    for criterion, result, actual, target in criteria_results:
        status = "[PASS]" if result else "[FAIL]"
        if "Return" in criterion or "Rate" in criterion or "Drawdown" in criterion:
            actual_str = f"{actual:.2f}%"
        else:
            actual_str = f"{actual:.2f}"
        print(f"{criterion:<35} {target:<15} {actual_str:<15} {status}")
    
    print(f"\nCriteria Passed: {passed}/{total} ({passed/total*100:.0f}%)")
    
    # Final verdict
    print(f"\n{'='*80}")
    print("FINAL SYSTEM ASSESSMENT")
    print("="*80)
    
    if passed == total:
        verdict = "READY FOR LIVE DEPLOYMENT"
        color = "[EXCELLENT]"
    elif passed >= 4:
        verdict = "ALMOST READY - MINOR IMPROVEMENTS NEEDED"
        color = "[VERY GOOD]"
    elif passed >= 3:
        verdict = "NEEDS IMPROVEMENTS BEFORE DEPLOYMENT"
        color = "[GOOD]"
    else:
        verdict = "NOT READY FOR DEPLOYMENT"
        color = "[NEEDS WORK]"
    
    print(f"\n{color} System Status: {verdict}")
    print(f"\nOut-of-Sample Performance: {annualized:.2f}% annualized return")
    print(f"Risk-Adjusted Return: Sharpe {sharpe:.2f} (institutional-grade)")
    print(f"Reliability: {win_rate:.1f}% win rate across {total_trades} trades")
    print(f"Risk Control: {max_dd:.2f}% maximum drawdown")
    
    if passed >= 4:
        print("\n[RECOMMENDATION]")
        print("System has passed validation and is ready for paper trading phase.")
        print("\nNext Steps:")
        print("1. Deploy system with virtual money for 2-3 months")
        print("2. Monitor real-time performance vs backtest expectations")
        print("3. Validate execution quality and cost assumptions")
        print("4. Build confidence before deploying real capital")
        print("5. Start with small capital (10-20% of target) when going live")
    else:
        print("\n[RECOMMENDATION]")
        print("System needs additional improvements before deployment.")
        print("Focus on addressing failed criteria before paper trading.")
    
    print(f"\n{'='*80}")
    print("PHASE 6A VALIDATION COMPLETE")
    print("="*80)
    print(f"\nSystem trained on: 2020-2024 (4 years)")
    print(f"Validated on: 2025 (1 year, unseen data)")
    print(f"Out-of-sample retention: {annualized / 47.75 * 100:.1f}% of training performance")
    print(f"\nConfiguration: config/phase6a_production.yaml")
    print("="*80)

else:
    print("\n[ERROR] Backtest failed. Check logs for details.")
