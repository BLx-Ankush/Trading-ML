"""
Phase 3.7: Retrain with 1.75:1 R:R Ratio (Compromise)

Strategy: Balance between 2:1 (best discrimination, low trades) and 1.5:1 (poor discrimination, high trades)
Expected: ~30% baseline WR, 52-55% final WR, 30-35 trades, >9.10% return
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
import numpy as np
from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.features.indicators import TechnicalIndicators
from src.ml.label_creator import LabelCreator
from src.ml.feature_engineer import FeatureEngineer
from src.ml.lightgbm_model import LightGBMModel
from src.models.hmm_regime import RegimeDetector
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("PHASE 3.7: RETRAIN WITH 1.75:1 R:R RATIO (COMPROMISE)")
print("="*80)
print("Phase 3.5 (2:1 R:R):   23.6% baseline - 60.87% final WR, 23 trades, 6.59% return")
print("Phase 3.6 (1.5:1 R:R): 37.1% baseline - 48.65% final WR, 37 trades, 6.70% return")
print("Phase 3.7 (1.75:1 R:R): ~30% baseline - 52-55% final WR, 30-35 trades, >9.10% target")
print("="*80)

# Load data
symbol = "RELIANCE.NS"
print(f"\nLoading data for {symbol}...")
loader = DataLoader()
raw_data = loader.fetch_yahoo_data(symbol, start_date="2020-01-01", end_date="2024-12-31")
data = DataProcessor.clean_data(raw_data)
data = TechnicalIndicators.calculate_all_indicators(data)
print(f"Loaded {len(data)} rows")

# Load HMM model and get regimes
print("\nLoading HMM regime model...")
regime_detector = RegimeDetector(n_states=3)
try:
    regime_detector.load('data/models/hmm_regime_model.pkl')
    _, regimes = regime_detector.predict(data)
except:
    print("HMM model not found, proceeding without regime features")
    regimes = None

# Create features (includes ATR needed for labels)
print("\nCreating features...")
feature_engineer = FeatureEngineer()
features = feature_engineer.create_features(
    data,
    regime=pd.Series(regimes, index=data.index) if regimes is not None else None
)

# Merge features back into data, but remove duplicate columns first
# Features from FeatureEngineer might overlap with indicator columns
data_cols = set(data.columns)
features_unique = features[[c for c in features.columns if c not in data_cols]]
data = pd.concat([data, features_unique], axis=1)
print(f"Created {len(features.columns)} engineered features, added {len(features_unique.columns)} unique, total columns: {len(data.columns)}")

# Create labels with 1.75:1 R:R (needs ATR from features)
print("\nCreating labels with 1.75:1 R:R ratio...")
print("  Stop: Entry - 2.0 x ATR")
print("  Target: Entry + 3.5 x ATR (1.75:1 ratio)")
print()

label_creator = LabelCreator(
    risk_multiplier=2.0,      # Stop at 2xATR
    reward_multiplier=3.5,     # Target at 3.5xATR (1.75:1 R:R)
    max_holding_days=20
)
labels, label_stats = label_creator.create_labels(data)

print(f"\nCreated {len(labels)} labels:")

# Count winners and losers manually
winners = (labels == 1).sum()
losers = (labels == 0).sum()

print(f"  Winners (1): {winners} ({winners/len(labels)*100:.2f}%)")
print(f"  Losers (0): {losers} ({losers/len(labels)*100:.2f}%)")

# Calculate average bars to outcome
if 'bars_to_outcome' in label_stats:
    win_bars = label_stats['bars_to_outcome'][labels == 1]
    loss_bars = label_stats['bars_to_outcome'][labels == 0]
    print(f"  Avg bars to win: {win_bars.mean():.1f}")
    print(f"  Avg bars to loss: {loss_bars.mean():.1f}")

print("\nLabel Statistics:")
print(f"  Winners: {winners} ({winners/len(labels)*100:.2f}%)")
print(f"  Losers: {losers} ({losers/len(labels)*100:.2f}%)")
print(f"  Baseline win rate: {winners/len(labels)*100:.2f}%")
print(f"  (2:1 R:R baseline: 23.6%, 1.5:1 R:R baseline: 37.1%)")

# Prepare training data
print("\nPreparing training data...")
data['label'] = labels
data = data.dropna()

# Get feature columns
feature_cols = [col for col in data.columns if col not in 
                ['Open', 'High', 'Low', 'Close', 'Volume', 'Date', 'label', 'bars_to_outcome']]

X = data[feature_cols]
y = data['label']

print(f"Training samples: {len(X)}")
print(f"Features: {len(feature_cols)}")
print(f"Baseline win rate: {y.mean()*100:.2f}%")

# Train model
print("\n" + "="*80)
print("TRAINING LIGHTGBM MODEL (1.75:1 R:R)")
print("="*80)

model = LightGBMModel(
    n_estimators=100,
    learning_rate=0.05,
    max_depth=5
)

train_metrics, val_metrics = model.train(X, y, validation_split=0.2, early_stopping_rounds=10)

print("\nTrain Metrics:")
print(f"  Accuracy:  {train_metrics['accuracy']:.4f}")
print(f"  Precision: {train_metrics['precision']:.4f}")
print(f"  Recall:    {train_metrics['recall']:.4f}")
print(f"  F1 Score:  {train_metrics['f1']:.4f}")
print(f"  AUC:       {train_metrics['auc']:.4f}")

print("\nValidation Metrics:")
print(f"  Accuracy:  {val_metrics['accuracy']:.4f}")
print(f"  Precision: {val_metrics['precision']:.4f}")
print(f"  Recall:    {val_metrics['recall']:.4f}")
print(f"  F1 Score:  {val_metrics['f1']:.4f}")
print(f"  AUC:       {val_metrics['auc']:.4f}")

# Feature importance
print("\nTOP 15 MOST IMPORTANT FEATURES:")
importance = model.model.feature_importances_
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': importance
}).sort_values('importance', ascending=False)

for idx, row in feature_importance.head(15).iterrows():
    print(f"  {row['feature']:<25}: {row['importance']:>8.0f}")

# Threshold analysis
print("\n" + "="*80)
print("THRESHOLD ANALYSIS (FOCUS: 0.22-0.30)")
print("="*80)

# Get validation set
from sklearn.model_selection import train_test_split
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)

# Predict probabilities
val_probs = model.predict_proba(X_val)
print(f"Validation samples: {len(val_probs)}")
print(f"Probability range: {val_probs.min():.3f} to {val_probs.max():.3f}")
print(f"Mean probability: {val_probs.mean():.3f}")
print(f"Median probability: {val_probs.median():.3f}")
print()

for threshold in [0.20, 0.22, 0.25, 0.27, 0.30, 0.35]:
    selected = val_probs >= threshold
    if selected.sum() > 0:
        selected_labels = y_val[selected]
        win_rate = selected_labels.mean() * 100
        extrapolated_trades = int(selected.sum() / 0.2)  # Scale to full dataset
        print(f"Threshold {threshold:.2f}: {selected.sum():>3} val ({selected.sum()/len(val_probs)*100:>5.1f}%), WR: {win_rate:>5.2f}%, Extrapolated: ~{extrapolated_trades} trades")
    else:
        print(f"Threshold {threshold:.2f}: 0 samples selected")

# Save model
print("\n" + "="*80)
print("SAVING MODEL")
print("="*80)

model_path = "data/models/lightgbm_entry_model_1_75_rr.txt"
model.save(model_path)
print(f"Model saved to {model_path}")

print("\n" + "="*80)
print("TRAINING COMPLETE")
print("="*80)

print("\nKey Results:")
print(f"  Train AUC: {train_metrics['auc']:.4f}")
print(f"  Val AUC: {val_metrics['auc']:.4f}")
print(f"  Val Precision: {val_metrics['precision']:.4f}")
print(f"  Val Recall: {val_metrics['recall']:.4f}")
print(f"  Baseline WR: {y.mean()*100:.2f}% (vs 23.6% with 2:1, 37.1% with 1.5:1)")

print("\nNEXT STEP: Backtest with thresholds 0.22-0.30")
print("TARGET: 30-35 trades, 52%+ win rate, >9.10% return")
print("="*80)
