# QuantLab Data Lab Environment

## Environment Overview

**Purpose:** Quantitative trading research and analysis workspace focused on discovering statistical edges in momentum trading strategies.

**Location:** `c:\QuantLab\Data_Lab`

**Python Version:** 3.13.5

**Environment Type:** Virtual Environment (.venv)

---

## User Profile

**Trading Style:** Momentum Trader (See [AGENT_CONTEXT.md](AGENT_CONTEXT.md) for detailed profile)

**Focus Areas:**
- Event-driven trading (earnings, economic data, press conferences)
- Gap analysis and continuation patterns
- Statistical edge discovery
- Chinese ADR momentum (BABA, JD, BIDU, PDD)
- Multi-day forward returns analysis

**Timeframes:** Intraday to 5 days (primary), 1-4 weeks (secondary)

---

## Available APIs & Data Sources

### 1. **Alpaca Markets** ✅ CONFIGURED & TESTED
- **Purpose:** Live trading, market data, historical prices
- **Credentials:** Stored in `.env` (ALPACA_API_KEY, ALPACA_API_SECRET)
- **Capabilities:**
  - Historical daily OHLCV data (unlimited lookback)
  - Latest trade prices
  - Multi-symbol snapshots
  - Market clock & calendar
  - Paper trading account (if funded)
- **SDK:** `alpaca-py` and `alpaca-trade-api`
- **Base URL:** `https://paper-api.alpaca.markets` (paper trading)
- **Data URL:** `https://data.alpaca.markets`
- **Client:** `AlpacaClient` in `config/api_clients.py`
- **Tested:** ✅ Working - Retrieved BABA data successfully

**Agent Key Selection:**
- The VSCode agent (and helper scripts) should select Alpaca credentials by checking `ALPACA_ENV` or prompt text.
- Supported modes:
  - `ALPACA_ENV=paper` — load keys from `shared/config/keys/paper.env` (paper trading).
  - `ALPACA_ENV=live` — load keys from `shared/config/keys/live.env` (live trading).
  - Prompt keywords: include `"use paper"` or `"use live"` in your prompt to instruct the agent which account to load.
- Implementation: the agent should call `from shared.config import env_loader; env_loader.set_alpaca_env('paper'|'live')` before constructing `AlpacaClient()` so `AlpacaClient(paper_trading=...)` reads the intended keys.
- Security: keys live in `shared/config/keys/*.env` and are loaded into the process only; avoid printing or committing these files to remote repos.

### 2. **Tiingo** ✅ CONFIGURED
- **Purpose:** Comprehensive stock market data, news
- **Credentials:** Stored in `.env` (TIINGO_API_KEY)
- **Capabilities:**
  - Daily stock prices with extended history
  - Intraday prices (IEX)
  - Crypto prices
  - Stock news feed
  - Ticker metadata
- **Base URL:** `https://api.tiingo.com`
- **Client:** `TiingoClient` in `config/api_clients.py`
- **Used In:** `analyze_baba_nbs.py` - Successfully pulled 20 conferences worth of BABA data

### 3. **Financial Modeling Prep (FMP)** ✅ CONFIGURED
- **Purpose:** Financial statements, company data, ratios
- **Credentials:** Stored in `.env` (FMP_API_KEY)
- **Capabilities:**
  - Real-time stock quotes
  - Income statements, balance sheets, cash flow
  - Financial ratios
  - Company profiles
- **Base URL:** `https://financialmodelingprep.com/api/v3`
- **Client:** `FMPClient` in `config/api_clients.py`

### 4. **Alpha Vantage** ✅ CONFIGURED
- **Purpose:** Stock time series data, technical indicators
- **Credentials:** Stored in `.env` (ALPHA_VANTAGE_API_KEY)
- **Capabilities:**
  - Intraday, daily, weekly, monthly time series
  - Technical indicators
  - Forex and crypto data
- **Base URL:** `https://www.alphavantage.co/query`
- **Client:** `AlphaVantageClient` in `config/api_clients.py`

### 5. **FRED (Federal Reserve)** ✅ CONFIGURED
- **Purpose:** US economic data
- **Credentials:** Stored in `.env` (FRED_API_KEY)
- **Capabilities:**
  - Economic data series (GDP, unemployment, inflation)
  - Series search
  - Historical economic indicators
- **Base URL:** `https://api.stlouisfed.org/fred`
- **Client:** `FREDClient` in `config/api_clients.py`

### 6. **CoinGecko** ✅ CONFIGURED
- **Purpose:** Cryptocurrency market data
- **Credentials:** Stored in `.env` (COINGECKO_API_KEY)
- **Capabilities:**
  - Crypto prices and market data
  - Historical crypto charts
  - Coin lists and metadata
- **Base URL:** `https://api.coingecko.com/api/v3`
- **Client:** `CoinGeckoClient` in `config/api_clients.py`

### 7. **SEC EDGAR** ✅ CONFIGURED
- **Purpose:** SEC filings and corporate disclosures
- **Credentials:** Stored in `.env` (SEC_EDGAR_API_KEY)
- **Capabilities:**
  - Company SEC filings (10-K, 10-Q, 8-K, etc.)
  - Filing search by company/ticker
- **Base URL:** `https://www.sec.gov/cgi-bin/browse-edgar`
- **Client:** `SECEdgarClient` in `config/api_clients.py`

### 8. **Charles Schwab** ✅ CONFIGURED
- **Purpose:** Market data and quotes
- **Credentials:** Stored in `.env` (SCHWAB_API_KEY, SCHWAB_API_SECRET)
- **Capabilities:**
  - Market quotes
  - Multiple symbol quotes
  - Market hours
- **Base URL:** `https://api.schwabapi.com/marketdata/v1`
- **Client:** `SchwabClient` in `config/api_clients.py`

---

## Project Structure

```
Data_Lab/
├── .env                          # API credentials (DO NOT COMMIT)
├── .venv/                        # Python virtual environment
├── requirements.txt              # Python dependencies
│
├── config/                       # API configuration & clients
│   ├── __init__.py
│   ├── api_config.py            # Centralized API key management
│   └── api_clients.py           # Ready-to-use API client classes
│
├── docs/
│   └── API_DOCUMENTATION.md     # Detailed API usage documentation
│
├── AGENT_CONTEXT.md             # User trading profile for AI assistants
├── README.md                     # Main project documentation
├── test_apis.py                 # API validation test suite
│
├── get_nbs_dates.py             # China NBS conference date scraper
├── analyze_baba_nbs.py          # BABA price action analysis on NBS dates
├── nbs_conference_dates.txt     # List of 20 NBS conference dates
├── baba_nbs_analysis.txt        # Full analysis results
├── baba_nbs_analysis.csv        # Analysis in CSV format
│
├── alpaca_examples.py           # Alpaca API usage examples
├── test_alpaca_connection.py    # Alpaca connection tests
├── test_alpaca_full.py          # Comprehensive Alpaca tests
└── test_alpaca_sdk.py           # Alpaca SDK tests (WORKING)
```

---

## Completed Research Projects

### 1. **BABA x China NBS Conference Analysis** ✅ COMPLETE
**File:** `analyze_baba_nbs.py`, `README.md`

**Objective:** Analyze Alibaba (BABA) price action on China National Bureau of Statistics monthly press conference dates.

**Dataset:** 20 NBS conferences (April 2023 - November 2024)

**Key Findings:**
- **Gap Behavior:** 35% up, 40% down, 25% flat
- **Forward Returns:** Avg -1.61% Day 2, -2.56% Day 3 (bearish bias)
- **Best Strategy:** "Fade the Gap Up" - 100% win rate on gaps >2.5%
- **Secondary Strategy:** "Buy Gap Down Reversals" - 67% win rate

**Deliverables:**
- Full statistical analysis with 20 data points
- 3 actionable trading strategies with entry/exit rules
- Case studies of best/worst setups
- Next conference prep checklist (Dec 15-18, 2025)

**Files Generated:**
- `baba_nbs_analysis.txt` - Detailed report
- `baba_nbs_analysis.csv` - Raw data
- `README.md` - Comprehensive trading playbook

---

## Installed Python Packages

**Core Data Science:**
- `requests` - HTTP library for API calls
- `beautifulsoup4` - Web scraping
- `lxml` - XML/HTML parsing
- `python-dotenv` - Environment variable management

**Trading & Market Data:**
- `alpaca-py` - Official Alpaca SDK
- `alpaca-trade-api` - Alternative Alpaca SDK
- `pytz` - Timezone handling for market data

**Standard Library Usage:**
- `datetime`, `timedelta` - Date/time manipulation
- `typing` - Type hints
- `json` - JSON parsing
- `csv` - CSV file handling
- `os`, `pathlib` - File system operations

---

## How to Use This Environment

### 1. **API Client Usage**

```python
# Import configured clients
from config.api_clients import AlpacaClient, TiingoClient, FMPClient

# Alpaca - Historical data
client = AlpacaClient()
bars = client.get_bars('BABA', timeframe='1Day', start='2024-01-01', limit=100)

# Tiingo - Daily prices
tiingo = TiingoClient()
data = tiingo.get_daily_prices('BABA', start_date='2024-01-01', end_date='2024-12-31')

# FMP - Company quote
fmp = FMPClient()
quote = fmp.get_quote('BABA')
```

### 2. **API Configuration Check**

```python
from config.api_config import APIConfig

# Check all API keys
APIConfig.print_status()

# Validate keys
validation = APIConfig.validate_keys()
```

### 3. **Running Existing Scripts**

```bash
# Test all APIs
python test_apis.py

# Get China NBS conference dates
python get_nbs_dates.py

# Analyze BABA on NBS dates
python analyze_baba_nbs.py

# Test Alpaca connection
python test_alpaca_sdk.py
```

### 4. **Environment Variables**

Set for current session (PowerShell):
```powershell
$env:ALPACA_API_KEY_ID="your_key"
$env:ALPACA_SECRET_KEY="your_secret"
```

Stored permanently in `.env` file (loaded automatically):
```
ALPACA_API_KEY=your_key
ALPACA_API_SECRET=your_secret
TIINGO_API_KEY=your_key
# ... etc
```

---

## Common Research Workflows

### Workflow 1: Event Study Analysis
1. **Identify Event Dates** - Scrape or manually collect
2. **Pull Historical Data** - Use Tiingo/Alpaca for OHLCV
3. **Calculate Metrics** - Gaps, intraday moves, forward returns
4. **Statistical Analysis** - Win rates, averages, expectancy
5. **Develop Strategy** - Entry/exit rules, position sizing
6. **Document Findings** - Create comprehensive README

### Workflow 2: Multi-Symbol Comparison
```python
# Get data for Chinese ADRs
from config.api_clients import AlpacaClient
client = AlpacaClient()

symbols = ['BABA', 'JD', 'BIDU', 'PDD']
snapshots = client.get_snapshots(symbols)

# Compare performance
for symbol, data in snapshots.items():
    print(f"{symbol}: ${data['latestTrade']['p']:.2f}")
```

### Workflow 3: Gap Analysis
```python
# Calculate opening gaps
gap_pct = ((open_price - prev_close) / prev_close) * 100
gap_direction = "UP" if gap_pct > 0.5 else "DOWN" if gap_pct < -0.5 else "FLAT"

# Check continuation
intraday_pct = ((close - open) / open) * 100
continuation = (gap_pct > 0 and intraday_pct > 0) or (gap_pct < 0 and intraday_pct < 0)
```

---

## Best Practices

### Data Collection
- **Rate Limiting:** Add `time.sleep(0.5)` between API calls
- **Error Handling:** Always use try/except blocks
- **Data Validation:** Check for empty responses and data quality
- **Caching:** Save results to CSV/JSON to avoid redundant API calls

### Analysis Output
- **Quantify Everything:** Win rates, averages, sample sizes
- **Show Examples:** Include specific dates and price movements
- **Risk Management:** Always include stop-loss and position sizing
- **Actionable:** Translate findings into tradeable rules

### Code Organization
- **Reusable Functions:** Put common logic in functions
- **Type Hints:** Use typing for function parameters
- **Documentation:** Clear docstrings for complex functions
- **Separation:** Keep data collection, analysis, and output separate

---

## Quick Reference Commands

### Virtual Environment
```powershell
# Activate (if needed)
.\.venv\Scripts\Activate.ps1

# Install package
pip install package-name

# Run Python script
python script_name.py
```

### API Testing
```powershell
# Test all APIs
python test_apis.py

# Test Alpaca specifically
python test_alpaca_sdk.py
```

### Data Analysis
```powershell
# Get NBS dates
python get_nbs_dates.py

# Analyze BABA
python analyze_baba_nbs.py
```

---

## Current Focus & Next Steps

### Active Research
- China NBS conference impact on Chinese ADRs ✅ COMPLETE
- Next conference: December 15-18, 2025 📅 UPCOMING

### Potential Research Areas
- **Earnings Gap Analysis:** Study gap behavior on earnings releases
- **Sector Rotation:** Compare Chinese ADR performance patterns
- **Fed Announcement Impact:** How rate decisions affect momentum stocks
- **IPO Lockup Expirations:** Price action around lockup dates
- **Short Interest Patterns:** Relationship between SI and momentum

### Tools to Build
- Automated gap scanner for daily setups
- Multi-day forward return calculator
- Event calendar integration (earnings, economic data)
- Real-time alert system for trading setups

---

## API Limitations & Notes

### Alpaca
- **Free Tier:** 15-minute delayed intraday data
- **Daily Bars:** Unlimited historical data ✅
- **Best For:** Historical analysis, daily data research

### Tiingo
- **Rate Limits:** Check tier for specific limits
- **Best For:** Long-term historical data, news

### FMP
- **Free Tier:** 250 requests/day
- **Best For:** Fundamental data, company profiles

### Alpha Vantage
- **Free Tier:** 25 requests/day, 5 requests/minute
- **Best For:** Technical indicators, limited use

---

## Security Notes

⚠️ **IMPORTANT:**
- `.env` file contains API keys - **NEVER commit to Git**
- Add `.env` to `.gitignore`
- API keys are personal - do not share
- Use paper trading for testing strategies

---

## Support Files

- **AGENT_CONTEXT.md** - Detailed user trading profile and preferences
- **API_DOCUMENTATION.md** - Comprehensive API usage guide (in docs/)
- **README.md** - Main project documentation with BABA/NBS analysis

---

## Version Info

**Created:** December 13, 2025  
**Python:** 3.13.5  
**Environment:** Windows 11, PowerShell  
**Status:** Fully operational with 8 configured APIs

---

*For questions about trading strategies and analysis preferences, see [AGENT_CONTEXT.md](AGENT_CONTEXT.md)*
