"""
Comprehensive Trading System Analysis
Runs complete tests on both training (2020-2024) and validation (2025) periods
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
from datetime import datetime
import time

from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.features.indicators import TechnicalIndicators
from src.backtesting.portfolio_engine import PortfolioEngine

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

def generate_signal(data, current_date):
    """Simple technical strategy."""
    try:
        row = data.loc[current_date]
        idx = data.index.get_loc(current_date)
        if idx == 0:
            return 0
        prev_row = data.iloc[idx - 1]
        
        rsi_oversold = row.get('rsi', 50) < 40
        macd_cross = (row.get('macd', 0) > row.get('macd_signal', 0) and 
                     prev_row.get('macd', 0) <= prev_row.get('macd_signal', 0))
        trend_up = row.get('close', 0) > row.get('ema_21', row.get('close', 0))
        
        return 1 if (rsi_oversold and macd_cross and trend_up) else 0
    except:
        return 0

def run_backtest(start_date, end_date, period_name):
    """Run backtest for a specific period."""
    print("\n" + "="*80)
    print(f"{period_name} BACKTEST")
    print("="*80)
    print(f"Period: {start_date} to {end_date}")
    print(f"Stocks: {len(STOCKS)} stocks")
    print("="*80)
    
    # Load data
    print(f"\nLoading {period_name} data...")
    stock_data = {}
    
    for symbol in STOCKS:
        print(f"  {symbol}...", end=" ", flush=True)
        data = load_stock_data(symbol, start_date, end_date)
        
        if not data.empty:
            data['Regime'] = 'TRENDING'
            stock_data[symbol] = data
            print(f"✓ {len(data)} days")
        else:
            print("✗")
    
    print(f"\n✅ Loaded {len(stock_data)}/{len(STOCKS)} stocks")
    
    if len(stock_data) == 0:
        print("❌ No data loaded")
        return None
    
    # Run backtest
    print(f"\nRunning {period_name} backtest...")
    start_time = time.time()
    
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
    
    all_dates = sorted(set(date for df in stock_data.values() for date in df.index))
    signals_generated = 0
    
    for current_date in all_dates:
        portfolio.update_equity_curve(current_date)
        
        # Check exits
        for symbol in list(portfolio.positions.keys()):
            if symbol in stock_data and current_date in stock_data[symbol].index:
                row = stock_data[symbol].loc[current_date]
                position = portfolio.positions[symbol]
                
                if row['low'] <= position.stop_loss:
                    portfolio.close_position(symbol, current_date, position.stop_loss, 'STOP')
                    continue
                
                if row['high'] >= position.take_profit:
                    portfolio.close_position(symbol, current_date, position.take_profit, 'TARGET')
                    continue
        
        # Check entries
        for symbol, data in stock_data.items():
            if current_date not in data.index or symbol in portfolio.positions:
                continue
            
            signal = generate_signal(data, current_date)
            
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
    
    elapsed = time.time() - start_time
    
    # Results
    metrics = portfolio.get_performance_metrics()
    
    print(f"\n{'='*80}")
    print(f"{period_name} RESULTS")
    print(f"{'='*80}")
    print(f"\n📊 PERFORMANCE:")
    print(f"   Trading Days:        {len(all_dates)}")
    print(f"   Signals Generated:   {signals_generated}")
    print(f"   Total Return:        {metrics['total_return']:.2f}%")
    print(f"   Total Trades:        {metrics['total_trades']}")
    print(f"   Win Rate:            {metrics['win_rate']:.2f}%")
    print(f"   Profit Factor:       {metrics['profit_factor']:.2f}")
    print(f"   Sharpe Ratio:        {metrics['sharpe_ratio']:.2f}")
    print(f"   Max Drawdown:        {metrics['max_drawdown']:.2f}%")
    avg_trade = metrics.get('avg_trade_return', 0)
    print(f"   Avg Trade Return:    {avg_trade:.2f}%")
    print(f"   Final Capital:       Rs. {portfolio.capital:,.2f}")
    print(f"\n⏱️  Execution Time:     {elapsed:.1f} seconds")
    
    return {
        'period': period_name,
        'start_date': start_date,
        'end_date': end_date,
        'days': len(all_dates),
        'signals': signals_generated,
        'metrics': metrics,
        'capital': portfolio.capital
    }

# Main execution
print("\n" + "="*80)
print("COMPREHENSIVE TRADING SYSTEM ANALYSIS")
print("="*80)
print("Testing on ALL 15 stocks across multiple periods")
print("Strategy: RSI + MACD + Trend (Simple Technical)")
print("="*80)

results = {}

# Test 1: Training Period (2020-2024)
print("\n\n🔵 TEST 1: TRAINING PERIOD (2020-2024)")
print("This is the baseline - what the system was developed on")
results['training'] = run_backtest('2020-01-01', '2024-12-31', 'TRAINING (2020-2024)')

# Test 2: Validation Period (2025)
print("\n\n🔴 TEST 2: OUT-OF-SAMPLE VALIDATION (2025)")
print("This is UNSEEN data - true test of system robustness")
results['validation'] = run_backtest('2025-01-01', '2025-12-31', 'VALIDATION (2025)')

# Comparative Analysis
print("\n\n" + "="*80)
print("COMPARATIVE ANALYSIS")
print("="*80)

if results['training'] and results['validation']:
    train = results['training']
    val = results['validation']
    
    print(f"\n📊 PERIOD COMPARISON:")
    print(f"\n   {'Metric':<25} {'Training (2020-2024)':<20} {'Validation (2025)':<20} {'Ratio'}")
    print(f"   {'-'*80}")
    
    # Trading days
    print(f"   {'Trading Days':<25} {train['days']:<20} {val['days']:<20} {val['days']/train['days']*100:.1f}%")
    
    # Signals
    print(f"   {'Signals Generated':<25} {train['signals']:<20} {val['signals']:<20} {val['signals']/train['signals']*100:.1f}%")
    
    # Returns
    train_return = train['metrics']['total_return']
    val_return = val['metrics']['total_return']
    train_annual = train_return / (train['days']/252)
    val_annual = val_return / (val['days']/252)
    
    print(f"   {'Total Return':<25} {train_return:.2f}%{'':<13} {val_return:.2f}%{'':<13} {val_return/train_return*100 if train_return > 0 else 0:.1f}%")
    print(f"   {'Annualized Return':<25} {train_annual:.2f}%{'':<13} {val_annual:.2f}%{'':<13} {val_annual/train_annual*100 if train_annual > 0 else 0:.1f}%")
    
    # Trades
    print(f"   {'Total Trades':<25} {train['metrics']['total_trades']:<20} {val['metrics']['total_trades']:<20} {val['metrics']['total_trades']/train['metrics']['total_trades']*100 if train['metrics']['total_trades'] > 0 else 0:.1f}%")
    
    # Win rate
    print(f"   {'Win Rate':<25} {train['metrics']['win_rate']:.2f}%{'':<13} {val['metrics']['win_rate']:.2f}%{'':<13} {val['metrics']['win_rate']/train['metrics']['win_rate']*100 if train['metrics']['win_rate'] > 0 else 0:.1f}%")
    
    # Sharpe
    print(f"   {'Sharpe Ratio':<25} {train['metrics']['sharpe_ratio']:.2f}{'':<18} {val['metrics']['sharpe_ratio']:.2f}{'':<18} {val['metrics']['sharpe_ratio']/train['metrics']['sharpe_ratio']*100 if train['metrics']['sharpe_ratio'] > 0 else 0:.1f}%")
    
    # Drawdown
    print(f"   {'Max Drawdown':<25} {train['metrics']['max_drawdown']:.2f}%{'':<13} {val['metrics']['max_drawdown']:.2f}%{'':<13} {'Better' if val['metrics']['max_drawdown'] < train['metrics']['max_drawdown'] else 'Worse'}")
    
    print(f"\n💡 KEY INSIGHTS:")
    
    # Performance ratio
    perf_ratio = val_annual / train_annual * 100 if train_annual > 0 else 0
    print(f"\n   Out-of-Sample Performance: {perf_ratio:.0f}% of training baseline")
    
    if perf_ratio >= 70:
        print(f"   ✅ EXCELLENT - System generalizes very well to unseen data")
    elif perf_ratio >= 40:
        print(f"   ✅ GOOD - Acceptable degradation, system is robust")
    elif perf_ratio >= 20:
        print(f"   ⚠️  FAIR - Significant degradation but still profitable")
    elif perf_ratio > 0:
        print(f"   ⚠️  WEAK - Major performance drop, needs improvement")
    else:
        print(f"   ❌ FAIL - Losing money on validation data")
    
    # Signal generation
    signal_ratio = val['signals'] / train['signals'] * 100 if train['signals'] > 0 else 0
    print(f"\n   Signal Generation Rate: {signal_ratio:.1f}% of training")
    if signal_ratio < 50:
        print(f"   📉 Very conservative - May need signal optimization")
    elif signal_ratio < 80:
        print(f"   ⚖️  Balanced - Good selectivity")
    else:
        print(f"   📈 Active - Generating signals consistently")
    
    # Win rate comparison
    if val['metrics']['win_rate'] > train['metrics']['win_rate']:
        print(f"\n   🎯 Win Rate IMPROVED on validation data (+{val['metrics']['win_rate'] - train['metrics']['win_rate']:.1f}%)")
    elif val['metrics']['win_rate'] >= train['metrics']['win_rate'] * 0.9:
        print(f"\n   🎯 Win Rate maintained well on validation data")
    else:
        print(f"\n   ⚠️  Win Rate declined on validation data (-{train['metrics']['win_rate'] - val['metrics']['win_rate']:.1f}%)")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)
