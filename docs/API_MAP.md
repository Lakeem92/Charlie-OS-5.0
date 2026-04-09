# API Map - Data Source Routing Guide

**Purpose:** Single source of truth for all data sources in QuantLab Data_Lab  
**Audience:** AI agents, trading researchers, automation scripts  
**Last Updated:** December 14, 2025

---

## What This Document Does

This map tells you **exactly which data source to use** for every type of analysis. No guessing, no trial-and-error. Follow this routing table, and you'll always get clean, reliable data.

**Key Principle:** Use what's already working. Don't add new data sources unless absolutely necessary.

---

## Default Routing Table

### CRITICAL: Study Type Routing Rules

**All volatility, TTP (time-to-profit), indicator evaluation, honesty tests, and return calculations MUST use Alpaca price data by default unless explicitly overridden.**

This ensures:
- Consistent price source across analysis and future execution
- No vendor discrepancies in forward returns or drawdown calculations
- Reproducible results when transitioning from backtest to paper/live trading
- Alignment with the same data feed that will be used for order execution

**Approved study types requiring Alpaca:**
- `volatility` - Any volatility calculation or regime analysis
- `returns` - Forward returns, holding period returns, drawdown analysis
- `indicator` - Indicator honesty tests, edge detection, signal evaluation
- `honesty_test` - Behavioral separation tests for indicators
- `ttp` - Time-to-profit studies

**Exception:** yfinance may ONLY be used for these study types when:
1. Explicitly overridden with `source='yfinance'` parameter
2. A warning is logged explaining why Alpaca is not being used
3. The symbol is not available on Alpaca (e.g., indices like ^VIX)

---

### Daily OHLCV (End-of-Day Prices)
**When:** Analyzing daily price action, gaps, multi-day forward returns, volume patterns

| Priority | Source | Use When | Don't Use When |
|----------|--------|----------|----------------|
| **1st: Alpaca** | US equities (all studies) | Need consistent daily bars | Non-US symbols or indices |
| **2nd: Tiingo** | Alpaca rate limited or gaps | Need verified data, news integration | Free tier rate limit hit |
| **3rd: yfinance** | Indices/proxies or quick checks | Need ^VIX, ^SPX, non-US symbols | Production analysis |

**Default Code:**
```python
from shared.config.api_clients import AlpacaClient

client = AlpacaClient()
data = client.get_bars('BABA', timeframe='1Day', start='2024-01-01', end='2024-12-31', limit=10000)
```

**Why Alpaca First:**
- One consistent price source across daily + intraday
- Alignment with future execution (same API for data + trading)
- Cleaner comparison across studies (no source discrepancies)
- Handles splits/dividends automatically
- Unlimited historical lookback

**When yfinance Is Acceptable:**
- **Indices and volatility symbols:** `^VIX`, `^MOVE`, `^VXN`, `^GSPC` (not available on Alpaca)
- **Quick exploratory analysis:** Testing ideas before formalizing study
- **Non-US symbols:** Chinese domestic A-shares, European stocks not on US exchanges
- **Fallback:** When Alpaca is down or rate limited

**Known Limits:**
- Requires API key (already in `.env`)
- US market equities only (no direct access to indices like ^VIX)
- Free tier sufficient for research use

---

### Intraday OHLCV (Minute/Hour Bars)
**When:** Opening range studies, gap-and-go analysis, intraday continuation patterns

| Priority | Source | Resolution | Use When |
|----------|--------|------------|----------|
| **1st: Alpaca** | 1min, 5min, 15min, 1hour | Need US equities intraday | Need crypto or forex |
| **2nd: Tiingo IEX** | Real-time snapshot | Need quick check | Need historical intraday |

**Default Code:**
```python
from shared.config.api_clients import AlpacaClient

client = AlpacaClient()
bars = client.get_bars('BABA', timeframe='5Min', start='2024-12-10', limit=100)
```

**Why Alpaca Is Canonical:**
- Same price source for daily + intraday = no discrepancies
- Already configured and tested (BABA 7-day history retrieved successfully)
- 1-minute resolution available
- Unlimited historical lookback
- Future-ready for paper trading and execution

**Known Limits:**
- US market hours only (9:30 AM - 4:00 PM ET)
- Requires API key (already in `.env`)
- Free tier sufficient for research use

---

### Macro/Fed Data (Economic Indicators)
**When:** Filtering trades by regime (VIX, rates, Fed policy), macro event studies

| Priority | Source | Series Available | Use When |
|----------|--------|------------------|----------|
| **1st: FRED** | 500,000+ economic series | Need official Fed data | Need real-time (20 min delay) |
| **2nd: yfinance** | Major indices only (^VIX, ^DXY) | Need quick proxy | Need granular FRED series |

**Default Code:**
```python
from shared.config.api_clients import FREDClient

fred = FREDClient()
vix_data = fred.get_series('VIXCLS')  # Official VIX daily close
```

**Why FRED First:**
- Official Federal Reserve data (most authoritative)
- Unlimited API calls (no rate limits)
- 500,000+ series available
- Already configured, never used yet (ready to go)

**Known Limits:**
- Daily data only (no intraday)
- 1-day lag on most series
- US-focused (limited international data)

---

### Volatility Proxies (Regime Filters)
**When:** Adding "only trade when VIX < 20" filters, measuring market stress

| Symbol/Series | Source | What It Measures | Use When |
|---------------|--------|------------------|----------|
| **VIXCLS** | FRED | CBOE VIX daily close (official) | Need authoritative data |
| **^VIX** | yfinance (index proxy) | VIX index (quick check) | Exploratory or alongside equity proxies |
| **^MOVE** | yfinance (index proxy) | Bond market volatility | Trading fixed income or macro |
| **^VXN** | yfinance (index proxy) | Nasdaq volatility | Tech-heavy strategies |
| **DGS10** | FRED | 10-year Treasury yield | Risk-on/risk-off filter |

**Default Code:**
```python
# Most Authoritative: Use FRED for official VIX
from shared.config.api_clients import FREDClient
fred = FREDClient()
vix_official = fred.get_series('VIXCLS')

# Fallback/Convenience: Use yfinance for index proxies
import yfinance as yf
vix = yf.download('^VIX', start='2024-01-01', end='2024-12-31')  # Index proxy only
```

**Regime Examples:**
- VIX < 15: Low volatility, trend-following works
- VIX 15-25: Normal market, most strategies work
- VIX > 25: High volatility, fade extremes, tight stops
- VIX > 40: Panic mode, avoid or size down dramatically

---

## Why Alpaca Is Canonical

**For US equities, Alpaca is now the primary data source for both daily and intraday OHLCV.** This normalization provides three critical advantages:

### 1. One Consistent Price Source
**Problem:** Using yfinance for daily and Alpaca for intraday creates discrepancies:
- Different data vendors may have slightly different OHLC values due to adjustments, splits, or data feeds
- Comparing a daily gap (from yfinance) to intraday continuation (from Alpaca) introduces potential mismatches
- Hard to debug: "Is this a real alpha signal or just a data artifact?"

**Solution:** Alpaca provides both daily (`1Day`) and intraday (`1Min`, `5Min`, `15Min`, `1Hour`) bars from the same feed:
- No vendor discrepancies across timeframes
- Seamless transition from daily analysis to intraday confirmation
- What you backtest is what you'll trade

### 2. Alignment with Future Execution
**Problem:** If you backtest on yfinance but execute on Alpaca, you're testing on different data than you'll trade:
- yfinance uses Yahoo Finance's adjusted close (proprietary adjustments)
- Alpaca uses SIP (Securities Information Processor) consolidated feed or IEX
- Forward returns calculated on yfinance may not match live returns on Alpaca

**Solution:** By using Alpaca for historical analysis, you're testing on the same data feed you'll use for paper/live trading:
- No surprises when transitioning from research to execution
- Same split adjustments, same corporate actions, same data latency
- True "walk-forward" compatibility

### 3. Cleaner Comparison Across Studies
**Problem:** If Study A uses yfinance, Study B uses Tiingo, and Study C uses Alpaca, comparing results is messy:
- "BABA gapped +3.2% on yfinance but +3.0% on Alpaca — which is real?"
- Inconsistent volume reporting across vendors
- Hard to build a meta-study aggregating multiple analyses

**Solution:** Standardizing on Alpaca for all US equity studies means:
- All studies use the same price source = apples-to-apples comparison
- Easier to aggregate results, build composite signals, or compare edges
- One source of truth for "what actually happened" on any given day

---

**When to Still Use yfinance:**
- Indices (`^VIX`, `^GSPC`, `^IXIC`) not available on Alpaca
- Non-US equities not traded on US exchanges
- Quick exploratory work before formalizing a study
- Fallback if Alpaca is down or rate limited

**Bottom line:** For production-quality US equity research, default to Alpaca. Use yfinance only for specific cases where Alpaca doesn't support the symbol type.

---

### News/Catalysts (Event Identification)
**When:** Finding earnings dates, FDA approvals, economic releases, conference announcements

| Priority | Source | Coverage | Use When |
|----------|--------|----------|----------|
| **1st: Web Scraping** | Official sources (NBS, FDA.gov, etc.) | Specific events | Source has public data |
| **2nd: Tiingo News** | Stocks, crypto, global news | Broad coverage needed | Rate limits allow (500/hr) |
| **3rd: Manual Calendar** | User provides dates | High-value events | No API has the data |

**Default Code (Web Scraping):**
```python
import requests
from bs4 import BeautifulSoup

url = "https://www.stats.gov.cn/english/PressRelease/"
response = requests.get(url, timeout=10)
soup = BeautifulSoup(response.content, 'html.parser')
# Parse dates and titles
```

**Default Code (Tiingo News):**
```python
from shared.config.api_clients import TiingoClient

client = TiingoClient()
news = client.get_news(tickers='BABA', limit=50)
```

**Why Web Scraping First:**
- Most accurate for scheduled events (earnings, data releases)
- Direct from source (NBS website used successfully for 20 conferences)
- No rate limits on official government sites

**Known Limits:**
- HTML structure changes break scrapers
- Requires maintenance if site redesigns
- No historical news beyond what's visible on page

---

### Fundamentals (Financials, Ratios, Profiles)
**When:** Filtering momentum plays by quality (earnings, debt, profitability)

| Priority | Source | Data Available | Use When |
|----------|--------|----------------|----------|
| **1st: FMP** | Financials, ratios, profiles | Need company fundamentals | 250 req/day limit okay |
| **2nd: Alpha Vantage** | Basic financials | FMP down or rate limited | Can wait for rate reset |

**Default Code:**
```python
from shared.config.api_clients import FMPClient

client = FMPClient()
quote = client.get_quote('BABA')
income = client.get_income_statement('BABA', period='annual')
ratios = client.get_financial_ratios('BABA')
```

**Why FMP First:**
- Already configured and referenced in BABA study (fallback)
- 250 requests/day sufficient for occasional use
- Good coverage of US and Chinese ADRs

**Known Limits:**
- Free tier: 250 requests/day (use sparingly)
- Quarterly data lags by 45-90 days
- International stocks may have gaps

---

## Agent Rules

### 1. Always Consult This Map First
Before writing any data-fetching code, check this routing table. Don't guess, don't experiment. Use the default source for your use case.

### 2. Prefer Existing Shared Clients
**DO:**
```python
from shared.config.api_clients import TiingoClient, AlpacaClient, FREDClient
client = TiingoClient()
```

**DON'T:**
```python
import requests
response = requests.get('https://api.tiingo.com/...', headers={'Authorization': 'Token xyz'})
```

**Why:** Shared clients handle authentication, errors, rate limits automatically.

### 3. Never Introduce New Data Providers
Unless explicitly requested by user, stick to the 9 configured APIs:
1. yfinance (Yahoo Finance)
2. Tiingo
3. Alpaca Markets
4. Alpha Vantage
5. Charles Schwab
6. Financial Modeling Prep (FMP)
7. FRED (Federal Reserve)
8. CoinGecko (crypto)
9. SEC EDGAR (filings)

**If existing sources can't provide the data:**
- Ask user for clarification
- Suggest manual data upload
- Propose web scraping from official source

### 4. Never Print or Log Secrets
**DO:**
```python
from shared.config.api_config import APIConfig
api_key = APIConfig.TIINGO_API_KEY
print("API key loaded successfully")
```

**DON'T:**
```python
print(f"Using API key: {api_key}")  # NEVER!
```

**Rule:** Treat `.env` as private. Never output actual key values, even in error messages.

### 5. Handle Rate Limits Gracefully
If you hit a rate limit:
1. Add `time.sleep(1)` between requests
2. Cache results locally (save to CSV)
3. Switch to fallback source
4. Tell user which limit was hit

**Example:**
```python
import yfinance as yf
import time

tickers = ['BABA', 'JD', 'PDD', 'BIDU']
for ticker in tickers:
    data = yf.download(ticker, start='2024-01-01')
    time.sleep(2)  # Avoid rate limit
```

---

## Standard Series & Symbols

### FRED Series IDs (Federal Reserve Data)

**Volatility & Risk:**
- `VIXCLS` - CBOE Volatility Index (VIX) daily close
- `VXTLT` - 20+ Year Treasury Bond ETF Volatility

**Interest Rates:**
- `DFF` - Federal Funds Effective Rate (overnight rate)
- `DGS10` - 10-Year Treasury Constant Maturity Rate
- `DGS2` - 2-Year Treasury Constant Maturity Rate
- `T10Y2Y` - 10-Year minus 2-Year Treasury Spread (recession indicator)

**Economic Indicators:**
- `UNRATE` - Unemployment Rate (monthly)
- `CPIAUCSL` - Consumer Price Index (CPI, inflation)
- `GDP` - Gross Domestic Product (quarterly)
- `PAYEMS` - Total Nonfarm Payrolls (monthly jobs)

**Credit & Stress:**
- `BAMLH0A0HYM2` - High Yield Corporate Bond Spread (credit risk)
- `T10YIE` - 10-Year Breakeven Inflation Rate
- `TEDRATE` - TED Spread (interbank stress)

**Usage Example:**
```python
from shared.config.api_clients import FREDClient

fred = FREDClient()

# Get VIX for regime filter
vix = fred.get_series('VIXCLS')

# Get Fed Funds Rate for policy analysis
fed_rate = fred.get_series('DFF')

# Get unemployment for macro context
unemployment = fred.get_series('UNRATE')
```

---

### Yahoo Finance Tickers (Indices & Volatility)

**Volatility Indices:**
- `^VIX` - CBOE Volatility Index (S&P 500 implied volatility)
- `^VXN` - CBOE Nasdaq Volatility Index
- `^VXD` - CBOE DJIA Volatility Index
- `^MOVE` - ICE BofA MOVE Index (Treasury volatility)

**Major Indices:**
- `^GSPC` or `SPY` - S&P 500 Index
- `^IXIC` or `QQQ` - Nasdaq Composite
- `^DJI` or `DIA` - Dow Jones Industrial Average
- `^RUT` or `IWM` - Russell 2000 (small caps)

**Sector ETFs:**
- `XLF` - Financial Select Sector SPDR Fund
- `XLE` - Energy Select Sector SPDR Fund
- `XLK` - Technology Select Sector SPDR Fund
- `XLV` - Health Care Select Sector SPDR Fund

**International:**
- `EEM` - iShares MSCI Emerging Markets ETF
- `FXI` - iShares China Large-Cap ETF
- `EWJ` - iShares MSCI Japan ETF

**Commodities:**
- `GLD` - SPDR Gold Trust
- `USO` - United States Oil Fund
- `UNG` - United States Natural Gas Fund

**Usage Example:**
```python
import yfinance as yf

# Get VIX for regime filter (easy method)
vix = yf.download('^VIX', start='2024-01-01', end='2024-12-31')

# Get SPY as market proxy
spy = yf.download('SPY', start='2024-01-01', end='2024-12-31')

# Get sector ETF for correlation study
xlf = yf.download('XLF', start='2024-01-01', end='2024-12-31')
```

---

## Examples: Correct Routing Decisions

### Example 1: Daily Event Study on Equities
**Scenario:** Analyze TSLA price action on earnings announcement dates (last 20 quarters)

**Correct Routing:**
1. **Earnings Dates:** Web scrape from nasdaq.com earnings calendar or manually compile from user's records
2. **Daily OHLCV:** Alpaca (`AlpacaClient.get_bars('TSLA', timeframe='1Day', ...)`)
3. **Gap Calculation:** Open vs previous close from Alpaca data
4. **Forward Returns:** Day 1, 3, 5 returns calculated from Alpaca data

**Code:**
```python
from shared.config.api_clients import AlpacaClient
import pandas as pd

# Step 1: Earnings dates (manual or scraped)
earnings_dates = ['2024-10-23', '2024-07-24', '2024-04-23', ...]

# Step 2: Get TSLA daily data from Alpaca
client = AlpacaClient()
tsla = client.get_bars('TSLA', timeframe='1Day', start='2023-01-01', end='2024-12-31', limit=10000)

# Step 3: Calculate gaps and returns for each date
for date in earnings_dates:
    # Extract date, previous day, and forward days
    # Calculate gap %, continuation, forward returns
```

**Why This Routing:**
- Alpaca primary for US equities (consistent source, execution-ready)
- Web scraping better than Tiingo News for scheduled earnings (more accurate)
- Same data feed for backtesting and future live trading

**Fallback:** If Alpaca is unavailable, use yfinance as convenience fallback:
```python
import yfinance as yf  # Fallback only
tsla = yf.download('TSLA', start='2023-01-01', end='2024-12-31')
```

---

### Example 2: Intraday Opening Range Study
**Scenario:** Analyze first 15 minutes after BABA gaps >2% on China economic data releases

**Correct Routing:**
1. **Event Dates:** Web scrape China NBS website (already done: `studies/baba_nbs/nbs_conference_dates.txt`)
2. **Daily Gaps:** Alpaca 1Day bars for overnight gap calculation
3. **Intraday Data:** Alpaca 5-minute bars for opening 15 minutes (9:30-9:45 AM)
4. **Continuation:** Compare 9:45 AM price to opening gap direction

**Code:**
```python
from shared.config.api_clients import AlpacaClient

# Step 1: Load NBS dates (already scraped)
with open('studies/baba_nbs/nbs_conference_dates.txt') as f:
    nbs_dates = [line.split()[0] for line in f.readlines()]

# Step 2: Get daily data for gap calculation (Alpaca)
alpaca = AlpacaClient()
baba_daily = alpaca.get_bars('BABA', timeframe='1Day', start='2023-04-01', end='2024-11-30', limit=10000)

# Step 3: For gap days >2%, get intraday data
for date in nbs_dates:
    # Check if gap >2%
    if gap_pct > 2:
        # Get 5-min bars for opening range (same source as daily)
        bars = alpaca.get_bars('BABA', timeframe='5Min', 
                              start=f'{date}T09:30:00', 
                              end=f'{date}T09:45:00')
```

**Why This Routing:**
- Alpaca for both daily gaps AND intraday (one consistent source)
- No vendor discrepancy between gap calculation and intraday follow-through
- 1-min/5-min resolution available, unlimited history
- Don't use Tiingo IEX (real-time only, not historical intraday)

---

### Example 3: Regime Filter Study Using VIX
**Scenario:** Test if "Fade BABA gap up" strategy works better when VIX < 20 vs VIX > 20

**Correct Routing:**
1. **BABA Daily Data:** Alpaca (US equity)
2. **VIX Daily Data:** FRED `VIXCLS` series (official) OR yfinance `^VIX` (index proxy fallback)
3. **Regime Classification:** Join BABA and VIX data by date, split into VIX < 20 and VIX > 20 buckets
4. **Strategy Performance:** Calculate avg returns for each regime

**Code:**
```python
from shared.config.api_clients import AlpacaClient, FREDClient

# Step 1: Get BABA data from Alpaca (primary for US equities)
alpaca = AlpacaClient()
baba = alpaca.get_bars('BABA', timeframe='1Day', start='2023-04-01', end='2024-11-30', limit=10000)

# Step 2: Get VIX from FRED (official) or yfinance (index proxy)
fred = FREDClient()
vix_fred = fred.get_series('VIXCLS')  # Most authoritative

# Fallback: Use yfinance for index proxy if needed
# import yfinance as yf
# vix = yf.download('^VIX', start='2023-04-01', end='2024-11-30')  # Index proxy only

# Join data by date
merged = baba.join(vix_fred['value'].rename('VIX'), how='inner')

# Split by regime
low_vix_days = merged[merged['VIX'] < 20]
high_vix_days = merged[merged['VIX'] >= 20]

# Calculate strategy returns for each regime
print(f"Low VIX (<20): {low_vix_days['return'].mean():.2f}%")
print(f"High VIX (≥20): {high_vix_days['return'].mean():.2f}%")
```

**Why This Routing:**
- Alpaca for BABA (canonical source for US equities)
- FRED `VIXCLS` most authoritative for VIX (official CBOE data)
- yfinance `^VIX` acceptable as index proxy fallback
- Consistent equity data source = cleaner study

---

## Quick Decision Tree

**Need daily stock prices (US equities)?** → Alpaca  
**Need intraday bars?** → Alpaca  
**Need VIX or macro data?** → FRED (official) or yfinance `^VIX` (index proxy fallback)  
**Need earnings/event dates?** → Web scrape official source  
**Need news headlines?** → Tiingo News API  
**Need company fundamentals?** → FMP  
**Need indices (^VIX, ^GSPC)?** → yfinance (index proxy)  
**Need non-US symbols?** → yfinance or Tiingo  

**Unsure?** → Default to Alpaca for US equities, yfinance for indices/non-US, FRED for macro

---

## Troubleshooting

### "yfinance is timing out"
→ Add `time.sleep(2)` between downloads or switch to Tiingo

### "I need intraday data older than 30 days"
→ Use Alpaca (unlimited historical intraday)

### "VIX data doesn't match between sources"
→ FRED `VIXCLS` is official daily close, yfinance may include intraday; use FRED for research

### "API key not found"
→ Check `.env` file in root directory, ensure variable name matches `shared/config/api_config.py`

### "Hit rate limit on [API]"
→ Check routing table for fallback source, implement caching, add sleep delays

---

## Maintenance

**Review this map when:**
- Adding a new study type (options, crypto, futures)
- Hitting repeated rate limits on default source
- Discovering data quality issues
- Adding new API to workspace

**Update priority:**
- If a default source consistently fails → promote fallback to default
- If new source proves more reliable → update routing table
- If rate limits change → update "Known Limits" section

---

**Document Status:** ✅ Active  
**Single Source of Truth:** Yes  
**Next Review:** When new API added or routing fails  
**Maintainer:** User + AI Assistant
