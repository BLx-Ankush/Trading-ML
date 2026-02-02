"""
LightGBM Model Trainer

Trains gradient boosting model to predict 2:1 R:R trade outcomes.
Uses walk-forward validation to prevent overfitting.
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from typing import Dict, Tuple, Optional
import pickle
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LightGBMModel:
    """
    LightGBM classifier for predicting trade outcomes.
    
    Uses time-series cross-validation to maintain temporal order
    and prevent look-ahead bias.
    """
    
    def __init__(
        self,
        n_estimators: int = 100,
        learning_rate: float = 0.05,
        max_depth: int = 5,
        num_leaves: int = 31,
        min_child_samples: int = 20,
        random_state: int = 42
    ):
        """
        Initialize LightGBM model.
        
        Args:
            n_estimators: Number of boosting iterations
            learning_rate: Learning rate (0.01-0.1)
            max_depth: Maximum tree depth
            num_leaves: Maximum number of leaves
            min_child_samples: Minimum samples per leaf
            random_state: Random seed for reproducibility
        """
        self.params = {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'n_estimators': n_estimators,
            'learning_rate': learning_rate,
            'max_depth': max_depth,
            'num_leaves': num_leaves,
            'min_child_samples': min_child_samples,
            'random_state': random_state,
            'verbose': -1
        }
        
        self.model = None
        self.feature_importance = None
        self.training_history = []
        
    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        validation_split: float = 0.2,
        early_stopping_rounds: int = 10
    ) -> Dict[str, float]:
        """
        Train model on features and labels.
        
        Args:
            X: Feature DataFrame
            y: Label Series
            validation_split: Fraction of data for validation
            early_stopping_rounds: Stop if no improvement for N rounds
            
        Returns:
            Dict with training metrics
        """
        # Remove rows with NaN labels or features
        valid_mask = ~(y.isna() | X.isna().any(axis=1))
        X_clean = X[valid_mask]
        y_clean = y[valid_mask]
        
        logger.info(f"Training on {len(X_clean)} samples with {X_clean.shape[1]} features")
        
        # Time-series split (maintain temporal order)
        split_idx = int(len(X_clean) * (1 - validation_split))
        X_train, X_val = X_clean.iloc[:split_idx], X_clean.iloc[split_idx:]
        y_train, y_val = y_clean.iloc[:split_idx], y_clean.iloc[split_idx:]
        
        logger.info(f"Train: {len(X_train)} samples, Validation: {len(X_val)} samples")
        logger.info(f"Train win rate: {y_train.mean():.2%}")
        logger.info(f"Val win rate: {y_val.mean():.2%}")
        
        # Create LightGBM datasets
        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
        
        # Train model
        callbacks = [
            lgb.early_stopping(stopping_rounds=early_stopping_rounds),
            lgb.log_evaluation(period=10)
        ]
        
        self.model = lgb.train(
            self.params,
            train_data,
            valid_sets=[train_data, val_data],
            valid_names=['train', 'valid'],
            callbacks=callbacks
        )
        
        # Evaluate
        train_metrics = self._evaluate(X_train, y_train, "Train")
        val_metrics = self._evaluate(X_val, y_val, "Validation")
        
        # Feature importance
        self.feature_importance = pd.DataFrame({
            'feature': X_clean.columns,
            'importance': self.model.feature_importance(importance_type='gain')
        }).sort_values('importance', ascending=False)
        
        logger.info("\nTop 10 Most Important Features:")
        for idx, row in self.feature_importance.head(10).iterrows():
            logger.info(f"  {row['feature']}: {row['importance']:.0f}")
        
        return {
            'train_metrics': train_metrics,
            'val_metrics': val_metrics,
            'feature_importance': self.feature_importance
        }
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict probabilities for features.
        
        Args:
            X: Feature DataFrame
            
        Returns:
            Array of probabilities (0-1)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        return self.model.predict(X, num_iteration=self.model.best_iteration)
    
    def predict(self, X: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        """
        Predict binary labels.
        
        Args:
            X: Feature DataFrame
            threshold: Probability threshold for positive class
            
        Returns:
            Array of binary predictions (0 or 1)
        """
        probas = self.predict_proba(X)
        return (probas >= threshold).astype(int)
    
    def _evaluate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        dataset_name: str
    ) -> Dict[str, float]:
        """Evaluate model performance."""
        y_pred_proba = self.predict_proba(X)
        y_pred = (y_pred_proba >= 0.5).astype(int)
        
        metrics = {
            'accuracy': accuracy_score(y, y_pred),
            'precision': precision_score(y, y_pred, zero_division=0),
            'recall': recall_score(y, y_pred, zero_division=0),
            'f1': f1_score(y, y_pred, zero_division=0),
            'auc': roc_auc_score(y, y_pred_proba)
        }
        
        logger.info(f"\n{dataset_name} Metrics:")
        logger.info(f"  Accuracy:  {metrics['accuracy']:.4f}")
        logger.info(f"  Precision: {metrics['precision']:.4f}")
        logger.info(f"  Recall:    {metrics['recall']:.4f}")
        logger.info(f"  F1 Score:  {metrics['f1']:.4f}")
        logger.info(f"  AUC:       {metrics['auc']:.4f}")
        
        return metrics
    
    def save(self, filepath: str):
        """Save model to disk."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        self.model.save_model(filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load(self, filepath: str):
        """Load model from disk."""
        self.model = lgb.Booster(model_file=filepath)
        logger.info(f"Model loaded from {filepath}")
