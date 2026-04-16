"""
API Configuration Manager
Centralized API key management for Data Lab
"""

# Load environment first
from . import env_loader

import os
from typing import Dict, Optional
from pathlib import Path


class APIConfig:
    """Centralized API configuration and key management"""
    
    # Alpaca Trading API
    ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
    ALPACA_API_SECRET = os.getenv('ALPACA_API_SECRET')
    ALPACA_BASE_URL = 'https://paper-api.alpaca.markets'  # Paper trading
    ALPACA_DATA_URL = 'https://data.alpaca.markets'  # Market data
    
    # SEC EDGAR Data API
    SEC_EDGAR_API_KEY = os.getenv('SEC_EDGAR_API_KEY')
    SEC_EDGAR_BASE_URL = 'https://www.sec.gov/cgi-bin/browse-edgar'
    
    # CoinGecko Crypto Data
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')
    COINGECKO_BASE_URL = 'https://api.coingecko.com/api/v3'
    
    # Financial Modeling Prep
    FMP_API_KEY = os.getenv('FMP_API_KEY')
    FMP_BASE_URL = 'https://financialmodelingprep.com/api/v3'
    
    # Alpha Vantage
    ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
    ALPHA_VANTAGE_BASE_URL = 'https://www.alphavantage.co/query'
    
    # FRED (Federal Reserve Economic Data)
    FRED_API_KEY = os.getenv('FRED_API_KEY')
    FRED_BASE_URL = 'https://api.stlouisfed.org/fred'
    
    # Charles Schwab
    SCHWAB_API_KEY = os.getenv('SCHWAB_API_KEY')
    SCHWAB_API_SECRET = os.getenv('SCHWAB_API_SECRET')
    SCHWAB_BASE_URL = 'https://api.schwabapi.com/marketdata/v1'
    
    # Tiingo
    TIINGO_API_KEY = os.getenv('TIINGO_API_KEY')
    TIINGO_BASE_URL = 'https://api.tiingo.com/tiingo'
    
    # USDA FoodData Central
    USDA_API_KEY = os.getenv('USDA_API_KEY')
    USDA_BASE_URL = 'https://api.nal.usda.gov/fdc/v1'
    
    # Anthropic (Claude API)
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    ANTHROPIC_BASE_URL = 'https://api.anthropic.com/v1'
    
    @classmethod
    def get_api_key(cls, api_name: str) -> Optional[str]:
        """
        Retrieve API key by service name
        
        Args:
            api_name: Name of the API service (sec_edgar, coingecko, fmp, alpha_vantage, fred, schwab, tiingo)
            
        Returns:
            API key string or None if not found
        """
        key_mapping = {
            'alpaca': cls.ALPACA_API_KEY,
            'sec_edgar': cls.SEC_EDGAR_API_KEY,
            'coingecko': cls.COINGECKO_API_KEY,
            'fmp': cls.FMP_API_KEY,
            'alpha_vantage': cls.ALPHA_VANTAGE_API_KEY,
            'fred': cls.FRED_API_KEY,
            'schwab': cls.SCHWAB_API_KEY,
            'tiingo': cls.TIINGO_API_KEY,
            'usda': cls.USDA_API_KEY,
            'anthropic': cls.ANTHROPIC_API_KEY,
        }
        return key_mapping.get(api_name.lower())
    
    @classmethod
    def get_api_config(cls, api_name: str) -> Dict[str, str]:
        """
        Get complete API configuration including base URL
        
        Args:
            api_name: Name of the API service
            
        Returns:
            Dictionary with 'api_key' and 'base_url'
        """
        config_mapping = {
            'alpaca': {
                'api_key': cls.ALPACA_API_KEY,
                'api_secret': cls.ALPACA_API_SECRET,
                'base_url': cls.ALPACA_BASE_URL,
                'data_url': cls.ALPACA_DATA_URL
            },
            'sec_edgar': {
                'api_key': cls.SEC_EDGAR_API_KEY,
                'base_url': cls.SEC_EDGAR_BASE_URL
            },
            'coingecko': {
                'api_key': cls.COINGECKO_API_KEY,
                'base_url': cls.COINGECKO_BASE_URL
            },
            'fmp': {
                'api_key': cls.FMP_API_KEY,
                'base_url': cls.FMP_BASE_URL
            },
            'alpha_vantage': {
                'api_key': cls.ALPHA_VANTAGE_API_KEY,
                'base_url': cls.ALPHA_VANTAGE_BASE_URL
            },
            'fred': {
                'api_key': cls.FRED_API_KEY,
                'base_url': cls.FRED_BASE_URL
            },
            'schwab': {
                'api_key': cls.SCHWAB_API_KEY,
                'api_secret': cls.SCHWAB_API_SECRET,
                'base_url': cls.SCHWAB_BASE_URL
            },
            'tiingo': {
                'api_key': cls.TIINGO_API_KEY,
                'base_url': cls.TIINGO_BASE_URL
            },
            'usda': {
                'api_key': cls.USDA_API_KEY,
                'base_url': cls.USDA_BASE_URL
            },
            'anthropic': {
                'api_key': cls.ANTHROPIC_API_KEY,
                'base_url': cls.ANTHROPIC_BASE_URL
            },
        }
        return config_mapping.get(api_name.lower(), {})
    
    @classmethod
    def validate_keys(cls) -> Dict[str, bool]:
        """
        Validate that all API keys are loaded
        
        Returns:
            Dictionary with API names and their validation status
        """
        return {
            'Alpaca': bool(cls.ALPACA_API_KEY and cls.ALPACA_API_SECRET),
            'SEC EDGAR': bool(cls.SEC_EDGAR_API_KEY),
            'CoinGecko': bool(cls.COINGECKO_API_KEY),
            'Financial Modeling Prep': bool(cls.FMP_API_KEY),
            'Alpha Vantage': bool(cls.ALPHA_VANTAGE_API_KEY),
            'FRED': bool(cls.FRED_API_KEY),
            'Charles Schwab': bool(cls.SCHWAB_API_KEY and cls.SCHWAB_API_SECRET),
            'Tiingo': bool(cls.TIINGO_API_KEY),
            'USDA': bool(cls.USDA_API_KEY),
            'Anthropic': bool(cls.ANTHROPIC_API_KEY),
        }
    
    @classmethod
    def print_status(cls):
        """Print API configuration status"""
        print("API Configuration Status")
        print("=" * 60)
        validation = cls.validate_keys()
        for api, status in validation.items():
            status_str = "✓ Loaded" if status else "✗ Missing"
            print(f"{api:30s} {status_str}")
        print("=" * 60)


# Convenience functions for quick access
def get_api_key(api_name: str) -> Optional[str]:
    """
    Quick access to API keys
    
    Example:
        >>> api_key = get_api_key('fmp')
        >>> api_key = get_api_key('alpha_vantage')
    """
    return APIConfig.get_api_key(api_name)


def get_api_config(api_name: str) -> Dict[str, str]:
    """
    Quick access to full API config
    
    Example:
        >>> config = get_api_config('tiingo')
        >>> print(config['api_key'])
        >>> print(config['base_url'])
    """
    return APIConfig.get_api_config(api_name)
