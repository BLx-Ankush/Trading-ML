"""
Phase 5 REVISED: Portfolio Strategy with Smart Risk Controls

Based on comparison results:
- Phase 4 baseline: 234% return, 1.44 Sharpe, 7.77% DD ✅ EXCELLENT
- Phase 5 optimized: 56% return, 1.08 Sharpe, 9.94% DD ❌ WORSE

Conclusion: Trailing stops and time exits CUT WINNERS TOO EARLY

Phase 5 Revised Strategy:
✅ KEEP: Phase 4's core logic (let winners run to 4×ATR targets)
✅ KEEP: Portfolio monthly circuit breaker (stop at -10% monthly DD)
❌ REMOVE: Trailing stops (caused 194 early exits)
❌ REMOVE: Time-based exits (cut 94 positions too early)

Goal: Match Phase 4's 234% returns while adding portfolio-level safety
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
import numpy as np
from datetime import datetime

from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.features.indicators import TechnicalIndicators
from src.models.hmm_regime import RegimeDetector
from src.strategy.ml_strategy_selector import MLStrategySelector
from src.backtesting.portfolio_engine import PortfolioEngine
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Same 15-stock universe
STOCK_UNIVERSE = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
    'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS',
    'BAJFINANCE.NS', 'LT.NS', 'HCLTECH.NS', 'AXISBANK.NS', 'MARUTI.NS'
]

def load_stock_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Load and prepare stock data with indicators."""
    try:
        loader = DataLoader()
        raw_data = loader.fetch_yahoo_data(symbol, start_date, end_date)
        
        if raw_data.empty:
            return pd.DataFrame()
        
        data = DataProcessor.clean_data(raw_data)
        data = TechnicalIndicators.calculate_all_indicators(data)
        return data
    
    except Exception as e:
        logger.error(f"Error loading {symbol}: {e}")
        return pd.DataFrame()


def run_revised_backtest(
    stocks: list,
    start_date: str = "2020-01-01",
    end_date: str = "2024-12-31",
    initial_capital: float = 200000
):
    """
    Run Phase 5 Revised backtest.
    
    Phase 4 core logic + portfolio circuit breaker only
    """
    print("\n" + "="*80)
    print("PHASE 5 REVISED: SMART PORTFOLIO STRATEGY")
    print("="*80)
    print(f"Stock Universe: {len(stocks)} stocks")
    print(f"Period: {start_date} to {end_date}")
    print(f"Initial Capital: Rs. {initial_capital:,.0f}")
    print("\nStrategy:")
    print("  ✅ Phase 4 core logic (2×ATR stop, 4×ATR target)")
    print("  ✅ Let winners run (NO trailing stops)")
    print("  ✅ Hold until target/stop (NO time exits)")
    print("  ✅ Portfolio circuit breaker (10% monthly DD)")
    print("="*80)
    
    # Load data
    print("\nLoading stock data...")
    stock_data = {}
    regime_data = {}
    
    regime_detector = RegimeDetector(n_states=3)
    regime_detector.load('data/models/hmm_regime_model.pkl')
    
    for symbol in stocks:
        print(f"  Loading {symbol}...", end=" ")
        data = load_stock_data(symbol, start_date, end_date)
        
        if not data.empty:
            _, regimes = regime_detector.predict(data)
            regime_series = pd.Series(regimes, index=data.index)
            
            stock_data[symbol] = data
            regime_data[symbol] = regime_series
            print(f"✓ ({len(data)} bars)")
        else:
            print("✗")
    
    print(f"\nLoaded {len(stock_data)}/{len(stocks)} stocks")
    
    if not stock_data:
        print("ERROR: No data loaded")
        return None
    
    # Initialize portfolio with REVISED settings
    print("\nInitializing portfolio engine...")
    portfolio = PortfolioEngine(
        initial_capital=initial_capital,
        max_positions=5,
        risk_per_trade=0.01,
        max_portfolio_risk=0.05,
        # Phase 5 Revised: Only portfolio circuit breaker
        enable_trailing_stop=False,  # Let winners run!
        enable_time_exit=False,      # Hold until target/stop!
        enable_monthly_stop=True,    # Emergency brake only
        monthly_stop_loss=0.10       # 10% monthly DD threshold
    )
    
    # Initialize ML strategy
    ml_selector = MLStrategySelector(
        model_path='data/models/lightgbm_entry_model.txt',
        threshold=0.30,
        enable_ml_filter=True,
        use_regime_thresholds=False
    )
    
    # Get all dates
    all_dates = sorted(set(
        date for data in stock_data.values() 
        for date in data.index
    ))
    
    print(f"\nBacktesting {len(all_dates)} trading days...")
    print("="*80)
    
    # Backtest loop
    for current_date in all_dates:
        portfolio.update_equity_curve(current_date)
        
        # Exit management
        for symbol in list(portfolio.positions.keys()):
            if symbol not in stock_data:
                continue
            
            data = stock_data[symbol]
            
            if current_date not in data.index:
                continue
            
            current_bar = data.loc[current_date]
            position = portfolio.positions[symbol]
            
            # Check stop loss
            if current_bar['low'] <= position.stop_loss:
                portfolio.close_position(symbol, current_date, position.stop_loss, 'STOP')
                continue
            
            # Check take profit
            if current_bar['high'] >= position.take_profit:
                portfolio.close_position(symbol, current_date, position.take_profit, 'TARGET')
                continue
        
        # Entry signals
        for symbol in stock_data.keys():
            if symbol in portfolio.positions:
                continue
            
            if not portfolio.can_open_position(symbol):
                continue
            
            data = stock_data[symbol]
            regime_series = regime_data[symbol]
            
            if current_date not in data.index:
                continue
            
            current_idx = data.index.get_loc(current_date)
            
            if current_idx < 50:
                continue
            
            regime = regime_series.iloc[current_idx]
            
            signal = ml_selector.get_entry_signal(
                regime=regime,
                data=data,
                current_idx=current_idx,
                regime_series=regime_series
            )
            
            if signal == 'LONG':
                current_bar = data.iloc[current_idx]
                entry_price = current_bar['close']
                atr = current_bar['atr']
                
                stop_loss = entry_price - (2 * atr)
                take_profit = entry_price + (4 * atr)
                
                portfolio.open_position(
                    symbol=symbol,
                    date=current_date,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    regime=regime
                )
    
    # Close remaining positions
    for symbol in list(portfolio.positions.keys()):
        if symbol in stock_data:
            data = stock_data[symbol]
            final_bar = data.iloc[-1]
            portfolio.close_position(symbol, data.index[-1], final_bar['close'], 'EOD')
    
    # Print results
    print("\n" + "="*80)
    print("PHASE 5 REVISED RESULTS")
    print("="*80)
    
    metrics = portfolio.get_performance_metrics()
    
    print(f"\nOverall Performance:")
    print(f"  Initial Capital:    Rs. {initial_capital:,.2f}")
    print(f"  Final Capital:      Rs. {portfolio.capital:,.2f}")
    print(f"  Total Return:       {metrics['total_return']:.2f}%")
    print(f"  Total Trades:       {metrics['total_trades']}")
    print(f"  Winning Trades:     {metrics['winning_trades']}")
    print(f"  Losing Trades:      {metrics['losing_trades']}")
    print(f"  Win Rate:           {metrics['win_rate']:.2f}%")
    print(f"  Avg Win:            Rs. {metrics['avg_win']:,.2f}")
    print(f"  Avg Loss:           Rs. {metrics['avg_loss']:,.2f}")
    print(f"  Profit Factor:      {metrics['profit_factor']:.2f}")
    print(f"  Sharpe Ratio:       {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown:       {metrics['max_drawdown']:.2f}%")
    
    months = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days / 30
    print(f"\n  Monthly Return:     {metrics['total_return'] / months:.2f}%")
    print(f"  Monthly Trades:     {metrics['total_trades'] / months:.2f}")
    
    # Circuit breaker stats
    if hasattr(portfolio, 'monthly_stops_triggered'):
        print(f"\nPortfolio Circuit Breaker:")
        print(f"  Monthly stops triggered: {portfolio.monthly_stops_triggered}")
    
    # Per-symbol breakdown
    print("\n" + "="*80)
    print("PER-SYMBOL PERFORMANCE")
    print("="*80)
    
    symbol_df = portfolio.get_symbol_breakdown()
    if not symbol_df.empty:
        print(f"\n{'Symbol':<15} {'Trades':<8} {'Wins':<6} {'Losses':<8} {'Win Rate':<10} {'Total PnL':<12} {'Avg PnL'}")
        print("-"*80)
        for _, row in symbol_df.iterrows():
            print(f"{row['symbol']:<15} {row['trades']:<8} {row['wins']:<6} {row['losses']:<8} "
                  f"{row['win_rate']:<10.2f}% Rs. {row['total_pnl']:<10,.2f} Rs. {row['avg_pnl_per_trade']:,.2f}")
    
    # Comparison
    print("\n" + "="*80)
    print("COMPARISON: PHASE 4 vs PHASE 5 REVISED")
    print("="*80)
    
    print(f"\nPhase 4 Baseline:")
    print(f"  Total Return:       234.39%")
    print(f"  Total Trades:       255")
    print(f"  Win Rate:           52.16%")
    print(f"  Sharpe Ratio:       1.44")
    print(f"  Max Drawdown:       7.77%")
    print(f"  Profit Factor:      2.01")
    
    print(f"\nPhase 5 Revised (This Run):")
    print(f"  Total Return:       {metrics['total_return']:.2f}%")
    print(f"  Total Trades:       {metrics['total_trades']}")
    print(f"  Win Rate:           {metrics['win_rate']:.2f}%")
    print(f"  Sharpe Ratio:       {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown:       {metrics['max_drawdown']:.2f}%")
    print(f"  Profit Factor:      {metrics['profit_factor']:.2f}")
    
    # Analysis
    return_diff = metrics['total_return'] - 234.39
    print(f"\nReturn Difference: {return_diff:+.2f}%")
    
    if abs(return_diff) < 10:
        print("✅ EXCELLENT! Returns match Phase 4 baseline")
    elif metrics['total_return'] > 200:
        print("✅ GOOD! Strong returns preserved")
    elif metrics['sharpe_ratio'] > 1.3:
        print("✅ Strong risk-adjusted returns")
    else:
        print("⚠️  Returns lower than expected - may need tuning")
    
    print("\n" + "="*80)
    print("✅ Phase 5 Revised backtest complete!")
    print("="*80)
    
    return portfolio


if __name__ == "__main__":
    portfolio = run_revised_backtest(
        stocks=STOCK_UNIVERSE,
        start_date="2020-01-01",
        end_date="2024-12-31",
        initial_capital=200000
    )
