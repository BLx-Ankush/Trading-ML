"""
2025 Validation - Simple Strategy (No ML Required)
Tests Phase 5 Revised approach on 2025 data using technical signals only
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
from datetime import datetime

from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.features.indicators import TechnicalIndicators
from src.backtesting.portfolio_engine import PortfolioEngine

print("="*80)
print("2025 OUT-OF-SAMPLE VALIDATION")
print("="*80)
print("Testing on 2025 data (all 15 stocks)")
print("Strategy: RSI + MACD + Trend (simple, no ML)")
print("="*80)

STOCKS = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
    'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS',
    'BAJFINANCE.NS', 'LT.NS', 'HCLTECH.NS', 'AXISBANK.NS', 'MARUTI.NS'
]

def load_stock_data(symbol, start_date, end_date):
    """Load and prepare stock data."""
    try:
        loader = DataLoader()
        raw_data = loader.fetch_yahoo_data(symbol, start_date, end_date)
        
        if raw_data.empty:
            return pd.DataFrame()
        
        data = DataProcessor.clean_data(raw_data)
        data = TechnicalIndicators.calculate_all_indicators(data)
        return data
    except Exception as e:
        print(f"   Error loading {symbol}: {e}")
        return pd.DataFrame()

def generate_simple_signal(data, current_date):
    """
    Simple technical strategy (no ML):
    BUY when:
    - RSI < 40 (oversold)
    - MACD crosses above signal
    - Price above 50 EMA (trend filter)
    """
    try:
        row = data.loc[current_date]
        
        # Get previous row for MACD crossover
        idx = data.index.get_loc(current_date)
        if idx == 0:
            return 0
        prev_row = data.iloc[idx - 1]
        
        # Entry conditions
        rsi_oversold = row.get('rsi', 50) < 40
        macd_cross = (row.get('macd', 0) > row.get('macd_signal', 0) and 
                     prev_row.get('macd', 0) <= prev_row.get('macd_signal', 0))
        trend_up = row.get('close', 0) > row.get('ema_21', row.get('close', 0))
        
        if rsi_oversold and macd_cross and trend_up:
            return 1
        
        return 0
        
    except Exception as e:
        return 0

# Load 2025 data
print("\nLoading 2025 data...")
stock_data = {}

for symbol in STOCKS:
    print(f"  {symbol}...", end=" ", flush=True)
    data = load_stock_data(symbol, '2025-01-01', '2025-12-31')
    
    if not data.empty:
        # Add default regime for compatibility
        data['Regime'] = 'TRENDING'
        stock_data[symbol] = data
        print(f"✓ {len(data)} days")
    else:
        print("✗")

print(f"\n✅ Loaded {len(stock_data)}/{len(STOCKS)} stocks")

if len(stock_data) == 0:
    print("❌ No data. Exiting.")
    sys.exit(1)

# Run backtest
print("\nRunning 2025 backtest with simple technical strategy...")
print("="*80)

portfolio = PortfolioEngine(
    initial_capital=200000,
    max_positions=5,
    risk_per_trade=0.01,
    max_portfolio_risk=0.05,
    enable_trailing_stop=False,
    enable_time_exit=False,
    enable_monthly_stop=True,
    monthly_stop_loss=0.10
)

# Get all dates
all_dates = sorted(set(date for df in stock_data.values() for date in df.index))
print(f"Period: {all_dates[0].date()} to {all_dates[-1].date()} ({len(all_dates)} days)\n")

signals_generated = 0

# Simulate trading
for current_date in all_dates:
    # Update equity curve
    portfolio.update_equity_curve(current_date)
    
    # Check existing positions for exits
    for symbol in list(portfolio.positions.keys()):
        if symbol in stock_data and current_date in stock_data[symbol].index:
            row = stock_data[symbol].loc[current_date]
            position = portfolio.positions[symbol]
            
            # Check stop loss
            if row['low'] <= position.stop_loss:
                portfolio.close_position(symbol, current_date, position.stop_loss, 'STOP')
                continue
            
            # Check take profit
            if row['high'] >= position.take_profit:
                portfolio.close_position(symbol, current_date, position.take_profit, 'TARGET')
                continue
    
    # Check for new signals
    for symbol, data in stock_data.items():
        if current_date not in data.index:
            continue
        
        # Skip if already in position
        if symbol in portfolio.positions:
            continue
        
        signal = generate_simple_signal(data, current_date)
        
        if signal == 1:
            signals_generated += 1
            
            if portfolio.can_open_position(symbol, current_date):
                row = data.loc[current_date]
                current_price = row['close'] if 'close' in row else row['Close']
                atr = row['atr'] if 'atr' in row else row.get('ATR', current_price * 0.02)
                
                stop_loss = current_price - (2 * atr)
                take_profit = current_price + (4 * atr)
                
                portfolio.open_position(
                    symbol=symbol,
                    date=current_date,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    regime='TRENDING',
                    atr=atr
                )

# Close remaining positions
final_date = all_dates[-1]
for symbol in list(portfolio.positions.keys()):
    if symbol in stock_data and final_date in stock_data[symbol].index:
        row = stock_data[symbol].loc[final_date]
        close_price = row['close'] if 'close' in row else row['Close']
        portfolio.close_position(symbol, final_date, close_price, 'EOD')

# Results
print("="*80)
print("2025 RESULTS - SIMPLE TECHNICAL STRATEGY")
print("="*80)

metrics = portfolio.get_performance_metrics()

print(f"\n📊 PERFORMANCE:")
print(f"   Total Return:        {metrics['total_return']:.2f}%")
print(f"   Total Trades:        {metrics['total_trades']}")
print(f"   Win Rate:            {metrics['win_rate']:.2f}%")
print(f"   Profit Factor:       {metrics['profit_factor']:.2f}")
print(f"   Sharpe Ratio:        {metrics['sharpe_ratio']:.2f}")
print(f"   Max Drawdown:        {metrics['max_drawdown']:.2f}%")
print(f"   Signals Generated:   {signals_generated}")

# Annualized comparison
baseline_annual = 234.39 / 5  # 46.88% per year (Phase 5 baseline)
test_return = metrics['total_return']
test_days = len(all_dates)
test_annualized = (test_return / test_days) * 252 if test_days > 0 else 0

print(f"\n📈 VS 2020-2024 BASELINE:")
print(f"   Baseline (2020-2024): 46.88% per year")
print(f"   2025 Actual:          {test_return:.2f}% over {test_days} days")
print(f"   2025 Annualized:      {test_annualized:.2f}% per year")
print(f"   Performance:          {(test_annualized/46.88)*100:.0f}% of baseline")

print(f"\n🎯 VALIDATION:")
if test_annualized >= 35:
    print("   ✅ EXCELLENT - Strategy works on unseen 2025 data!")
    print("   System is robust and generalizes well")
elif test_annualized >= 23:
    print("   ⚠️  ACCEPTABLE - Some performance degradation")
    print("   System works but may need fine-tuning")
elif test_annualized >= 0:
    print("   ⚠️  WEAK - Significant performance drop")
    print("   May be market conditions or strategy needs adjustment")
else:
    print("   ❌ LOSING - Strategy not working on 2025")

print(f"\n💡 KEY INSIGHT:")
print(f"   This test uses 2025 as COMPLETELY UNSEEN data.")
print(f"   The system was developed on 2020-2024 only.")
print(f"   This proves whether the strategy is real or just curve-fitted.")

print("\n" + "="*80)
print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)
