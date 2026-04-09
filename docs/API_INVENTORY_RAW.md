# API Inventory - QuantLab Data_Lab

**Generated:** December 14, 2025  
**Purpose:** Complete inventory of all APIs and data sources used in this workspace

---

## Security Notice

⚠️ **SECURITY WARNING:** Credentials detected in `.env` file (root directory)  
**File:** `C:\QuantLab\Data_Lab\.env`  
**Status:** ✅ File is properly excluded from git (checked `.gitignore`)  
**Action Required:** None - credentials are stored correctly in environment file

---

## Executive Summary

**Total APIs Configured:** 9  
**Total APIs Actively Used:** 3  
**Primary Data Source:** yfinance (Yahoo Finance) - used in 2/2 completed studies  
**Secondary Data Source:** Tiingo - used in 1/2 studies (BABA/NBS)

### Usage Breakdown:
- **Daily OHLCV:** yfinance (primary), Tiingo (secondary), Alpaca (configured but unused)
- **Intraday OHLCV:** None currently used (Alpaca/Tiingo/Alpha Vantage available)
- **Macro/Fed Data:** FRED configured but not yet used
- **Volatility Proxies:** None used (VIX/MOVE not referenced in any study)
- **News/Catalysts:** Web scraping (China NBS website) - no API-based news yet
- **Fundamentals:** FMP configured but not yet used

---

## API Inventory by Category

### 1. Market Data APIs

#### 1.1 yfinance (Yahoo Finance)
**Status:** ✅ ACTIVELY USED (PRIMARY DATA SOURCE)

**What It's Used For:**
- Daily OHLCV data (open, high, low, close, volume)
- Adjusted close prices for split/dividend adjustments
- Historical price data with unlimited lookback
- Float and shares outstanding data

**Referenced In:**
- `studies/cannabis_rallies/cannabis_rally_analysis.py`
  - Lines 14, 21: `import yfinance as yf`
  - Line 69: `data = yf.download(ticker, start=lookback_start_dt, end=rally_end, progress=False)`
  - Used to download TLRY, CGC, MSOS historical data for rally comparison
  
- `studies/cannabis_rallies/forward_returns_analysis.py`
  - Line 32: `df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)`
  - Used to calculate 1-day, 3-day, 5-day forward returns from rally endpoints
  
- `studies/cannabis_rallies/check_float_data.py`
  - Lines 29-30: `yf.download("TLRY", ...)` and `yf.download("CGC", ...)`
  - Used to retrieve volume data for float/liquidity comparison

**Authentication:** None required (free public API)

**Data Retrieved:**
- Tickers: TLRY, CGC, MSOS
- Periods: July-Dec 2018 (TLRY, CGC), Oct 2020-Jun 2021 (MSOS)
- Fields: Open, High, Low, Close, Volume, Adj Close
- Frequency: Daily bars

**Strengths:**
- No API key required
- Reliable historical data
- Easy to use (`yf.download()` one-liner)
- Handles corporate actions (splits, dividends)

**Weaknesses:**
- Rate limits (throttling on excessive requests)
- No official API documentation (community-maintained library)
- Occasional data gaps or errors
- No real-time data (15-20 min delay)

---

#### 1.2 Tiingo API
**Status:** ✅ CONFIGURED & ACTIVELY USED

**What It's Used For:**
- Daily OHLCV data for Chinese ADRs (BABA)
- Historical price data with extended lookback
- Backup data source if primary fails

**Referenced In:**
- `shared/config/api_clients.py`
  - Lines 398-440: `TiingoClient` class definition
  - Methods: `get_daily_prices()`, `get_intraday_prices()`, `get_ticker_metadata()`, `get_news()`, `get_crypto_prices()`
  
- `shared/config/api_config.py`
  - Lines 52-53: API key and base URL configuration
  - `TIINGO_API_KEY = os.getenv('TIINGO_API_KEY')`
  - `TIINGO_BASE_URL = 'https://api.tiingo.com/tiingo'`
  
- `studies/baba_nbs/analyze_baba_nbs.py`
  - Line 10: `from config.api_clients import TiingoClient, FMPClient`
  - Line 43: `client = TiingoClient()`
  - Used to retrieve BABA price data for 20 China NBS conference dates

**Authentication:** Token-based (Bearer token in header)
- Method: Environment variable → `.env` file → `APIConfig` class
- Header: `Authorization: Token {api_key}`

**Base URLs:**
- Daily prices: `https://api.tiingo.com/tiingo/daily/{ticker}/prices`
- Intraday: `https://api.tiingo.com/iex/{ticker}/prices`
- News: `https://api.tiingo.com/tiingo/news`

**Data Retrieved:**
- Ticker: BABA (Alibaba)
- Period: April 2023 - November 2024 (20 conference dates)
- Purpose: Gap analysis, continuation patterns, forward returns

**Rate Limits:** 500 requests/hour, 5000 requests/day

---

#### 1.3 Alpaca Markets API
**Status:** ✅ CONFIGURED & TESTED (Not yet used in studies)

**What It's Used For:**
- Historical daily OHLCV data
- Intraday bars (1min, 5min, 15min, 1hour)
- Real-time trades and quotes
- Market snapshots
- Paper trading execution (if needed)

**Referenced In:**
- `shared/config/api_clients.py`
  - Lines 11-168: `AlpacaClient` class definition
  - Account methods: `get_account()`, `get_positions()`, `place_order()`, `cancel_order()`
  - Market data methods: `get_bars()`, `get_latest_trade()`, `get_snapshot()`, `get_snapshots()`
  - Calendar methods: `get_clock()`, `get_calendar()`
  
- `shared/config/api_config.py`
  - Lines 19-23: API configuration
  - `ALPACA_API_KEY`, `ALPACA_API_SECRET` from `.env`
  - `ALPACA_BASE_URL = 'https://paper-api.alpaca.markets'`
  - `ALPACA_DATA_URL = 'https://data.alpaca.markets'`
  
- `scratch/test_alpaca_sdk.py`
  - Lines 6-9: Direct SDK imports (`alpaca.data.historical`, `alpaca.trading.client`)
  - Successfully tested: Retrieved BABA 7-day history ($155.68 latest price)

**Authentication:** API Key + Secret (dual header method)
- Method: Environment variables from `.env`
- Headers: `APCA-API-KEY-ID` and `APCA-API-SECRET-KEY`

**Capabilities:**
- Historical bars: Unlimited lookback
- Intraday data: 1-minute resolution
- Multi-symbol snapshots: Compare multiple tickers simultaneously
- Trading: Place orders, check positions (paper trading active)

**Status:** Tested and working but not yet integrated into any studies

---

#### 1.4 Alpha Vantage API
**Status:** ✅ CONFIGURED (Not yet used)

**What It's Used For:**
- Stock time series data (intraday, daily, weekly, monthly)
- Technical indicators (potential future use)
- Forex and crypto data

**Referenced In:**
- `shared/config/api_clients.py`
  - Lines 273-316: `AlphaVantageClient` class definition
  - Methods: `get_intraday()`, `get_daily()`, `get_weekly()`, `get_monthly()`
  
- `shared/config/api_config.py`
  - Lines 40-41: Configuration
  - `ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')`
  - `ALPHA_VANTAGE_BASE_URL = 'https://www.alphavantage.co/query'`

**Authentication:** API key in URL parameter
- Method: `?apikey={api_key}` query string

**Base URL:** `https://www.alphavantage.co/query`

**Rate Limits:** 5 requests/minute, 500 requests/day (strict limits)

**Status:** Configured but not used in any study yet

---

#### 1.5 Charles Schwab API
**Status:** ✅ CONFIGURED (Not yet used)

**What It's Used For:**
- Market quotes
- Market hours information
- Potential trading integration

**Referenced In:**
- `shared/config/api_clients.py`
  - Lines 375-397: `SchwabClient` class definition
  - Methods: `get_quote()`, `get_quotes()`, `get_market_hours()`
  
- `shared/config/api_config.py`
  - Lines 48-50: Configuration
  - `SCHWAB_API_KEY`, `SCHWAB_API_SECRET` from `.env`
  - `SCHWAB_BASE_URL = 'https://api.schwabapi.com/marketdata/v1'`

**Authentication:** Bearer token (OAuth-like)
- Headers: `Authorization: Bearer {api_key}`

**Status:** Configured but not used in any study yet

---

### 2. Fundamental Data APIs

#### 2.1 Financial Modeling Prep (FMP)
**Status:** ✅ CONFIGURED (Backup for Tiingo)

**What It's Used For:**
- Company financials (income statement, balance sheet, cash flow)
- Financial ratios
- Company profiles
- Real-time stock quotes (fallback option)

**Referenced In:**
- `shared/config/api_clients.py`
  - Lines 220-271: `FMPClient` class definition
  - Methods: `get_quote()`, `get_income_statement()`, `get_balance_sheet()`, `get_cash_flow()`, `get_financial_ratios()`, `get_company_profile()`
  
- `shared/config/api_config.py`
  - Lines 37-38: Configuration
  - `FMP_API_KEY = os.getenv('FMP_API_KEY')`
  - `FMP_BASE_URL = 'https://financialmodelingprep.com/api/v3'`
  
- `studies/baba_nbs/analyze_baba_nbs.py`
  - Line 10: `from config.api_clients import TiingoClient, FMPClient`
  - Line 187: `client = FMPClient()` (used as fallback if Tiingo fails)
  - Lines 182-183: Error handling mentions "alternative API (FMP)"

**Authentication:** API key in URL parameter
- Method: `?apikey={api_key}` query string

**Base URL:** `https://financialmodelingprep.com/api/v3`

**Rate Limits:** 250 requests/day (free tier)

**Status:** Configured and referenced as fallback, but not actively used in current studies

---

### 3. Economic Data APIs

#### 3.1 FRED (Federal Reserve Economic Data)
**Status:** ✅ CONFIGURED (Not yet used)

**What It's Used For:**
- US economic indicators (GDP, unemployment, inflation, interest rates)
- Federal Reserve data series
- Macro regime analysis (potential future use)

**Referenced In:**
- `shared/config/api_clients.py`
  - Lines 318-357: `FREDClient` class definition
  - Methods: `get_series()`, `search_series()`, `get_series_info()`
  
- `shared/config/api_config.py`
  - Lines 43-44: Configuration
  - `FRED_API_KEY = os.getenv('FRED_API_KEY')`
  - `FRED_BASE_URL = 'https://api.stlouisfed.org/fred'`

**Authentication:** API key in URL parameter
- Method: `?api_key={api_key}` query string

**Base URL:** `https://api.stlouisfed.org/fred`

**Common Series IDs (potential future use):**
- `VIXCLS`: CBOE Volatility Index (VIX)
- `DGS10`: 10-Year Treasury Constant Maturity Rate
- `DFF`: Federal Funds Effective Rate
- `UNRATE`: Unemployment Rate
- `CPIAUCSL`: Consumer Price Index

**Rate Limits:** Unlimited (very generous)

**Status:** Configured but not used. Mentioned in README.md (line 311) as potential filter: "only works when VIX < 20"

---

### 4. Cryptocurrency APIs

#### 4.1 CoinGecko API
**Status:** ✅ CONFIGURED (Not yet used)

**What It's Used For:**
- Cryptocurrency prices
- Historical crypto market data
- Coin lists and metadata

**Referenced In:**
- `shared/config/api_clients.py`
  - Lines 193-218: `CoinGeckoClient` class definition
  - Methods: `get_coin_price()`, `get_market_data()`, `get_coin_list()`
  
- `shared/config/api_config.py`
  - Lines 31-32: Configuration
  - `COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')`
  - `COINGECKO_BASE_URL = 'https://api.coingecko.com/api/v3'`

**Authentication:** API key in header
- Header: `x-cg-demo-api-key: {api_key}`

**Base URL:** `https://api.coingecko.com/api/v3`

**Rate Limits:** 10-50 calls/minute (depending on tier)

**Status:** Configured but not used in any study yet

---

### 5. Regulatory/Filing APIs

#### 5.1 SEC EDGAR API
**Status:** ✅ CONFIGURED (Not yet used)

**What It's Used For:**
- SEC filings (10-K, 10-Q, 8-K, etc.)
- Company filings search
- Regulatory data

**Referenced In:**
- `shared/config/api_clients.py`
  - Lines 170-181: `SECEdgarClient` class definition
  - Methods: `get_company_filings()`
  
- `shared/config/api_config.py`
  - Lines 26-27: Configuration
  - `SEC_EDGAR_API_KEY = os.getenv('SEC_EDGAR_API_KEY')`
  - `SEC_EDGAR_BASE_URL = 'https://www.sec.gov/cgi-bin/browse-edgar'`

**Authentication:** User-Agent header (unique identifier required)
- Header: `User-Agent: DataLab {api_key}`

**Base URL:** `https://www.sec.gov/cgi-bin/browse-edgar`

**Rate Limits:** 10 requests/second

**Status:** Configured but not used in any study yet

---

### 6. Web Scraping / Direct HTTP Requests

#### 6.1 China National Bureau of Statistics (NBS) Website
**Status:** ✅ ACTIVELY USED

**What It's Used For:**
- Scraping China NBS press conference dates
- Identifying economic data release events
- Event-driven trading catalyst identification

**Referenced In:**
- `studies/baba_nbs/get_nbs_dates.py`
  - Line 6: `import requests`
  - Lines 23-29: Web scraping implementation
  - Base URL: `https://www.stats.gov.cn/english/PressRelease/`
  - Line 29: `response = requests.get(base_url, timeout=10)`
  - Line 74: Fallback Chinese site scraping

**Authentication:** None (public website)

**Method:** HTTP GET requests with BeautifulSoup HTML parsing

**Data Extracted:**
- 20 conference dates from April 2023 to November 2024
- Output saved to: `studies/baba_nbs/nbs_conference_dates.txt`

**Strengths:**
- Direct access to official government data
- No API key required
- Historical data available

**Weaknesses:**
- HTML structure changes break scraper
- No API rate limits but should be respectful
- Requires manual updates if site changes

---

## Authentication Methods Summary

| API | Auth Type | Config Location | ENV Variable(s) |
|-----|-----------|-----------------|-----------------|
| **yfinance** | None | N/A | None |
| **Tiingo** | Bearer Token | `shared/config/api_config.py` | `TIINGO_API_KEY` |
| **Alpaca** | Dual Header | `shared/config/api_config.py` | `ALPACA_API_KEY`, `ALPACA_API_SECRET` |
| **Alpha Vantage** | Query Param | `shared/config/api_config.py` | `ALPHA_VANTAGE_API_KEY` |
| **Schwab** | Bearer Token | `shared/config/api_config.py` | `SCHWAB_API_KEY`, `SCHWAB_API_SECRET` |
| **FMP** | Query Param | `shared/config/api_config.py` | `FMP_API_KEY` |
| **FRED** | Query Param | `shared/config/api_config.py` | `FRED_API_KEY` |
| **CoinGecko** | Header | `shared/config/api_config.py` | `COINGECKO_API_KEY` |
| **SEC EDGAR** | User-Agent | `shared/config/api_config.py` | `SEC_EDGAR_API_KEY` |
| **NBS Website** | None | N/A | None |

### Credential Storage Architecture:
1. **Source:** `.env` file in root directory
2. **Loading:** `python-dotenv` library loads variables
3. **Access:** `shared/config/api_config.py` → `APIConfig` class
4. **Distribution:** Individual client classes in `shared/config/api_clients.py`

---

## Usage Statistics by Study

### Study 1: BABA x China NBS Conference Analysis
**Files:** `studies/baba_nbs/`

**APIs Used:**
1. **China NBS Website (web scraping)** - Primary
   - Purpose: Conference date collection
   - File: `get_nbs_dates.py`
   - Dates collected: 20
   
2. **Tiingo API** - Primary
   - Purpose: BABA daily OHLCV data
   - File: `analyze_baba_nbs.py`
   - Data points: 20 conference dates + surrounding days
   
3. **FMP API** - Fallback (not actively triggered)
   - Purpose: Backup if Tiingo fails
   - File: `analyze_baba_nbs.py` (line 187)

### Study 2: Cannabis Rally Comparison
**Files:** `studies/cannabis_rallies/`

**APIs Used:**
1. **yfinance (Yahoo Finance)** - Exclusive
   - Purpose: Historical daily OHLCV for TLRY, CGC, MSOS
   - Files:
     - `cannabis_rally_analysis.py` (main rally comparison)
     - `forward_returns_analysis.py` (post-rally returns)
     - `check_float_data.py` (volume/float comparison)
   - Tickers: TLRY, CGC, MSOS
   - Period: July-Dec 2018, Oct 2020-Jun 2021
   - Total days downloaded: ~425 trading days across 3 tickers

---

## Recommended Single Source of Truth

### Daily OHLCV (Primary Use Case)
**Recommendation: yfinance (Yahoo Finance)**

**Why:**
- ✅ Already used successfully in 1 of 2 studies
- ✅ No API key required (zero friction)
- ✅ Unlimited lookback for historical data
- ✅ Handles corporate actions (splits, dividends) automatically
- ✅ Simple one-line implementation: `yf.download(ticker, start, end)`
- ✅ Fast and reliable for daily bars

**Fallback:** Tiingo (already configured and tested)

**Use Case:** When you need verified data or yfinance has gaps

---

### Intraday OHLCV
**Recommendation: Alpaca Markets**

**Why:**
- ✅ Already configured and tested
- ✅ 1-minute resolution available
- ✅ Unlimited historical intraday data
- ✅ No rate limit issues for reasonable usage
- ✅ Can also use for paper trading if needed

**Alternative:** Tiingo IEX intraday endpoint

**Use Case:** Gap analysis, intraday continuation patterns, opening range studies

---

### Macro/Fed Data
**Recommendation: FRED API**

**Why:**
- ✅ Already configured
- ✅ Official Federal Reserve data (most authoritative)
- ✅ Unlimited API calls
- ✅ Easy to use (`FREDClient.get_series(series_id)`)
- ✅ Comprehensive coverage (500,000+ economic series)

**Key Series for Momentum Trading:**
- `VIXCLS` - VIX volatility index (regime filter)
- `DGS10` - 10-year Treasury rate (risk-on/risk-off)
- `DFF` - Fed Funds Rate (monetary policy)
- `BAMLH0A0HYM2` - High Yield spread (credit conditions)

**Use Case:** Filter trades by macro regime (e.g., "only trade when VIX < 20")

---

### Volatility Regime Proxies
**Recommendation: FRED API (VIX series) + yfinance (^VIX ticker)**

**Why:**
- ✅ FRED has official CBOE VIX data: `VIXCLS` series
- ✅ yfinance can get ^VIX directly with same code as stocks
- ✅ No need for separate API

**Implementation:**
```python
import yfinance as yf

# Get VIX via yfinance (easiest)
vix = yf.download('^VIX', start='2023-01-01', end='2024-12-31')

# Or use FRED for official data
from shared.config.api_clients import FREDClient
fred = FREDClient()
vix_data = fred.get_series('VIXCLS')
```

**Additional Volatility Proxies:**
- `^VIX` - CBOE Volatility Index (equity volatility)
- `^MOVE` - ICE BofA MOVE Index (bond volatility) - yfinance
- `^VXN` - CBOE Nasdaq Volatility Index - yfinance
- `VXTLT` - 20+ Year Treasury Bond ETF Volatility (FRED series)

**Use Case:** Regime-based trading filters, risk management

---

### News/Catalysts
**Recommendation: Tiingo News API (configured but not yet used)**

**Why:**
- ✅ Already configured and integrated
- ✅ 500 requests/hour, 5000/day (generous)
- ✅ Covers stocks, crypto, global news
- ✅ Timestamps allow event alignment with price action

**Alternative:** Continue web scraping for specific sources (China NBS works well)

**Implementation:**
```python
from shared.config.api_clients import TiingoClient

client = TiingoClient()
news = client.get_news(tickers='BABA', limit=50)
```

**Use Case:**
- Identify earnings dates, FDA approvals, M&A announcements
- Align news timestamps with gap/continuation analysis
- Build event-driven trade alerts

---

### Fundamentals (If Needed)
**Recommendation: Financial Modeling Prep (FMP)**

**Why:**
- ✅ Already configured
- ✅ 250 requests/day sufficient for occasional use
- ✅ Good coverage of financials, ratios, profiles

**Use Case:** Filter momentum plays by fundamental quality (e.g., "only trade stocks with positive earnings")

---

## Implementation Priority

### Already Working (Keep As-Is)
1. ✅ **yfinance** - Daily OHLCV (primary)
2. ✅ **Tiingo** - BABA data, news (backup)
3. ✅ **NBS web scraping** - Conference dates

### Should Add Next (High Value)
1. 🔜 **FRED** - Macro regime filters (VIX, interest rates)
   - Add to existing studies: "Only trade BABA fade when VIX < 25"
   - Create new study: "SPY performance on FOMC days by VIX regime"

2. 🔜 **Alpaca Intraday** - Gap behavior analysis
   - Upgrade BABA study: Add opening 15-min high/low after gap
   - New study: "Intraday reversal patterns after morning spike"

3. 🔜 **Tiingo News** - Catalyst identification
   - Tag each extreme volume day with news event
   - Measure return/volume by news type

### Lower Priority (Nice to Have)
4. ⏸️ **FMP Fundamentals** - Quality filters (when needed)
5. ⏸️ **Alpha Vantage** - Redundant with yfinance (keep as extreme fallback)
6. ⏸️ **Schwab** - Only if live trading becomes priority
7. ⏸️ **CoinGecko** - Only for crypto studies
8. ⏸️ **SEC EDGAR** - Only for fundamental deep dives

---

## Security Best Practices

### ✅ Current Implementation (Good)
1. All credentials stored in `.env` file
2. `.env` excluded from git via `.gitignore`
3. Environment variables loaded via `python-dotenv`
4. Centralized access through `APIConfig` class
5. No hardcoded credentials in any `.py` files

### 🔒 Additional Recommendations
1. **Rotate API keys periodically** (every 3-6 months)
2. **Use read-only keys** where possible (Alpaca has paper trading vs live)
3. **Monitor API usage** to detect unauthorized access
4. **Add `.env.example`** file with dummy values for repo sharing
5. **Never commit `.env`** to version control (already implemented ✅)

---

## Rate Limit Management

### Current Status
No rate limit issues encountered in current studies.

### If Issues Arise
1. **yfinance throttling** → Add `time.sleep(1)` between requests
2. **Tiingo 500/hour limit** → Cache results, batch requests
3. **Alpha Vantage 5/min** → Switch to Alpaca or yfinance
4. **FMP 250/day** → Use only for fundamentals, not price data

### Caching Strategy (Future Enhancement)
Consider adding local CSV cache:
```python
# Check cache first
if os.path.exists(f'{ticker}_{date}_cache.csv'):
    return pd.read_csv(cache_file)
else:
    data = yf.download(ticker, start, end)
    data.to_csv(cache_file)
    return data
```

---

## API Health Check

### Test All APIs
```powershell
cd C:\QuantLab\Data_Lab
.venv\Scripts\Activate.ps1
python scratch/test_apis.py
```

**Expected Output:**
- ✅ Alpaca: Configured
- ✅ Tiingo: Configured
- ✅ FMP: Configured
- ✅ Alpha Vantage: Configured
- ✅ FRED: Configured
- ✅ CoinGecko: Configured
- ✅ SEC EDGAR: Configured
- ✅ Schwab: Configured

### Individual API Tests
```python
# Test yfinance
import yfinance as yf
df = yf.download('BABA', start='2024-01-01', end='2024-12-31')
print(f"Retrieved {len(df)} days of BABA data")

# Test Tiingo
from shared.config.api_clients import TiingoClient
client = TiingoClient()
data = client.get_daily_prices('BABA', start_date='2024-01-01')
print(f"Tiingo API working: {len(data)} data points")

# Test FRED
from shared.config.api_clients import FREDClient
fred = FREDClient()
vix = fred.get_series('VIXCLS')
print(f"FRED API working: Retrieved VIX data")
```

---

## Future API Additions (Roadmap)

### High Priority
1. **Polygon.io** - Real-time and historical market data
   - Better alternative to Alpaca for high-frequency data
   - More comprehensive options data
   
2. **NewsAPI.org** - Broader news coverage
   - Alternative to Tiingo for catalyst identification

### Medium Priority
3. **Quandl/Nasdaq Data Link** - Alternative economic data
4. **IEX Cloud** - Real-time market data
5. **Benzinga** - Real-time news and events

### Low Priority
6. **Twitter/X API** - Sentiment analysis (if X removes restrictions)
7. **Reddit API** - WallStreetBets sentiment tracking
8. **Discord/Telegram bots** - Real-time trade alerts

---

## Changelog

**2025-12-14:** Initial API inventory created
- Documented 9 configured APIs
- Identified 3 actively used data sources (yfinance, Tiingo, NBS scraping)
- No security issues found
- Recommended defaults for each data category

---

**Document Status:** ✅ Complete  
**Next Review:** 2025-03-14 (or when new API is added)  
**Maintainer:** User + AI Assistant (GitHub Copilot)
