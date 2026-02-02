"""
Phase 3 Step 4: Integrated Backtest

Two-layer system:
- Layer 2 (Fuzzy Logic): Generate candidate trades
- Layer 3 (LightGBM): Final gatekeeper with threshold 0.30
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
from src.risk.position_sizing import PositionSizer
from src.risk.risk_manager import RiskManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run_integrated_backtest(symbol: str = "RELIANCE.NS", threshold: float = 0.30, model_path: str = 'data/models/lightgbm_entry_model.txt'):
    """
    Run integrated backtest with Fuzzy + ML filtering.
    
    Args:
        symbol: Stock symbol to test
        threshold: ML probability threshold
        model_path: Path to LightGBM model file
    """
    
    logger.info("=" * 80)
    logger.info(f"PHASE 3 INTEGRATED BACKTEST: {symbol}")
    logger.info(f"Layer 2: Fuzzy Logic | Layer 3: LightGBM (threshold={threshold})")
    logger.info(f"Model: {model_path}")
    logger.info("=" * 80)
    
    # Load data
    logger.info(f"\nLoading data for {symbol}...")
    loader = DataLoader()
    raw_data = loader.fetch_yahoo_data(symbol, "2020-01-01", "2024-12-31")
    
    # Process data
    data = DataProcessor.clean_data(raw_data)
    data = TechnicalIndicators.calculate_all_indicators(data)
    logger.info(f"Loaded {len(data)} trading days")
    
    # Load regime detector
    logger.info("\nLoading HMM regime model...")
    regime_detector = RegimeDetector(n_states=3)
    regime_detector.load('data/models/hmm_regime_model.pkl')
    _, regimes = regime_detector.predict(data)
    regime_series = pd.Series(regimes, index=data.index)
    
    # Initialize ML strategy selector
    logger.info(f"\nInitializing ML Strategy Selector (regime-adaptive thresholds)...")
    ml_selector = MLStrategySelector(
        model_path=model_path,
        threshold=threshold,
        enable_ml_filter=True,
        use_regime_thresholds=True  # Phase 3.8: Enable regime-specific thresholds
    )
    
    # Initialize risk management
    initial_capital = 200000
    risk_manager = RiskManager(initial_capital)
    position_sizer = PositionSizer(initial_capital)
    
    # Backtest state
    capital = initial_capital
    position = None
    trades = []
    equity_curve = []
    
    logger.info("\n" + "=" * 80)
    logger.info("RUNNING BACKTEST")
    logger.info("=" * 80)
    
    # Run through historical data
    for i in range(30, len(data)):  # Start after warmup period
        current_bar = data.iloc[i]
        current_date = current_bar.name
        current_price = current_bar['close']
        current_regime = regimes[i]
        
        # Record equity
        position_value = position['quantity'] * current_price if position else 0
        total_equity = capital + position_value
        equity_curve.append({
            'date': current_date,
            'capital': capital,
            'position_value': position_value,
            'total_equity': total_equity
        })
        
        # Check if we can trade
        can_trade, _ = risk_manager.can_trade()
        
        # Exit management
        if position is not None:
            # Check stop-loss
            if current_price <= position['stop_loss']:
                logger.info(f"[{current_date.date()}] STOP HIT at {current_price:.2f}")
                pnl = (current_price - position['entry_price']) * position['quantity']
                capital += current_price * position['quantity']
                
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': current_date,
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'quantity': position['quantity'],
                    'pnl': pnl,
                    'pnl_pct': (current_price / position['entry_price'] - 1) * 100,
                    'outcome': 'loss',
                    'regime': position['entry_regime']
                })
                
                # Update risk manager
                trade_return = pnl / (position['entry_price'] * position['quantity'])
                risk_manager.record_trade(trade_return, current_date)
                
                position = None
                continue
            
            # Check take-profit
            if current_price >= position['take_profit']:
                logger.info(f"[{current_date.date()}] TARGET HIT at {current_price:.2f}")
                pnl = (current_price - position['entry_price']) * position['quantity']
                capital += current_price * position['quantity']
                
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': current_date,
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'quantity': position['quantity'],
                    'pnl': pnl,
                    'pnl_pct': (current_price / position['entry_price'] - 1) * 100,
                    'outcome': 'win',
                    'regime': position['entry_regime']
                })
                
                # Update risk manager
                trade_return = pnl / (position['entry_price'] * position['quantity'])
                risk_manager.record_trade(trade_return, current_date)
                
                position = None
                continue
        
        # Entry signal
        if position is None and can_trade:
            signal = ml_selector.get_entry_signal(
                regime=current_regime,
                data=data,
                current_idx=i,
                regime_series=regime_series
            )
            
            if signal == 'LONG':
                # Calculate position size
                atr = current_bar['atr']
                stop_loss = position_sizer.calculate_stop_loss(
                    current_price, atr, direction='long', multiplier=2.0
                )
                take_profit = position_sizer.calculate_take_profit(
                    current_price, stop_loss, risk_reward_ratio=2.0, direction='long'
                )
                
                position_result = position_sizer.calculate_position_size(
                    entry_price=current_price,
                    stop_loss_price=stop_loss,
                    atr=atr
                )
                position_size = position_result['shares']
                
                # Apply regime multiplier
                regime_multiplier = ml_selector.fuzzy_selector.get_position_size_multiplier(current_regime)
                position_size = int(position_size * regime_multiplier)
                
                if position_size > 0:
                    position_value = position_size * current_price
                    
                    # Check max position size
                    if position_value <= capital * 0.1:
                        capital -= position_value
                        position = {
                            'entry_date': current_date,
                            'entry_price': current_price,
                            'quantity': position_size,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'entry_regime': current_regime
                        }
                        logger.info(f"[{current_date.date()}] ENTER LONG {position_size} @ {current_price:.2f} | SL: {stop_loss:.2f} | TP: {take_profit:.2f} | Regime: {current_regime}")
    
    # Close any remaining position
    if position is not None:
        final_price = data.iloc[-1]['close']
        pnl = (final_price - position['entry_price']) * position['quantity']
        capital += final_price * position['quantity']
        
        trades.append({
            'entry_date': position['entry_date'],
            'exit_date': data.index[-1],
            'entry_price': position['entry_price'],
            'exit_price': final_price,
            'quantity': position['quantity'],
            'pnl': pnl,
            'pnl_pct': (final_price / position['entry_price'] - 1) * 100,
            'outcome': 'win' if pnl > 0 else 'loss',
            'regime': position['entry_regime']
        })
    
    # Calculate performance metrics
    logger.info("\n" + "=" * 80)
    logger.info("BACKTEST RESULTS")
    logger.info("=" * 80)
    
    trades_df = pd.DataFrame(trades)
    equity_df = pd.DataFrame(equity_curve)
    
    if len(trades) == 0:
        logger.info("NO TRADES EXECUTED")
        return
    
    # Basic metrics
    total_return = (capital - initial_capital) / initial_capital * 100
    total_trades = len(trades)
    winning_trades = len(trades_df[trades_df['outcome'] == 'win'])
    win_rate = winning_trades / total_trades * 100
    
    avg_win = trades_df[trades_df['outcome'] == 'win']['pnl_pct'].mean() if winning_trades > 0 else 0
    avg_loss = trades_df[trades_df['outcome'] == 'loss']['pnl_pct'].mean() if total_trades > winning_trades else 0
    
    # Drawdown
    equity_df['peak'] = equity_df['total_equity'].cummax()
    equity_df['drawdown'] = (equity_df['total_equity'] - equity_df['peak']) / equity_df['peak'] * 100
    max_drawdown = equity_df['drawdown'].min()
    
    # Sharpe ratio (annualized)
    equity_df['returns'] = equity_df['total_equity'].pct_change()
    sharpe_ratio = equity_df['returns'].mean() / equity_df['returns'].std() * np.sqrt(252) if equity_df['returns'].std() > 0 else 0
    
    # ML filter statistics
    ml_stats = ml_selector.get_stats()
    
    logger.info(f"\nPERFORMANCE:")
    logger.info(f"  Initial Capital: Rs.{initial_capital:,.2f}")
    logger.info(f"  Final Capital:   Rs.{capital:,.2f}")
    logger.info(f"  Total Return:    {total_return:.2f}%")
    logger.info(f"  Max Drawdown:    {max_drawdown:.2f}%")
    logger.info(f"  Sharpe Ratio:    {sharpe_ratio:.2f}")
    
    logger.info(f"\nTRADE STATISTICS:")
    logger.info(f"  Total Trades:    {total_trades}")
    logger.info(f"  Winning Trades:  {winning_trades}")
    logger.info(f"  Win Rate:        {win_rate:.2f}%")
    logger.info(f"  Avg Win:         {avg_win:.2f}%")
    logger.info(f"  Avg Loss:        {avg_loss:.2f}%")
    
    logger.info(f"\nML FILTER STATISTICS:")
    logger.info(f"  Fuzzy Candidates:  {ml_stats['fuzzy_candidates']}")
    logger.info(f"  ML Approved:       {ml_stats['ml_approved']}")
    logger.info(f"  ML Rejected:       {ml_stats['ml_rejected']}")
    logger.info(f"  Approval Rate:     {ml_stats['approval_rate']:.2%}")
    
    logger.info(f"\nREGIME BREAKDOWN:")
    for regime in ['trending', 'ranging', 'high_volatility']:
        regime_trades = trades_df[trades_df['regime'] == regime]
        if len(regime_trades) > 0:
            regime_wins = len(regime_trades[regime_trades['outcome'] == 'win'])
            regime_wr = regime_wins / len(regime_trades) * 100
            logger.info(f"  {regime:18s}: {len(regime_trades):2d} trades, {regime_wr:.1f}% win rate")
    
    logger.info("\n" + "=" * 80)
    logger.info("BACKTEST COMPLETE")
    logger.info("=" * 80)
    
    return {
        'total_return': total_return,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'ml_stats': ml_stats,
        'trades': trades_df
    }


if __name__ == "__main__":
    # Test on RELIANCE with threshold 0.30
    results = run_integrated_backtest("RELIANCE.NS", threshold=0.30)
