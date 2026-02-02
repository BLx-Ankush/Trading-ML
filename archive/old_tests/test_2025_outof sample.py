"""
2025 OUT-OF-SAMPLE VALIDATION TEST
====================================
Tests if Phase 5 Revised system (trained on 2020-2024) works on unseen 2025 data.
Tests ALL 15 stocks from your portfolio.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
from datetime import datetime
import yfinance as yf

from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.features.indicators import TechnicalIndicators
from src.models.hmm_regime import RegimeDetector
from src.strategy.ml_strategy_selector import MLStrategySelector
from src.backtesting.portfolio_engine import PortfolioEngine

# Configuration
STOCKS = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
    'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS',
    'BAJFINANCE.NS', 'LT.NS', 'HCLTECH.NS', 'AXISBANK.NS', 'MARUTI.NS'
]

print("=" * 80)
print("2025 OUT-OF-SAMPLE VALIDATION TEST")
print("=" * 80)
print(f"\nTrain: 2020-2024 (Phase 5 Revised baseline)")
print(f"Test:  2025 (UNSEEN DATA - True validation)")
print(f"Stocks: {len(STOCKS)} stocks (full portfolio)")
print("=" * 80)

# Check 2025 data availability
print("\n[Step 1/5] Checking 2025 Data Availability...")
sample = yf.download('RELIANCE.NS', start='2025-01-01', end='2025-12-31', progress=False)
if len(sample) == 0:
    print("❌ No 2025 data available yet")
    sys.exit(1)
    
print(f"✅ 2025 data available: {len(sample)} trading days")
print(f"   Date range: {sample.index[0].date()} to {sample.index[-1].date()}")
last_close = float(sample['Close'].iloc[-1])
print(f"   RELIANCE last: Rs. {last_close:.2f}")

def load_stock_data(symbol, start_date, end_date):
    """Load and prepare stock data (same as run_portfolio.py)."""
    try:
        loader = DataLoader()
        raw_data = loader.fetch_yahoo_data(symbol, start_date, end_date)
        
        if raw_data.empty:
            return pd.DataFrame()
        
        data = DataProcessor.clean_data(raw_data)
        data = TechnicalIndicators.calculate_all_indicators(data)
        return data
    
    except Exception as e:
        print(f"   ❌ {symbol}: {str(e)}")
        return pd.DataFrame()

# Load training data (2020-2024)
print(f"\n[Step 2/5] Loading Training Data (2020-2024)...")
training_data = {}
regime_detector = RegimeDetector(n_states=3)

for symbol in STOCKS:
    print(f"   {symbol}...", end=" ")
    data = load_stock_data(symbol, '2020-01-01', '2024-12-31')
    
    if not data.empty:
        training_data[symbol] = data
        print(f"✓ {len(data)} days")
    else:
        print("✗")

print(f"\n✅ Loaded {len(training_data)}/{len(STOCKS)} stocks for training")

if len(training_data) == 0:
    print("❌ No training data loaded. Exiting.")
    sys.exit(1)

# Train regime detector
print(f"\n[Step 3/5] Training Regime Detector on 2020-2024...")
print("   Training HMM model...")
first_stock = list(training_data.keys())[0]
regime_detector.fit(training_data[first_stock])
regime_detector.save('models/hmm_regime_model.pkl')
print("   ✅ Regime model trained")

# Train ML strategy
print(f"\n[Step 4/5] Training ML Strategy on 2020-2024...")
ml_strategy = MLStrategySelector(model_path='models/ml_strategy_model.pkl')

for symbol, data in training_data.items():
    print(f"   {symbol}...", end=" ")
    _, regimes = regime_detector.predict(data)
    data['Regime'] = regimes
    ml_strategy.train_model(data, symbol)
    print("✓")

print(f"   ✅ ML models trained for {len(training_data)} stocks")

# Load 2025 test data
print(f"\n[Step 5/5] Testing on 2025 Data (OUT-OF-SAMPLE)...")
print("=" * 80)
print("Loading 2025 data for testing...")

test_data = {}
regime_data = {}

for symbol in training_data.keys():  # Only test stocks we trained on
    print(f"   {symbol}...", end=" ")
    data = load_stock_data(symbol, '2025-01-01', '2025-12-31')
    
    if not data.empty:
        _, regimes = regime_detector.predict(data)
        data['Regime'] = regimes
        test_data[symbol] = data
        regime_data[symbol] = pd.Series(regimes, index=data.index)
        print(f"✓ {len(data)} days")
    else:
        print("✗")

print(f"\n✅ Loaded {len(test_data)} stocks for 2025 testing")
print("\nRunning backtest on 2025...")

# Run portfolio backtest on 2025
portfolio = PortfolioEngine(
    initial_capital=200000,
    max_positions=5,
    risk_per_trade=0.01,
    max_portfolio_risk=0.05,
    enable_trailing_stop=False,      # Phase 5 Revised settings
    enable_time_exit=False,
    enable_monthly_stop=True,
    monthly_stop_loss=0.10
)

# Get all trading dates from 2025
all_dates = sorted(set(date for df in test_data.values() for date in df.index))
print(f"Trading {len(all_dates)} days in 2025...")

# Simulate trading
for current_date in all_dates:
    # Update existing positions
    for symbol in list(portfolio.positions.keys()):
        if symbol in test_data and current_date in test_data[symbol].index:
            row = test_data[symbol].loc[current_date]
            portfolio.update_positions(symbol, current_date, row)
    
    # Check for new entry signals
    for symbol, data in test_data.items():
        if current_date not in data.index:
            continue
            
        signal = ml_strategy.generate_signal(data, current_date, symbol)
        
        if signal == 1 and portfolio.can_open_position(symbol, current_date):
            row = data.loc[current_date]
            current_price = row['Close']
            atr = row['ATR']
            
            stop_loss = current_price - (2 * atr)
            take_profit = current_price + (4 * atr)
            
            portfolio.open_position(
                symbol=symbol,
                entry_date=current_date,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                regime=row['Regime']
            )

# Close all open positions at end
final_date = all_dates[-1]
for symbol in list(portfolio.positions.keys()):
    if symbol in test_data and final_date in test_data[symbol].index:
        portfolio.close_position(
            symbol, 
            final_date, 
            test_data[symbol].loc[final_date, 'Close'], 
            'EOD'
        )

# Results
print("\n" + "=" * 80)
print("2025 OUT-OF-SAMPLE RESULTS (ALL 15 STOCKS)")
print("=" * 80)

metrics = portfolio.get_performance_metrics()

print(f"\n📊 PERFORMANCE METRICS:")
print(f"   Total Return:        {metrics['total_return']:.2f}%")
print(f"   Total Trades:        {metrics['total_trades']}")
print(f"   Win Rate:            {metrics['win_rate']:.2f}%")
print(f"   Profit Factor:       {metrics['profit_factor']:.2f}")
print(f"   Sharpe Ratio:        {metrics['sharpe_ratio']:.2f}")
print(f"   Max Drawdown:        {metrics['max_drawdown']:.2f}%")
print(f"   Avg Trade Return:    {metrics['avg_trade_return']:.2f}%")

# Compare to 2020-2024 baseline
print(f"\n📈 COMPARISON TO 2020-2024 TRAINING PERIOD:")
baseline_annual = 234.39 / 5  # 46.88% per year (5 years)
test_return = metrics['total_return']
test_days = len(all_dates)
test_annualized = (test_return / test_days) * 252 if test_days > 0 else 0

print(f"   2020-2024 Baseline:  46.88% per year (234% over 5 years)")
print(f"   2025 Actual:         {test_return:.2f}% ({test_days} days)")
print(f"   2025 Annualized:     {test_annualized:.2f}% per year")
print(f"   Performance Ratio:   {(test_annualized/46.88)*100:.1f}% of baseline")

print(f"\n🎯 VALIDATION RESULT:")
if test_annualized >= 35:  # 75% of baseline
    print("   ✅ EXCELLENT - System performs well on unseen 2025 data!")
    print("   🎉 Strategy is robust and generalizes well")
elif test_annualized >= 23:  # 50% of baseline
    print("   ⚠️  ACCEPTABLE - Some performance degradation")
    print("   💡 System works but may need minor tuning")
elif test_annualized >= 0:
    print("   ⚠️  WEAK - Significant performance drop")
    print("   ⚠️  May be overfitted to 2020-2024 period")
else:
    print("   ❌ FAIL - Losing money on 2025 data")
    print("   ⚠️  System likely overfitted, needs revision")

print(f"\n📋 KEY INSIGHT:")
print(f"   This test uses 2025 as UNSEEN data - the system has NEVER")
print(f"   seen this data before. It was trained only on 2020-2024.")
print(f"   This is the true test of whether your strategy is real or just curve-fitted.")

print("\n" + "=" * 80)
print(f"Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
