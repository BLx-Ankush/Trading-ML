"""
Order execution engine.
"""
from typing import Optional, Dict
from datetime import datetime
import random

from .order import Order, OrderType, OrderStatus, OrderSide
from ..utils.logger import get_logger
from ..utils.config_loader import get_config

logger = get_logger()
config = get_config()


class OrderExecutor:
    """
    Execute trading orders with realistic simulation.
    
    For backtesting: Simulates execution with slippage and commissions
    For live trading: Integrates with broker API (Phase 4)
    """
    
    def __init__(
        self,
        mode: str = "backtest",
        slippage_pct: float = 0.001,
        commission_pct: float = 0.0003
    ):
        """
        Initialize executor.
        
        Args:
            mode: 'backtest', 'paper', or 'live'
            slippage_pct: Slippage percentage (default: 0.1%)
            commission_pct: Commission percentage (default: 0.03%)
        """
        self.mode = mode
        self.slippage_pct = slippage_pct
        self.commission_pct = commission_pct
        
        self.order_history = []
        self.active_orders = {}
    
    def execute_order(
        self,
        order: Order,
        current_price: float,
        current_data: Optional[Dict] = None
    ) -> Order:
        """
        Execute an order.
        
        Args:
            order: Order to execute
            current_price: Current market price
            current_data: Current OHLCV data (for limit order simulation)
            
        Returns:
            Executed order
        """
        if self.mode == "backtest":
            return self._execute_backtest(order, current_price, current_data)
        elif self.mode == "paper":
            return self._execute_paper(order, current_price)
        elif self.mode == "live":
            return self._execute_live(order)
        else:
            raise ValueError(f"Unknown mode: {self.mode}")
    
    def _execute_backtest(
        self,
        order: Order,
        current_price: float,
        current_data: Optional[Dict] = None
    ) -> Order:
        """
        Execute order in backtest mode with realistic simulation.
        
        Simulates:
        - Slippage (price moves against you)
        - Commission costs
        - Limit order fill logic
        """
        if order.order_type == OrderType.MARKET:
            # Market orders: Apply slippage
            filled_price = self._apply_slippage(current_price, order.side)
            
        elif order.order_type == OrderType.LIMIT:
            # Limit orders: Check if price reached limit
            if not self._limit_order_filled(order, current_data):
                order.status = OrderStatus.PENDING
                self.active_orders[order.order_id] = order
                logger.debug(f"Limit order pending: {order}")
                return order
            
            # Limit order filled at limit price (optimistic assumption)
            filled_price = order.price
        
        else:
            raise ValueError(f"Unsupported order type: {order.order_type}")
        
        # Calculate commission
        position_value = filled_price * order.quantity
        commission = position_value * self.commission_pct
        
        # STT (Securities Transaction Tax) for Indian markets
        stt = position_value * 0.00025  # 0.025%
        total_commission = commission + stt
        
        # Calculate slippage amount
        slippage = abs(filled_price - current_price) * order.quantity
        
        # Fill the order
        order.fill(
            filled_price=filled_price,
            commission=total_commission,
            slippage=slippage
        )
        
        self.order_history.append(order)
        
        logger.trade(
            f"Executed {order.side.value.upper()} {order.quantity} {order.symbol} "
            f"@ Rs.{filled_price:.2f} | Commission: Rs.{total_commission:.2f} | "
            f"Slippage: Rs.{slippage:.2f}"
        )
        
        return order
    
    def _apply_slippage(self, price: float, side: OrderSide) -> float:
        """
        Apply realistic slippage to market orders.
        
        Buy orders: Price moves UP (worse for you)
        Sell orders: Price moves DOWN (worse for you)
        """
        slippage = price * self.slippage_pct
        
        if side == OrderSide.BUY:
            return price + slippage
        else:  # SELL
            return price - slippage
    
    def _limit_order_filled(self, order: Order, current_data: Dict) -> bool:
        """
        Check if limit order would be filled based on current candle.
        
        Logic:
        - Buy limit: Fills if low <= limit_price
        - Sell limit: Fills if high >= limit_price
        """
        if current_data is None:
            return False
        
        if order.side == OrderSide.BUY:
            # Buy limit fills if price went down to our limit
            return current_data['low'] <= order.price
        else:  # SELL
            # Sell limit fills if price went up to our limit
            return current_data['high'] >= order.price
    
    def _execute_paper(self, order: Order, current_price: float) -> Order:
        """
        Execute in paper trading mode (connects to real-time data).
        Similar to backtest but with live data feed.
        """
        # For now, same as backtest
        # In Phase 4, this will use real broker API in paper mode
        return self._execute_backtest(order, current_price, None)
    
    def _execute_live(self, order: Order) -> Order:
        """
        Execute on live broker account.
        
        To be implemented in Phase 4 with broker API integration.
        """
        raise NotImplementedError("Live trading not yet implemented")
    
    def check_stop_loss(
        self,
        position: Dict,
        current_price: float
    ) -> Optional[Order]:
        """
        Check if stop-loss should trigger.
        
        Args:
            position: Current position dictionary
            current_price: Current market price
            
        Returns:
            Exit order if stop-loss triggered, None otherwise
        """
        if position['side'] == 'long':
            if current_price <= position['stop_loss']:
                logger.risk(f"Stop-loss triggered at Rs.{current_price:.2f}")
                return Order(
                    symbol=position['symbol'],
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=position['quantity'],
                    notes="Stop-loss exit"
                )
        
        elif position['side'] == 'short':
            if current_price >= position['stop_loss']:
                logger.risk(f"Stop-loss triggered at Rs.{current_price:.2f}")
                return Order(
                    symbol=position['symbol'],
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=position['quantity'],
                    notes="Stop-loss exit"
                )
        
        return None
    
    def check_take_profit(
        self,
        position: Dict,
        current_price: float
    ) -> Optional[Order]:
        """
        Check if take-profit should trigger.
        
        Args:
            position: Current position dictionary
            current_price: Current market price
            
        Returns:
            Exit order if take-profit triggered, None otherwise
        """
        if position['side'] == 'long':
            if current_price >= position['take_profit']:
                logger.trade(f"Take-profit triggered at Rs.{current_price:.2f}")
                return Order(
                    symbol=position['symbol'],
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=position['quantity'],
                    notes="Take-profit exit"
                )
        
        elif position['side'] == 'short':
            if current_price <= position['take_profit']:
                logger.trade(f"Take-profit triggered at Rs.{current_price:.2f}")
                return Order(
                    symbol=position['symbol'],
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=position['quantity'],
                    notes="Take-profit exit"
                )
        
        return None
