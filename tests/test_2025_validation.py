"""
2025 OUT-OF-SAMPLE VALIDATION TEST
===================================
Tests if Phase 5 Revised system (trained on 2020-2024) works on unseen 2025 data.
This is the ultimate validation - if it works on 2025, the system is robust.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import yfinance as yf
import pandas as pd
from datetime import datetime

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

TRAINING_START = '2020-01-01'
TRAINING_END = '2024-12-31'
TEST_START = '2025-01-01'
TEST_END = '2025-12-31'

print("=" * 80)
print("2025 OUT-OF-SAMPLE VALIDATION TEST")
print("=" * 80)
print(f"\nTraining Period: {TRAINING_START} to {TRAINING_END} (2020-2024)")
print(f"Test Period: {TEST_START} to {TEST_END} (2025 - UNSEEN DATA)")
print("\n" + "=" * 80)

# Check 2025 data availability
print("\n[1/5] Checking 2025 Data Availability...")
sample = yf.download('RELIANCE.NS', start=TEST_START, end=TEST_END, progress=False)
if len(sample) == 0:
    print("❌ ERROR: No 2025 data available yet on Yahoo Finance")
    sys.exit(1)
    
print(f"✅ 2025 data available: {len(sample)} trading days")
print(f"   Date range: {sample.index[0].strftime('%Y-%m-%d')} to {sample.index[-1].strftime('%Y-%m-%d')}")
close_value = sample['Close'].iloc[-1]
print(f"   RELIANCE last close: Rs. {float(close_value):.2f}")

# Load training data (2020-2024)
print(f"\n[2/5] Loading Training Data (2020-2024)...")
data_loader = DataLoader()
training_data = {}
for symbol in STOCKS:
    try:
        df = data_loader.load_stock_data(symbol, TRAINING_START, TRAINING_END)
        if df is not None and len(df) > 0:
            training_data[symbol] = df
            print(f"   ✅ {symbol}: {len(df)} days")
    except Exception as e:
        print(f"   ❌ {symbol}: {str(e)}")

print(f"\n✅ Loaded {len(training_data)}/{len(STOCKS)} stocks for training")

# Train models on 2020-2024 data
print(f"\n[3/5] Training ML Models on 2020-2024 Data...")
data_processor = DataProcessor()
technical_indicators = TechnicalIndicators()
regime_detector = RegimeDetector()
ml_strategy = MLStrategySelector()

trained_stocks = {}
for symbol, df in training_data.items():
    try:
        # Process features
        df = data_processor.calculate_returns(df)
        df = technical_indicators.add_all_indicators(df)
        df = regime_detector.detect_regime(df)
        
        # Train ML model
        trained_model = ml_strategy.train_model(df, symbol)
        if trained_model is not None:
            trained_stocks[symbol] = df
            print(f"   ✅ {symbol}: Model trained")
    except Exception as e:
        print(f"   ❌ {symbol}: {str(e)}")

print(f"\n✅ Trained models for {len(trained_stocks)} stocks")

# Load 2025 test data
print(f"\n[4/5] Loading 2025 Test Data (UNSEEN)...")
test_data = {}
for symbol in trained_stocks.keys():
    try:
        df = data_loader.load_stock_data(symbol, TEST_START, TEST_END)
        if df is not None and len(df) > 0:
            # Process with same features (but don't retrain!)
            df = data_processor.calculate_returns(df)
            df = technical_indicators.add_all_indicators(df)
            df = regime_detector.detect_regime(df)
            
            test_data[symbol] = df
            print(f"   ✅ {symbol}: {len(df)} days")
    except Exception as e:
        print(f"   ❌ {symbol}: {str(e)}")

print(f"\n✅ Loaded {len(test_data)} stocks for 2025 testing")

# Run backtest on 2025 data
print(f"\n[5/5] Running Backtest on 2025 (Out-of-Sample)...")
print("=" * 80)

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

# Get all dates from 2025 test data
all_dates = sorted(set(date for df in test_data.values() for date in df.index))

for current_date in all_dates:
    # Update portfolio with current prices
    for symbol, df in test_data.items():
        if current_date in df.index:
            portfolio.update_positions(symbol, current_date, df.loc[current_date])
    
    # Check for new signals
    for symbol, df in test_data.items():
        if current_date in df.index:
            signal = ml_strategy.generate_signal(df, current_date, symbol)
            
            if signal == 1 and portfolio.can_open_position(symbol, current_date):
                current_price = df.loc[current_date, 'Close']
                atr = df.loc[current_date, 'ATR']
                stop_loss = current_price - (2 * atr)
                take_profit = current_price + (4 * atr)
                
                portfolio.open_position(
                    symbol=symbol,
                    entry_date=current_date,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    regime=df.loc[current_date, 'Regime']
                )

# Close all positions at end
for symbol, df in test_data.items():
    last_date = df.index[-1]
    portfolio.close_position(symbol, last_date, df.loc[last_date, 'Close'], 'EOD')

# Results
print("\n" + "=" * 80)
print("2025 OUT-OF-SAMPLE RESULTS")
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
print(f"\n📈 COMPARISON TO 2020-2024 TRAINING:")
baseline_annual = 234.39 / 5  # 46.88% per year
test_actual = metrics['total_return']
days_in_2025 = len(all_dates)
test_annualized = (test_actual / days_in_2025) * 252 if days_in_2025 > 0 else 0

print(f"   2020-2024 Baseline:  46.88% per year")
print(f"   2025 Actual:         {test_actual:.2f}% ({days_in_2025} days)")
print(f"   2025 Annualized:     {test_annualized:.2f}% per year")
print(f"   Performance Ratio:   {(test_annualized/46.88)*100:.1f}% of baseline")

print(f"\n🎯 VALIDATION RESULT:")
if test_annualized >= 35:  # 75% of baseline
    print("   ✅ PASS - System performs well on unseen 2025 data")
    print("   🎉 Robust system confirmed!")
elif test_annualized >= 23:  # 50% of baseline
    print("   ⚠️  ACCEPTABLE - Some degradation on unseen data")
    print("   💡 Consider recalibration")
else:
    print("   ❌ FAIL - Significant degradation on unseen data")
    print("   ⚠️  System may be overfitted to 2020-2024")

print("\n" + "=" * 80)
print(f"Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
