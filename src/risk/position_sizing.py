"""
Position sizing calculator using GARCH volatility forecasts.
"""
import numpy as np
from typing import Dict, Optional

from ..models.garch import GARCHVolatility
from ..utils.logger import get_logger
from ..utils.config_loader import get_config

logger = get_logger()
config = get_config()


class PositionSizer:
    """
    Calculate optimal position size based on:
    1. Risk per trade (1% of capital)
    2. Stop-loss distance (based on ATR)
    3. Volatility forecast (from GARCH)
    """
    
    def __init__(
        self,
        capital: float,
        risk_per_trade: float = 0.01,
        max_position_size: float = 0.10
    ):
        """
        Initialize position sizer.
        
        Args:
            capital: Total trading capital
            risk_per_trade: Risk percentage per trade (default: 1%)
            max_position_size: Maximum position as % of capital
        """
        self.capital = capital
        self.risk_per_trade = risk_per_trade
        self.max_position_size = max_position_size
        
        self.garch = GARCHVolatility()
    
    def update_capital(self, new_capital: float):
        """Update capital after profit/loss."""
        self.capital = new_capital
        logger.debug(f"Capital updated to Rs.{new_capital:,.2f}")
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        atr: float,
        volatility_forecast: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate position size using risk-based formula.
        
        Formula:
        Position Size = (Capital × Risk%) / (Entry - Stop Loss)
        
        Then adjusted by volatility multiplier.
        
        Args:
            entry_price: Planned entry price
            stop_loss_price: Stop-loss price
            atr: Current ATR value
            volatility_forecast: Forecasted volatility (optional)
            
        Returns:
            Dictionary with position sizing details
        """
        # Calculate risk amount in currency
        risk_amount = self.capital * self.risk_per_trade
        
        # Calculate stop loss distance
        stop_distance = abs(entry_price - stop_loss_price)
        
        if stop_distance == 0:
            logger.error("Stop loss distance is zero!")
            return self._zero_position()
        
        # Calculate base position size (number of shares)
        base_shares = risk_amount / stop_distance
        
        # Apply volatility adjustment if available
        volatility_multiplier = 1.0
        if volatility_forecast is not None:
            # Placeholder - in real implementation, use GARCH classification
            # For now, just ensure we have a multiplier
            volatility_multiplier = 1.0
        
        # Adjusted position size
        adjusted_shares = base_shares * volatility_multiplier
        
        # Calculate position value
        position_value = adjusted_shares * entry_price
        
        # Apply maximum position size constraint
        max_value = self.capital * self.max_position_size
        if position_value > max_value:
            logger.warning(f"Position size capped at {self.max_position_size*100}% of capital")
            adjusted_shares = max_value / entry_price
            position_value = max_value
        
        # Calculate position as % of capital
        position_pct = position_value / self.capital
        
        # Calculate risk-reward ratio
        potential_loss = adjusted_shares * stop_distance
        
        return {
            'shares': int(adjusted_shares),
            'position_value': position_value,
            'position_pct': position_pct,
            'risk_amount': risk_amount,
            'potential_loss': potential_loss,
            'stop_distance': stop_distance,
            'volatility_multiplier': volatility_multiplier,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price
        }
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
        direction: str = 'long',
        multiplier: float = 2.0
    ) -> float:
        """
        Calculate stop-loss price based on ATR.
        
        Standard approach: Stop = Entry ± (2 × ATR)
        
        Args:
            entry_price: Entry price
            atr: Average True Range
            direction: 'long' or 'short'
            multiplier: ATR multiplier (default: 2.0)
            
        Returns:
            Stop-loss price
        """
        stop_distance = atr * multiplier
        
        if direction == 'long':
            stop_loss = entry_price - stop_distance
        else:  # short
            stop_loss = entry_price + stop_distance
        
        return stop_loss
    
    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss_price: float,
        risk_reward_ratio: float = 1.5,
        direction: str = 'long'
    ) -> float:
        """
        Calculate take-profit price based on risk-reward ratio.
        
        Args:
            entry_price: Entry price
            stop_loss_price: Stop-loss price
            risk_reward_ratio: Desired R:R ratio (default: 1.5)
            direction: 'long' or 'short'
            
        Returns:
            Take-profit price
        """
        risk = abs(entry_price - stop_loss_price)
        reward = risk * risk_reward_ratio
        
        if direction == 'long':
            take_profit = entry_price + reward
        else:  # short
            take_profit = entry_price - reward
        
        return take_profit
    
    def _zero_position(self) -> Dict[str, float]:
        """Return zero position (when calculation fails)."""
        return {
            'shares': 0,
            'position_value': 0.0,
            'position_pct': 0.0,
            'risk_amount': 0.0,
            'potential_loss': 0.0,
            'stop_distance': 0.0,
            'volatility_multiplier': 0.0,
            'entry_price': 0.0,
            'stop_loss_price': 0.0
        }
    
    def validate_position(self, position: Dict[str, float]) -> bool:
        """
        Validate position before execution.
        
        Args:
            position: Position dictionary from calculate_position_size
            
        Returns:
            True if valid, False otherwise
        """
        if position['shares'] == 0:
            logger.warning("Position size is zero")
            return False
        
        if position['position_pct'] > self.max_position_size:
            logger.error(f"Position exceeds max size: {position['position_pct']:.2%}")
            return False
        
        if position['position_value'] > self.capital:
            logger.error("Insufficient capital for position")
            return False
        
        return True
