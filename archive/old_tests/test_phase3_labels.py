"""
Phase 3 Step 1: Test Label Creation

Verify that labels are being created correctly by simulating
2:1 R:R outcomes on historical data.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.features.indicators import TechnicalIndicators
from src.ml.label_creator import LabelCreator
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_label_creation():
    """Test label creation on one stock."""
    
    logger.info("=" * 80)
    logger.info("PHASE 3 STEP 1: LABEL CREATION TEST")
    logger.info("=" * 80)
    
    # Load data
    symbol = "RELIANCE.NS"
    logger.info(f"\nLoading data for {symbol}...")
    
    loader = DataLoader()
    raw_data = loader.fetch_yahoo_data(symbol, "2020-01-01", "2024-12-31")
    
    # Clean and add indicators
    data = DataProcessor.clean_data(raw_data)
    data = TechnicalIndicators.calculate_all_indicators(data)
    
    logger.info(f"Loaded {len(data)} rows")
    
    # Create labels
    logger.info("\nCreating labels (simulating 2:1 R:R outcomes)...")
    label_creator = LabelCreator(
        risk_multiplier=2.0,  # Stop = entry - 2× ATR
        reward_multiplier=4.0,  # Target = entry + 4× ATR (2:1 R:R)
        max_holding_days=20
    )
    
    labels, stats = label_creator.create_labels(data)
    
    # Show sample labels
    logger.info("\n" + "=" * 80)
    logger.info("SAMPLE LABELS (First 20 with clear outcomes):")
    logger.info("=" * 80)
    
    sample_data = pd.DataFrame({
        'date': data.index,
        'close': data['close'],
        'atr': data['atr'],
        'label': labels
    })
    
    valid_samples = sample_data[sample_data['label'].notna()].head(20)
    
    for idx, row in valid_samples.iterrows():
        outcome = "WIN" if row['label'] == 1 else "LOSS"
        logger.info(f"{row['date'].strftime('%Y-%m-%d')} | "
                   f"Close: {row['close']:.2f} | "
                   f"ATR: {row['atr']:.2f} | "
                   f"{outcome}")
    
    # Statistics
    logger.info("\n" + "=" * 80)
    logger.info("LABEL STATISTICS:")
    logger.info("=" * 80)
    logger.info(f"Total potential entries: {len(labels)}")
    logger.info(f"Winners (Label = 1): {stats['win_count']} ({stats['win_rate']:.2%})")
    logger.info(f"Losers (Label = 0): {stats['loss_count']} ({stats['loss_rate']:.2%})")
    logger.info(f"Avg bars to win: {stats['avg_bars_to_win']:.1f} days")
    logger.info(f"Avg bars to loss: {stats['avg_bars_to_loss']:.1f} days")
    
    logger.info("\n" + "=" * 80)
    logger.info("INTERPRETATION:")
    logger.info("=" * 80)
    
    if stats['win_rate'] >= 0.40:
        logger.info(f"[OK] Win rate {stats['win_rate']:.1%} is REALISTIC for 2:1 R:R")
        logger.info("  (40-45% win rate with 2:1 R:R = profitable system)")
    else:
        logger.info(f"[!] Win rate {stats['win_rate']:.1%} is LOW")
        logger.info("  May need to adjust R:R parameters")
    
    if stats['avg_bars_to_win'] < stats['avg_bars_to_loss']:
        logger.info(f"[OK] Winners close faster ({stats['avg_bars_to_win']:.1f}d) than losers ({stats['avg_bars_to_loss']:.1f}d)")
        logger.info("  This is GOOD - shows momentum edge")
    else:
        logger.info(f"[!] Winners take longer - may indicate mean-reversion behavior")
    
    logger.info("\n" + "=" * 80)
    logger.info("NEXT STEP: Feature engineering (Phase 3 Step 2)")
    logger.info("=" * 80)
    
    return labels, stats


if __name__ == "__main__":
    test_label_creation()
