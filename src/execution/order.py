"""
Order class representing a trade order.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class OrderType(Enum):
    """Order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderSide(Enum):
    """Order side (buy/sell)."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """
    Represents a trading order.
    """
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Execution details
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: Optional[float] = None
    commission: float = 0.0
    slippage: float = 0.0
    
    # Timestamps
    created_at: datetime = None
    filled_at: Optional[datetime] = None
    
    # Metadata
    order_id: Optional[str] = None
    strategy: Optional[str] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Set default values."""
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == OrderStatus.FILLED
    
    def is_active(self) -> bool:
        """Check if order is active (pending or partial)."""
        return self.status in [OrderStatus.PENDING, OrderStatus.PARTIAL]
    
    def fill(
        self,
        filled_price: float,
        filled_quantity: int = None,
        commission: float = 0.0,
        slippage: float = 0.0
    ):
        """
        Mark order as filled.
        
        Args:
            filled_price: Actual execution price
            filled_quantity: Quantity filled (defaults to order quantity)
            commission: Brokerage commission
            slippage: Price slippage
        """
        if filled_quantity is None:
            filled_quantity = self.quantity
        
        self.filled_quantity = filled_quantity
        self.filled_price = filled_price
        self.commission = commission
        self.slippage = slippage
        self.filled_at = datetime.now()
        
        if self.filled_quantity == self.quantity:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIAL
    
    def cancel(self):
        """Cancel the order."""
        self.status = OrderStatus.CANCELLED
    
    def reject(self, reason: str = None):
        """Reject the order."""
        self.status = OrderStatus.REJECTED
        if reason:
            self.notes = f"Rejected: {reason}"
    
    def get_total_cost(self) -> float:
        """Calculate total cost including commissions."""
        if not self.is_filled():
            return 0.0
        
        base_cost = self.filled_price * self.filled_quantity
        return base_cost + self.commission
    
    def get_pnl(self, exit_price: float) -> float:
        """
        Calculate P&L if position was closed at exit_price.
        
        Args:
            exit_price: Exit price
            
        Returns:
            Profit/Loss including commissions
        """
        if not self.is_filled():
            return 0.0
        
        if self.side == OrderSide.BUY:
            pnl = (exit_price - self.filled_price) * self.filled_quantity
        else:  # SELL
            pnl = (self.filled_price - exit_price) * self.filled_quantity
        
        # Subtract commissions (entry + exit)
        pnl -= (self.commission * 2)
        
        return pnl
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Order({self.symbol} {self.side.value} {self.quantity}@{self.price} "
            f"[{self.status.value}])"
        )
