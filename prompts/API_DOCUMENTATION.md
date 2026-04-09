# API Documentation & Usage Guide

## Quick Reference

| API | Purpose | Rate Limit | Documentation |
|-----|---------|------------|---------------|
| SEC EDGAR | SEC filings, 10-K, 10-Q | 10 req/sec | [Link](https://www.sec.gov/edgar/sec-api-documentation) |
| CoinGecko | Crypto prices & data | 10-50 calls/min | [Link](https://www.coingecko.com/api/documentation) |
| Financial Modeling Prep | Stock quotes, financials | 250 req/day | [Link](https://site.financialmodelingprep.com/developer/docs) |
| Alpha Vantage | Stock data, indicators | 5/min, 500/day | [Link](https://www.alphavantage.co/documentation/) |
| FRED | Economic indicators | Unlimited | [Link](https://fred.stlouisfed.org/docs/api/fred/) |
| Charles Schwab | Trading, market data | Varies | [Link](https://developer.schwab.com/) |
| Tiingo | Stock prices, news | 500/hour, 5000/day | [Link](https://www.tiingo.com/documentation/general/overview) |

---

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Test configuration
python test_apis.py
```

---

## Basic Usage

### Get API Configuration Status

```python
from config.api_config import APIConfig

# Print all API status
APIConfig.print_status()

# Get specific API key
api_key = APIConfig.get_api_key('fmp')

# Get full config (key + base URL)
config = APIConfig.get_api_config('tiingo')
print(config['api_key'])
print(config['base_url'])
```

---

## API Client Examples

### 1. Financial Modeling Prep (FMP)

**Stock Quotes & Financial Data**

```python
from config.api_clients import FMPClient

client = FMPClient()

# Get real-time quote
quote = client.get_quote('BABA')
print(f"Price: ${quote[0]['price']}")

# Get income statement
income = client.get_income_statement('AAPL', period='annual')

# Get balance sheet
balance = client.get_balance_sheet('TSLA')

# Get cash flow
cashflow = client.get_cash_flow('MSFT')

# Get financial ratios
ratios = client.get_financial_ratios('NVDA')

# Get company profile
profile = client.get_company_profile('GOOGL')
```

### 2. Alpha Vantage

**Time Series Data & Technical Indicators**

```python
from config.api_clients import AlphaVantageClient

client = AlphaVantageClient()

# Intraday data (5min, 15min, 30min, 60min)
intraday = client.get_intraday('MSFT', interval='5min')

# Daily data
daily = client.get_daily('AAPL', outputsize='full')

# Weekly data
weekly = client.get_weekly('TSLA')

# Monthly data
monthly = client.get_monthly('NVDA')
```

### 3. FRED Economic Data

**Macroeconomic Indicators**

```python
from config.api_clients import FREDClient

client = FREDClient()

# Get economic series
gdp = client.get_series('GDP')
unemployment = client.get_series('UNRATE')
cpi = client.get_series('CPIAUCSL')
sp500 = client.get_series('SP500')

# Search for series
results = client.search_series('inflation', limit=20)

# Get series info
info = client.get_series_info('GDP')
```

**Popular FRED Series IDs:**
- `GDP` - Gross Domestic Product
- `UNRATE` - Unemployment Rate
- `CPIAUCSL` - Consumer Price Index
- `FEDFUNDS` - Federal Funds Rate
- `DGS10` - 10-Year Treasury Rate
- `SP500` - S&P 500 Index
- `DEXCHUS` - USD/CNY Exchange Rate

### 4. Tiingo

**Stock Prices, News & Crypto**

```python
from config.api_clients import TiingoClient

client = TiingoClient()

# Daily prices
prices = client.get_daily_prices('BABA', start_date='2025-01-01')

# Intraday prices
intraday = client.get_intraday_prices('TSLA')

# Ticker metadata
meta = client.get_ticker_metadata('AAPL')

# Stock news
news = client.get_news('BABA,NVDA', limit=20)

# Crypto prices
btc = client.get_crypto_prices('btcusd')
```

### 5. CoinGecko

**Cryptocurrency Data**

```python
from config.api_clients import CoinGeckoClient

client = CoinGeckoClient()

# Current price
btc_price = client.get_coin_price('bitcoin')
eth_price = client.get_coin_price('ethereum', vs_currency='usd')

# Historical market data (30 days)
history = client.get_market_data('bitcoin', days=30)

# Get list of all coins
coins = client.get_coin_list()
```

### 6. SEC EDGAR

**SEC Filings**

```python
from config.api_clients import SECEdgarClient

client = SECEdgarClient()

# Get company filings
filings_10k = client.get_company_filings('AAPL', filing_type='10-K')
filings_10q = client.get_company_filings('TSLA', filing_type='10-Q')
filings_8k = client.get_company_filings('MSFT', filing_type='8-K')
```

### 7. Charles Schwab

**Market Data & Trading**

```python
from config.api_clients import SchwabClient

client = SchwabClient()

# Single quote
quote = client.get_quote('SPY')

# Multiple quotes
quotes = client.get_quotes(['AAPL', 'MSFT', 'GOOGL'])

# Market hours
hours = client.get_market_hours('equity')
```

---

## Common Use Cases

### Multi-Source Stock Analysis

```python
from config.api_clients import FMPClient, AlphaVantageClient, TiingoClient

ticker = 'BABA'

# Get quote from FMP
fmp = FMPClient()
fmp_quote = fmp.get_quote(ticker)
print(f"FMP Price: ${fmp_quote[0]['price']}")

# Get daily data from Alpha Vantage
av = AlphaVantageClient()
av_data = av.get_daily(ticker)

# Get news from Tiingo
tiingo = TiingoClient()
news = tiingo.get_news(ticker, limit=5)
```

### Economic Context for Trading

```python
from config.api_clients import FREDClient

fred = FREDClient()

# Get key economic indicators
gdp = fred.get_series('GDP')
inflation = fred.get_series('CPIAUCSL')
unemployment = fred.get_series('UNRATE')
fed_rate = fred.get_series('FEDFUNDS')

# Analyze economic environment
print("Current Economic Data:")
print(f"Latest GDP: {gdp['observations'][-1]['value']}")
print(f"Latest CPI: {inflation['observations'][-1]['value']}")
```

### Crypto + Stock Correlation

```python
from config.api_clients import CoinGeckoClient, FMPClient

# Crypto
crypto = CoinGeckoClient()
btc = crypto.get_coin_price('bitcoin')
eth = crypto.get_coin_price('ethereum')

# Tech stocks
stock = FMPClient()
spy = stock.get_quote('SPY')
qqq = stock.get_quote('QQQ')

print(f"BTC: ${btc['bitcoin']['usd']:,.0f}")
print(f"SPY: ${spy[0]['price']:.2f}")
```

---

## Error Handling

```python
import requests
from typing import Optional, Dict

def safe_api_call(func, *args, **kwargs) -> Optional[Dict]:
    """Wrapper for safe API calls"""
    try:
        return func(*args, **kwargs)
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
    except requests.exceptions.ConnectionError:
        print("Connection Error: Check internet")
    except requests.exceptions.Timeout:
        print("Timeout: API took too long")
    except Exception as e:
        print(f"Error: {e}")
    return None

# Usage
from config.api_clients import FMPClient

client = FMPClient()
quote = safe_api_call(client.get_quote, 'BABA')
if quote:
    print(f"Price: ${quote[0]['price']}")
```

---

## Rate Limiting

```python
import time
from functools import wraps

def rate_limit(calls_per_minute):
    """Decorator to enforce rate limits"""
    min_interval = 60.0 / calls_per_minute
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            wait = min_interval - elapsed
            if wait > 0:
                time.sleep(wait)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator

# Usage with Alpha Vantage (5 calls/min limit)
@rate_limit(calls_per_minute=5)
def get_stock_data(symbol):
    from config.api_clients import AlphaVantageClient
    client = AlphaVantageClient()
    return client.get_daily(symbol)
```

---

## Security Best Practices

1. **Never commit `.env` file** - Already protected by `.gitignore`
2. **Rotate API keys** every 90 days
3. **Monitor usage** to avoid rate limits
4. **Use environment-specific keys** for dev/prod
5. **Never log API keys** in error messages

---

## Troubleshooting

### API Keys Not Loading

```python
from config.api_config import APIConfig

# Check if .env file exists
import os
from pathlib import Path

env_file = Path(__file__).parent.parent / '.env'
print(f".env exists: {env_file.exists()}")

# Print what's loaded
APIConfig.print_status()
```

### Rate Limit Exceeded

```python
# Add delays between requests
import time

for symbol in ['AAPL', 'MSFT', 'GOOGL']:
    quote = client.get_quote(symbol)
    time.sleep(1)  # Wait 1 second between calls
```

### Connection Issues

```python
# Add timeout and retry
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)
```

---

## Additional Resources

- **Project README:** `/README.md` - Alibaba NBS Conference Analysis
- **Test Script:** `test_apis.py` - Validate all API configurations
- **Config Module:** `config/api_config.py` - Centralized key management
- **Client Module:** `config/api_clients.py` - Ready-to-use API clients

---

**Last Updated:** December 13, 2025  
**Maintained By:** Data Lab Team
