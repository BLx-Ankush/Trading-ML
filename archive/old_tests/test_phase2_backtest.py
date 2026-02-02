"""
Phase 2 Backtest: Regime-Based Trading

Full backtest comparing:
1. Phase 1: Random entries (baseline)
2. Phase 2: Regime-filtered entries with strategy selection

Tests whether regime awareness improves returns over random entries.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm

from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.features.indicators import TechnicalIndicators
from src.models.garch import GARCHVolatility
from src.models.hmm_regime import RegimeDetector
from src.strategy.strategy_selector import StrategySelector
from src.risk.position_sizing import PositionSizer
from src.risk.risk_manager import RiskManager
from src.execution.order import Order, OrderSide, OrderType
from src.execution.executor import OrderExecutor
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Set style
sns.set_style("darkgrid")


class RegimeBacktest:
    """Backtest with regime detection and strategy selection."""
    
    def __init__(
        self,
        data: pd.DataFrame,
        regime_detector: RegimeDetector,
        strategy_selector: StrategySelector,
        initial_capital: float = 200000,
        risk_per_trade: float = 0.01,
        risk_reward_ratio: float = 2.0
    ):
        """Initialize regime-based backtest."""
        self.data = data
        self.regime_detector = regime_detector
        self.strategy_selector = strategy_selector
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.risk_reward_ratio = risk_reward_ratio
        
        # Components
        self.garch = GARCHVolatility()
        self.position_sizer = PositionSizer(initial_capital, risk_per_trade)
        self.risk_manager = RiskManager(initial_capital)
        self.executor = OrderExecutor(mode='backtest')
        
        # State
        self.capital = initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = []
        
    def run(self, use_regime_filter: bool = True) -> dict:
        """
        Run backtest.
        
        Args:
            use_regime_filter: If True, use regime filtering; if False, random entries
            
        Returns:
            Dictionary with results
        """
        logger.info(f"Running backtest: {'Regime-Based' if use_regime_filter else 'Random Entries'}")
        
        # Get regimes for entire dataset
        if use_regime_filter:
            _, regimes = self.regime_detector.predict(self.data)
            self.data = self.data.iloc[-len(regimes):].copy()
            self.data['regime'] = regimes
        
        # Reset state
        self.capital = self.initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = []
        
        # Iterate through data
        for i in tqdm(range(100, len(self.data)), desc="Backtesting"):
            current_bar = self.data.iloc[i]
            current_date = self.data.index[i]
            current_price = current_bar['close']
            
            # Record equity
            position_value = 0
            if self.position:
                position_value = self.position['quantity'] * current_price
            
            total_equity = self.capital + position_value
            self.equity_curve.append({
                'date': current_date,
                'capital': self.capital,
                'position_value': position_value,
                'total_equity': total_equity
            })
            
            # Check if risk manager allows trading
            if not self.risk_manager.can_trade():
                continue
            
            # Check existing position for exit
            if self.position:
                self._check_exit(current_bar, i)
                continue
            
            # Entry logic
            if use_regime_filter:
                signal = self._regime_based_entry(current_bar, i)
            else:
                signal = self._random_entry(current_bar, i)
            
            if signal == 'LONG':
                self._enter_position(current_bar, i)
        
        # Close any open position at end
        if self.position:
            final_bar = self.data.iloc[-1]
            self._exit_position(final_bar, len(self.data) - 1, 'End of backtest')
        
        # Calculate results
        results = self._calculate_results()
        return results
    
    def _regime_based_entry(self, bar: pd.Series, index: int) -> str:
        """Generate entry signal based on regime and strategy selector (PHASE 2.5)."""
        
        # Get current regime
        regime = bar.get('regime', 'ranging')
        
        # Check if we should trade this regime
        if not self.strategy_selector.should_trade(regime):
            return None
        
        # Get indicators for strategy selector (including ATR for fuzzy scoring)
        indicators = {
            'ema_20': bar.get('ema_20'),
            'rsi': bar.get('rsi'),
            'adx': bar.get('adx'),
            'bb_lower': bar.get('bb_lower'),
            'bb_upper': bar.get('bb_upper'),
            'atr': bar.get('atr')
        }
        
        # Get signal from strategy selector (NO MORE RANDOMNESS)
        signal = self.strategy_selector.get_entry_signal(
            regime=regime,
            price=bar['close'],
            indicators=indicators,
            track_near_miss=True
        )
        
        # Return signal directly (removed 30% probability filter)
        return signal
    
    def _random_entry(self, bar: pd.Series, index: int) -> str:
        """Random entry signal (Phase 1 baseline)."""
        # 10% probability of entry (same as Phase 1)
        if np.random.random() < 0.10:
            return 'LONG'
        return None
    
    def _enter_position(self, bar: pd.Series, index: int):
        """Enter a position."""
        entry_price = bar['close'] * 1.001  # Slippage
        
        # Calculate ATR for stop-loss
        atr = bar.get('atr', bar['close'] * 0.02)
        stop_loss_distance = 2 * atr
        stop_loss_price = entry_price - stop_loss_distance
        
        # Position sizing
        risk_amount = self.capital * self.risk_per_trade
        quantity = int(risk_amount / stop_loss_distance)
        
        # Cap at 10% of capital
        max_position_value = self.capital * 0.10
        max_quantity = int(max_position_value / entry_price)
        quantity = min(quantity, max_quantity)
        
        if quantity <= 0:
            return
        
        # Calculate costs
        position_value = quantity * entry_price
        commission = position_value * 0.0003
        stt = position_value * 0.00025
        total_cost = commission + stt
        
        # Check if we have enough capital
        if position_value + total_cost > self.capital:
            return
        
        # Take-profit based on risk-reward ratio
        profit_target = entry_price + (stop_loss_distance * self.risk_reward_ratio)
        
        # Update capital
        self.capital -= (position_value + total_cost)
        
        # Record position
        self.position = {
            'entry_date': self.data.index[index],
            'entry_index': index,
            'entry_price': entry_price,
            'quantity': quantity,
            'stop_loss': stop_loss_price,
            'take_profit': profit_target,
            'regime': bar.get('regime', 'unknown'),
            'entry_cost': total_cost
        }
    
    def _check_exit(self, bar: pd.Series, index: int):
        """Check if position should be exited."""
        current_price = bar['close']
        
        # Stop-loss
        if current_price <= self.position['stop_loss']:
            self._exit_position(bar, index, 'Stop-loss')
            return
        
        # Take-profit
        if current_price >= self.position['take_profit']:
            self._exit_position(bar, index, 'Take-profit')
            return
    
    def _exit_position(self, bar: pd.Series, index: int, reason: str):
        """Exit current position."""
        exit_price = bar['close'] * 0.999  # Slippage
        quantity = self.position['quantity']
        
        # Calculate exit value
        exit_value = quantity * exit_price
        commission = exit_value * 0.0003
        stt = exit_value * 0.00025
        total_cost = commission + stt
        
        # Update capital
        self.capital += (exit_value - total_cost)
        
        # Calculate P&L
        gross_pnl = (exit_price - self.position['entry_price']) * quantity
        total_costs = self.position['entry_cost'] + total_cost
        net_pnl = gross_pnl - total_costs
        
        # Record trade
        trade = {
            'entry_date': self.position['entry_date'],
            'exit_date': self.data.index[index],
            'entry_price': self.position['entry_price'],
            'exit_price': exit_price,
            'quantity': quantity,
            'gross_pnl': gross_pnl,
            'costs': total_costs,
            'net_pnl': net_pnl,
            'return_pct': (net_pnl / (self.position['entry_price'] * quantity)) * 100,
            'regime': self.position['regime'],
            'exit_reason': reason,
            'holding_days': (self.data.index[index] - self.position['entry_date']).days
        }
        
        self.trades.append(trade)
        
        # Update strategy selector stats
        if hasattr(self, 'strategy_selector'):
            self.strategy_selector.update_stats(self.position['regime'], net_pnl)
        
        # Update risk manager
        self.risk_manager.record_trade(net_pnl, self.data.index[index])
        
        # Clear position
        self.position = None
    
    def _calculate_results(self) -> dict:
        """Calculate backtest results."""
        if not self.trades:
            return {
                'total_return': 0,
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'final_capital': self.capital
            }
        
        trades_df = pd.DataFrame(self.trades)
        equity_df = pd.DataFrame(self.equity_curve)
        
        # Calculate metrics
        total_return = (self.capital - self.initial_capital) / self.initial_capital
        total_trades = len(trades_df)
        
        winning_trades = trades_df[trades_df['net_pnl'] > 0]
        losing_trades = trades_df[trades_df['net_pnl'] <= 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        avg_win = winning_trades['net_pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['net_pnl'].mean() if len(losing_trades) > 0 else 0
        
        # Drawdown
        equity_df['peak'] = equity_df['total_equity'].cummax()
        equity_df['drawdown'] = (equity_df['total_equity'] - equity_df['peak']) / equity_df['peak']
        max_drawdown = equity_df['drawdown'].min()
        
        # Sharpe ratio
        equity_df['returns'] = equity_df['total_equity'].pct_change()
        sharpe_ratio = (equity_df['returns'].mean() / equity_df['returns'].std() * np.sqrt(252)) if equity_df['returns'].std() > 0 else 0
        
        return {
            'total_return': total_return,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'final_capital': self.capital,
            'trades': trades_df,
            'equity_curve': equity_df
        }


def run_comparison_test():
    """Run comparison between Phase 1 and Phase 2."""
    
    logger.info("=" * 80)
    logger.info("PHASE 2: REGIME-BASED BACKTEST COMPARISON")
    logger.info("=" * 80)
    
    # Load data
    logger.info("\nLoading historical data...")
    data_loader = DataLoader()
    
    stocks = [
        "RELIANCE.NS",
        "TCS.NS",
        "INFY.NS",
        "HDFCBANK.NS",
        "ICICIBANK.NS"
    ]
    
    start_date = "2020-01-01"
    end_date = "2024-12-31"
    
    # Load HMM model
    logger.info("\nLoading trained HMM model...")
    regime_detector = RegimeDetector()
    model_path = "data/models/hmm_regime_model.pkl"
    regime_detector.load(model_path)
    
    # Results storage
    phase1_results = []
    phase2_results = []
    
    for symbol in stocks:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Testing {symbol}")
        logger.info('=' * 80)
        
        # Load and prepare data
        raw_data = data_loader.get_data(symbol, start_date, end_date)
        if raw_data.empty:
            logger.warning(f"No data for {symbol}")
            continue
        
        clean_data = DataProcessor.clean_data(raw_data)
        clean_data = TechnicalIndicators.calculate_all_indicators(clean_data)
        
        # Initialize strategy selector
        strategy_selector = StrategySelector()
        
        # Create backtest engine
        backtest = RegimeBacktest(
            data=clean_data.copy(),
            regime_detector=regime_detector,
            strategy_selector=strategy_selector,
            initial_capital=200000,
            risk_per_trade=0.01,
            risk_reward_ratio=2.0
        )
        
        # Run Phase 1 (Random entries)
        logger.info(f"\nRunning Phase 1 (Random Entries)...")
        np.random.seed(42)  # For reproducibility
        phase1 = backtest.run(use_regime_filter=False)
        phase1_results.append({
            'symbol': symbol,
            **{k: v for k, v in phase1.items() if k not in ['trades', 'equity_curve']}
        })
        
        logger.info(f"  Return: {phase1['total_return']:.2%}")
        logger.info(f"  Trades: {phase1['total_trades']}")
        logger.info(f"  Win Rate: {phase1['win_rate']:.2%}")
        logger.info(f"  Sharpe: {phase1['sharpe_ratio']:.2f}")
        
        # Run Phase 2 (Regime-based)
        logger.info(f"\nRunning Phase 2 (Regime-Based)...")
        backtest = RegimeBacktest(
            data=clean_data.copy(),
            regime_detector=regime_detector,
            strategy_selector=strategy_selector,
            initial_capital=200000,
            risk_per_trade=0.01,
            risk_reward_ratio=2.0
        )
        np.random.seed(42)  # Same seed for fair comparison
        phase2 = backtest.run(use_regime_filter=True)
        phase2_results.append({
            'symbol': symbol,
            **{k: v for k, v in phase2.items() if k not in ['trades', 'equity_curve']}
        })
        
        logger.info(f"  Return: {phase2['total_return']:.2%}")
        logger.info(f"  Trades: {phase2['total_trades']}")
        logger.info(f"  Win Rate: {phase2['win_rate']:.2%}")
        logger.info(f"  Sharpe: {phase2['sharpe_ratio']:.2f}")
        
        # Comparison
        improvement = ((phase2['total_return'] - phase1['total_return']) / abs(phase1['total_return']) * 100) if phase1['total_return'] != 0 else 0
        logger.info(f"\n  Improvement: {improvement:+.1f}%")
    
    # Aggregate results
    logger.info("\n" + "=" * 80)
    logger.info("AGGREGATE RESULTS")
    logger.info("=" * 80)
    
    phase1_df = pd.DataFrame(phase1_results)
    phase2_df = pd.DataFrame(phase2_results)
    
    logger.info("\nPHASE 1 (Random Entries):")
    logger.info(f"  Avg Return: {phase1_df['total_return'].mean():.2%}")
    logger.info(f"  Avg Win Rate: {phase1_df['win_rate'].mean():.2%}")
    logger.info(f"  Avg Sharpe: {phase1_df['sharpe_ratio'].mean():.2f}")
    logger.info(f"  Avg Trades: {phase1_df['total_trades'].mean():.0f}")
    
    logger.info("\nPHASE 2 (Regime-Based):")
    logger.info(f"  Avg Return: {phase2_df['total_return'].mean():.2%}")
    logger.info(f"  Avg Win Rate: {phase2_df['win_rate'].mean():.2%}")
    logger.info(f"  Avg Sharpe: {phase2_df['sharpe_ratio'].mean():.2f}")
    logger.info(f"  Avg Trades: {phase2_df['total_trades'].mean():.0f}")
    
    # Overall improvement
    return_improvement = ((phase2_df['total_return'].mean() - phase1_df['total_return'].mean()) / abs(phase1_df['total_return'].mean()) * 100) if phase1_df['total_return'].mean() != 0 else 0
    
    logger.info("\n" + "=" * 80)
    logger.info(f"OVERALL IMPROVEMENT: {return_improvement:+.1f}%")
    logger.info("=" * 80)
    
    # Create comparison visualization
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Returns comparison
    ax = axes[0, 0]
    x = np.arange(len(stocks))
    width = 0.35
    ax.bar(x - width/2, phase1_df['total_return'] * 100, width, label='Phase 1', alpha=0.8)
    ax.bar(x + width/2, phase2_df['total_return'] * 100, width, label='Phase 2', alpha=0.8)
    ax.set_xlabel('Stock')
    ax.set_ylabel('Return (%)')
    ax.set_title('Total Return Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace('.NS', '') for s in stocks], rotation=45)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Win rate comparison
    ax = axes[0, 1]
    ax.bar(x - width/2, phase1_df['win_rate'] * 100, width, label='Phase 1', alpha=0.8)
    ax.bar(x + width/2, phase2_df['win_rate'] * 100, width, label='Phase 2', alpha=0.8)
    ax.set_xlabel('Stock')
    ax.set_ylabel('Win Rate (%)')
    ax.set_title('Win Rate Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace('.NS', '') for s in stocks], rotation=45)
    ax.axhline(y=40, color='r', linestyle='--', alpha=0.5, label='Break-even (2:1 R:R)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Sharpe ratio comparison
    ax = axes[1, 0]
    ax.bar(x - width/2, phase1_df['sharpe_ratio'], width, label='Phase 1', alpha=0.8)
    ax.bar(x + width/2, phase2_df['sharpe_ratio'], width, label='Phase 2', alpha=0.8)
    ax.set_xlabel('Stock')
    ax.set_ylabel('Sharpe Ratio')
    ax.set_title('Sharpe Ratio Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace('.NS', '') for s in stocks], rotation=45)
    ax.axhline(y=1.0, color='r', linestyle='--', alpha=0.5, label='Good (>1.0)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Trade count comparison
    ax = axes[1, 1]
    ax.bar(x - width/2, phase1_df['total_trades'], width, label='Phase 1', alpha=0.8)
    ax.bar(x + width/2, phase2_df['total_trades'], width, label='Phase 2', alpha=0.8)
    ax.set_xlabel('Stock')
    ax.set_ylabel('Number of Trades')
    ax.set_title('Trade Count Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace('.NS', '') for s in stocks], rotation=45)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    output_dir = Path("backtest_results/phase2_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_dir / "phase1_vs_phase2_comparison.png", dpi=300, bbox_inches='tight')
    logger.info(f"\nComparison chart saved to {output_dir / 'phase1_vs_phase2_comparison.png'}")
    
    # Save results
    phase1_df.to_csv(output_dir / "phase1_results.csv", index=False)
    phase2_df.to_csv(output_dir / "phase2_results.csv", index=False)
    
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2 BACKTEST COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    run_comparison_test()
