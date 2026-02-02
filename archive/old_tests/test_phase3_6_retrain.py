"""
Phase 3.6: Retrain LightGBM with 1.5:1 R:R Ratio

Strategy: Lower R:R = Higher win rate baseline + More trades
Target: 45+ trades, 55%+ WR, >9.10% return
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
import numpy as np
from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.features.indicators import TechnicalIndicators
from src.ml.feature_engineer import FeatureEngineer
from src.ml.label_creator import LabelCreator
from src.ml.lightgbm_model import LightGBMModel
from src.models.hmm_regime import RegimeDetector
from src.utils.logger import get_logger

logger = get_logger(__name__)


def train_with_new_rr():
    """Train LightGBM with 1.5:1 R:R ratio."""
    
    logger.info("=" * 80)
    logger.info("PHASE 3.6: RETRAIN WITH 1.5:1 R:R RATIO")
    logger.info("Previous: 2:1 R:R - 23.6% baseline win rate - 60% final WR, 23 trades")
    logger.info("New Goal: 1.5:1 R:R - ~35% baseline win rate - 55% final WR, 45+ trades")
    logger.info("=" * 80)
    
    # Load data
    symbol = "RELIANCE.NS"
    logger.info(f"\nLoading data for {symbol}...")
    
    loader = DataLoader()
    raw_data = loader.fetch_yahoo_data(symbol, "2020-01-01", "2024-12-31")
    
    # Process data
    data = DataProcessor.clean_data(raw_data)
    data = TechnicalIndicators.calculate_all_indicators(data)
    
    logger.info(f"Loaded {len(data)} rows")
    
    # Load regime detector
    logger.info("\nLoading HMM regime model...")
    regime_detector = RegimeDetector(n_states=3)
    
    try:
        regime_detector.load('data/models/hmm_regime_model.pkl')
        _, regimes = regime_detector.predict(data)
    except FileNotFoundError:
        logger.info("HMM model not found, proceeding without regime features")
        regimes = None
    
    # Create features
    logger.info("\nCreating features...")
    feature_engineer = FeatureEngineer()
    features = feature_engineer.create_features(
        data, 
        regime=pd.Series(regimes, index=data.index) if regimes is not None else None
    )
    
    # Create labels with 1.5:1 R:R
    logger.info("\nCreating labels with 1.5:1 R:R ratio...")
    logger.info("  Stop: Entry - 2.0 × ATR")
    logger.info("  Target: Entry + 3.0 × ATR (1.5:1 ratio)")
    
    label_creator = LabelCreator(
        risk_multiplier=2.0,      # Stop at 2 ATR
        reward_multiplier=3.0,     # Target at 3 ATR (1.5:1 R:R)
        max_holding_days=20
    )
    labels, label_stats = label_creator.create_labels(data)
    
    # Count winners/losers
    winners = (labels == 1).sum()
    losers = (labels == 0).sum()
    total = winners + losers
    win_rate = winners / total if total > 0 else 0
    
    logger.info(f"\nLabel Statistics:")
    logger.info(f"  Winners: {winners} ({win_rate:.2%})")
    logger.info(f"  Losers: {losers} ({1-win_rate:.2%})")
    logger.info(f"  Baseline win rate: {win_rate:.2%}")
    logger.info(f"  (Previous 2:1 R:R baseline: 23.6%)")
    
    # Combine and clean
    logger.info("\nPreparing training data...")
    X = features
    y = labels
    
    # Remove NaN rows
    valid_mask = ~(y.isna() | X.isna().any(axis=1))
    X_clean = X[valid_mask]
    y_clean = y[valid_mask]
    
    logger.info(f"Training samples: {len(X_clean)}")
    logger.info(f"Features: {X_clean.shape[1]}")
    logger.info(f"Baseline win rate: {y_clean.mean():.2%}")
    
    # Train model
    logger.info("\n" + "=" * 80)
    logger.info("TRAINING LIGHTGBM MODEL (1.5:1 R:R)")
    logger.info("=" * 80)
    
    model = LightGBMModel(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=5,
        num_leaves=31,
        min_child_samples=20
    )
    
    training_results = model.train(
        X_clean, 
        y_clean,
        validation_split=0.2,
        early_stopping_rounds=10
    )
    
    # Feature importance
    logger.info("\n" + "=" * 80)
    logger.info("TOP 15 MOST IMPORTANT FEATURES")
    logger.info("=" * 80)
    
    for idx, row in training_results['feature_importance'].head(15).iterrows():
        logger.info(f"  {row['feature']:25s}: {row['importance']:8.0f}")
    
    # Analyze predictions on validation set
    logger.info("\n" + "=" * 80)
    logger.info("PREDICTION ANALYSIS")
    logger.info("=" * 80)
    
    # Get validation split
    split_idx = int(len(X_clean) * 0.8)
    X_val = X_clean.iloc[split_idx:]
    y_val = y_clean.iloc[split_idx:]
    
    # Predict probabilities
    probas = model.predict_proba(X_val)
    
    logger.info(f"Validation samples: {len(X_val)}")
    logger.info(f"Probability range: {probas.min():.3f} to {probas.max():.3f}")
    logger.info(f"Mean probability: {probas.mean():.3f}")
    logger.info(f"Median probability: {np.median(probas):.3f}")
    
    # Threshold analysis
    logger.info("\n" + "=" * 80)
    logger.info("THRESHOLD ANALYSIS (FOCUS: 0.20-0.25)")
    logger.info("=" * 80)
    
    thresholds = [0.15, 0.20, 0.22, 0.25, 0.27, 0.30]
    
    for threshold in thresholds:
        predictions = (probas >= threshold).astype(int)
        selected = predictions.sum()
        
        if selected > 0:
            selected_labels = y_val[predictions == 1]
            win_rate = selected_labels.mean()
            
            # Extrapolate to full backtest
            extrapolated_trades = int(selected / len(y_val) * len(X_clean))
            
            logger.info(f"Threshold {threshold:.2f}: {selected:3d} val ({selected/len(y_val)*100:5.1f}%), WR: {win_rate:5.2%}, Extrapolated: ~{extrapolated_trades} trades")
        else:
            logger.info(f"Threshold {threshold:.2f}:   0 trades")
    
    # Save model
    logger.info("\n" + "=" * 80)
    logger.info("SAVING MODEL")
    logger.info("=" * 80)
    
    model.save('data/models/lightgbm_entry_model_1_5_rr.txt')
    
    logger.info("\n" + "=" * 80)
    logger.info("TRAINING COMPLETE")
    logger.info("=" * 80)
    logger.info("\nKey Results:")
    logger.info(f"  Train AUC: {training_results['train_metrics']['auc']:.4f}")
    logger.info(f"  Val AUC: {training_results['val_metrics']['auc']:.4f}")
    logger.info(f"  Val Precision: {training_results['val_metrics']['precision']:.4f}")
    logger.info(f"  Val Recall: {training_results['val_metrics']['recall']:.4f}")
    logger.info(f"  Baseline WR: {y_clean.mean():.2%} (vs 23.6% with 2:1 R:R)")
    logger.info("\nNEXT STEP: Backtest with thresholds 0.20-0.25")
    logger.info("TARGET: 40+ trades, 55%+ win rate, >9.10% return")
    logger.info("=" * 80)
    
    return model, training_results


if __name__ == "__main__":
    train_with_new_rr()
