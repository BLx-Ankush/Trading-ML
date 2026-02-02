"""
GARCH model for volatility forecasting.
Used for dynamic position sizing based on predicted market volatility.
"""
import pandas as pd
import numpy as np
from arch import arch_model
from typing import Optional

from ..utils.logger import get_logger

logger = get_logger()


class GARCHVolatility:
    """
    GARCH(1,1) model for volatility forecasting.
    
    Used in Layer 4 for dynamic position sizing:
    - Low volatility → Larger positions
    - High volatility → Smaller positions
    """
    
    def __init__(self, lookback_days: int = 60):
        """
        Initialize GARCH model.
        
        Args:
            lookback_days: Number of days to use for training
        """
        self.lookback_days = lookback_days
        self.model = None
        self.fitted_model = None
        
    def fit(self, returns: pd.Series) -> bool:
        """
        Fit GARCH(1,1) model to historical returns.
        
        Args:
            returns: Series of percentage returns
            
        Returns:
            True if fitting succeeded, False otherwise
        """
        try:
            # Use last N days for training
            train_returns = returns.tail(self.lookback_days).dropna()
            
            if len(train_returns) < 30:
                logger.warning(f"Insufficient data for GARCH: {len(train_returns)} days")
                return False
            
            # Scale returns to percentage (GARCH works better with scaled data)
            scaled_returns = train_returns * 100
            
            # Initialize GARCH(1,1) model
            self.model = arch_model(
                scaled_returns,
                vol='Garch',
                p=1,
                q=1,
                dist='normal'
            )
            
            # Fit the model
            self.fitted_model = self.model.fit(disp='off', show_warning=False)
            
            logger.debug(f"GARCH model fitted with {len(train_returns)} observations")
            return True
            
        except Exception as e:
            logger.error(f"Error fitting GARCH model: {str(e)}")
            return False
    
    def forecast(self, horizon: int = 1) -> Optional[float]:
        """
        Forecast volatility for next period(s).
        
        Args:
            horizon: Number of periods ahead to forecast
            
        Returns:
            Forecasted volatility (annualized) or None if forecast fails
        """
        if self.fitted_model is None:
            logger.error("Model not fitted. Call fit() first.")
            return None
        
        try:
            # Forecast variance
            forecast = self.fitted_model.forecast(horizon=horizon)
            
            # Get forecasted variance (scaled back from percentage)
            forecasted_variance = forecast.variance.values[-1, 0] / (100 ** 2)
            
            # Convert to annualized volatility
            # Daily volatility * sqrt(252 trading days)
            annualized_volatility = np.sqrt(forecasted_variance * 252)
            
            return annualized_volatility
            
        except Exception as e:
            logger.error(f"Error forecasting volatility: {str(e)}")
            return None
    
    def get_current_volatility(self, returns: pd.Series, window: int = 20) -> float:
        """
        Calculate current realized volatility (fallback if GARCH fails).
        
        Args:
            returns: Series of returns
            window: Rolling window for calculation
            
        Returns:
            Annualized volatility
        """
        recent_returns = returns.tail(window).dropna()
        daily_vol = recent_returns.std()
        annualized_vol = daily_vol * np.sqrt(252)
        return annualized_vol
    
    def classify_volatility(self, current_vol: float, returns: pd.Series) -> str:
        """
        Classify volatility as Low, Normal, or High.
        
        Args:
            current_vol: Current/forecasted volatility
            returns: Historical returns for percentile calculation
            
        Returns:
            'low', 'normal', or 'high'
        """
        # Calculate historical volatility distribution
        rolling_vol = returns.rolling(window=20).std() * np.sqrt(252)
        
        low_threshold = rolling_vol.quantile(0.30)
        high_threshold = rolling_vol.quantile(0.70)
        
        if current_vol < low_threshold:
            return 'low'
        elif current_vol > high_threshold:
            return 'high'
        else:
            return 'normal'
    
    def get_volatility_multiplier(self, volatility_class: str) -> float:
        """
        Get position size multiplier based on volatility.
        
        Low vol → 1.2x position
        Normal vol → 1.0x position
        High vol → 0.5x position
        
        Args:
            volatility_class: 'low', 'normal', or 'high'
            
        Returns:
            Multiplier for position sizing
        """
        multipliers = {
            'low': 1.2,
            'normal': 1.0,
            'high': 0.5
        }
        
        return multipliers.get(volatility_class, 1.0)
