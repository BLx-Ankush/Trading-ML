"""
Phase 3 Step 3: Train LightGBM Model

Train ML model to predict 2:1 R:R outcomes using engineered features.
Uses time-series split to prevent look-ahead bias.
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


def train_lightgbm_model():
    """Train LightGBM on single stock."""
    
    logger.info("=" * 80)
    logger.info("PHASE 3 STEP 3: LIGHTGBM MODEL TRAINING")
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
    
    # Create labels
    logger.info("Creating labels...")
    label_creator = LabelCreator(
        risk_multiplier=2.0,
        reward_multiplier=4.0,
        max_holding_days=20
    )
    labels, label_stats = label_creator.create_labels(data)
    
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
    logger.info("TRAINING LIGHTGBM MODEL")
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
    logger.info("THRESHOLD ANALYSIS")
    logger.info("=" * 80)
    
    thresholds = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
    
    for threshold in thresholds:
        predictions = (probas >= threshold).astype(int)
        selected = predictions.sum()
        
        if selected > 0:
            selected_labels = y_val[predictions == 1]
            win_rate = selected_labels.mean()
            logger.info(f"Threshold {threshold:.2f}: {selected:3d} trades ({selected/len(y_val)*100:5.1f}%), Win Rate: {win_rate:.2%}")
        else:
            logger.info(f"Threshold {threshold:.2f}:   0 trades")
    
    # Save model
    logger.info("\n" + "=" * 80)
    logger.info("SAVING MODEL")
    logger.info("=" * 80)
    
    model.save('data/models/lightgbm_entry_model.txt')
    
    logger.info("\n" + "=" * 80)
    logger.info("TRAINING COMPLETE")
    logger.info("=" * 80)
    logger.info("\nKey Results:")
    logger.info(f"  Train AUC: {training_results['train_metrics']['auc']:.4f}")
    logger.info(f"  Val AUC: {training_results['val_metrics']['auc']:.4f}")
    logger.info(f"  Val Precision: {training_results['val_metrics']['precision']:.4f}")
    logger.info(f"  Val Recall: {training_results['val_metrics']['recall']:.4f}")
    logger.info("\nNEXT STEP: Calibrate threshold and backtest (Phase 3 Step 4)")
    logger.info("=" * 80)
    
    return model, training_results


if __name__ == "__main__":
    train_lightgbm_model()
