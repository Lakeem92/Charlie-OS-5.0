"""
Data Router - Centralized Data Source Routing
Enforces docs/API_MAP.md routing rules across all studies.

CRITICAL: ALL studies use Alpaca as the PRIMARY data source.
yfinance is ONLY used as a fallback when Alpaca fails or for indices (^VIX, ^SPX, etc.).
"""

import yfinance as yf
import pandas as pd
from typing import Optional, Union, List
from datetime import datetime, timedelta
import warnings


# Study types that require Alpaca by default
ALPACA_REQUIRED_STUDIES = {'volatility', 'returns', 'indicator', 'honesty_test', 'ttp'}


class DataRouter:
    """
    Central data routing function that enforces API_MAP.md rules.
    
    Always routes to the correct data source based on:
    - Study type (volatility, returns, indicator, etc.)
    - Data type (daily OHLCV, intraday, macro, volatility)
    - Timeframe requirements
    - Fallback logic if primary source fails
    
    See docs/API_MAP.md for complete routing rules.
    """
    
    @staticmethod
    def get_price_data(
        ticker: Union[str, List[str]],
        start_date: str,
        end_date: Optional[str] = None,
        timeframe: str = 'daily',
        source: Optional[str] = None,
        fallback: bool = True,
        study_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get price data with automatic source routing per API_MAP.md rules.
        
        Args:
            ticker: Single ticker string or list of tickers
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format). If None, uses today.
            timeframe: 'daily', '5min', '15min', '1hour', '1min'
            source: Override default source ('yfinance', 'alpaca', 'tiingo')
            fallback: If True, tries fallback sources on failure
            study_type: Type of study ('volatility', 'returns', 'indicator', 'honesty_test', 'ttp')
                       If specified and in ALPACA_REQUIRED_STUDIES, defaults to Alpaca
            
        Returns:
            pd.DataFrame with OHLCV data
            
        Raises:
            ValueError: If invalid timeframe or source
            RuntimeError: If all sources fail
            
        Examples:
            # Volatility study (auto-routes to Alpaca)
            data = DataRouter.get_price_data('TSLA', '2024-01-01', study_type='returns')
            
            # Indicator honesty test (auto-routes to Alpaca)
            data = DataRouter.get_price_data('BABA', '2024-01-01', study_type='honesty_test')
            
            # Force specific source with warning
            data = DataRouter.get_price_data('TSLA', '2024-01-01', source='yfinance', study_type='returns')
        """
        # Validate timeframe
        valid_timeframes = ['daily', '1min', '5min', '15min', '1hour']
        if timeframe not in valid_timeframes:
            raise ValueError(f"Invalid timeframe: {timeframe}. Must be one of {valid_timeframes}")
        
        # Set end_date to today if not provided
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # GOVERNANCE: Check if study type requires Alpaca
        requires_alpaca = study_type and study_type.lower() in ALPACA_REQUIRED_STUDIES
        
        # If study requires Alpaca but user specified yfinance, issue warning
        if requires_alpaca and source == 'yfinance':
            warnings.warn(
                f"⚠️  GOVERNANCE WARNING: Study type '{study_type}' requires Alpaca data by default per API_MAP.md. "
                f"Using yfinance may introduce vendor discrepancies in forward returns and execution alignment. "
                f"Reason: Explicitly overridden with source='yfinance'",
                UserWarning,
                stacklevel=2
            )
        
        # Override source to Alpaca if study requires it and no source specified
        if requires_alpaca and source is None:
            source = 'alpaca'
        
        # Routing logic based on API_MAP.md
        if source:
            # User explicitly requested a source
            return DataRouter._fetch_from_source(source, ticker, start_date, end_date, timeframe)
        
        # Default routing per API_MAP.md: ALPACA FIRST for all data
        if timeframe == 'daily':
            # Daily OHLCV: Alpaca → yfinance fallback
            try:
                return DataRouter._fetch_from_alpaca(ticker, start_date, end_date, 'daily')
            except Exception as e:
                if not fallback:
                    raise RuntimeError(f"Alpaca failed: {e}")
                
                print(f"⚠️ Alpaca failed ({e}), trying yfinance fallback...")
                try:
                    return DataRouter._fetch_from_yfinance(ticker, start_date, end_date)
                except Exception as e2:
                    if not fallback:
                        raise RuntimeError(f"yfinance failed: {e2}")
                    
                    print(f"⚠️ yfinance failed ({e2}), trying Tiingo fallback...")
                    return DataRouter._fetch_from_tiingo(ticker, start_date, end_date)
        
        else:
            # Intraday: Alpaca → Tiingo IEX
            try:
                return DataRouter._fetch_from_alpaca(ticker, start_date, end_date, timeframe)
            except Exception as e:
                if not fallback:
                    raise RuntimeError(f"Alpaca failed: {e}")
                
                print(f"⚠️ Alpaca failed ({e}), trying Tiingo IEX fallback...")
                return DataRouter._fetch_from_tiingo_intraday(ticker)
    
    @staticmethod
    def _fetch_from_source(source: str, ticker: str, start_date: str, end_date: str, timeframe: str) -> pd.DataFrame:
        """Route to explicitly requested source."""
        if source == 'yfinance':
            return DataRouter._fetch_from_yfinance(ticker, start_date, end_date)
        elif source == 'tiingo':
            return DataRouter._fetch_from_tiingo(ticker, start_date, end_date)
        elif source == 'alpaca':
            return DataRouter._fetch_from_alpaca(ticker, start_date, end_date, timeframe)
        else:
            raise ValueError(f"Unknown source: {source}. Valid: 'yfinance', 'tiingo', 'alpaca'")
    
    @staticmethod
    def _fetch_from_yfinance(ticker: Union[str, List[str]], start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch daily data from yfinance (API_MAP default for daily)."""
        data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
        if data.empty:
            raise RuntimeError(f"yfinance returned no data for {ticker}")
        # yfinance ≥0.2 returns MultiIndex columns for a single ticker — flatten them
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data
    
    @staticmethod
    def _fetch_from_tiingo(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch daily data from Tiingo (API_MAP fallback #1)."""
        from shared.config.api_clients import TiingoClient
        
        client = TiingoClient()
        data = client.get_daily_prices(ticker, start_date=start_date, end_date=end_date)
        
        if not data:
            raise RuntimeError(f"Tiingo returned no data for {ticker}")
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # Rename columns to match yfinance format
        df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
            'adjClose': 'Adj Close'
        }, inplace=True)
        
        return df
    
    @staticmethod
    def _fetch_from_alpaca(ticker: str, start_date: str, end_date: str, timeframe: str) -> pd.DataFrame:
        """Fetch intraday or daily data from Alpaca using IEX feed."""
        from config.api_clients import LabAlpacaClient as AlpacaClient
        
        client = AlpacaClient()
        
        # Map timeframe to Alpaca format
        timeframe_map = {
            'daily': '1Day',
            '1min': '1Min',
            '5min': '5Min',
            '15min': '15Min',
            '1hour': '1Hour'
        }
        alpaca_timeframe = timeframe_map.get(timeframe, '1Day')
        
        # Use IEX feed (free tier) instead of SIP (requires paid subscription)
        data = client.get_bars(ticker, timeframe=alpaca_timeframe, start=start_date, end=end_date, limit=10000, feed='iex')
        
        if not data or 'bars' not in data:
            raise RuntimeError(f"Alpaca returned no data for {ticker}")
        
        # Convert to DataFrame
        bars = data['bars']
        df = pd.DataFrame(bars)
        df['t'] = pd.to_datetime(df['t'])
        df.set_index('t', inplace=True)
        
        # Rename columns to match yfinance format
        df.rename(columns={
            'o': 'Open',
            'h': 'High',
            'l': 'Low',
            'c': 'Close',
            'v': 'Volume'
        }, inplace=True)
        
        return df
    
    @staticmethod
    def _fetch_from_tiingo_intraday(ticker: str) -> pd.DataFrame:
        """Fetch latest intraday snapshot from Tiingo IEX."""
        from shared.config.api_clients import TiingoClient
        
        client = TiingoClient()
        data = client.get_intraday_prices(ticker)
        
        if not data:
            raise RuntimeError(f"Tiingo IEX returned no data for {ticker}")
        
        # Convert to DataFrame (note: this is real-time snapshot, not historical intraday)
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        return df
    
    @staticmethod
    def get_macro_data(series_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get macro/Fed data from FRED (API_MAP default for macro).
        
        Args:
            series_id: FRED series ID (e.g., 'VIXCLS', 'DFF', 'DGS10')
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            
        Returns:
            pd.DataFrame with macro series data
            
        Examples:
            # Get VIX data
            vix = DataRouter.get_macro_data('VIXCLS', '2024-01-01', '2024-12-31')
            
            # Get Fed Funds Rate
            fed_rate = DataRouter.get_macro_data('DFF')
        """
        from shared.config.api_clients import FREDClient
        
        client = FREDClient()
        data = client.get_series(series_id)
        
        if not data or 'observations' not in data:
            raise RuntimeError(f"FRED returned no data for series {series_id}")
        
        # Convert to DataFrame
        df = pd.DataFrame(data['observations'])
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # Filter by date range if provided
        if start_date:
            df = df[df.index >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df.index <= pd.to_datetime(end_date)]
        
        # Convert value column to numeric
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        
        return df
    
    @staticmethod
    def get_volatility_proxy(proxy: str = 'VIX', start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get volatility proxy data (VIX, MOVE, VXN, etc.).
        
        Args:
            proxy: 'VIX', 'MOVE', 'VXN', 'VIXCLS' (FRED)
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            
        Returns:
            pd.DataFrame with volatility data
            
        Examples:
            # Get VIX via yfinance (easy)
            vix = DataRouter.get_volatility_proxy('VIX', '2024-01-01', '2024-12-31')
            
            # Get official VIX from FRED
            vix_official = DataRouter.get_volatility_proxy('VIXCLS', '2024-01-01', '2024-12-31')
        """
        if proxy == 'VIXCLS':
            # Use FRED for official VIX data
            return DataRouter.get_macro_data('VIXCLS', start_date, end_date)
        else:
            # Use yfinance for quick access (^VIX, ^MOVE, ^VXN)
            ticker_map = {
                'VIX': '^VIX',
                'MOVE': '^MOVE',
                'VXN': '^VXN'
            }
            ticker = ticker_map.get(proxy.upper(), f'^{proxy.upper()}')
            
            end_date = end_date or datetime.now().strftime('%Y-%m-%d')
            return DataRouter._fetch_from_yfinance(ticker, start_date, end_date)


# Convenience functions (shortcuts)
def get_daily_prices(ticker: Union[str, List[str]], start: str, end: Optional[str] = None) -> pd.DataFrame:
    """Shortcut for daily OHLCV (uses yfinance per API_MAP)."""
    return DataRouter.get_price_data(ticker, start, end, timeframe='daily')


def get_intraday_prices(ticker: str, start: str, end: Optional[str] = None, resolution: str = '5min') -> pd.DataFrame:
    """Shortcut for intraday OHLCV (uses Alpaca per API_MAP)."""
    return DataRouter.get_price_data(ticker, start, end, timeframe=resolution)


def get_vix(start: str, end: Optional[str] = None, official: bool = False) -> pd.DataFrame:
    """Shortcut for VIX data."""
    if official:
        return DataRouter.get_volatility_proxy('VIXCLS', start, end)
    else:
        return DataRouter.get_volatility_proxy('VIX', start, end)
