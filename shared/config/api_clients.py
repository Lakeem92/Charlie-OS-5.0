"""
API Client Examples
Ready-to-use client functions for each API service
"""

import os
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from .api_config import APIConfig
try:
    from . import env_loader
except Exception:
    env_loader = None


class LabAlpacaClient:
    """Alpaca Trading & Market Data API Client"""
    
    def __init__(self, **kwargs):
        paper_trading = kwargs.get('paper_trading', True)
        """
        Initialize Alpaca client
        
        Args:
            paper_trading: If True, uses paper trading URL. If False, uses live trading URL.
        """
        # Attempt to load keys for the requested env (paper/live) from shared/config/keys
        if env_loader:
            try:
                # Force loading so in-session live vars don't block switching to paper
                env_loader.load_keys('paper' if paper_trading else 'live', override=True)
            except Exception:
                pass

        # Read keys from environment (or APIConfig fallbacks)
        self.api_key = os.getenv('ALPACA_API_KEY') or APIConfig.ALPACA_API_KEY
        self.api_secret = os.getenv('ALPACA_API_SECRET') or APIConfig.ALPACA_API_SECRET
        # Prefer explicit APCA_API_BASE_URL env var; otherwise choose paper vs live defaults.
        self.base_url = os.getenv('APCA_API_BASE_URL') or ('https://paper-api.alpaca.markets' if paper_trading else (os.getenv('ALPACA_API_BASE_URL') or 'https://api.alpaca.markets'))
        self.data_url = APIConfig.ALPACA_DATA_URL
        self.headers = {
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.api_secret
        }
    
    # Account & Trading Methods
    def get_account(self) -> Dict:
        """Get account information"""
        url = f"{self.base_url}/v2/account"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        url = f"{self.base_url}/v2/positions"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_position(self, symbol: str) -> Dict:
        """Get position for a specific symbol"""
        url = f"{self.base_url}/v2/positions/{symbol}"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def place_order(self, symbol: str, qty: float, side: str, 
                   order_type: str = 'market', time_in_force: str = 'day',
                   limit_price: Optional[float] = None, 
                   stop_price: Optional[float] = None) -> Dict:
        """
        Place an order
        
        Args:
            symbol: Stock symbol (e.g., 'BABA')
            qty: Quantity of shares
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', 'stop', 'stop_limit'
            time_in_force: 'day', 'gtc', 'ioc', 'fok'
            limit_price: Limit price for limit orders
            stop_price: Stop price for stop orders
        """
        url = f"{self.base_url}/v2/orders"
        data = {
            'symbol': symbol,
            'qty': qty,
            'side': side,
            'type': order_type,
            'time_in_force': time_in_force
        }
        if limit_price:
            data['limit_price'] = limit_price
        if stop_price:
            data['stop_price'] = stop_price
        
        response = requests.post(url, headers=self.headers, json=data)
        return response.json()
    
    def cancel_order(self, order_id: str) -> None:
        """Cancel an order"""
        url = f"{self.base_url}/v2/orders/{order_id}"
        response = requests.delete(url, headers=self.headers)
        return response.status_code == 204
    
    def get_orders(self, status: str = 'open') -> List[Dict]:
        """
        Get orders
        
        Args:
            status: 'open', 'closed', 'all'
        """
        url = f"{self.base_url}/v2/orders"
        params = {'status': status}
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()
    
    # Market Data Methods
    def get_bars(self, symbol: str, timeframe: str = '1Day', 
                start: Optional[str] = None, end: Optional[str] = None,
                limit: int = 100, feed: str = 'iex') -> Dict:
        """
        Get historical price bars
        
        Args:
            symbol: Stock symbol
            timeframe: '1Min', '5Min', '15Min', '1Hour', '1Day'
            start: Start date (YYYY-MM-DD or RFC3339)
            end: End date (YYYY-MM-DD or RFC3339)
            limit: Number of bars to return
            feed: Data feed ('iex' for free, 'sip' for paid subscription)
        """
        url = f"{self.data_url}/v2/stocks/{symbol}/bars"
        params = {
            'timeframe': timeframe,
            'limit': limit,
            'feed': feed
        }
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()
    
    def get_latest_trade(self, symbol: str) -> Dict:
        """Get latest trade for a symbol"""
        url = f"{self.data_url}/v2/stocks/{symbol}/trades/latest"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_latest_quote(self, symbol: str) -> Dict:
        """Get latest quote (bid/ask) for a symbol"""
        url = f"{self.data_url}/v2/stocks/{symbol}/quotes/latest"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_snapshot(self, symbol: str) -> Dict:
        """Get market snapshot (latest trade, quote, bar, etc.)"""
        url = f"{self.data_url}/v2/stocks/{symbol}/snapshot"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_snapshots(self, symbols: List[str]) -> Dict:
        """Get market snapshots for multiple symbols"""
        url = f"{self.data_url}/v2/stocks/snapshots"
        params = {'symbols': ','.join(symbols)}
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()
    
    # Calendar & Clock
    def get_clock(self) -> Dict:
        """Get market clock (open/closed status)"""
        url = f"{self.base_url}/v2/clock"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_calendar(self, start: Optional[str] = None, end: Optional[str] = None) -> List[Dict]:
        """Get market calendar (trading days)"""
        url = f"{self.base_url}/v2/calendar"
        params = {}
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()
    
    # Options Methods
    def get_option_chain(self, underlying: str, feed: str = 'indicative') -> Dict:
        """Get options chain for underlying"""
        if not hasattr(self, 'data_url'):
            # Workaround for __init__ not executed
            self.data_url = 'https://data.alpaca.markets'
            self.headers = {'APCA-API-KEY-ID': '', 'APCA-API-SECRET-KEY': ''}
        url = f"{self.data_url}/v1beta1/options/snapshots/{underlying}"
        params = {'feed': feed}
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()
    
    def get_option_contract(self, symbol: str) -> Dict:
        """Get option contract details including open interest"""
        if not hasattr(self, 'data_url'):
            # Workaround
            self.data_url = 'https://data.alpaca.markets'
            self.headers = {'APCA-API-KEY-ID': '', 'APCA-API-SECRET-KEY': ''}
        url = f"{self.data_url}/v1beta1/options/contracts/{symbol}"
        response = requests.get(url, headers=self.headers)
        return response.json()


class SECEdgarClient:
    """SEC EDGAR Data API Client"""
    
    def __init__(self):
        self.api_key = APIConfig.SEC_EDGAR_API_KEY
        self.base_url = APIConfig.SEC_EDGAR_BASE_URL
        self.headers = {'User-Agent': f'DataLab {self.api_key}'}
    
    def get_company_filings(self, ticker: str, filing_type: str = '10-K') -> Dict:
        """Get company SEC filings"""
        params = {
            'action': 'getcompany',
            'CIK': ticker,
            'type': filing_type,
            'output': 'json'
        }
        response = requests.get(self.base_url, params=params, headers=self.headers)
        return response.json()


class CoinGeckoClient:
    """CoinGecko Crypto Data API Client"""
    
    def __init__(self):
        self.api_key = APIConfig.COINGECKO_API_KEY
        self.base_url = APIConfig.COINGECKO_BASE_URL
        self.headers = {'x-cg-demo-api-key': self.api_key}
    
    def get_coin_price(self, coin_id: str, vs_currency: str = 'usd') -> Dict:
        """Get current cryptocurrency price"""
        url = f"{self.base_url}/simple/price"
        params = {'ids': coin_id, 'vs_currencies': vs_currency}
        response = requests.get(url, params=params, headers=self.headers)
        return response.json()
    
    def get_market_data(self, coin_id: str, days: int = 30) -> Dict:
        """Get historical market data"""
        url = f"{self.base_url}/coins/{coin_id}/market_chart"
        params = {'vs_currency': 'usd', 'days': days}
        response = requests.get(url, params=params, headers=self.headers)
        return response.json()
    
    def get_coin_list(self) -> List[Dict]:
        """Get list of all supported coins"""
        url = f"{self.base_url}/coins/list"
        response = requests.get(url, headers=self.headers)
        return response.json()


class FMPClient:
    """Financial Modeling Prep API Client"""
    
    def __init__(self):
        self.api_key = APIConfig.FMP_API_KEY
        self.base_url = APIConfig.FMP_BASE_URL
    
    def get_quote(self, symbol: str) -> Dict:
        """Get real-time stock quote"""
        url = f"{self.base_url}/quote/{symbol}"
        params = {'apikey': self.api_key}
        response = requests.get(url, params=params)
        return response.json()
    
    def get_income_statement(self, symbol: str, period: str = 'annual') -> Dict:
        """Get income statement data"""
        url = f"{self.base_url}/income-statement/{symbol}"
        params = {'apikey': self.api_key, 'period': period}
        response = requests.get(url, params=params)
        return response.json()
    
    def get_balance_sheet(self, symbol: str, period: str = 'annual') -> Dict:
        """Get balance sheet data"""
        url = f"{self.base_url}/balance-sheet-statement/{symbol}"
        params = {'apikey': self.api_key, 'period': period}
        response = requests.get(url, params=params)
        return response.json()
    
    def get_cash_flow(self, symbol: str, period: str = 'annual') -> Dict:
        """Get cash flow statement"""
        url = f"{self.base_url}/cash-flow-statement/{symbol}"
        params = {'apikey': self.api_key, 'period': period}
        response = requests.get(url, params=params)
        return response.json()
    
    def get_financial_ratios(self, symbol: str) -> Dict:
        """Get financial ratios"""
        url = f"{self.base_url}/ratios/{symbol}"
        params = {'apikey': self.api_key}
        response = requests.get(url, params=params)
        return response.json()
    
    def get_company_profile(self, symbol: str) -> Dict:
        """Get company profile"""
        url = f"{self.base_url}/profile/{symbol}"
        params = {'apikey': self.api_key}
        response = requests.get(url, params=params)
        return response.json()


class AlphaVantageClient:
    """Alpha Vantage API Client"""
    
    def __init__(self):
        self.api_key = APIConfig.ALPHA_VANTAGE_API_KEY
        self.base_url = APIConfig.ALPHA_VANTAGE_BASE_URL
    
    def get_intraday(self, symbol: str, interval: str = '5min') -> Dict:
        """Get intraday time series data"""
        params = {
            'function': 'TIME_SERIES_INTRADAY',
            'symbol': symbol,
            'interval': interval,
            'apikey': self.api_key
        }
        response = requests.get(self.base_url, params=params)
        return response.json()
    
    def get_daily(self, symbol: str, outputsize: str = 'compact') -> Dict:
        """Get daily time series data"""
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'outputsize': outputsize,
            'apikey': self.api_key
        }
        response = requests.get(self.base_url, params=params)
        return response.json()
    
    def get_weekly(self, symbol: str) -> Dict:
        """Get weekly time series data"""
        params = {
            'function': 'TIME_SERIES_WEEKLY',
            'symbol': symbol,
            'apikey': self.api_key
        }
        response = requests.get(self.base_url, params=params)
        return response.json()
    
    def get_monthly(self, symbol: str) -> Dict:
        """Get monthly time series data"""
        params = {
            'function': 'TIME_SERIES_MONTHLY',
            'symbol': symbol,
            'apikey': self.api_key
        }
        response = requests.get(self.base_url, params=params)
        return response.json()


class FREDClient:
    """FRED Economic Data API Client — powered by fredapi."""

    def __init__(self):
        import fredapi
        self.api_key = os.environ.get('FRED_API_KEY') or APIConfig.FRED_API_KEY
        if not self.api_key:
            raise ValueError("FRED_API_KEY not found in environment or APIConfig")
        self._fred = fredapi.Fred(api_key=self.api_key)

    def get_series(self, series_id: str, start_date: str = None, end_date: str = None):
        """Return a pandas Series with the requested FRED data."""
        kwargs = {}
        if start_date:
            kwargs['observation_start'] = start_date
        if end_date:
            kwargs['observation_end'] = end_date
        return self._fred.get_series(series_id, **kwargs)

    def search_series(self, query: str, limit: int = 10):
        """Search FRED for series matching query."""
        return self._fred.search(query, limit=limit)

    def get_series_info(self, series_id: str):
        """Get metadata for a FRED series."""
        return self._fred.get_series_info(series_id)


class SchwabClient:
    """Charles Schwab API Client"""
    
    def __init__(self):
        self.api_key = APIConfig.SCHWAB_API_KEY
        self.api_secret = APIConfig.SCHWAB_API_SECRET
        self.base_url = APIConfig.SCHWAB_BASE_URL
        self.headers = {'Authorization': f'Bearer {self.api_key}'}
    
    def get_quote(self, symbol: str) -> Dict:
        """Get market quote"""
        url = f"{self.base_url}/quotes"
        params = {'symbols': symbol}
        response = requests.get(url, params=params, headers=self.headers)
        return response.json()
    
    def get_quotes(self, symbols: List[str]) -> Dict:
        """Get multiple market quotes"""
        url = f"{self.base_url}/quotes"
        params = {'symbols': ','.join(symbols)}
        response = requests.get(url, params=params, headers=self.headers)
        return response.json()
    
    def get_market_hours(self, markets: str = 'equity') -> Dict:
        """Get market hours"""
        url = f"{self.base_url}/markets"
        params = {'markets': markets}
        response = requests.get(url, params=params, headers=self.headers)
        return response.json()


class TiingoClient:
    """Tiingo API Client"""
    
    def __init__(self):
        self.api_key = APIConfig.TIINGO_API_KEY
        self.base_url = APIConfig.TIINGO_BASE_URL
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {self.api_key}'
        }
    
    def get_daily_prices(self, ticker: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
        """Get daily stock prices"""
        url = f"{self.base_url}/daily/{ticker}/prices"
        params = {}
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
        response = requests.get(url, params=params, headers=self.headers)
        return response.json()
    
    def get_intraday_prices(self, ticker: str) -> Dict:
        """Get intraday stock prices"""
        url = f"https://api.tiingo.com/iex/{ticker}/prices"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_ticker_metadata(self, ticker: str) -> Dict:
        """Get ticker metadata and info"""
        url = f"{self.base_url}/daily/{ticker}"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_news(self, tickers: str, limit: int = 10) -> Dict:
        """Get stock news"""
        url = f"https://api.tiingo.com/tiingo/news"
        params = {'tickers': tickers, 'limit': limit}
        response = requests.get(url, params=params, headers=self.headers)
        return response.json()
    
    def get_crypto_prices(self, ticker: str) -> Dict:
        """Get cryptocurrency prices"""
        url = f"https://api.tiingo.com/tiingo/crypto/prices"
        params = {'tickers': ticker}
        response = requests.get(url, params=params, headers=self.headers)
        return response.json()
