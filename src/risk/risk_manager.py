"""
Risk management system with kill switches and loss limits.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque

from ..utils.logger import get_logger
from ..utils.config_loader import get_config

logger = get_logger()
config = get_config()


class RiskManager:
    """
    Multi-layer risk management system.
    
    Layer 1: Per-trade risk (1.5% max loss)
    Layer 2: Daily loss limit (5%)
    Layer 3: Weekly loss limit (10%)
    Layer 4: Monthly loss limit (15%)
    Layer 5: Consecutive loss limit (5 trades)
    Layer 6: Max drawdown (25%)
    """
    
    def __init__(
        self,
        initial_capital: float,
        daily_loss_limit: float = 0.05,
        weekly_loss_limit: float = 0.10,
        monthly_loss_limit: float = 0.15,
        max_drawdown: float = 0.25,
        consecutive_loss_limit: int = 5
    ):
        """
        Initialize risk manager.
        
        Args:
            initial_capital: Starting capital
            daily_loss_limit: Daily loss limit (% of capital)
            weekly_loss_limit: Weekly loss limit (% of capital)
            monthly_loss_limit: Monthly loss limit (% of capital)
            max_drawdown: Maximum drawdown allowed
            consecutive_loss_limit: Max consecutive losses before pause
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        
        # Loss limits
        self.daily_loss_limit = daily_loss_limit
        self.weekly_loss_limit = weekly_loss_limit
        self.monthly_loss_limit = monthly_loss_limit
        self.max_drawdown = max_drawdown
        self.consecutive_loss_limit = consecutive_loss_limit
        
        # Tracking
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.monthly_pnl = 0.0
        
        self.current_date = None
        self.week_start = None
        self.month_start = None
        
        # Trade history
        self.recent_trades: deque = deque(maxlen=consecutive_loss_limit)
        self.trade_count = 0
        
        # System state
        self.is_active = True
        self.pause_reason = None
        self.pause_until = None
        
    def record_trade(self, pnl: float, trade_date: datetime) -> Dict[str, any]:
        """
        Record trade P&L and check all risk limits.
        
        Args:
            pnl: Profit/Loss from trade
            trade_date: Date of trade execution
            
        Returns:
            Dictionary with risk check results
        """
        self.trade_count += 1
        
        # Update capital
        self.current_capital += pnl
        
        # Update peak capital (for drawdown calculation)
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        # Reset daily/weekly/monthly counters if needed
        self._check_date_rollover(trade_date)
        
        # Add to period P&L
        self.daily_pnl += pnl
        self.weekly_pnl += pnl
        self.monthly_pnl += pnl
        
        # Track win/loss
        self.recent_trades.append('loss' if pnl < 0 else 'win')
        
        # Check all risk limits
        risk_status = self._check_all_limits()
        
        # Log trade
        logger.trade(
            f"Trade #{self.trade_count} | P&L: Rs.{pnl:,.2f} | "
            f"Capital: Rs.{self.current_capital:,.2f} | "
            f"Daily P&L: Rs.{self.daily_pnl:,.2f}"
        )
        
        return risk_status
    
    def can_trade(self) -> tuple[bool, Optional[str]]:
        """
        Check if system can take new trades.
        
        Returns:
            Tuple of (can_trade, reason_if_not)
        """
        if not self.is_active:
            return False, self.pause_reason
        
        # Check if pause period has expired
        if self.pause_until and datetime.now() < self.pause_until:
            remaining = (self.pause_until - datetime.now()).total_seconds() / 3600
            return False, f"System paused for {remaining:.1f} more hours"
        
        # Pause has expired, reactivate
        if self.pause_until and datetime.now() >= self.pause_until:
            self._reactivate()
        
        return True, None
    
    def _check_all_limits(self) -> Dict[str, any]:
        """Check all risk limits and pause if needed."""
        status = {
            'can_trade': True,
            'warnings': [],
            'triggered_limits': []
        }
        
        # Daily loss limit
        daily_loss_pct = abs(self.daily_pnl) / self.initial_capital
        if self.daily_pnl < 0 and daily_loss_pct >= self.daily_loss_limit:
            self._trigger_pause(
                f"Daily loss limit reached: {daily_loss_pct:.2%}",
                hours=24
            )
            status['triggered_limits'].append('daily_loss')
        elif self.daily_pnl < 0 and daily_loss_pct >= self.daily_loss_limit * 0.7:
            status['warnings'].append(f"Approaching daily limit: {daily_loss_pct:.2%}")
        
        # Weekly loss limit
        weekly_loss_pct = abs(self.weekly_pnl) / self.initial_capital
        if self.weekly_pnl < 0 and weekly_loss_pct >= self.weekly_loss_limit:
            self._trigger_pause(
                f"Weekly loss limit reached: {weekly_loss_pct:.2%}",
                hours=72
            )
            status['triggered_limits'].append('weekly_loss')
        
        # Monthly loss limit
        monthly_loss_pct = abs(self.monthly_pnl) / self.initial_capital
        if self.monthly_pnl < 0 and monthly_loss_pct >= self.monthly_loss_limit:
            self._trigger_pause(
                f"Monthly loss limit reached: {monthly_loss_pct:.2%}",
                days=7
            )
            status['triggered_limits'].append('monthly_loss')
        
        # Max drawdown
        current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        if current_drawdown >= self.max_drawdown:
            self._trigger_pause(
                f"Max drawdown reached: {current_drawdown:.2%}",
                manual_review=True
            )
            status['triggered_limits'].append('max_drawdown')
        elif current_drawdown >= self.max_drawdown * 0.8:
            status['warnings'].append(f"High drawdown: {current_drawdown:.2%}")
        
        # Consecutive losses
        if len(self.recent_trades) == self.consecutive_loss_limit:
            if all(trade == 'loss' for trade in self.recent_trades):
                self._trigger_pause(
                    f"Consecutive loss limit reached: {self.consecutive_loss_limit} losses",
                    hours=48
                )
                status['triggered_limits'].append('consecutive_losses')
        
        status['can_trade'] = self.is_active
        
        return status
    
    def _trigger_pause(
        self,
        reason: str,
        hours: int = None,
        days: int = None,
        manual_review: bool = False
    ):
        """Pause trading system."""
        self.is_active = False
        self.pause_reason = reason
        
        if manual_review:
            self.pause_until = None  # Requires manual restart
            logger.risk(f"SYSTEM PAUSED (MANUAL REVIEW REQUIRED): {reason}")
        elif hours:
            self.pause_until = datetime.now() + timedelta(hours=hours)
            logger.risk(f"SYSTEM PAUSED for {hours}h: {reason}")
        elif days:
            self.pause_until = datetime.now() + timedelta(days=days)
            logger.risk(f"SYSTEM PAUSED for {days}d: {reason}")
    
    def _reactivate(self):
        """Reactivate system after pause period."""
        logger.info(f"System reactivated after pause: {self.pause_reason}")
        self.is_active = True
        self.pause_reason = None
        self.pause_until = None
    
    def manual_restart(self):
        """Manually restart system (requires manual review)."""
        if self.pause_until is None:  # Was waiting for manual review
            logger.info("System manually restarted after review")
            self._reactivate()
        else:
            logger.warning("System not in manual review state")
    
    def _check_date_rollover(self, current_date: datetime):
        """Reset period counters on date rollover."""
        if self.current_date is None:
            self.current_date = current_date.date()
            self.week_start = current_date.date()
            self.month_start = current_date.date()
            return
        
        # Daily rollover
        if current_date.date() > self.current_date:
            logger.debug(f"Day rollover: Daily P&L was Rs.{self.daily_pnl:,.2f}")
            self.daily_pnl = 0.0
            self.current_date = current_date.date()
        
        # Weekly rollover (Monday = 0)
        if (current_date.date() - self.week_start).days >= 7:
            logger.debug(f"Week rollover: Weekly P&L was Rs.{self.weekly_pnl:,.2f}")
            self.weekly_pnl = 0.0
            self.week_start = current_date.date()
        
        # Monthly rollover
        if current_date.month != self.month_start.month:
            logger.debug(f"Month rollover: Monthly P&L was Rs.{self.monthly_pnl:,.2f}")
            self.monthly_pnl = 0.0
            self.month_start = current_date.date()
    
    def get_status(self) -> Dict[str, any]:
        """Get current risk status."""
        current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        
        return {
            'is_active': self.is_active,
            'pause_reason': self.pause_reason,
            'current_capital': self.current_capital,
            'peak_capital': self.peak_capital,
            'current_drawdown': current_drawdown,
            'daily_pnl': self.daily_pnl,
            'weekly_pnl': self.weekly_pnl,
            'monthly_pnl': self.monthly_pnl,
            'trade_count': self.trade_count,
            'recent_streak': list(self.recent_trades)
        }
