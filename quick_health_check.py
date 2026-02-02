"""
Quick System Health Check
Tests core functionality on December 2025 data
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import run_portfolio
import yaml

print("\n" + "="*60)
print("SYSTEM HEALTH CHECK - December 2025")
print("="*60)

# Load production config
with open('config/phase6a_production.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Test on last month only
config['backtest']['start_date'] = '2025-12-01'
config['backtest']['end_date'] = '2025-12-31'

print("\nRunning quick validation...")
portfolio = run_portfolio.run_backtest(config)

if portfolio:
    metrics = portfolio.get_performance_metrics()
    
    print("\n" + "="*60)
    print("HEALTH CHECK RESULTS")
    print("="*60)
    print(f"\nReturn: {metrics['total_return']:.2f}%")
    print(f"Trades: {metrics['total_trades']}")
    print(f"Win Rate: {metrics['win_rate']:.2f}%")
    print(f"Sharpe: {metrics['sharpe_ratio']:.2f}")
    
    # Check for critical issues
    issues = []
    if metrics['total_trades'] == 0:
        issues.append("No trades executed")
    if metrics['total_return'] < -5:
        issues.append(f"Large loss: {metrics['total_return']:.2f}%")
    
    print("\n" + "="*60)
    if issues:
        print("STATUS: ⚠️ WARNINGS")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("STATUS: ✅ SYSTEM HEALTHY")
    print("="*60)
else:
    print("\n[ERROR] Backtest failed")
    sys.exit(1)
