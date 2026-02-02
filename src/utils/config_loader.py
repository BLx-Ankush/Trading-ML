"""
Utility functions for loading and validating configuration.
"""
import yaml
from pathlib import Path
from typing import Dict, Any
import os
from dotenv import load_dotenv


class ConfigLoader:
    """Load and manage configuration from YAML and environment variables."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize configuration loader.
        
        Args:
            config_path: Path to config.yaml file
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_yaml()
        self._load_env()
        
    def _load_yaml(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def _load_env(self):
        """Load environment variables from .env file."""
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    
    def get(self, key: str, default=None) -> Any:
        """
        Get configuration value by dot-notation key.
        
        Args:
            key: Configuration key (e.g., 'trading.capital')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_env(self, key: str, default=None) -> str:
        """Get environment variable."""
        return os.getenv(key, default)
    
    def get_trading_capital(self) -> float:
        """Get trading capital from env or config."""
        capital = self.get_env('TRADING_CAPITAL')
        if capital:
            return float(capital)
        return self.get('trading.capital', 200000)
    
    def get_risk_per_trade(self) -> float:
        """Get risk percentage per trade."""
        return self.get('trading.risk_per_trade', 0.01)
    
    def get_daily_loss_limit(self) -> float:
        """Get daily loss limit percentage."""
        return self.get('risk_management.daily_loss_limit', 0.05)
    
    def validate(self) -> bool:
        """Validate configuration values."""
        required_keys = [
            'trading.capital',
            'trading.risk_per_trade',
            'risk_management.daily_loss_limit',
        ]
        
        for key in required_keys:
            if self.get(key) is None:
                raise ValueError(f"Required configuration key missing: {key}")
        
        # Validate ranges
        if self.get('trading.risk_per_trade') > 0.05:
            raise ValueError("Risk per trade too high (>5%)")
        
        if self.get('trading.capital') < 10000:
            raise ValueError("Capital too low (<10,000)")
        
        return True


# Global config instance
_config = None

def get_config(config_path: str = None) -> ConfigLoader:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = ConfigLoader(config_path)
    return _config
