"""
Technical indicators calculation.
"""
import pandas as pd
import numpy as np
from typing import Tuple


class TechnicalIndicators:
    """Calculate technical indicators for trading."""
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR).
        
        Critical for position sizing and stop-loss placement.
        
        Args:
            df: DataFrame with OHLCV data
            period: ATR period (default: 14)
            
        Returns:
            Series with ATR values
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # True Range calculation
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR is the moving average of TR
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            df: DataFrame with OHLCV data
            period: RSI period (default: 14)
            
        Returns:
            Series with RSI values (0-100)
        """
        close = df['close']
        delta = close.diff()
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            df: DataFrame with OHLCV data
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
            
        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        close = df['close']
        
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_bollinger_bands(
        df: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands.
        
        Args:
            df: DataFrame with OHLCV data
            period: Moving average period
            std_dev: Standard deviation multiplier
            
        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        close = df['close']
        
        middle_band = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        return upper_band, middle_band, lower_band
    
    @staticmethod
    def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average Directional Index (ADX).
        
        Measures trend strength (not direction).
        ADX > 25 = Trending market
        ADX < 20 = Ranging market
        
        Args:
            df: DataFrame with OHLCV data
            period: ADX period
            
        Returns:
            Series with ADX values (0-100)
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calculate +DM and -DM
        high_diff = high.diff()
        low_diff = -low.diff()
        
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
        
        # Calculate ATR
        atr = TechnicalIndicators.calculate_atr(df, period)
        
        # Calculate +DI and -DI
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        # Calculate DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    @staticmethod
    def calculate_ema(df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return df['close'].ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_sma(df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Simple Moving Average."""
        return df['close'].rolling(window=period).mean()
    
    @staticmethod
    def calculate_volume_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate volume moving average."""
        return df['volume'].rolling(window=period).mean()
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators and add to DataFrame.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with all indicators added
        """
        df = df.copy()
        
        # Normalize column names (handle both lowercase and Title case)
        col_mapping = {}
        for col in df.columns:
            lower_col = col.lower()
            if lower_col in ['open', 'high', 'low', 'close', 'volume']:
                col_mapping[col] = lower_col
        df = df.rename(columns=col_mapping)
        
        try:
            # ATR (Critical for position sizing)
            df['atr'] = TechnicalIndicators.calculate_atr(df, 14)
            df['ATR'] = df['atr']  # Add both for compatibility
            
            # RSI
            df['rsi'] = TechnicalIndicators.calculate_rsi(df, 14)
            
            # MACD
            macd, signal, hist = TechnicalIndicators.calculate_macd(df)
            df['macd'] = macd
            df['macd_signal'] = signal
            df['macd_hist'] = hist
            
            # Bollinger Bands
            upper, middle, lower = TechnicalIndicators.calculate_bollinger_bands(df)
            df['bb_upper'] = upper
            df['bb_middle'] = middle
            df['bb_lower'] = lower
            
            # ADX (Critical for regime detection)
            df['adx'] = TechnicalIndicators.calculate_adx(df, 14)
            
            # Moving Averages
            df['ema_9'] = TechnicalIndicators.calculate_ema(df, 9)
            df['ema_21'] = TechnicalIndicators.calculate_ema(df, 21)
            df['sma_50'] = TechnicalIndicators.calculate_sma(df, 50)
            df['sma_200'] = TechnicalIndicators.calculate_sma(df, 200)
            
            # Volume indicators
            df['volume_sma'] = TechnicalIndicators.calculate_volume_sma(df, 20)
            # Safe division for volume_ratio
            df['volume_ratio'] = df['volume'] / df['volume_sma'].where(df['volume_sma'] != 0, np.nan)
            
            # Returns
            df['returns'] = df['close'].pct_change()
            
            # Replace any infinity values with NaN
            df = df.replace([np.inf, -np.inf], np.nan)
            
            # Fill NaN in indicators with forward fill (max 3 periods)
            indicator_cols = ['atr', 'rsi', 'macd', 'macd_signal', 'macd_hist', 
                            'bb_upper', 'bb_middle', 'bb_lower', 'adx',
                            'ema_9', 'ema_21', 'sma_50', 'sma_200',
                            'volume_sma', 'volume_ratio']
            
            for col in indicator_cols:
                if col in df.columns:
                    df[col] = df[col].ffill(limit=3)
            
            # Ensure ATR has a minimum value (for position sizing safety)
            if 'atr' in df.columns:
                df['atr'] = df['atr'].fillna(df['close'] * 0.02)  # 2% default
                df['atr'] = df['atr'].replace(0, df['close'] * 0.02)
                df['ATR'] = df['atr']  # Uppercase version for compatibility
            
            # Add Title case columns for compatibility with portfolio engine
            if 'close' in df.columns:
                df['Close'] = df['close']
            if 'regime' in df.columns or 'Regime' in df.columns:
                if 'regime' in df.columns:
                    df['Regime'] = df['regime']
                
        except Exception as e:
            print(f"Warning: Error calculating indicators: {e}")
            # Ensure critical columns exist with safe defaults
            if 'atr' not in df.columns:
                df['atr'] = df['close'] * 0.02
                df['ATR'] = df['atr']
            if 'rsi' not in df.columns:
                df['rsi'] = 50
            if 'adx' not in df.columns:
                df['adx'] = 25
        
        return df
