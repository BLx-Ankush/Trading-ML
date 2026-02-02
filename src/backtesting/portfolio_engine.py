"""
Portfolio Backtesting Engine

Manages multiple stocks simultaneously with capital allocation,
position limits, and portfolio-level risk management.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PortfolioPosition:
    """Represents an open position in the portfolio."""
    symbol: str
    entry_date: datetime
    entry_price: float
    quantity: int
    stop_loss: float
    take_profit: float
    capital_allocated: float
    regime: str
    highest_price: float = None  # For trailing stop
    trailing_stop_active: bool = False  # Trailing stop status
    
    def __post_init__(self):
        """Initialize highest price to entry price."""
        if self.highest_price is None:
            self.highest_price = self.entry_price


class PortfolioEngine:
    """
    Multi-stock portfolio backtesting engine.
    
    Features:
    - Simultaneous trading across multiple stocks
    - Capital allocation with position limits
    - Portfolio-level risk management
    - Diversification tracking
    """
    
    def __init__(
        self,
        initial_capital: float = 200000,
        max_positions: int = 5,
        risk_per_trade: float = 0.01,
        max_portfolio_risk: float = 0.05,
        enable_trailing_stop: bool = False,  # DISABLED by default - hurts returns
        trailing_stop_activation: float = 1.0,  # Activate after 1×ATR profit
        trailing_stop_distance: float = 1.5,  # Trail at 1.5×ATR from highest
        enable_time_exit: bool = False,  # DISABLED by default - cuts winners short
        max_holding_days: int = 30,  # Close after 30 days
        profitable_exit_days: int = 20,  # Close if profitable after 20 days
        enable_monthly_stop: bool = True,  # Keep portfolio circuit breaker
        monthly_stop_loss: float = 0.10,  # 10% monthly DD threshold (was 8%)
        # Phase 6A: Trading costs
        enable_trading_costs: bool = True,  # Enable realistic costs
        slippage_pct: float = 0.0025,  # 0.25% slippage per trade
        brokerage_pct: float = 0.0004,  # 0.04% brokerage per trade
        stt_pct: float = 0.001  # 0.1% STT on sell side only
    ):
        """
        Initialize portfolio engine with Phase 1 optimizations.
        
        Args:
            initial_capital: Starting capital (Rs. 2 lakhs)
            max_positions: Maximum concurrent positions (default: 5)
            risk_per_trade: Risk per trade as fraction of capital (default: 1%)
            max_portfolio_risk: Maximum total portfolio risk (default: 5%)
            enable_trailing_stop: Enable trailing stop (DISABLED - reduces returns)
            trailing_stop_activation: ATR multiplier to activate trailing stop
            trailing_stop_distance: ATR multiplier for trailing stop distance
            enable_time_exit: Enable time-based exits (DISABLED - cuts winners)
            max_holding_days: Maximum days to hold position
            profitable_exit_days: Days to hold if profitable
            enable_monthly_stop: Enable monthly stop loss (ENABLED - circuit breaker)
            monthly_stop_loss: Monthly drawdown threshold (default: 10%)
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.max_positions = max_positions
        self.risk_per_trade = risk_per_trade
        self.max_portfolio_risk = max_portfolio_risk
        
        # Phase 1 optimizations
        self.enable_trailing_stop = enable_trailing_stop
        self.trailing_stop_activation = trailing_stop_activation
        self.trailing_stop_distance = trailing_stop_distance
        self.enable_time_exit = enable_time_exit
        self.max_holding_days = max_holding_days
        self.profitable_exit_days = profitable_exit_days
        self.enable_monthly_stop = enable_monthly_stop
        self.monthly_stop_loss = monthly_stop_loss
        
        # Phase 6A: Trading costs (Budget 2026 confirmed - unchanged)
        self.enable_trading_costs = enable_trading_costs
        self.slippage_pct = slippage_pct
        self.brokerage_pct = brokerage_pct
        self.stt_pct = stt_pct
        
        # Phase 6A Week 3: Sector diversification
        self.sector_map = {
            'HDFCBANK.NS': 'Banking',
            'ICICIBANK.NS': 'Banking',
            'KOTAKBANK.NS': 'Banking',
            'SBIN.NS': 'Banking',
            'AXISBANK.NS': 'Banking',
            'TCS.NS': 'IT',
            'INFY.NS': 'IT',
            'HCLTECH.NS': 'IT',
            'RELIANCE.NS': 'Energy',
            'HINDUNILVR.NS': 'Consumer',
            'ITC.NS': 'Consumer',
            'MARUTI.NS': 'Auto',
            'BHARTIARTL.NS': 'Telecom',
            'BAJFINANCE.NS': 'NBFC',
            'LT.NS': 'Infrastructure'
        }
        self.sector_limits = {
            'Banking': 2,  # Max 2 banking stocks simultaneously
            'IT': 2,       # Max 2 IT stocks simultaneously
            'Consumer': 2,
            'Auto': 1,
            'Telecom': 1,
            'NBFC': 1,
            'Energy': 1,
            'Infrastructure': 1
        }
        
        # Portfolio state
        self.positions: Dict[str, PortfolioPosition] = {}
        self.closed_trades: List[Dict] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        
        # Monthly tracking for stop loss
        self.monthly_high: Dict[str, float] = {}  # month_key: highest_capital
        self.trading_paused_until: Optional[datetime] = None
        
        # Statistics
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'by_symbol': {},
            'trailing_stop_exits': 0,
            'time_based_exits': 0,
            'monthly_stops_triggered': 0,
            # Phase 6A: Cost tracking
            'total_costs': 0.0,
            'slippage_costs': 0.0,
            'brokerage_costs': 0.0,
            'stt_costs': 0.0
        }
        
    def is_trading_paused(self, current_date: datetime) -> bool:
        """
        Check if trading is paused due to monthly stop loss.
        
        Args:
            current_date: Current date
            
        Returns:
            True if trading is paused
        """
        if not self.enable_monthly_stop:
            return False
            
        if self.trading_paused_until is None:
            return False
            
        return current_date < self.trading_paused_until
    
    def can_open_position(self, symbol: str, current_date: datetime = None) -> bool:
        """
        Check if we can open a new position.
        
        Args:
            symbol: Stock symbol
            current_date: Current date (for monthly stop check)
            
        Returns:
            True if position can be opened
        """
        # Check if trading is paused
        if current_date and self.is_trading_paused(current_date):
            logger.debug(f"Cannot open {symbol}: Trading paused due to monthly stop loss")
            return False
        
        # Check max positions limit
        if len(self.positions) >= self.max_positions:
            logger.debug(f"Cannot open {symbol}: Max positions ({self.max_positions}) reached")
            return False
        
        # Check if already have position in this symbol
        if symbol in self.positions:
            logger.debug(f"Cannot open {symbol}: Already have open position")
            return False
        
        # Phase 6A Week 3: Check sector diversification limits
        sector = self.sector_map.get(symbol)
        if sector:
            sector_limit = self.sector_limits.get(sector, 999)
            current_sector_positions = sum(
                1 for sym, pos in self.positions.items()
                if self.sector_map.get(sym) == sector
            )
            if current_sector_positions >= sector_limit:
                logger.debug(f"Cannot open {symbol}: Sector {sector} limit ({sector_limit}) reached")
                return False
        
        # Check portfolio risk
        current_risk = sum(
            pos.capital_allocated * self.risk_per_trade 
            for pos in self.positions.values()
        )
        if current_risk >= self.initial_capital * self.max_portfolio_risk:
            logger.debug(f"Cannot open {symbol}: Max portfolio risk reached")
            return False
        
        return True
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float
    ) -> Tuple[int, float]:
        """
        Calculate position size based on risk management.
        
        Args:
            symbol: Stock symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            
        Returns:
            (quantity, capital_allocated)
        """
        # Risk per trade in rupees
        risk_amount = self.capital * self.risk_per_trade
        
        # Risk per share
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share == 0:
            return 0, 0.0
        
        # Calculate quantity
        quantity = int(risk_amount / risk_per_share)
        
        # Capital allocated
        capital_allocated = quantity * entry_price
        
        # Ensure we have enough capital
        available_capital = self.capital - sum(
            pos.capital_allocated for pos in self.positions.values()
        )
        
        if capital_allocated > available_capital:
            # Scale down to available capital
            quantity = int(available_capital / entry_price)
            capital_allocated = quantity * entry_price
        
        return quantity, capital_allocated
    
    def open_position(
        self,
        symbol: str,
        date: datetime,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        regime: str,
        atr: float = None  # For trailing stop calculations
    ) -> bool:
        """
        Open a new position.
        
        Args:
            symbol: Stock symbol
            date: Entry date
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            regime: Market regime
            atr: Average True Range (for trailing stops)
            
        Returns:
            True if position opened successfully
        """
        if not self.can_open_position(symbol, date):
            return False
        
        # Calculate position size
        quantity, capital_allocated = self.calculate_position_size(
            symbol, entry_price, stop_loss
        )
        
        if quantity == 0:
            logger.debug(f"Cannot open {symbol}: Insufficient capital")
            return False
        
        # Create position
        position = PortfolioPosition(
            symbol=symbol,
            entry_date=date,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            capital_allocated=capital_allocated,
            regime=regime
        )
        
        self.positions[symbol] = position
        
        logger.info(
            f"[{date.date()}] OPEN {symbol}: {quantity} @ {entry_price:.2f} "
            f"(SL: {stop_loss:.2f}, TP: {take_profit:.2f}, Regime: {regime})"
        )
        
        return True
    
    def close_position(
        self,
        symbol: str,
        date: datetime,
        exit_price: float,
        reason: str
    ) -> Optional[float]:
        """
        Close an existing position.
        
        Args:
            symbol: Stock symbol
            date: Exit date
            exit_price: Exit price
            reason: Reason for exit ('TARGET', 'STOP', 'EOD')
            
        Returns:
            PnL or None if position doesn't exist
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        
        # Calculate PnL
        gross_pnl = (exit_price - position.entry_price) * position.quantity
        
        # Phase 6A: Calculate trading costs
        trading_costs = 0.0
        slippage_cost = 0.0
        brokerage_cost = 0.0
        stt_cost = 0.0
        
        if self.enable_trading_costs:
            # Entry costs: slippage + brokerage
            entry_value = position.entry_price * position.quantity
            entry_slippage = entry_value * self.slippage_pct
            entry_brokerage = entry_value * self.brokerage_pct
            
            # Exit costs: slippage + brokerage + STT
            exit_value = exit_price * position.quantity
            exit_slippage = exit_value * self.slippage_pct
            exit_brokerage = exit_value * self.brokerage_pct
            exit_stt = exit_value * self.stt_pct  # STT only on sell side
            
            # Total costs
            slippage_cost = entry_slippage + exit_slippage
            brokerage_cost = entry_brokerage + exit_brokerage
            stt_cost = exit_stt
            trading_costs = slippage_cost + brokerage_cost + stt_cost
            
            # Track costs
            self.stats['total_costs'] += trading_costs
            self.stats['slippage_costs'] += slippage_cost
            self.stats['brokerage_costs'] += brokerage_cost
            self.stats['stt_costs'] += stt_cost
        
        # Net PnL after costs
        pnl = gross_pnl - trading_costs
        pnl_pct = (pnl / position.capital_allocated) * 100
        
        # Update capital
        self.capital += pnl
        
        # Record trade
        trade = {
            'symbol': symbol,
            'entry_date': position.entry_date,
            'exit_date': date,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'quantity': position.quantity,
            'pnl': pnl,
            'gross_pnl': gross_pnl,
            'pnl_pct': pnl_pct,
            'capital_allocated': position.capital_allocated,
            'regime': position.regime,
            'reason': reason,
            'holding_days': (date - position.entry_date).days,
            # Phase 6A: Cost breakdown
            'trading_costs': trading_costs,
            'slippage_cost': slippage_cost,
            'brokerage_cost': brokerage_cost,
            'stt_cost': stt_cost
        }
        
        self.closed_trades.append(trade)
        
        # Update statistics
        self.stats['total_trades'] += 1
        self.stats['total_pnl'] += pnl
        
        if pnl > 0:
            self.stats['winning_trades'] += 1
        else:
            self.stats['losing_trades'] += 1
        
        # Track exit reasons
        if reason == 'TRAILING_STOP':
            self.stats['trailing_stop_exits'] += 1
        elif reason == 'TIME_EXIT':
            self.stats['time_based_exits'] += 1
        
        if symbol not in self.stats['by_symbol']:
            self.stats['by_symbol'][symbol] = {
                'trades': 0, 'wins': 0, 'pnl': 0.0
            }
        
        self.stats['by_symbol'][symbol]['trades'] += 1
        self.stats['by_symbol'][symbol]['pnl'] += pnl
        if pnl > 0:
            self.stats['by_symbol'][symbol]['wins'] += 1
        
        # Remove position
        del self.positions[symbol]
        
        # Log with cost breakdown if enabled
        if self.enable_trading_costs and trading_costs > 0:
            logger.info(
                f"[{date.date()}] CLOSE {symbol}: {position.quantity} @ {exit_price:.2f} "
                f"| {reason} | Gross: {gross_pnl:+,.2f} | Costs: {trading_costs:,.2f} "
                f"| Net: {pnl:+,.2f} ({pnl_pct:+.2f}%) | Capital: {self.capital:,.2f}"
            )
        else:
            logger.info(
                f"[{date.date()}] CLOSE {symbol}: {position.quantity} @ {exit_price:.2f} "
                f"| {reason} | PnL: {pnl:+,.2f} ({pnl_pct:+.2f}%) | Capital: {self.capital:,.2f}"
            )
        
        return pnl
    
    def update_trailing_stop(
        self,
        symbol: str,
        current_price: float,
        atr: float
    ) -> Optional[float]:
        """
        Update trailing stop for a position.
        
        Args:
            symbol: Stock symbol
            current_price: Current price
            atr: Average True Range
            
        Returns:
            New trailing stop price or None
        """
        if not self.enable_trailing_stop or symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        
        # Update highest price
        if current_price > position.highest_price:
            position.highest_price = current_price
        
        # Check if trailing stop should activate
        profit = position.highest_price - position.entry_price
        activation_threshold = self.trailing_stop_activation * atr
        
        if profit >= activation_threshold:
            position.trailing_stop_active = True
            
            # Calculate trailing stop
            new_stop = position.highest_price - (self.trailing_stop_distance * atr)
            
            # Never worse than original stop
            new_stop = max(new_stop, position.entry_price - (2 * atr))
            
            # Update stop if it's better (higher)
            if new_stop > position.stop_loss:
                logger.debug(
                    f"{symbol} trailing stop updated: {position.stop_loss:.2f} → {new_stop:.2f} "
                    f"(Highest: {position.highest_price:.2f}, ATR: {atr:.2f})"
                )
                position.stop_loss = new_stop
                return new_stop
        
        return None
    
    def check_time_based_exit(
        self,
        symbol: str,
        current_date: datetime,
        current_price: float
    ) -> bool:
        """
        Check if position should be closed based on time.
        
        Args:
            symbol: Stock symbol
            current_date: Current date
            current_price: Current price
            
        Returns:
            True if should exit
        """
        if not self.enable_time_exit or symbol not in self.positions:
            return False
        
        position = self.positions[symbol]
        holding_days = (current_date - position.entry_date).days
        
        # Check if holding too long
        if holding_days >= self.max_holding_days:
            logger.info(f"{symbol} held for {holding_days} days (max: {self.max_holding_days}) - Time exit")
            return True
        
        # Check profitable exit threshold
        if holding_days >= self.profitable_exit_days:
            profit = current_price - position.entry_price
            if profit > 0:
                logger.info(
                    f"{symbol} held for {holding_days} days with profit "
                    f"{profit:.2f} - Profitable time exit"
                )
                return True
        
        return False
    
    def update_monthly_stop_loss(self, current_date: datetime):
        """
        Update and check monthly stop loss.
        
        Args:
            current_date: Current date
        """
        if not self.enable_monthly_stop:
            return
        
        # Get month key (YYYY-MM)
        month_key = current_date.strftime('%Y-%m')
        
        # Initialize monthly high if needed
        if month_key not in self.monthly_high:
            self.monthly_high[month_key] = self.capital
            # Reset trading pause at start of new month
            if self.trading_paused_until and self.trading_paused_until < current_date:
                self.trading_paused_until = None
                logger.info(f"[{current_date.date()}] Trading resumed - New month started")
        
        # Update monthly high
        if self.capital > self.monthly_high[month_key]:
            self.monthly_high[month_key] = self.capital
        
        # Check monthly drawdown
        monthly_high = self.monthly_high[month_key]
        monthly_dd = (monthly_high - self.capital) / monthly_high
        
        if monthly_dd >= self.monthly_stop_loss and self.trading_paused_until is None:
            # Pause trading for rest of month
            # Find first day of next month
            year = current_date.year
            month = current_date.month + 1
            if month > 12:
                month = 1
                year += 1
            
            from datetime import datetime as dt
            self.trading_paused_until = dt(year, month, 1)
            
            self.stats['monthly_stops_triggered'] += 1
            
            logger.warning(
                f"[{current_date.date()}] MONTHLY STOP LOSS TRIGGERED! "
                f"Drawdown: {monthly_dd*100:.2f}% (Threshold: {self.monthly_stop_loss*100:.1f}%) | "
                f"Trading paused until {self.trading_paused_until.date()}"
            )
    
    def update_equity_curve(self, date: datetime):
        """
        Update equity curve with current portfolio value.
        
        Args:
            date: Current date
        """
        # Calculate current portfolio value
        portfolio_value = self.capital
        
        self.equity_curve.append((date, portfolio_value))
        
        # Update monthly stop loss tracking
        self.update_monthly_stop_loss(date)
    
    def get_performance_metrics(self) -> Dict:
        """
        Calculate portfolio performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        if not self.closed_trades:
            return {
                'total_return': 0.0,
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'profit_factor': 0.0
            }
        
        # Basic metrics
        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        total_trades = len(self.closed_trades)
        winning_trades = [t for t in self.closed_trades if t['pnl'] > 0]
        losing_trades = [t for t in self.closed_trades if t['pnl'] <= 0]
        
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        
        # Profit factor
        gross_profit = sum(t['pnl'] for t in winning_trades) if winning_trades else 0
        gross_loss = abs(sum(t['pnl'] for t in losing_trades)) if losing_trades else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Sharpe ratio
        if len(self.equity_curve) > 1:
            returns = []
            for i in range(1, len(self.equity_curve)):
                prev_value = self.equity_curve[i-1][1]
                curr_value = self.equity_curve[i][1]
                ret = (curr_value - prev_value) / prev_value
                returns.append(ret)
            
            if returns and np.std(returns) > 0:
                sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0
        
        # Max drawdown
        if len(self.equity_curve) > 1:
            equity_values = [v for _, v in self.equity_curve]
            peak = equity_values[0]
            max_dd = 0
            
            for value in equity_values:
                if value > peak:
                    peak = value
                dd = (peak - value) / peak * 100
                max_dd = max(max_dd, dd)
        else:
            max_dd = 0.0
        
        # Phase 6A: Calculate cost metrics
        total_costs = self.stats.get('total_costs', 0.0)
        gross_return = ((self.capital + total_costs - self.initial_capital) / self.initial_capital) * 100
        cost_impact_pct = (total_costs / self.initial_capital) * 100
        
        return {
            'total_return': total_return,
            'gross_return': gross_return,
            'total_costs': total_costs,
            'cost_impact_pct': cost_impact_pct,
            'slippage_costs': self.stats.get('slippage_costs', 0.0),
            'brokerage_costs': self.stats.get('brokerage_costs', 0.0),
            'stt_costs': self.stats.get('stt_costs', 0.0),
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_dd,
            'profit_factor': profit_factor
        }
    
    def get_symbol_breakdown(self) -> pd.DataFrame:
        """
        Get per-symbol performance breakdown.
        
        Returns:
            DataFrame with per-symbol metrics
        """
        symbol_data = []
        
        for symbol, stats in self.stats['by_symbol'].items():
            trades = stats['trades']
            wins = stats['wins']
            pnl = stats['pnl']
            
            win_rate = (wins / trades * 100) if trades > 0 else 0
            
            symbol_data.append({
                'symbol': symbol,
                'trades': trades,
                'wins': wins,
                'losses': trades - wins,
                'win_rate': win_rate,
                'total_pnl': pnl,
                'avg_pnl_per_trade': pnl / trades if trades > 0 else 0
            })
        
        df = pd.DataFrame(symbol_data)
        if not df.empty:
            df = df.sort_values('total_pnl', ascending=False)
        
        return df
