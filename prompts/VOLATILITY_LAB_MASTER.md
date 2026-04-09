# Volatility Lab Master Protocol

**Purpose:** This document defines the canonical rules for volatility analysis, Time-to-Peak (TTP) calculations, and return analysis in the QuantLab Data_Lab.

**Scope:** All studies measuring price volatility, peak timing, forward returns, and related statistical metrics must follow these rules unless explicitly overridden by the user.

---

## Canonical Price Data Rule

**All volatility metrics, Time-to-Peak (TTP) calculations, and return calculations must use Alpaca price data unless explicitly overridden by the user or by documented limitations in [docs/API_MAP.md](../docs/API_MAP.md).**

### Clarifications:

- **Alpaca is the default** for both daily and intraday US equity price data
  - Daily bars: Use `timeframe='1Day'`
  - Intraday bars: Use `timeframe='5Min'`, `'15Min'`, or `'1Hour'` as appropriate
  - Ensures consistency across volatility calculations and return measurements

- **Fallback sources** (Tiingo, yfinance) may be used only when Alpaca cannot provide the required data, and must be explicitly noted in the study output
  - Example: "Data source: yfinance (fallback used due to non-US symbol)"
  - Document the reason for fallback in study notes

- **Volatility indices and macro series** (^VIX, VIXCLS, rates, Fed data) are exempt from this rule and should follow [docs/API_MAP.md](../docs/API_MAP.md) routing
  - VIX: Use FRED `VIXCLS` (official) or yfinance `^VIX` (index proxy)
  - Macro: Use FRED for official Fed data
  - See API_MAP.md for complete routing table

---

## Why This Rule Exists

Using a single canonical price source across all volatility studies ensures:

1. **Consistent volatility measurements:** No discrepancies from vendor-specific adjustments or data feeds
2. **Accurate TTP calculations:** Peak timing measured against the same baseline price data
3. **Comparable returns:** Forward return calculations use identical OHLC values across all studies
4. **Execution alignment:** Backtested volatility matches live trading data (same Alpaca feed)

---

## Implementation

### For Daily Volatility Studies:
```python
from shared.config.api_clients import AlpacaClient

client = AlpacaClient()
data = client.get_bars('BABA', timeframe='1Day', start='2024-01-01', end='2024-12-31', limit=10000)

# Calculate volatility metrics on Alpaca data
# Calculate forward returns on Alpaca data
```

### For Intraday Volatility Studies:
```python
from shared.config.api_clients import AlpacaClient

client = AlpacaClient()
bars = client.get_bars('TSLA', timeframe='5Min', start='2024-12-10T09:30:00', end='2024-12-10T16:00:00')

# Calculate intraday volatility, TTP, returns
```

### For Studies Requiring Fallback:
```python
# Document why fallback is used
import yfinance as yf  # Fallback: Non-US symbol not available on Alpaca

data = yf.download('0700.HK', start='2024-01-01', end='2024-12-31')
# Note: Returns calculated on yfinance data (fallback)
```

---

## Exceptions

The following cases are **exempt** from the Alpaca-first rule:

1. **Non-US equities** not traded on US exchanges (e.g., Chinese A-shares, European domestic listings)
2. **Index symbols** not supported by Alpaca (^VIX, ^GSPC, ^IXIC)
3. **Macro/volatility series** (VIXCLS, DFF, DGS10) → use FRED or yfinance per API_MAP.md
4. **User-specified override** for testing or comparison purposes (must be documented)

---

## Maintenance

**When to update this protocol:**
- Alpaca API changes or deprecations
- New data source proves more reliable for volatility studies
- User establishes new default for specific asset classes

**How to update:**
- Update this file first (single source of truth)
- Update [docs/API_MAP.md](../docs/API_MAP.md) if routing changes
- Update [shared/data_router.py](../shared/data_router.py) to match new rules
- Notify existing studies of breaking changes (if any)

---

**Document Status:** ✅ Active  
**Last Updated:** December 14, 2025  
**Related Files:**
- [docs/API_MAP.md](../docs/API_MAP.md) - Complete data routing guide
- [docs/ENFORCEMENT_NOTES.md](../docs/ENFORCEMENT_NOTES.md) - Enforcement system documentation
- [shared/data_router.py](../shared/data_router.py) - Programmatic data routing utility

---

*Update: Canonical price source standardized to Alpaca.*
