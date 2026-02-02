"""
Phase 4: Multi-Stock Portfolio Backtest

Strategy: Run the same ML system across 10-15 NSE stocks simultaneously
Goal: Multiply trade frequency and diversify returns

Expected: 
- Single stock: 0.38 trades/month, 6.59% return
- Portfolio (15 stocks): 5.7 trades/month, 15-20% return
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


def run_portfolio_backtest(
    stocks: list,
    start_date: str = "2020-01-01",
    end_date: str = "2024-12-31",
    model_path: str = 'data/models/lightgbm_entry_model.txt',
    initial_capital: float = 200000,
    max_positions: int = 5
):
    """
    Run portfolio backtest across multiple stocks.
    
    Args:
        stocks: List of stock symbols
        start_date: Start date
        end_date: End date
        model_path: Path to ML model
        initial_capital: Starting capital
        max_positions: Maximum concurrent positions
    """
    print("\n" + "="*80)
    print("PHASE 4: MULTI-STOCK PORTFOLIO BACKTEST")
    print("="*80)
    print(f"Stock Universe: {len(stocks)} stocks")
    print(f"Initial Capital: Rs. {initial_capital:,.0f}")
    print(f"Max Positions: {max_positions}")
    print(f"Period: {start_date} to {end_date}")
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
    
    # Initialize portfolio engine
    print(f"\nInitializing portfolio engine...")
    portfolio = PortfolioEngine(
        initial_capital=initial_capital,
        max_positions=max_positions,
        risk_per_trade=0.01,
        max_portfolio_risk=0.05
    )
    
    # Initialize ML strategy selector
    print(f"Loading ML model from {model_path}...")
    ml_selector = MLStrategySelector(
        model_path=model_path,
        threshold=0.30,  # Use best threshold from Phase 3.5
        enable_ml_filter=True,
        use_regime_thresholds=False  # Use flat threshold for consistency
    )
    
    # Get all trading dates (union of all stock dates)
    all_dates = sorted(set(
        date for data in stock_data.values() 
        for date in data.index
    ))
    
    print(f"\nBacktesting {len(all_dates)} trading days...")
    print("="*80)
    
    # Backtest loop
    for date_idx, current_date in enumerate(all_dates):
        # Update equity curve
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
            
            # Check stop loss
            if current_bar['low'] <= position.stop_loss:
                portfolio.close_position(
                    symbol, current_date, position.stop_loss, 'STOP'
                )
                continue
            
            # Check take profit
            if current_bar['high'] >= position.take_profit:
                portfolio.close_position(
                    symbol, current_date, position.take_profit, 'TARGET'
                )
                continue
        
        # Check for new entry signals across all stocks
        for symbol in stock_data.keys():
            # Skip if we already have a position in this stock
            if symbol in portfolio.positions:
                continue
            
            # Skip if we can't open more positions
            if not portfolio.can_open_position(symbol):
                continue
            
            data = stock_data[symbol]
            regime_series = regime_data[symbol]
            
            # Find current index
            if current_date not in data.index:
                continue
            
            current_idx = data.index.get_loc(current_date)
            
            # Need enough history for indicators
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
                
                # Calculate stop loss and take profit (2:1 R:R)
                stop_loss = entry_price - (2 * atr)
                take_profit = entry_price + (4 * atr)
                
                # Try to open position
                portfolio.open_position(
                    symbol=symbol,
                    date=current_date,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    regime=regime
                )
    
    # Close any remaining positions at end date
    for symbol in list(portfolio.positions.keys()):
        if symbol in stock_data:
            data = stock_data[symbol]
            final_bar = data.iloc[-1]
            portfolio.close_position(
                symbol, data.index[-1], final_bar['close'], 'EOD'
            )
    
    # Print results
    print("\n" + "="*80)
    print("PORTFOLIO PERFORMANCE")
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
    
    # Monthly metrics
    months = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days / 30
    monthly_return = metrics['total_return'] / months
    monthly_trades = metrics['total_trades'] / months
    
    print(f"\n  Monthly Return:     {monthly_return:.2f}%")
    print(f"  Monthly Trades:     {monthly_trades:.2f}")
    
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
    
    print("\n" + "="*80)
    print("COMPARISON: SINGLE STOCK vs PORTFOLIO")
    print("="*80)
    
    print(f"\nSingle Stock (Phase 3.5 - RELIANCE):")
    print(f"  Total Return:       6.59%")
    print(f"  Total Trades:       23")
    print(f"  Monthly Return:     0.11%")
    print(f"  Monthly Trades:     0.38")
    
    print(f"\nPortfolio ({len(stock_data)} stocks):")
    print(f"  Total Return:       {metrics['total_return']:.2f}%")
    print(f"  Total Trades:       {metrics['total_trades']}")
    print(f"  Monthly Return:     {monthly_return:.2f}%")
    print(f"  Monthly Trades:     {monthly_trades:.2f}")
    
    improvement = ((metrics['total_return'] - 6.59) / 6.59 * 100) if metrics['total_return'] > 0 else 0
    
    print(f"\nImprovement vs Single Stock: {improvement:+.1f}%")
    
    if metrics['total_return'] >= 15:
        print("\n🎉 SUCCESS! Portfolio strategy achieves meaningful returns!")
    elif metrics['total_return'] >= 10:
        print("\n✅ GOOD PROGRESS! Portfolio multiplier working as expected")
    else:
        print("\n⚠️  Portfolio improvement exists but may need optimization")
    
    print("="*80)
    
    return portfolio


if __name__ == "__main__":
    portfolio = run_portfolio_backtest(
        stocks=STOCK_UNIVERSE,
        start_date="2020-01-01",
        end_date="2024-12-31",
        initial_capital=200000,
        max_positions=5
    )
