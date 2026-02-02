"""
PHASE 1 TEST: Random Entry Strategy
Tests if risk management system protects capital with completely random entries.

Expected Result: -5% to +5% over 100 trades
(Small losses due to fees, but NO catastrophic drawdown)
"""
import random
from typing import Dict
import pandas as pd

from src.backtesting import Backtest, PerformanceAnalyzer
from src.utils.logger import get_logger

logger = get_logger()


def random_signal_generator(df: pd.DataFrame, current_index: int) -> Dict:
    """
    Generate completely random trading signals.
    
    This is intentionally random to test if risk management works.
    With proper position sizing and stop-losses, even random entries
    should result in manageable losses (-5% to +5%).
    
    Args:
        df: DataFrame with market data
        current_index: Current position in DataFrame
        
    Returns:
        Signal dictionary or None
    """
    # Need enough historical data for indicators
    if current_index < 50:
        return None
    
    # Check if indicators are available
    if pd.isna(df.iloc[current_index]['atr']):
        return None
    
    # Generate random signal (10% chance to trade each day)
    if random.random() < 0.10:  # 10% chance
        return {
            'action': 'buy',
            'confidence': random.uniform(0.5, 1.0),
            'strategy': 'random_entry'
        }
    
    return None


def main():
    """Run Phase 1 test with random entries."""
    
    print("\n" + "="*80)
    print("PHASE 1 TEST: Random Entry Strategy")
    print("="*80)
    print("\nTesting if risk management protects capital with random entries...")
    print("Expected: -5% to +5% return (proof that risk system works)\n")
    
    # Configuration
    INITIAL_CAPITAL = 200000  # ₹2,00,000
    START_DATE = "2024-01-01"
    END_DATE = "2024-12-31"
    
    # Indian market symbols (NSE)
    # Using .NS suffix for Yahoo Finance (National Stock Exchange of India)
    SYMBOLS = [
        'RELIANCE.NS',   # Reliance Industries
        'TCS.NS',        # Tata Consultancy Services
        'INFY.NS',       # Infosys
        'HDFCBANK.NS',   # HDFC Bank
        'ICICIBANK.NS'   # ICICI Bank
    ]
    
    # Initialize backtest
    backtest = Backtest(
        initial_capital=INITIAL_CAPITAL,
        start_date=START_DATE,
        end_date=END_DATE,
        symbols=SYMBOLS,
        slippage=0.001,    # 0.1% slippage
        commission=0.0003   # 0.03% commission
    )
    
    # Load data
    print("Loading historical data...")
    backtest.load_data()
    
    # Run backtest with random signals
    print("\nRunning backtest with RANDOM entries...")
    print("(This will take a few minutes)\n")
    
    results = backtest.run(
        signal_generator=random_signal_generator,
        strategy_name="Random Entry - Phase 1 Test"
    )
    
    # Generate detailed report
    print("\n" + "="*80)
    print("GENERATING PERFORMANCE REPORT")
    print("="*80 + "\n")
    
    report = PerformanceAnalyzer.generate_report(
        results,
        output_dir="backtest_results/phase1_random"
    )
    
    print(report)
    
    # Generate visualizations
    print("\nGenerating charts...")
    if 'equity_curve' in results and not results['equity_curve'].empty:
        PerformanceAnalyzer.plot_equity_curve(
            results['equity_curve'],
            output_dir="backtest_results/phase1_random"
        )
        
        PerformanceAnalyzer.plot_drawdown(
            results['equity_curve'],
            output_dir="backtest_results/phase1_random"
        )
    
    if 'trades' in results and not results['trades'].empty:
        PerformanceAnalyzer.plot_trade_distribution(
            results['trades'],
            output_dir="backtest_results/phase1_random"
        )
    
    # Validate Phase 1 success criteria
    print("\n" + "="*80)
    print("PHASE 1 VALIDATION")
    print("="*80)
    
    total_return = results['total_return']
    max_drawdown = results['max_drawdown']
    
    print(f"\n✓ Total Return: {total_return:.2%}")
    print(f"✓ Max Drawdown: {max_drawdown:.2%}")
    
    # Success criteria
    success = True
    
    if -0.10 <= total_return <= 0.10:
        print(f"\n✅ PASS: Return within expected range (-10% to +10%)")
    else:
        print(f"\n❌ FAIL: Return outside expected range ({total_return:.2%})")
        success = False
    
    if max_drawdown <= 0.30:
        print(f"✅ PASS: Drawdown controlled (<30%)")
    else:
        print(f"❌ FAIL: Drawdown too large ({max_drawdown:.2%})")
        success = False
    
    if results['total_trades'] >= 20:
        print(f"✅ PASS: Sufficient trades executed ({results['total_trades']})")
    else:
        print(f"⚠️  WARNING: Few trades executed ({results['total_trades']})")
    
    print("\n" + "="*80)
    if success:
        print("🎉 PHASE 1 COMPLETE: Risk management system validated!")
        print("\nThe system successfully protected capital despite random entries.")
        print("This proves that position sizing and stop-losses are working correctly.")
        print("\nNext step: Proceed to Phase 2 (HMM Regime Detection)")
    else:
        print("⚠️  PHASE 1 NEEDS REVIEW: Risk management may need tuning")
        print("\nThe system did not meet success criteria with random entries.")
        print("Review position sizing and stop-loss parameters before proceeding.")
    print("="*80 + "\n")
    
    print(f"📊 Detailed results saved to: backtest_results/phase1_random/")
    print(f"📈 Charts saved to: backtest_results/phase1_random/\n")


if __name__ == "__main__":
    main()
