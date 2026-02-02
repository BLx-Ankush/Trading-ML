"""
Phase 4 Baseline vs Phase 5 Optimized - Direct Comparison

This script runs both:
1. Phase 4 baseline (NO Phase 1 optimizations)
2. Phase 5 optimized (WITH Phase 1 optimizations)

Using EXACT same:
- Stock universe (15 stocks)
- Time period (2020-2024)
- Data source (Yahoo Finance)
- ML model & parameters

Goal: Clearly compare the impact of Phase 1 optimizations
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

# EXACT same universe as Phase 5
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
            logger.warning(f"No data for {symbol}")
            return pd.DataFrame()
        
        data = DataProcessor.clean_data(raw_data)
        data = TechnicalIndicators.calculate_all_indicators(data)
        
        return data
    
    except Exception as e:
        logger.error(f"Error loading {symbol}: {e}")
        return pd.DataFrame()


def run_backtest(
    stocks: list,
    start_date: str,
    end_date: str,
    initial_capital: float,
    enable_phase1_optimizations: bool = False
):
    """
    Run backtest with or without Phase 1 optimizations.
    
    Args:
        enable_phase1_optimizations: If True, enable trailing stops, time exits, monthly stop loss
    """
    # Load data
    stock_data = {}
    regime_data = {}
    
    regime_detector = RegimeDetector(n_states=3)
    regime_detector.load('data/models/hmm_regime_model.pkl')
    
    for symbol in stocks:
        data = load_stock_data(symbol, start_date, end_date)
        
        if not data.empty:
            _, regimes = regime_detector.predict(data)
            regime_series = pd.Series(regimes, index=data.index)
            
            stock_data[symbol] = data
            regime_data[symbol] = regime_series
    
    if not stock_data:
        return None
    
    # Initialize portfolio engine
    if enable_phase1_optimizations:
        # Phase 5: WITH optimizations
        portfolio = PortfolioEngine(
            initial_capital=initial_capital,
            max_positions=5,
            risk_per_trade=0.01,
            max_portfolio_risk=0.05,
            # Phase 1 optimizations
            enable_trailing_stop=True,
            trailing_stop_activation=1.0,
            trailing_stop_distance=1.5,
            enable_time_exit=True,
            max_holding_days=30,
            profitable_exit_days=20,
            enable_monthly_stop=True,
            monthly_stop_loss=0.08
        )
    else:
        # Phase 4: NO optimizations (baseline)
        portfolio = PortfolioEngine(
            initial_capital=initial_capital,
            max_positions=5,
            risk_per_trade=0.01,
            max_portfolio_risk=0.05,
            # Disable Phase 1 optimizations
            enable_trailing_stop=False,
            enable_time_exit=False,
            enable_monthly_stop=False
        )
    
    # Initialize ML strategy selector
    ml_selector = MLStrategySelector(
        model_path='data/models/lightgbm_entry_model.txt',
        threshold=0.30,
        enable_ml_filter=True,
        use_regime_thresholds=False
    )
    
    # Get all trading dates
    all_dates = sorted(set(
        date for data in stock_data.values() 
        for date in data.index
    ))
    
    # Backtest loop
    for current_date in all_dates:
        portfolio.update_equity_curve(current_date)
        
        # Check exits for open positions
        for symbol in list(portfolio.positions.keys()):
            if symbol not in stock_data:
                continue
            
            data = stock_data[symbol]
            position = portfolio.positions[symbol]
            
            if current_date not in data.index:
                continue
            
            current_bar = data.loc[current_date]
            current_idx = data.index.get_loc(current_date)
            
            # Phase 5: Check trailing stop
            if enable_phase1_optimizations:
                atr = current_bar['atr']
                portfolio.update_trailing_stop(symbol, current_bar['close'], atr)
                
                # Check time-based exit
                if portfolio.check_time_based_exit(symbol, current_date, current_bar['close']):
                    portfolio.close_position(symbol, current_date, current_bar['close'], 'TIME_EXIT')
                    continue
            
            # Check stop loss
            if current_bar['low'] <= position.stop_loss:
                portfolio.close_position(symbol, current_date, position.stop_loss, 'STOP')
                continue
            
            # Check take profit
            if current_bar['high'] >= position.take_profit:
                portfolio.close_position(symbol, current_date, position.take_profit, 'TARGET')
                continue
        
        # Check for new entry signals
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
                
                # Phase 5: Pass ATR for trailing stop calculation
                if enable_phase1_optimizations:
                    portfolio.open_position(
                        symbol=symbol,
                        date=current_date,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        regime=regime,
                        atr=atr  # For trailing stop
                    )
                else:
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
    
    return portfolio


def print_results(portfolio, phase_name: str):
    """Print results for a phase."""
    metrics = portfolio.get_performance_metrics()
    
    print(f"\n{phase_name}:")
    print(f"  Total Return:       {metrics['total_return']:.2f}%")
    print(f"  Total Trades:       {metrics['total_trades']}")
    print(f"  Win Rate:           {metrics['win_rate']:.2f}%")
    print(f"  Sharpe Ratio:       {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown:       {metrics['max_drawdown']:.2f}%")
    print(f"  Profit Factor:      {metrics['profit_factor']:.2f}")
    
    # Phase 5 specific stats
    if hasattr(portfolio, 'trailing_stop_exits'):
        print(f"  Trailing Stop Exits: {portfolio.trailing_stop_exits}")
        print(f"  Time-Based Exits:    {portfolio.time_based_exits}")
        print(f"  Monthly Stops:       {portfolio.monthly_stops_triggered}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("PHASE 4 vs PHASE 5 COMPARISON")
    print("="*80)
    print(f"Stock Universe: {len(STOCK_UNIVERSE)} stocks")
    print(f"Period: 2020-01-01 to 2024-12-31")
    print(f"Initial Capital: Rs. 200,000")
    print("="*80)
    
    # Run Phase 4 baseline (NO optimizations)
    print("\n[1/2] Running Phase 4 BASELINE (no optimizations)...")
    phase4 = run_backtest(
        stocks=STOCK_UNIVERSE,
        start_date="2020-01-01",
        end_date="2024-12-31",
        initial_capital=200000,
        enable_phase1_optimizations=False
    )
    
    # Run Phase 5 optimized (WITH optimizations)
    print("\n[2/2] Running Phase 5 OPTIMIZED (with Phase 1 enhancements)...")
    phase5 = run_backtest(
        stocks=STOCK_UNIVERSE,
        start_date="2020-01-01",
        end_date="2024-12-31",
        initial_capital=200000,
        enable_phase1_optimizations=True
    )
    
    # Print comparison
    print("\n" + "="*80)
    print("RESULTS COMPARISON")
    print("="*80)
    
    if phase4:
        print_results(phase4, "Phase 4 Baseline (No Optimizations)")
    
    if phase5:
        print_results(phase5, "Phase 5 Optimized (With Phase 1 Enhancements)")
    
    if phase4 and phase5:
        p4_metrics = phase4.get_performance_metrics()
        p5_metrics = phase5.get_performance_metrics()
        
        print("\n" + "="*80)
        print("IMPROVEMENT ANALYSIS")
        print("="*80)
        
        return_change = p5_metrics['total_return'] - p4_metrics['total_return']
        sharpe_change = p5_metrics['sharpe_ratio'] - p4_metrics['sharpe_ratio']
        dd_change = p5_metrics['max_drawdown'] - p4_metrics['max_drawdown']
        
        print(f"\nReturn Change:       {return_change:+.2f}% ({return_change/p4_metrics['total_return']*100 if p4_metrics['total_return'] != 0 else 0:+.1f}%)")
        print(f"Sharpe Change:       {sharpe_change:+.2f} ({sharpe_change/p4_metrics['sharpe_ratio']*100 if p4_metrics['sharpe_ratio'] != 0 else 0:+.1f}%)")
        print(f"Max DD Change:       {dd_change:+.2f}% ({dd_change/p4_metrics['max_drawdown']*100 if p4_metrics['max_drawdown'] != 0 else 0:+.1f}%)")
        
        print("\nConclusion:")
        if p5_metrics['sharpe_ratio'] > p4_metrics['sharpe_ratio']:
            print("✅ Phase 1 optimizations IMPROVE risk-adjusted returns (higher Sharpe)")
        if abs(return_change) > 10:
            if return_change > 0:
                print("✅ Phase 1 optimizations SIGNIFICANTLY INCREASE absolute returns")
            else:
                print("⚠️  Phase 1 optimizations REDUCE absolute returns (but may improve risk metrics)")
        if dd_change < 0:
            print("✅ Phase 1 optimizations REDUCE maximum drawdown")
    
    print("\n" + "="*80)
