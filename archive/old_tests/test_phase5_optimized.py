"""
Phase 5: Optimized Portfolio with Phase 1 Enhancements

Implements:
1. Trailing stops (lock in profits)
2. Time-based exits (free up capital)
3. Portfolio monthly stop loss (risk control)

Expected improvements:
- Better risk-adjusted returns (Sharpe: 0.49 → 0.65+)
- Reduced max drawdown (18% → 14%)
- Higher total returns (234% → 280-300%)
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

# NSE Top 15 stocks (diversified across sectors)
STOCK_UNIVERSE = [
    'RELIANCE.NS',    # Oil & Gas
    'TCS.NS',         # IT Services
    'HDFCBANK.NS',    # Banking
    'INFY.NS',        # IT Services
    'ICICIBANK.NS',   # Banking
    'HINDUNILVR.NS',  # FMCG
    'ITC.NS',         # FMCG/Tobacco
    'SBIN.NS',        # Banking
    'BHARTIARTL.NS',  # Telecom
    'KOTAKBANK.NS',   # Banking
    'BAJFINANCE.NS',  # Finance
    'LT.NS',          # Infrastructure
    'HCLTECH.NS',     # IT Services
    'AXISBANK.NS',    # Banking
    'MARUTI.NS'       # Automobile
]

def load_stock_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Load and prepare stock data with indicators."""
    try:
        loader = DataLoader()
        raw_data = loader.fetch_yahoo_data(symbol, start_date, end_date)
        
        if raw_data.empty:
            logger.warning(f"No data for {symbol}")
            return pd.DataFrame()
        
        data = DataProcessor.clean_data(raw_data)
        data = TechnicalIndicators.calculate_all_indicators(data)
        
        return data
    
    except Exception as e:
        logger.error(f"Error loading {symbol}: {e}")
        return pd.DataFrame()


def run_optimized_backtest(
    stocks: list,
    start_date: str = "2020-01-01",
    end_date: str = "2024-12-31",
    model_path: str = 'data/models/lightgbm_entry_model.txt',
    initial_capital: float = 200000,
    max_positions: int = 5,
    # Phase 1 optimization parameters
    enable_trailing_stop: bool = True,
    trailing_activation: float = 1.0,  # Activate after 1×ATR profit
    trailing_distance: float = 1.5,    # Trail at 1.5×ATR
    enable_time_exit: bool = True,
    max_holding_days: int = 30,
    profitable_exit_days: int = 20,
    enable_monthly_stop: bool = True,
    monthly_stop_threshold: float = 0.08  # 8% monthly drawdown limit
):
    """
    Run optimized portfolio backtest with Phase 1 enhancements.
    
    Args:
        stocks: List of stock symbols
        start_date: Start date
        end_date: End date
        model_path: Path to ML model
        initial_capital: Starting capital
        max_positions: Maximum concurrent positions
        enable_trailing_stop: Enable trailing stop mechanism
        trailing_activation: ATR multiplier to activate trailing
        trailing_distance: ATR multiplier for trailing distance
        enable_time_exit: Enable time-based exits
        max_holding_days: Maximum holding period
        profitable_exit_days: Exit if profitable after N days
        enable_monthly_stop: Enable monthly stop loss
        monthly_stop_threshold: Monthly drawdown threshold
    """
    print("\n" + "="*80)
    print("PHASE 5: OPTIMIZED MULTI-STOCK PORTFOLIO BACKTEST")
    print("="*80)
    print(f"Stock Universe: {len(stocks)} stocks")
    print(f"Initial Capital: Rs. {initial_capital:,.0f}")
    print(f"Max Positions: {max_positions}")
    print(f"Period: {start_date} to {end_date}")
    print("\nPhase 1 Optimizations:")
    print(f"  ✓ Trailing Stops: {'Enabled' if enable_trailing_stop else 'Disabled'}")
    if enable_trailing_stop:
        print(f"    - Activation: {trailing_activation}×ATR profit")
        print(f"    - Distance: {trailing_distance}×ATR from highest")
    print(f"  ✓ Time-Based Exits: {'Enabled' if enable_time_exit else 'Disabled'}")
    if enable_time_exit:
        print(f"    - Max holding: {max_holding_days} days")
        print(f"    - Profitable exit: {profitable_exit_days} days")
    print(f"  ✓ Monthly Stop Loss: {'Enabled' if enable_monthly_stop else 'Disabled'}")
    if enable_monthly_stop:
        print(f"    - Threshold: {monthly_stop_threshold*100:.1f}% monthly drawdown")
    print("="*80)
    
    # Load data for all stocks
    print("\nLoading data for all stocks...")
    stock_data = {}
    regime_data = {}
    
    # Load regime detector once
    regime_detector = RegimeDetector(n_states=3)
    regime_detector.load('data/models/hmm_regime_model.pkl')
    
    for symbol in stocks:
        print(f"  Loading {symbol}...", end=" ")
        data = load_stock_data(symbol, start_date, end_date)
        
        if not data.empty:
            # Get regime predictions
            _, regimes = regime_detector.predict(data)
            regime_series = pd.Series(regimes, index=data.index)
            
            stock_data[symbol] = data
            regime_data[symbol] = regime_series
            print(f"✓ ({len(data)} bars)")
        else:
            print("✗ (No data)")
    
    print(f"\nSuccessfully loaded {len(stock_data)}/{len(stocks)} stocks")
    
    if not stock_data:
        print("ERROR: No stock data loaded. Exiting.")
        return None
    
    # Initialize portfolio engine with Phase 1 optimizations
    print(f"\nInitializing optimized portfolio engine...")
    portfolio = PortfolioEngine(
        initial_capital=initial_capital,
        max_positions=max_positions,
        risk_per_trade=0.01,
        max_portfolio_risk=0.05,
        enable_trailing_stop=enable_trailing_stop,
        trailing_stop_activation=trailing_activation,
        trailing_stop_distance=trailing_distance,
        enable_time_exit=enable_time_exit,
        max_holding_days=max_holding_days,
        profitable_exit_days=profitable_exit_days,
        enable_monthly_stop=enable_monthly_stop,
        monthly_stop_loss=monthly_stop_threshold
    )
    
    # Initialize ML strategy selector
    print(f"Loading ML model from {model_path}...")
    ml_selector = MLStrategySelector(
        model_path=model_path,
        threshold=0.30,  # Best threshold from Phase 3.5
        enable_ml_filter=True,
        use_regime_thresholds=False  # Flat threshold
    )
    
    # Get all trading dates
    all_dates = sorted(set(
        date for data in stock_data.values() 
        for date in data.index
    ))
    
    print(f"Loaded ML model (flat threshold=0.30)")
    print(f"\nBacktesting {len(all_dates)} trading days...")
    print("="*80)
    
    # Backtest loop
    for date_idx, current_date in enumerate(all_dates):
        # Update equity curve (includes monthly stop loss check)
        portfolio.update_equity_curve(current_date)
        
        # Check exits for all open positions
        for symbol in list(portfolio.positions.keys()):
            if symbol not in stock_data:
                continue
            
            data = stock_data[symbol]
            position = portfolio.positions[symbol]
            
            # Find current bar
            if current_date not in data.index:
                continue
            
            current_bar = data.loc[current_date]
            current_price = current_bar['close']
            atr = current_bar['atr']
            
            # Update trailing stop
            if portfolio.enable_trailing_stop:
                portfolio.update_trailing_stop(symbol, current_price, atr)
            
            # Check time-based exit
            if portfolio.check_time_based_exit(symbol, current_date, current_price):
                portfolio.close_position(
                    symbol, current_date, current_price, 'TIME_EXIT'
                )
                continue
            
            # Check stop loss (may have been updated by trailing stop)
            if current_bar['low'] <= position.stop_loss:
                exit_reason = 'TRAILING_STOP' if position.trailing_stop_active else 'STOP'
                portfolio.close_position(
                    symbol, current_date, position.stop_loss, exit_reason
                )
                continue
            
            # Check take profit
            if current_bar['high'] >= position.take_profit:
                portfolio.close_position(
                    symbol, current_date, position.take_profit, 'TARGET'
                )
                continue
        
        # Check for new entry signals (respects monthly stop loss)
        for symbol in stock_data.keys():
            # Skip if we already have a position
            if symbol in portfolio.positions:
                continue
            
            # Check if we can open position (includes monthly stop check)
            if not portfolio.can_open_position(symbol, current_date):
                continue
            
            data = stock_data[symbol]
            regime_series = regime_data[symbol]
            
            # Find current index
            if current_date not in data.index:
                continue
            
            current_idx = data.index.get_loc(current_date)
            
            # Need enough history
            if current_idx < 50:
                continue
            
            # Get current regime
            regime = regime_series.iloc[current_idx]
            
            # Check for entry signal
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
                
                # Calculate stops (2:1 R:R)
                stop_loss = entry_price - (2 * atr)
                take_profit = entry_price + (4 * atr)
                
                # Open position with ATR for trailing stop
                portfolio.open_position(
                    symbol=symbol,
                    date=current_date,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    regime=regime,
                    atr=atr  # Pass ATR for trailing stop tracking
                )
    
    # Close remaining positions
    for symbol in list(portfolio.positions.keys()):
        if symbol in stock_data:
            data = stock_data[symbol]
            final_bar = data.iloc[-1]
            portfolio.close_position(
                symbol, data.index[-1], final_bar['close'], 'EOD'
            )
    
    # Print results
    print("\n" + "="*80)
    print("OPTIMIZED PORTFOLIO PERFORMANCE")
    print("="*80)
    
    metrics = portfolio.get_performance_metrics()
    
    print("\nOverall Performance:")
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
    
    # Calculate time-based metrics
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    months = ((end_dt.year - start_dt.year) * 12 + 
              (end_dt.month - start_dt.month))
    
    monthly_return = metrics['total_return'] / months if months > 0 else 0
    monthly_trades = metrics['total_trades'] / months if months > 0 else 0
    
    print(f"\n  Monthly Return:     {monthly_return:.2f}%")
    print(f"  Monthly Trades:     {monthly_trades:.2f}")
    
    # Phase 1 optimization stats
    print(f"\nPhase 1 Optimization Stats:")
    print(f"  Trailing Stop Exits:  {portfolio.stats.get('trailing_stop_exits', 0)}")
    print(f"  Time-Based Exits:     {portfolio.stats.get('time_based_exits', 0)}")
    print(f"  Monthly Stops Triggered: {portfolio.stats.get('monthly_stops_triggered', 0)}")
    
    # Per-symbol breakdown
    print("\n" + "="*80)
    print("PER-SYMBOL PERFORMANCE")
    print("="*80)
    
    symbol_df = portfolio.get_symbol_breakdown()
    if not symbol_df.empty:
        print("\nSymbol          Trades   Wins   Losses   Win Rate   Total PnL    Avg PnL")
        print("-" * 80)
        for _, row in symbol_df.iterrows():
            print(
                f"{row['symbol']:<15} {row['trades']:<8} {row['wins']:<6} "
                f"{row['losses']:<8} {row['win_rate']:>7.1f}%   "
                f"Rs. {row['total_pnl']:>9,.0f}   Rs. {row['avg_pnl_per_trade']:>7,.0f}"
            )
    
    print("\n" + "="*80)
    
    return portfolio


if __name__ == "__main__":
    # Run optimized backtest
    portfolio = run_optimized_backtest(
        stocks=STOCK_UNIVERSE,
        start_date="2020-01-01",
        end_date="2024-12-31",
        initial_capital=200000,
        max_positions=5,
        enable_trailing_stop=True,
        trailing_activation=1.0,
        trailing_distance=1.5,
        enable_time_exit=True,
        max_holding_days=30,
        profitable_exit_days=20,
        enable_monthly_stop=True,
        monthly_stop_threshold=0.08
    )
    
    if portfolio:
        print("\n✅ Phase 5 optimized backtest complete!")
        print("🎯 Review metrics above to validate Phase 1 improvements")
