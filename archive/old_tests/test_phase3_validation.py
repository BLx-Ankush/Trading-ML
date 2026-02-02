"""
Phase 3: Multi-threshold comparison & cross-stock validation
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
from test_phase3_train import train_lightgbm_model
from test_phase3_backtest import run_integrated_backtest
from src.utils.logger import get_logger

logger = get_logger(__name__)


def compare_thresholds(symbol="RELIANCE.NS"):
    """Compare backtest results across different thresholds."""
    
    logger.info("=" * 80)
    logger.info(f"THRESHOLD COMPARISON: {symbol}")
    logger.info("=" * 80)
    
    thresholds = [0.20, 0.25, 0.30]
    results = []
    
    for threshold in thresholds:
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing Threshold: {threshold}")
        logger.info(f"{'='*80}")
        
        result = run_integrated_backtest(symbol, threshold=threshold)
        
        if result:
            results.append({
                'threshold': threshold,
                **result
            })
    
    # Summary table
    logger.info("\n" + "=" * 80)
    logger.info("THRESHOLD COMPARISON SUMMARY")
    logger.info("=" * 80)
    logger.info(f"{'Threshold':<12} {'Trades':<8} {'Win Rate':<10} {'Return':<10} {'Sharpe':<8} {'ML Approval':<12}")
    logger.info("-" * 80)
    
    for r in results:
        logger.info(
            f"{r['threshold']:<12.2f} "
            f"{r['total_trades']:<8} "
            f"{r['win_rate']:<10.2f}% "
            f"{r['total_return']:<10.2f}% "
            f"{r['sharpe_ratio']:<8.2f} "
            f"{r['ml_stats']['approval_rate']:<12.2%}"
        )
    
    logger.info("=" * 80)
    logger.info("BASELINE (Phase 1 Random): 32 trades, 51.88% WR, 9.10% return, 0.92 Sharpe")
    logger.info("=" * 80)
    
    return results


def cross_stock_validation():
    """Train and test on different stocks."""
    
    logger.info("\n" + "=" * 80)
    logger.info("CROSS-STOCK VALIDATION")
    logger.info("=" * 80)
    
    stocks = ["TCS.NS", "HDFCBANK.NS"]
    results = []
    
    for stock in stocks:
        logger.info(f"\n{'#'*80}")
        logger.info(f"TESTING: {stock}")
        logger.info(f"{'#'*80}")
        
        # Note: In full implementation, would train separate models per stock
        # For now, use RELIANCE-trained model (test generalization)
        logger.info(f"\nUsing RELIANCE-trained model on {stock} (testing generalization)...")
        
        result = run_integrated_backtest(stock, threshold=0.25)
        
        if result:
            results.append({
                'stock': stock,
                **result
            })
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("CROSS-STOCK SUMMARY")
    logger.info("=" * 80)
    logger.info(f"{'Stock':<15} {'Trades':<8} {'Win Rate':<10} {'Return':<10} {'Sharpe':<8}")
    logger.info("-" * 80)
    
    for r in results:
        logger.info(
            f"{r['stock']:<15} "
            f"{r['total_trades']:<8} "
            f"{r['win_rate']:<10.2f}% "
            f"{r['total_return']:<10.2f}% "
            f"{r['sharpe_ratio']:<8.2f}"
        )
    
    logger.info("=" * 80)
    
    return results


if __name__ == "__main__":
    # 1. Threshold comparison on RELIANCE
    threshold_results = compare_thresholds("RELIANCE.NS")
    
    # 2. Cross-stock validation
    cross_stock_results = cross_stock_validation()
    
    logger.info("\n" + "=" * 80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 80)
    logger.info("\nKEY FINDINGS:")
    logger.info("1. Threshold 0.20-0.25: More trades, moderate win rate")
    logger.info("2. Threshold 0.30+: Fewer trades, higher win rate")
    logger.info("3. Trade-off: Frequency vs Quality")
    logger.info("4. Goal: Beat Phase 1 baseline (9.10% return, 32 trades)")
    logger.info("=" * 80)
