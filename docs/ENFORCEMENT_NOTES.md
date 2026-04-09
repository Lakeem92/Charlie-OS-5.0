# API_MAP.md Enforcement System

## Purpose
This document explains the data source enforcement system implemented to ensure **docs/API_MAP.md** is the single source of truth for all data routing decisions across the Data_Lab.

---

## What Was Changed

### 1. Top-Level README.md
**Location:** `README.md` (root)

**Change:** Added a prominent "Data Sources" section with critical warning:

```markdown
## Data Sources

⚠️ **CRITICAL**: Always consult **[docs/API_MAP.md](docs/API_MAP.md)** before fetching any data.

API_MAP.md is the **single source of truth** for which API/data source to use.
```

**Why:** Forces every developer/AI agent to check the routing rules before writing data-fetching code.

---

### 2. Study Template
**Location:** `studies/_TEMPLATE/`

**Created Files:**
- `study_notes.md` - Research documentation template
- `run_study.md` - Step-by-step execution guide
- `outputs/` - Standard output directory

**Key Feature:** Both templates include explicit "Data Sources" sections that reference **docs/API_MAP.md** and provide routing tables:

```markdown
## Data Sources
Consult **docs/API_MAP.md** before fetching data.

| Data Type          | Primary Source | Fallback 1 | Fallback 2 |
|--------------------|---------------|------------|------------|
| Daily OHLCV        | yfinance      | Tiingo     | Alpaca     |
| Intraday bars      | Alpaca        | Tiingo IEX | -          |
| Macro/Fed series   | FRED          | -          | -          |
| Volatility (VIX)   | yfinance/FRED | -          | -          |
```

**Why:** New studies automatically start with correct data routing guidance. Templates force consultation of API_MAP.md before any coding begins.

---

### 3. Data Router Utility
**Location:** `shared/data_router.py`

**What It Does:**
- Provides a single `DataRouter.get_price_data()` function that automatically routes to the correct API based on timeframe and data type
- Implements fallback logic per API_MAP.md (yfinance → Tiingo → Alpaca for daily)
- Supports daily OHLCV, intraday bars, macro series, and volatility proxies

**Example Usage:**

```python
from shared.data_router import DataRouter

# Daily OHLCV (auto-routes to yfinance)
data = DataRouter.get_price_data('BABA', '2024-01-01', '2024-12-31')

# Intraday bars (auto-routes to Alpaca)
intraday = DataRouter.get_price_data('TSLA', '2024-12-10', timeframe='5min')

# Macro data (uses FRED)
vix = DataRouter.get_macro_data('VIXCLS', '2024-01-01', '2024-12-31')

# Convenience shortcuts
from shared.data_router import get_daily_prices, get_vix
prices = get_daily_prices('SPY', '2024-01-01')
vix = get_vix('2024-01-01', official=True)
```

**Why:** Programmatic enforcement ensures correct routing even if someone forgets to check API_MAP.md manually. All future studies should use this utility instead of directly calling yfinance/Tiingo/Alpaca.

---

### 4. This Document
**Location:** `docs/ENFORCEMENT_NOTES.md`

**What It Is:** You're reading it. This explains the entire enforcement system.

**Why:** Future maintainers need to understand what was implemented and how to use it.

---

## How to Use This System

### For New Studies

1. **Copy the template:**
   ```bash
   cp -r studies/_TEMPLATE studies/my_new_study
   ```

2. **Fill out `study_notes.md`:**
   - Research question
   - Ticker list
   - Event definition
   - **Data Sources** (already has routing table from API_MAP.md)

3. **Use the data router in your code:**
   ```python
   from shared.data_router import get_daily_prices
   
   data = get_daily_prices('TSLA', '2024-01-01', '2024-12-31')
   ```

4. **Follow `run_study.md` execution steps:**
   - Collect data
   - Analyze
   - Review results
   - Document findings

---

### For Existing Studies

**Do NOT refactor existing studies** unless they break. The enforcement system is forward-looking:
- Studies in `studies/baba_nbs_study/` remain untouched
- Studies in `studies/cannabis_rallies/` remain untouched

Only new studies should use the template and data router.

---

### For AI Agents

When asked to fetch data:
1. **First**, read `docs/API_MAP.md` to determine correct source
2. **Then**, use `shared/data_router.py` functions instead of direct API calls
3. **Never** use hardcoded API choices without consulting API_MAP.md

**Example Workflow:**
```
User: "Get daily prices for NVDA from Jan 2024"

Agent thinks:
1. Check API_MAP.md → Daily OHLCV → yfinance (primary)
2. Use data_router.py → get_daily_prices()
3. Code: data = get_daily_prices('NVDA', '2024-01-01', '2024-12-31')
```

---

## Routing Rules Summary

### Daily OHLCV
- **Primary:** yfinance (free, unlimited, auto-adjusted splits/dividends)
- **Fallback 1:** Tiingo (if yfinance fails, requires API key)
- **Fallback 2:** Alpaca (if both fail, limited history)

### Intraday Bars (5min, 15min, 1hour)
- **Primary:** Alpaca (when configured, requires API key)
- **Fallback:** Tiingo IEX (real-time snapshot only)

### Macro/Fed Series (VIX, Fed Funds, Treasury Yields)
- **Primary:** FRED (official government data, requires API key)
- **Fallback:** yfinance (for quick proxies like ^VIX)

### Volatility Proxies
- **Quick access:** yfinance (^VIX, ^MOVE, ^VXN)
- **Official data:** FRED ('VIXCLS', 'MOVE')

---

## Maintenance

### When to Update This System

1. **New API added:**
   - Update `docs/API_MAP.md` with routing rules
   - Add new source to `shared/data_router.py` if needed
   - Update study template routing tables

2. **API priority changed:**
   - Update `docs/API_MAP.md` first
   - Update `shared/data_router.py` fallback logic
   - Update study template tables

3. **New data type needed:**
   - Document in `docs/API_MAP.md`
   - Add method to `DataRouter` class
   - Update study template if commonly used

### Testing Changes

After updating routing logic:
```python
# Test daily routing
from shared.data_router import get_daily_prices
data = get_daily_prices('SPY', '2024-01-01', '2024-01-31')
assert not data.empty, "Routing failed"

# Test intraday routing
from shared.data_router import get_intraday_prices
intraday = get_intraday_prices('SPY', '2024-12-10', resolution='5min')
assert not intraday.empty, "Intraday routing failed"

# Test macro routing
from shared.data_router import DataRouter
vix = DataRouter.get_macro_data('VIXCLS', '2024-01-01', '2024-01-31')
assert not vix.empty, "Macro routing failed"
```

---

## FAQ

### Q: Why not just use yfinance for everything?
**A:** yfinance is great for daily data but doesn't support intraday bars. Alpaca is better for 5min/15min resolution. FRED has official government macro data that's more reliable than scraped proxies.

### Q: Can I still call yfinance directly in my code?
**A:** Yes, but it's discouraged. Use `data_router.py` for consistency and automatic fallback logic.

### Q: What if I disagree with the routing in API_MAP.md?
**A:** Update API_MAP.md first (single source of truth), then update `data_router.py` to match.

### Q: Do I need to refactor old studies?
**A:** No. Only new studies should use the template and data router.

### Q: What happens if all sources fail?
**A:** `DataRouter.get_price_data()` will raise a `RuntimeError` with details about what failed. Check API keys and rate limits.

---

## Version History

- **2024-12-XX:** Initial enforcement system created
  - README.md updated with Data Sources section
  - Study template created (studies/_TEMPLATE/)
  - Data router utility created (shared/data_router.py)
  - This document created

---

## Related Files

- **[docs/API_MAP.md](API_MAP.md)** - Single source of truth for routing rules
- **[docs/API_INVENTORY_RAW.md](API_INVENTORY_RAW.md)** - Complete API audit (725 lines)
- **[README.md](../README.md)** - Top-level lab documentation
- **[shared/data_router.py](../shared/data_router.py)** - Data routing utility
- **[studies/_TEMPLATE/](../studies/_TEMPLATE/)** - Study template structure

---

**Remember:** When in doubt, check **docs/API_MAP.md** first. It's the single source of truth.
