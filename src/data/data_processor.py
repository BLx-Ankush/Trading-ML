"""
Data processing and validation utilities.
"""
import pandas as pd
import numpy as np
from typing import Tuple

from ..utils.logger import get_logger

logger = get_logger()


class DataProcessor:
    """Process and validate market data."""
    
    @staticmethod
    def validate_data(df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Validate OHLCV data quality.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if df.empty:
            return False, "DataFrame is empty"
        
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            return False, f"Missing columns: {missing_cols}"
        
        # Check for negative values
        if (df[['open', 'high', 'low', 'close', 'volume']] < 0).any().any():
            return False, "Negative values found in data"
        
        # Check high >= low
        if (df['high'] < df['low']).any():
            return False, "High < Low found in data"
        
        # Check for missing values
        missing_pct = df[required_cols].isnull().sum() / len(df) * 100
        if (missing_pct > 5).any():
            return False, f"Too many missing values: {missing_pct.to_dict()}"
        
        return True, "Data is valid"
    
    @staticmethod
    def clean_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and prepare data for analysis.
        
        Args:
            df: Raw OHLCV DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        logger.info(f"Cleaning data: {len(df)} rows")
        
        df = df.copy()
        
        # Remove duplicate indices
        df = df[~df.index.duplicated(keep='first')]
        
        # Replace infinity with NaN
        df = df.replace([np.inf, -np.inf], np.nan)
        
        # Forward fill missing values (max 2 days)
        df = df.ffill(limit=2)
        
        # Backward fill if needed
        df = df.bfill(limit=1)
        
        # Drop any remaining NaN rows
        original_len = len(df)
        df = df.dropna()
        dropped = original_len - len(df)
        
        if dropped > 0:
            logger.warning(f"Dropped {dropped} rows with missing data")
        
        # Remove outliers (5 standard deviations) - but more carefully
        for col in ['open', 'high', 'low', 'close']:
            if len(df) > 0:
                mean = df[col].mean()
                std = df[col].std()
                if std > 0:  # Only remove outliers if std is valid
                    df = df[np.abs(df[col] - mean) <= (5 * std)]
        
        # Ensure volume is non-negative
        if 'volume' in df.columns:
            df = df[df['volume'] >= 0]
        
        logger.info(f"Cleaned data: {len(df)} rows remaining")
        
        return df
    
    @staticmethod
    def add_returns(df: pd.DataFrame) -> pd.DataFrame:
        """Add return columns to DataFrame."""
        df = df.copy()
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        return df
    
    @staticmethod
    def resample_data(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Resample data to different timeframe.
        
        Args:
            df: OHLCV DataFrame
            timeframe: Target timeframe ('1h', '4h', '1d', '1W')
            
        Returns:
            Resampled DataFrame
        """
        resampled = pd.DataFrame()
        resampled['open'] = df['open'].resample(timeframe).first()
        resampled['high'] = df['high'].resample(timeframe).max()
        resampled['low'] = df['low'].resample(timeframe).min()
        resampled['close'] = df['close'].resample(timeframe).last()
        resampled['volume'] = df['volume'].resample(timeframe).sum()
        
        return resampled.dropna()
