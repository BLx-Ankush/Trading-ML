"""
Phase 3 Step 2: Test Feature Engineering

Create ML features from technical indicators and verify
they are properly calculated and normalized.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.features.indicators import TechnicalIndicators
from src.ml.feature_engineer import FeatureEngineer
from src.ml.label_creator import LabelCreator
from src.models.hmm_regime import RegimeDetector
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_feature_engineering():
    """Test feature creation on one stock."""
    
    logger.info("=" * 80)
    logger.info("PHASE 3 STEP 2: FEATURE ENGINEERING TEST")
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
    
    # Load HMM regime detector (if available)
    logger.info("\nLoading HMM regime model...")
    regime_detector = RegimeDetector(n_states=3)
    
    try:
        regime_detector.load('data/models/hmm_regime_model.pkl')
        _, regimes = regime_detector.predict(data)
        logger.info(f"Regime distribution: {pd.Series(regimes).value_counts().to_dict()}")
    except FileNotFoundError:
        logger.info("HMM model not found, proceeding without regime features")
        regimes = None
    
    # Create features
    logger.info("\nCreating ML features...")
    feature_engineer = FeatureEngineer()
    features = feature_engineer.create_features(data, regime=pd.Series(regimes, index=data.index) if regimes is not None else None)
    
    logger.info(f"Created {len(features.columns)} features")
    
    # Show sample features
    logger.info("\n" + "=" * 80)
    logger.info("SAMPLE FEATURES (Row 100):")
    logger.info("=" * 80)
    
    sample_row = features.iloc[100]
    for feature_name, value in sample_row.items():
        if pd.notna(value):
            logger.info(f"  {feature_name:25s}: {value:8.4f}")
    
    # Check for NaN values
    nan_counts = features.isna().sum()
    logger.info("\n" + "=" * 80)
    logger.info("NaN VALUE CHECK:")
    logger.info("=" * 80)
    
    total_nans = nan_counts.sum()
    if total_nans > 0:
        logger.info(f"Total NaN values: {total_nans}")
        logger.info("\nFeatures with NaN values:")
        for feature, count in nan_counts[nan_counts > 0].items():
            pct = (count / len(features)) * 100
            logger.info(f"  {feature:25s}: {count:4d} ({pct:5.1f}%)")
    else:
        logger.info("No NaN values found - all features valid!")
    
    # Feature statistics
    logger.info("\n" + "=" * 80)
    logger.info("FEATURE STATISTICS:")
    logger.info("=" * 80)
    
    logger.info(f"Total rows: {len(features)}")
    logger.info(f"Total features: {len(features.columns)}")
    logger.info(f"Valid rows (no NaN): {len(features.dropna())}")
    logger.info(f"Feature coverage: {(len(features.dropna()) / len(features)) * 100:.1f}%")
    
    # Create labels for integration test
    logger.info("\n" + "=" * 80)
    logger.info("INTEGRATION TEST: Features + Labels")
    logger.info("=" * 80)
    
    label_creator = LabelCreator()
    labels, _ = label_creator.create_labels(data)
    
    # Combine features and labels
    combined = pd.concat([features, labels.rename('label')], axis=1)
    combined_clean = combined.dropna()
    
    logger.info(f"Rows with both features and labels: {len(combined_clean)}")
    logger.info(f"Win rate in labeled data: {combined_clean['label'].mean():.2%}")
    
    logger.info("\n" + "=" * 80)
    logger.info("READY FOR MODEL TRAINING")
    logger.info("=" * 80)
    logger.info(f"Training samples available: {len(combined_clean)}")
    logger.info(f"Feature dimension: {len(features.columns)}")
    logger.info("\nNEXT STEP: Model training (Phase 3 Step 3)")
    logger.info("=" * 80)
    
    return features, labels


if __name__ == "__main__":
    test_feature_engineering()
