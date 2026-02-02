"""
Quick Start Demo - Paper Trading System
Run this to test your setup before going live

This script:
1. Connects to broker in DEMO mode (no credentials needed)
2. Fetches live quotes for your stock universe
3. Simulates placing orders
4. Shows how the system would work in real-time

Author: Phase 6A Trading System
Date: February 2, 2026
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from broker_interface import BrokerInterface
import yaml
import time

def main():
    print("\n" + "="*70)
    print("🚀 PAPER TRADING QUICK START DEMO")
    print("="*70)
    print("\nThis demo shows how your system will work in real-time.")
    print("NO broker credentials needed - running in DEMO mode with free data.")
    print("\nPress Ctrl+C to stop anytime.")
    print("="*70)
    
    # Load your production config
    with open('config/phase6a_production.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize broker in DEMO mode
    print("\n[STEP 1] Connecting to broker...")
    broker = BrokerInterface(broker="demo", paper_trading=True)
    print("✅ Connected in DEMO mode (using free yfinance data)")
    
    # Get your stock universe
    stocks = config['stocks']
    excluded = config['portfolio'].get('excluded_stocks', [])
    active_stocks = [s for s in stocks if s not in excluded]
    
    print(f"\n[STEP 2] Scanning {len(active_stocks)} stocks...")
    print("="*70)
    
    # Fetch live quotes
    quotes = {}
    for symbol in active_stocks:
        try:
            print(f"📊 Fetching {symbol}...", end=" ")
            quote = broker.get_live_quote(symbol)
            
            if quote:
                quotes[symbol] = quote
                print(f"Rs. {quote['last_price']:,.2f} ✅")
            else:
                print("❌ Failed")
            
            time.sleep(0.5)  # Respectful delay
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "="*70)
    print(f"✅ Successfully fetched {len(quotes)}/{len(active_stocks)} quotes")
    
    # Show top 5 by price
    if quotes:
        print("\n[STEP 3] Top 5 Stocks by Price:")
        print("="*70)
        sorted_quotes = sorted(quotes.items(), key=lambda x: x[1]['last_price'], reverse=True)
        
        for i, (symbol, quote) in enumerate(sorted_quotes[:5], 1):
            print(f"{i}. {symbol:<20} Rs. {quote['last_price']:>10,.2f}")
    
    # Simulate a trade
    print("\n[STEP 4] Simulating a trade...")
    print("="*70)
    
    if quotes:
        # Pick the first stock
        test_symbol = list(quotes.keys())[0]
        test_quote = quotes[test_symbol]
        test_quantity = 10
        
        print(f"\n🟢 Simulating BUY order:")
        print(f"   Stock: {test_symbol}")
        print(f"   Quantity: {test_quantity}")
        print(f"   Price: Rs. {test_quote['last_price']:.2f}")
        print(f"   Estimated Cost: Rs. {test_quote['last_price'] * test_quantity:,.2f}")
        
        # Place paper order
        order_id = broker.place_order(
            symbol=test_symbol,
            transaction_type="BUY",
            quantity=test_quantity,
            order_type="MARKET"
        )
        
        if order_id:
            print(f"\n✅ Order executed successfully!")
            print(f"   Order ID: {order_id}")
            
            # Show updated position
            positions = broker.get_positions()
            capital = broker.get_capital()
            
            print(f"\n📈 Current Portfolio:")
            print(f"   Positions: {positions}")
            print(f"   Available Capital: Rs. {capital:,.2f}")
    
    # Summary
    print("\n" + "="*70)
    print("🎉 DEMO COMPLETE!")
    print("="*70)
    print("\nWhat you just saw:")
    print("✅ Real-time quote fetching (via yfinance, ~15 min delay)")
    print("✅ Paper order execution (simulated locally)")
    print("✅ Position tracking (stored in memory)")
    print("✅ Capital management (tracked automatically)")
    
    print("\n📋 Next Steps:")
    print("1. Read PAPER_TRADING_GUIDE.md for full setup")
    print("2. Choose a broker (Zerodha recommended)")
    print("3. Get API credentials")
    print("4. Replace 'demo' with 'zerodha' in code")
    print("5. Run for 2-3 months in paper mode")
    print("6. Deploy small live capital (₹20K) if successful")
    
    print("\n💡 Pro Tip:")
    print("Don't rush to live trading. Paper trade for at least 2 months!")
    print("Your backtest showed 18.70% annual - expect 12-20% in paper trading.")
    
    print("\n" + "="*70)
    print("Happy Trading! 🚀")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Demo stopped by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
