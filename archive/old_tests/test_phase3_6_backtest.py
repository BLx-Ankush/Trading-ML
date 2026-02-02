"""
Phase 3.6: Backtest with 1.5:1 R:R Model

Test new model across thresholds 0.20-0.30
Focus: HDFC (showed 37 trades - highest)
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from test_phase3_backtest import run_integrated_backtest
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Update MLStrategySelector to use new model
import importlib
from src.strategy import ml_strategy_selector
importlib.reload(ml_strategy_selector)

print("\n" + "="*80)
print("PHASE 3.6: BACKTEST WITH 1.5:1 R:R MODEL")
print("="*80)
print("Model: lightgbm_entry_model_1_5_rr.txt")
print("Baseline: 37.14% win rate (vs 23.6% with 2:1 R:R)")
print("Target: 40+ trades, 55%+ WR, >9.10% return")
print("="*80)

# Test on RELIANCE
print("\n" + "="*80)
print("RELIANCE.NS - THRESHOLD SWEEP")
print("="*80)
print(f"{'Threshold':<12} {'Trades':<8} {'Win Rate':<12} {'Return':<12} {'Sharpe':<10} {'Fuzzy->ML'}")
print("-"*80)

# Temporarily modify backtest to use new model
import src.strategy.ml_strategy_selector as ml_sel
original_model_path = 'data/models/lightgbm_entry_model.txt'
new_model_path = 'data/models/lightgbm_entry_model_1_5_rr.txt'

for threshold in [0.20, 0.22, 0.25, 0.27, 0.30]:
    # Modify backtest to use new model by patching
    result = run_integrated_backtest("RELIANCE.NS", threshold=threshold)
    
    # But the backtest hardcodes the model path - need to pass it
    # For now, manually copy the model file
    print(f"NOTE: Using OLD model (2:1 R:R) - need to update backtest code")
    break

print("\n[!] Need to update backtest to accept model_path parameter")
print("="*80)
