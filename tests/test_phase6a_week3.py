"""
Phase 6A Week 3: Sector Diversification

Implements:
1. Sector classification for all 15 stocks
2. Sector-based position limits:
   - Banking: Max 2 positions (HDFCBANK, KOTAKBANK, SBIN, AXISBANK)
   - IT: Max 2 positions (TCS, INFY, HCLTECH)
   - Consumer: Max 2 (HINDUNILVR, ITC)
   - Others: Max 1 each

Expected Impact:
- Reduce correlated sector risk
- Better portfolio diversification
- More stable returns during sector rotations
- Slightly fewer trades, higher quality
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import yaml

# Configuration with Phase 6A Week 3 improvements
config_phase6a_week3 = {
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
        # Phase 6A Week 1: Trading costs
        'enable_trading_costs': True,
        'slippage_pct': 0.0025,
        'brokerage_pct': 0.0004,
        'stt_pct': 0.001,
        # Phase 6A Week 2: Problem stock filters
        'excluded_stocks': ['ICICIBANK.NS'],
        'stock_ml_thresholds': {
            'KOTAKBANK.NS': 0.45,
            'ITC.NS': 0.40
        }
        # Phase 6A Week 3: Sector limits now built into PortfolioEngine
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
print("PHASE 6A WEEK 3: SECTOR DIVERSIFICATION")
print("="*80)
print("\nSector Classification:")
print("  Banking (Max 2): HDFCBANK, SBIN, KOTAKBANK, AXISBANK")
print("  IT (Max 2): TCS, INFY, HCLTECH")
print("  Consumer (Max 2): HINDUNILVR, ITC")
print("  Others (Max 1 each): RELIANCE, MARUTI, BHARTIARTL, BAJFINANCE, LT")
print("\nProblem in Week 2:")
print("  Could hold 4 banking stocks simultaneously -> correlated risk")
print("  Example: All banking stocks down together during sector decline")
print("\nSolution:")
print("  Limit Banking sector to 2 positions maximum")
print("  Limit IT sector to 2 positions maximum")
print("  Better diversification across sectors")
print("\nExpected Impact:")
print("  * Reduce correlated sector risk")
print("  * More stable returns during sector rotations")
print("  * Better risk-adjusted returns (higher Sharpe)")
print("  * Slightly fewer total trades (better quality)")

config_dir = Path('config')
config_dir.mkdir(exist_ok=True)

config_path = config_dir / 'phase6a_week3.yaml'
with open(config_path, 'w') as f:
    yaml.dump(config_phase6a_week3, f, default_flow_style=False)

print(f"\n[OK] Created config: {config_path}")
print("\n" + "="*80)
print("RUNNING VALIDATION WITH WEEK 3 IMPROVEMENTS...")
print("="*80)
print()

# Run the backtest
import run_portfolio
portfolio_week3 = run_portfolio.run_backtest(config_phase6a_week3)

if portfolio_week3:
    metrics_week3 = portfolio_week3.get_performance_metrics()
    
    # Week 2 baseline
    week2_return = 18.24
    week2_trades = 35
    week2_win_rate = 65.71
    week2_sharpe = 2.10
    week2_dd = 2.61
    
    # Week 3 results
    net_return = metrics_week3['total_return']
    total_trades = metrics_week3['total_trades']
    win_rate = metrics_week3['win_rate']
    sharpe = metrics_week3['sharpe_ratio']
    max_dd = metrics_week3['max_drawdown']
    
    print("\n\n" + "="*80)
    print("PHASE 6A WEEK 3 RESULTS: BEFORE vs AFTER")
    print("="*80)
    
    print(f"\n{'Metric':<30} {'Week 2 Baseline':<20} {'Week 3 Diversified':<20} {'Change'}")
    print("-"*90)
    print(f"{'Total Return (Net)':<30} {week2_return:.2f}%{'':<14} {net_return:.2f}%{'':<14} {net_return-week2_return:+.2f}%")
    print(f"{'Total Trades':<30} {week2_trades:<20} {total_trades:<20} {total_trades-week2_trades:+d}")
    print(f"{'Win Rate':<30} {week2_win_rate:.2f}%{'':<14} {win_rate:.2f}%{'':<14} {win_rate-week2_win_rate:+.2f}%")
    print(f"{'Sharpe Ratio':<30} {week2_sharpe:.2f}{'':<18} {sharpe:.2f}{'':<18} {sharpe-week2_sharpe:+.2f}")
    print(f"{'Max Drawdown':<30} {week2_dd:.2f}%{'':<14} {max_dd:.2f}%{'':<14} {max_dd-week2_dd:+.2f}%")
    
    # Sector analysis
    print("\n" + "="*80)
    print("SECTOR DIVERSIFICATION ANALYSIS")
    print("="*80)
    
    symbol_df = portfolio_week3.get_symbol_breakdown()
    
    # Group by sector
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
    
    print("\nSector Performance:")
    sector_stats = {}
    for _, row in symbol_df.iterrows():
        sector = sector_map.get(row['symbol'], 'Other')
        if sector not in sector_stats:
            sector_stats[sector] = {'trades': 0, 'pnl': 0, 'wins': 0}
        sector_stats[sector]['trades'] += row['trades']
        sector_stats[sector]['pnl'] += row['total_pnl']
        sector_stats[sector]['wins'] += int(row['trades'] * row['win_rate'] / 100)
    
    print(f"\n{'Sector':<15} {'Trades':<10} {'Win Rate':<12} {'Total PnL'}")
    print("-"*60)
    for sector, stats in sorted(sector_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
        wr = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
        print(f"{sector:<15} {stats['trades']:<10} {wr:<11.1f}% Rs.{stats['pnl']:>10,.0f}")
    
    print("\n" + "="*80)
    print("WEEK 3 ASSESSMENT")
    print("="*80)
    
    improvement = net_return - week2_return
    annualized = net_return / (248 / 252)
    
    print(f"\nNet Return: {net_return:.2f}% (Annualized: {annualized:.2f}%)")
    print(f"Change from Week 2: {improvement:+.2f}%")
    print(f"Win Rate: {win_rate:.2f}% ({win_rate-week2_win_rate:+.2f}%)")
    print(f"Sharpe Ratio: {sharpe:.2f} ({sharpe-week2_sharpe:+.2f})")
    print(f"Max Drawdown: {max_dd:.2f}% ({max_dd-week2_dd:+.2f}%)")
    
    # Assess sector diversification impact
    if improvement > 0 and sharpe > week2_sharpe:
        verdict = "[EXCELLENT]"
        meaning = "Sector diversification improved both returns and risk metrics"
        action = "Ready for Week 4: Final validation and comparison"
    elif sharpe > week2_sharpe:
        verdict = "[GOOD]"
        meaning = "Better risk-adjusted returns despite similar absolute returns"
        action = "Proceed to Week 4 - diversification stabilized performance"
    elif improvement > 0:
        verdict = "[ACCEPTABLE]"
        meaning = "Slight improvement in returns"
        action = "Diversification helped, ready for Week 4"
    elif abs(improvement) < 0.5:
        verdict = "[NEUTRAL]"
        meaning = "Sector limits had minimal impact on returns"
        action = "Risk control achieved, proceed to Week 4"
    else:
        verdict = "[REVIEW]"
        meaning = "Sector limits may be too restrictive"
        action = "Consider relaxing limits or different sector groupings"
    
    print(f"\nVerdict: {verdict}")
    print(f"Meaning: {meaning}")
    print(f"Action: {action}")
    
    print("\n" + "="*80)
    print("NEXT STEPS - PHASE 6A WEEK 4")
    print("="*80)
    print("""
Week 4 Plan: Final Validation & Comparison

Complete Phase 6A implementation includes:
1. Trading costs: 0.68% per round trip (Week 1)
2. Problem stocks: ICICIBANK excluded, KOTAKBANK/ITC thresholds raised (Week 2)
3. Sector diversification: Max 2 banking, max 2 IT (Week 3)

Week 4 Tasks:
1. Run comprehensive validation on 2025 data
2. Compare vs original baseline (no improvements)
3. Calculate overall improvement metrics
4. Assess if system is ready for live deployment

Success Criteria:
- Net return: 15-20% annual (beats mutual funds)
- Win rate: 60%+ (up from 53.85% baseline)
- Sharpe ratio: 2.0+ (excellent risk-adjusted returns)
- Max drawdown: <5% (tight risk control)
- Profit factor: 2.5+ (strong edge)

If criteria met -> System ready for paper trading phase
If not met -> Review and iterate on Phase 6A improvements
""")
    
    print("="*80)
    print("SUMMARY")
    print("="*80)
    status = 'COMPLETE' if improvement >= -0.5 else 'NEEDS REVIEW'
    print(f"""
Phase 6A Week 3: [OK] {status}

Changes Implemented:
  * Added sector classification for all 15 stocks
  * Implemented sector limits:
    - Banking: Max 2 positions
    - IT: Max 2 positions
    - Others: Max 1-2 each
  * Prevents correlated sector risk

Results:
  * Net Return: {net_return:.2f}%
  * Change: {improvement:+.2f}%
  * Win Rate: {win_rate:.2f}% ({win_rate-week2_win_rate:+.2f}%)
  * Sharpe: {sharpe:.2f} ({sharpe-week2_sharpe:+.2f})
  * Max DD: {max_dd:.2f}% ({max_dd-week2_dd:+.2f}%)
  * Verdict: {verdict}

{'Ready for Week 4: Final validation' if abs(improvement) <= 1.0 else 'Review sector limits before Week 4'}
""")
    
    print("\n" + "="*80)
    print("PHASE 6A PROGRESS TRACKER")
    print("="*80)
    print(f"""
Baseline (No improvements):     22.21% gross, 15.65% net after costs
Week 1 (Trading costs):         15.65% net (baseline with realistic costs)
Week 2 (Problem stocks):        18.24% net (+2.59% improvement)
Week 3 (Sector diversification): {net_return:.2f}% net ({improvement:+.2f}% from Week 2)

Total Improvement vs Baseline:  {net_return - 15.65:+.2f}%
Annualized Net Return:          {annualized:.2f}%
Beats Mutual Funds (10-12%):    {'YES' if annualized > 12 else 'NO'}
Beats Index Funds (12-15%):     {'YES' if annualized > 15 else 'NO'}
Ready for Live Deployment:      {'YES' if annualized > 15 and sharpe > 2.0 else 'REVIEW NEEDED'}
""")

else:
    print("[FAILED] Backtest failed. Check logs for errors.")
