"""
Backtesting engine for strategy validation.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Callable
from tqdm import tqdm

from ..data import DataLoader, DataProcessor
from ..features import TechnicalIndicators
from ..risk import PositionSizer, RiskManager
from ..execution import Order, OrderSide, OrderType, OrderExecutor
from ..utils.logger import get_logger
from ..utils.config_loader import get_config

logger = get_logger()
config = get_config()


class Backtest:
    """
    Backtesting engine with realistic cost simulation.
    
    Tests trading strategies against historical data with:
    - Realistic slippage
    - Commission costs
    - Position sizing
    - Risk management
    """
    
    def __init__(
        self,
        initial_capital: float,
        start_date: str,
        end_date: str,
        symbols: List[str],
        slippage: float = 0.001,
        commission: float = 0.0003
    ):
        """
        Initialize backtest.
        
        Args:
            initial_capital: Starting capital
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            symbols: List of symbols to trade
            slippage: Slippage percentage (default: 0.1%)
            commission: Commission percentage (default: 0.03%)
        """
        self.initial_capital = initial_capital
        self.start_date = start_date
        self.end_date = end_date
        self.symbols = symbols
        
        # Initialize components
        self.data_loader = DataLoader()
        self.executor = OrderExecutor(mode="backtest", slippage_pct=slippage, commission_pct=commission)
        self.risk_manager = RiskManager(initial_capital)
        self.position_sizer = PositionSizer(initial_capital)
        
        # State
        self.current_capital = initial_capital
        self.positions = {}  # symbol -> position dict
        self.trades = []
        self.equity_curve = []
        
        # Data
        self.data = {}
        
    def load_data(self):
        """Load historical data for all symbols."""
        logger.info(f"Loading data from {self.start_date} to {self.end_date}")
        
        for symbol in self.symbols:
            df = self.data_loader.get_data(symbol, self.start_date, self.end_date)
            
            if df.empty:
                logger.warning(f"No data for {symbol}, skipping")
                continue
            
            # Clean data
            df = DataProcessor.clean_data(df)
            
            # Add technical indicators
            df = TechnicalIndicators.calculate_all_indicators(df)
            
            self.data[symbol] = df
            logger.info(f"Loaded {len(df)} days for {symbol}")
        
        if not self.data:
            raise ValueError("No data loaded for any symbol")
    
    def run(
        self,
        signal_generator: Callable,
        strategy_name: str = "Strategy"
    ) -> Dict:
        """
        Run backtest with given signal generator.
        
        Args:
            signal_generator: Function that takes (data, current_index) and returns signal
                             Signal format: {'action': 'buy'/'sell'/'hold', 'confidence': 0.0-1.0}
            strategy_name: Name of strategy for logging
            
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Starting backtest: {strategy_name}")
        logger.info(f"Period: {self.start_date} to {self.end_date}")
        logger.info(f"Initial Capital: Rs.{self.initial_capital:,.2f}")
        
        # Get date range from first symbol's data
        first_symbol = list(self.data.keys())[0]
        dates = self.data[first_symbol].index
        
        # Initialize equity curve
        self.equity_curve = []
        
        # Iterate through each trading day
        for i in tqdm(range(len(dates)), desc="Backtesting"):
            current_date = dates[i]
            
            # Check risk manager status
            can_trade, reason = self.risk_manager.can_trade()
            
            # Update equity curve
            self.equity_curve.append({
                'date': current_date,
                'capital': self.current_capital,
                'positions_value': sum(p['value'] for p in self.positions.values()),
                'total_equity': self.current_capital + sum(p['value'] for p in self.positions.values())
            })
            
            # Process each symbol
            for symbol in self.symbols:
                if symbol not in self.data:
                    continue
                
                df = self.data[symbol]
                
                if i >= len(df):
                    continue
                
                current_bar = df.iloc[i]
                current_price = current_bar['close']
                
                # Check existing positions for stop-loss/take-profit
                if symbol in self.positions:
                    self._check_exit_conditions(symbol, current_bar, current_date)
                
                # Generate signal if we can trade
                if can_trade and symbol not in self.positions:
                    signal = signal_generator(df, i)
                    
                    if signal and signal.get('action') == 'buy':
                        self._enter_position(symbol, current_bar, current_date, signal)
        
        # Close any remaining positions at end
        self._close_all_positions(dates[-1])
        
        # Calculate performance metrics
        results = self._calculate_performance()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Backtest Complete: {strategy_name}")
        logger.info(f"{'='*60}")
        logger.info(f"Total Return: {results['total_return']:.2%}")
        logger.info(f"Total Trades: {results['total_trades']}")
        logger.info(f"Win Rate: {results['win_rate']:.2%}")
        logger.info(f"Max Drawdown: {results['max_drawdown']:.2%}")
        logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        logger.info(f"Final Capital: Rs.{results['final_capital']:,.2f}")
        logger.info(f"{'='*60}\n")
        
        return results
    
    def _enter_position(
        self,
        symbol: str,
        current_bar: pd.Series,
        current_date: datetime,
        signal: Dict
    ):
        """Enter a new position."""
        entry_price = current_bar['close']
        atr = current_bar['atr']
        
        # Calculate stop-loss using ATR
        stop_loss = self.position_sizer.calculate_stop_loss(
            entry_price,
            atr,
            direction='long',
            multiplier=2.0
        )
        
        # Calculate take-profit
        take_profit = self.position_sizer.calculate_take_profit(
            entry_price,
            stop_loss,
            risk_reward_ratio=2.0,  # Changed from 1.5 to 2.0 for higher reward
            direction='long'
        )
        
        # Calculate position size
        position_info = self.position_sizer.calculate_position_size(
            entry_price,
            stop_loss,
            atr
        )
        
        if not self.position_sizer.validate_position(position_info):
            return
        
        # Create order
        order = Order(
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=position_info['shares'],
            price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy=signal.get('strategy', 'Unknown')
        )
        
        # Execute order
        order = self.executor.execute_order(order, entry_price, current_bar.to_dict())
        
        if order.is_filled():
            # Update capital
            self.current_capital -= order.get_total_cost()
            
            # Store position
            self.positions[symbol] = {
                'symbol': symbol,
                'side': 'long',
                'entry_price': order.filled_price,
                'quantity': order.filled_quantity,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'entry_date': current_date,
                'entry_order': order,
                'value': order.filled_price * order.filled_quantity
            }
            
            logger.trade(f"Entered LONG {symbol} | {order.quantity} @ Rs.{order.filled_price:.2f}")
    
    def _check_exit_conditions(
        self,
        symbol: str,
        current_bar: pd.Series,
        current_date: datetime
    ):
        """Check if position should be exited."""
        position = self.positions[symbol]
        current_price = current_bar['close']
        
        exit_order = None
        
        # Check stop-loss
        exit_order = self.executor.check_stop_loss(position, current_price)
        
        # Check take-profit
        if not exit_order:
            exit_order = self.executor.check_take_profit(position, current_price)
        
        if exit_order:
            self._exit_position(symbol, exit_order, current_price, current_date, current_bar)
    
    def _exit_position(
        self,
        symbol: str,
        exit_order: Order,
        current_price: float,
        current_date: datetime,
        current_bar: pd.Series
    ):
        """Exit a position."""
        position = self.positions[symbol]
        
        # Execute exit order
        exit_order = self.executor.execute_order(exit_order, current_price, current_bar.to_dict())
        
        if exit_order.is_filled():
            # Calculate P&L
            entry_order = position['entry_order']
            pnl = entry_order.get_pnl(exit_order.filled_price)
            
            # Update capital
            self.current_capital += (exit_order.filled_price * exit_order.filled_quantity)
            self.current_capital -= exit_order.commission
            
            # Record trade
            trade_record = {
                'symbol': symbol,
                'entry_date': position['entry_date'],
                'exit_date': current_date,
                'entry_price': entry_order.filled_price,
                'exit_price': exit_order.filled_price,
                'quantity': entry_order.filled_quantity,
                'pnl': pnl,
                'pnl_pct': pnl / (entry_order.filled_price * entry_order.filled_quantity),
                'hold_days': (current_date - position['entry_date']).days,
                'exit_reason': exit_order.notes
            }
            
            self.trades.append(trade_record)
            
            # Update risk manager
            self.risk_manager.record_trade(pnl, current_date)
            
            # Update position sizer capital
            self.position_sizer.update_capital(self.current_capital)
            
            # Remove position
            del self.positions[symbol]
            
            logger.trade(
                f"Exited {symbol} | P&L: Rs.{pnl:,.2f} ({trade_record['pnl_pct']:.2%}) | "
                f"Reason: {exit_order.notes}"
            )
    
    def _close_all_positions(self, final_date: datetime):
        """Close all remaining positions at end of backtest."""
        for symbol in list(self.positions.keys()):
            position = self.positions[symbol]
            df = self.data[symbol]
            final_bar = df.loc[final_date]
            final_price = final_bar['close']
            
            exit_order = Order(
                symbol=symbol,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=position['quantity'],
                notes="End of backtest"
            )
            
            self._exit_position(symbol, exit_order, final_price, final_date, final_bar)
    
    def _calculate_performance(self) -> Dict:
        """Calculate performance metrics."""
        if not self.trades:
            return {
                'total_return': 0.0,
                'total_trades': 0,
                'win_rate': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'final_capital': self.initial_capital
            }
        
        trades_df = pd.DataFrame(self.trades)
        equity_df = pd.DataFrame(self.equity_curve)
        
        # Total return
        final_capital = self.current_capital
        total_return = (final_capital - self.initial_capital) / self.initial_capital
        
        # Win rate
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        total_trades = len(trades_df)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # Max drawdown
        equity_df['peak'] = equity_df['total_equity'].cummax()
        equity_df['drawdown'] = (equity_df['total_equity'] - equity_df['peak']) / equity_df['peak']
        max_drawdown = abs(equity_df['drawdown'].min())
        
        # Sharpe ratio
        equity_df['returns'] = equity_df['total_equity'].pct_change()
        sharpe_ratio = (equity_df['returns'].mean() / equity_df['returns'].std()) * np.sqrt(252) if equity_df['returns'].std() > 0 else 0.0
        
        # Average win/loss
        avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0.0
        avg_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].mean()) if (total_trades - winning_trades) > 0 else 0.0
        
        return {
            'initial_capital': self.initial_capital,
            'total_return': total_return,
            'final_capital': final_capital,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'win_loss_ratio': avg_win / avg_loss if avg_loss > 0 else 0.0,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'trades': trades_df,
            'equity_curve': equity_df
        }
