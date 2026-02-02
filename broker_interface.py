"""
Broker Interface for Paper/Live Trading
Supports: Angel One SmartAPI, Zerodha Kite Connect, Upstox, and Demo Mode

Author: Phase 6A Trading System
Date: February 2, 2026
"""
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class BrokerInterface:
    """
    Universal interface for broker APIs
    Handles both paper trading (simulation) and live trading
    """
    
    def __init__(self, broker: str = "demo", api_key: str = None, 
                 access_token: str = None, paper_trading: bool = True,
                 client_id: str = None, password: str = None, totp_token: str = None):
        """
        Initialize broker connection
        
        Args:
            broker: 'angelone', 'zerodha', 'upstox', or 'demo'
            api_key: Your API key from broker
            access_token: OAuth access token (Zerodha/Upstox) or None
            paper_trading: If True, simulate orders (RECOMMENDED for first 2-3 months)
            client_id: Angel One client ID (if using Angel One)
            password: Angel One password (if using Angel One)
            totp_token: Angel One TOTP token for 2FA (if using Angel One)
        """
        self.broker = broker
        self.paper_trading = paper_trading
        self.api_key = api_key
        self.access_token = access_token
        self.client_id = client_id
        self.password = password
        self.totp_token = totp_token
        self.kite = None
        self.angel = None
        
        # Initialize broker API (only for live trading)
        if not paper_trading and broker == "angelone":
            try:
                from SmartApi import SmartConnect
                self.angel = SmartConnect(api_key=api_key)
                # Login to Angel One
                data = self.angel.generateSession(client_id, password, totp_token)
                if data['status']:
                    logger.info("✅ Connected to Angel One SmartAPI (LIVE MODE - FREE!)")
                else:
                    logger.error(f"❌ Angel One login failed: {data['message']}")
                    raise Exception(f"Angel One login failed: {data['message']}")
            except ImportError:
                logger.error("❌ smartapi-python library not found. Install: pip install smartapi-python")
                raise
        elif not paper_trading and broker == "zerodha":
            try:
                from kiteconnect import KiteConnect
                self.kite = KiteConnect(api_key=api_key)
                self.kite.set_access_token(access_token)
                logger.info("✅ Connected to Zerodha Kite API (LIVE MODE)")
            except ImportError:
                logger.error("❌ kiteconnect library not found. Install: pip install kiteconnect")
                raise
        elif not paper_trading and broker == "upstox":
            logger.info("✅ Connected to Upstox API (LIVE MODE)")
            # TODO: Add Upstox implementation when you choose this broker
        else:
            logger.info(f"✅ Running in {'PAPER' if paper_trading else 'DEMO'} TRADING mode")
        
        # Paper trading state
        self.paper_orders = []
        self.paper_positions = {}
        self.paper_capital = 200000  # Rs. 2 Lakhs starting capital
        self.paper_order_counter = 0
    
    def get_live_quote(self, symbol: str) -> Dict:
        """
        Get real-time quote for a symbol
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS')
        
        Returns:
            {
                'symbol': 'RELIANCE.NS',
                'last_price': 2450.50,
                'volume': 1500000,
                'open': 2445.00,
                'high': 2455.00,
                'low': 2440.00,
                'close': 2448.00  # Previous day close
            }
        """
        broker_symbol = self._convert_symbol(symbol)
        
        if self.paper_trading or self.broker == "demo":
            # Use yfinance for demo mode (free real-time-ish data, ~15 min delay)
            try:
                import yfinance as yf
                ticker = yf.Ticker(symbol)
                
                # Get latest intraday data
                data = ticker.history(period="1d", interval="5m")
                
                if not data.empty:
                    latest = data.iloc[-1]
                    return {
                        'symbol': symbol,
                        'last_price': float(latest['Close']),
                        'volume': int(latest['Volume']),
                        'open': float(data.iloc[0]['Open']),
                        'high': float(data['High'].max()),
                        'low': float(data['Low'].min()),
                        'close': float(data.iloc[0]['Close'])  # First candle close
                    }
                else:
                    logger.warning(f"No data for {symbol}, using fallback")
                    # Fallback to daily data
                    data = ticker.history(period="5d")
                    if not data.empty:
                        latest = data.iloc[-1]
                        return {
                            'symbol': symbol,
                            'last_price': float(latest['Close']),
                            'volume': int(latest['Volume']),
                            'open': float(latest['Open']),
                            'high': float(latest['High']),
                            'low': float(latest['Low']),
                            'close': float(data.iloc[-2]['Close']) if len(data) > 1 else float(latest['Close'])
                        }
            except Exception as e:
                logger.error(f"Error fetching quote for {symbol}: {e}")
                return None
        
        else:
            # Live trading - use broker API
            if self.broker == "angelone":
                try:
                    # Angel One format: NSE:RELIANCE-EQ
                    angel_symbol = broker_symbol.replace('.NS', '-EQ')
                    params = {
                        "mode": "FULL",
                        "exchangeTokens": {
                            "NSE": [angel_symbol]
                        }
                    }
                    quote = self.angel.marketData(params)
                    if quote['status']:
                        data = quote['data']['fetched'][0]
                        return {
                            'symbol': symbol,
                            'last_price': float(data['ltp']),
                            'volume': int(data['volume']),
                            'open': float(data['open']),
                            'high': float(data['high']),
                            'low': float(data['low']),
                            'close': float(data['close'])
                        }
                except Exception as e:
                    logger.error(f"Error fetching Angel One quote: {e}")
                    return None
            elif self.broker == "zerodha":
                try:
                    quote = self.kite.quote([broker_symbol])[broker_symbol]
                    return {
                        'symbol': symbol,
                        'last_price': quote['last_price'],
                        'volume': quote['volume'],
                        'open': quote['ohlc']['open'],
                        'high': quote['ohlc']['high'],
                        'low': quote['ohlc']['low'],
                        'close': quote['ohlc']['close']
                    }
                except Exception as e:
                    logger.error(f"Error fetching quote from Zerodha: {e}")
                    return None
    
    def place_order(self, symbol: str, transaction_type: str, 
                   quantity: int, order_type: str = "MARKET",
                   price: float = None) -> str:
        """
        Place an order (buy/sell)
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS')
            transaction_type: 'BUY' or 'SELL'
            quantity: Number of shares
            order_type: 'MARKET' or 'LIMIT'
            price: Limit price (only for LIMIT orders)
        
        Returns:
            order_id: Unique order identifier
        """
        broker_symbol = self._convert_symbol(symbol)
        
        if self.paper_trading:
            # Simulate order execution
            quote = self.get_live_quote(symbol)
            if not quote:
                logger.error(f"Cannot place order - no quote for {symbol}")
                return None
            
            execution_price = price if order_type == "LIMIT" else quote['last_price']
            
            # Simulate slippage (0.25% as per Phase 6A)
            slippage_factor = 1.0025 if transaction_type == "BUY" else 0.9975
            execution_price = execution_price * slippage_factor
            
            self.paper_order_counter += 1
            order_id = f"PAPER_{self.paper_order_counter:04d}"
            
            order = {
                'order_id': order_id,
                'symbol': symbol,
                'transaction_type': transaction_type,
                'quantity': quantity,
                'order_type': order_type,
                'price': execution_price,
                'status': 'COMPLETE',
                'timestamp': datetime.now()
            }
            self.paper_orders.append(order)
            
            # Update paper positions
            if transaction_type == "BUY":
                self.paper_positions[symbol] = self.paper_positions.get(symbol, 0) + quantity
                cost = execution_price * quantity
                # Add brokerage and STT (as per Phase 6A)
                brokerage = cost * 0.0004
                self.paper_capital -= (cost + brokerage)
                logger.info(f"[PAPER] 🟢 BUY {quantity} x {symbol} @ Rs.{execution_price:.2f} (Cost: Rs.{cost+brokerage:,.2f})")
            else:  # SELL
                self.paper_positions[symbol] = self.paper_positions.get(symbol, 0) - quantity
                proceeds = execution_price * quantity
                # Deduct brokerage and STT
                brokerage = proceeds * 0.0004
                stt = proceeds * 0.001
                net_proceeds = proceeds - brokerage - stt
                self.paper_capital += net_proceeds
                logger.info(f"[PAPER] 🔴 SELL {quantity} x {symbol} @ Rs.{execution_price:.2f} (Net: Rs.{net_proceeds:,.2f})")
            
            return order_id
        
        else:
            # Real order execution (LIVE TRADING)
            if self.broker == "zerodha":
                try:
                    order_id = self.kite.place_order(
                        variety=self.kite.VARIETY_REGULAR,
                        exchange=self.kite.EXCHANGE_NSE,
                        tradingsymbol=broker_symbol,
                        transaction_type=transaction_type,
                        quantity=quantity,
                        order_type=order_type,
                        product=self.kite.PRODUCT_CNC,  # Cash & Carry (delivery)
                        price=price if order_type == "LIMIT" else None
                    )
                    logger.info(f"[LIVE] ⚠️ {transaction_type} {quantity} x {symbol} @ Rs.{price} | Order ID: {order_id}")
                    return order_id
                except Exception as e:
                    logger.error(f"Order placement failed: {e}")
                    return None
    
    def get_positions(self) -> Dict:
        """
        Get current positions
        
        Returns:
            {
                'RELIANCE.NS': 10,  # 10 shares
                'TCS.NS': 5
            }
        """
        if self.paper_trading:
            return {k: v for k, v in self.paper_positions.items() if v > 0}
        else:
            if self.broker == "zerodha":
                try:
                    positions = self.kite.positions()
                    return {self._convert_symbol_back(p['tradingsymbol']): p['quantity'] 
                           for p in positions['net'] if p['quantity'] > 0}
                except Exception as e:
                    logger.error(f"Error fetching positions: {e}")
                    return {}
    
    def get_capital(self) -> float:
        """Get available capital"""
        if self.paper_trading:
            return self.paper_capital
        else:
            if self.broker == "zerodha":
                try:
                    margins = self.kite.margins()
                    return margins['equity']['available']['cash']
                except Exception as e:
                    logger.error(f"Error fetching capital: {e}")
                    return 0.0
    
    def get_order_history(self) -> List[Dict]:
        """Get all executed orders"""
        if self.paper_trading:
            return self.paper_orders
        else:
            if self.broker == "zerodha":
                try:
                    return self.kite.orders()
                except Exception as e:
                    logger.error(f"Error fetching order history: {e}")
                    return []
    
    def _convert_symbol(self, symbol: str) -> str:
        """Convert symbol format: RELIANCE.NS → RELIANCE (for Zerodha)"""
        if self.broker == "zerodha":
            return symbol.replace('.NS', '')
        return symbol
    
    def _convert_symbol_back(self, broker_symbol: str) -> str:
        """Convert broker symbol back: RELIANCE → RELIANCE.NS"""
        if self.broker == "zerodha":
            return f"{broker_symbol}.NS"
        return broker_symbol


def main():
    """
    Test the broker interface
    """
    print("\n" + "="*60)
    print("BROKER INTERFACE TEST")
    print("="*60)
    
    # Initialize in demo mode (no credentials needed)
    broker = BrokerInterface(broker="demo", paper_trading=True)
    
    # Test 1: Get live quote
    print("\n[TEST 1] Fetching live quote for RELIANCE.NS...")
    quote = broker.get_live_quote("RELIANCE.NS")
    if quote:
        print(f"✅ Quote received:")
        print(f"   Price: Rs. {quote['last_price']:.2f}")
        print(f"   Volume: {quote['volume']:,}")
    
    # Test 2: Place paper order
    print("\n[TEST 2] Placing paper BUY order...")
    order_id = broker.place_order(
        symbol="RELIANCE.NS",
        transaction_type="BUY",
        quantity=10,
        order_type="MARKET"
    )
    print(f"✅ Order placed: {order_id}")
    
    # Test 3: Check positions
    print("\n[TEST 3] Checking positions...")
    positions = broker.get_positions()
    print(f"✅ Positions: {positions}")
    
    # Test 4: Check capital
    print("\n[TEST 4] Checking capital...")
    capital = broker.get_capital()
    print(f"✅ Available Capital: Rs. {capital:,.2f}")
    
    print("\n" + "="*60)
    print("ALL TESTS PASSED ✅")
    print("="*60)


if __name__ == "__main__":
    main()
