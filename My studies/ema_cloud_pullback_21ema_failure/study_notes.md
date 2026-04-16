# [Study Name] - Research Notes

**Created:** [Date]  
**Status:** [Planning / In Progress / Complete]

---

## Research Question

What pattern or edge are you trying to discover?

**Example:** "Does TSLA exhibit predictable price action on earnings announcement dates?"

---

## Study Design

### Ticker(s)
List all tickers to analyze:
- Primary: [TSLA]
- Related: [RIVN, LCID] (if comparing multiple)

### Event/Trigger Definition
What event triggers the pattern you're looking for?

**Example:**
- Event: Earnings announcement (after-market close)
- Source: nasdaq.com earnings calendar or SEC 8-K filings
- Sample size target: 20+ events (last 5 years)

### Timeframe
What time period are you analyzing?

**Example:**
- Historical range: 2019-01-01 to 2024-12-31
- Event window: Day -1 (before), Day 0 (event), Days +1 to +5 (forward returns)

### Windows & Metrics
What specific metrics will you calculate?

**Example:**
- Gap %: (Open_Day0 - Close_Day-1) / Close_Day-1
- Intraday continuation: (Close_Day0 - Open_Day0) / Open_Day0
- Forward returns: Day +1, +3, +5 returns from event close
- Volume spike: Event day volume / 20-day avg volume

---

## Data Sources

**⚠️ REQUIRED: Consult [docs/API_MAP.md](../../docs/API_MAP.md) before fetching data.**

### Data Requirements

| Data Type | Timeframe | Source | Why This Source |
|-----------|-----------|--------|-----------------|
| **Price (OHLCV)** | Daily | yfinance | Default for daily bars, no API key |
| **Event Dates** | N/A | Web scraping (nasdaq.com) | Official source, scheduled events |
| **Volatility Filter** | Daily | yfinance (^VIX) | Quick check, same code as stocks |

**Alternative Sources (if needed):**
- If daily data gaps → Tiingo API (already configured)
- If need intraday → Alpaca Markets (1-min bars available)
- If need macro filter → FRED API (VIXCLS, DFF, etc.)

**Routing Rule from API_MAP:**
```
Daily OHLCV → yfinance (1st) → Tiingo (2nd) → Alpaca (3rd)
Intraday → Alpaca (1st) → Tiingo IEX (2nd)
Macro → FRED (1st) → yfinance indices (2nd)
```

---

## Expected Outputs

### Files to Generate

1. **[study_name]_analysis.csv**
   - Columns: Date, Ticker, Event, Gap%, Continuation%, Day1_Return, Day3_Return, Day5_Return, Volume_Spike, etc.
   - One row per event

2. **[study_name]_analysis.txt**
   - Summary statistics (avg returns, win rate, max drawdown)
   - Trade-by-trade breakdown with context

3. **README.md**
   - Executive summary (key finding in 2-3 sentences)
   - Detailed analysis with tables and statistics
   - Actionable trading strategies (entry/exit rules, position sizing)
   - Risk management lessons

4. **outputs/** folder
   - All CSV, TXT, and chart files saved here
   - Keep organized for easy archiving

---

## Hypothesis

What do you expect to find? (Can be wrong—that's the point of research!)

**Example:**
"I expect TSLA to fade gap-ups on earnings days, similar to the BABA/NBS pattern. Hypothesis: >2.5% gap ups lead to -2% or worse 3-day returns."

---

## Success Criteria

How will you know if this study found a tradeable edge?

- [ ] Sample size ≥ 15 events (statistical significance)
- [ ] Win rate ≥ 60% (for directional trades)
- [ ] Average return > 1.5% per trade (expectancy)
- [ ] Pattern holds across different market regimes (bull/bear)
- [ ] Max drawdown < 10% (risk management)

---

## Notes & Observations

Track discoveries during analysis:

- **2024-12-14:** Initial data collection complete, found 23 earnings events
- **2024-12-15:** Gap up fade works in high VIX (>25) but not low VIX (<15)
- **2024-12-16:** Need to add volume filter—low volume gaps don't fade reliably

---

## Next Steps

- [ ] Collect event dates (target: 20+)
- [ ] Write data collection script (`collect_data.py`)
- [ ] Write analysis script (`analyze_[ticker]_[event].py`)
- [ ] Run analysis and generate outputs
- [ ] Write comprehensive README.md with strategies
- [ ] Add VIX regime filter (optional enhancement)
- [ ] Backtest strategy with position sizing rules

---

**Template Version:** 1.0  
**Last Updated:** December 14, 2025
