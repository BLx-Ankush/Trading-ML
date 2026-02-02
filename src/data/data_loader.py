"""
Data loading and fetching from various sources.
"""
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
import pickle

from ..utils.logger import get_logger

logger = get_logger()


class DataLoader:
    """Load and manage market data from various sources."""
    
    def __init__(self, data_dir: str = None):
        """
        Initialize data loader.
        
        Args:
            data_dir: Directory to store cached data
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data" / "raw"
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def fetch_yahoo_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch data from Yahoo Finance.
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS' for NSE)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval (1d, 1h, etc.)
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Fetching {symbol} data from {start_date} to {end_date}")
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval=interval)
            
            if df.empty:
                logger.error(f"No data returned for {symbol}")
                return pd.DataFrame()
            
            # Standardize column names
            df.columns = [col.lower() for col in df.columns]
            
            # Keep only OHLCV
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            df = df[required_cols]
            
            logger.info(f"Fetched {len(df)} rows for {symbol}")
            
            # Cache the data
            self._cache_data(symbol, df, start_date, end_date)
            
            return df
        
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}", exc_info=True)
            return pd.DataFrame()
    
    def load_cached_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        Load cached data if available.
        
        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame if cached, None otherwise
        """
        cache_file = self.data_dir / f"{symbol}_{start_date}_{end_date}.pkl"
        
        if cache_file.exists():
            logger.info(f"Loading cached data for {symbol}")
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        
        return None
    
    def _cache_data(self, symbol: str, df: pd.DataFrame, start_date: str, end_date: str):
        """Cache data to disk."""
        cache_file = self.data_dir / f"{symbol}_{start_date}_{end_date}.pkl"
        with open(cache_file, 'wb') as f:
            pickle.dump(df, f)
        logger.debug(f"Cached data to {cache_file}")
    
    def get_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Get data with caching support.
        
        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            use_cache: Whether to use cached data
            
        Returns:
            DataFrame with OHLCV data
        """
        if use_cache:
            cached_df = self.load_cached_data(symbol, start_date, end_date)
            if cached_df is not None:
                return cached_df
        
        return self.fetch_yahoo_data(symbol, start_date, end_date)
    
    def get_multiple_symbols(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> dict:
        """
        Fetch data for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary mapping symbols to DataFrames
        """
        data = {}
        for symbol in symbols:
            df = self.get_data(symbol, start_date, end_date)
            if not df.empty:
                data[symbol] = df
        
        return data
