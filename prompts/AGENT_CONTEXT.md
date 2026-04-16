# QUANTLAB DATA LAB — AGENT CONTEXT & OPERATING MANUAL
*Last Updated: February 26, 2026*
*Read this file at the start of every session. It is your briefing.*

---

## WHO I AM

I am Lakeem. Full-time proprietary momentum and trend-following trader. I trade LONG and SHORT with equal conviction across ~239 stocks. My edge is preparation — forensic research before the open, then execution with conviction.

Pre-market window: 6:30–8:25 AM Central. I use an 8-pillar War Room framework to score catalysts before the market opens.

**My AI setup:**
- **VS Code Copilot (you)** → Full pipeline operator. War Room v10.0 catalyst scoring, fundamental forensics, margin analysis, transcript deep-dives, options levels interpretation, quantitative studies, chart generation, data pulls, pattern validation. Everything.
- **Me** → Price action, execution, final decisions. Never tell me what to trade.

**Session startup:** Read `prompts/WAR_ROOM_CONTEXT.md` for current macro regime, active names, and confirmed edges. Then confirm lab is ready.

---

## WHAT THIS LAB IS

QuantLab is my quantitative research laboratory. The goal:

> **Replace "I think this works" with "here's what the data actually says."**

This is NOT a trading terminal. NOT a charting platform. It is a science lab where I bring hypotheses — from earnings setups, prediction market signals, indicator behavior, macro events, squeeze dynamics, gap patterns, anything — and we test whether the edge is real.

**The query workflow — this is everything:**
1. I ask a plain English question
2. You identify which data in the lab answers it
3. You run the analysis
4. You return: **text summary first (with sample size), then a chart**

No hand-holding. No asking me which library to use. No long preambles. Answer first, explain second.

---

## LAB STRUCTURE — KNOW THE MAP

```
C:\QuantLab\Data_Lab\
├── shared/
│   ├── data_router.py        ← ALL equity price data routes here. SACRED. Never bypass.
│   ├── chart_builder.py      ← ALL visualizations route here. Always output .html
│   ├── watchlist.py          ← get_watchlist() returns the 239-ticker universe
│   ├── config/
│   │   └── watchlist.csv     ← Master ticker list. 239 names. Source of truth.
│   └── indicators/           ← TrendStrength, TTM Squeeze. DO NOT MODIFY EVER.
│
├── databases/
│   └── earnings_master.csv   ← Fundamental + price reaction data per earnings event.
│                                One query source among many — not the whole lab.
│
├── studies/                  ← Completed research. Each folder has outputs/ with
│   ├── beat_and_sell_probability/    results and charts. Do not delete or overwrite.
│   ├── alab_gapdown_study/
│   ├── baba_nbs/
│   ├── tsla_indicator_honesty/
│   └── [new studies added here as they complete]
│
├── tools/
│   ├── prediction_markets/   ← 40GB Polymarket/Kalshi historical odds data
│   │   └── pm_data_loader.py ← search_markets(), run_event_study()
│   └── levels_engine/        ← Price levels analysis
│
├── docs/                     ← Governance. These are LAW.
│   ├── API_MAP.md            ← Data routing rules
│   ├── INDICATOR_SPECS.md    ← Canonical indicator definitions
│   └── STUDY_INDEX.md        ← Master study tracker
│
├── prompts/
│   └── AGENT_CONTEXT.md      ← THIS FILE. Read every session.
│
└── scratch/                  ← Quick queries and one-off analyses go here
    └── test_visualization.ipynb
```

---

## DATA ROUTING — NON-NEGOTIABLE

| Data Type | Source | Method |
|-----------|--------|--------|
| ALL US equity price data | Alpaca | `DataRouter.get_price_data()` |
| Index data (VIX, SPX, MOVE) | yfinance | `^VIX`, `^SPX`, `^MOVE` only |
| Fundamental/earnings data | yfinance | `Ticker.quarterly_income_stmt` |
| Macro series | FRED | Via fredapi (`VIXCLS`, `DGS10`, `FEDFUNDS`) |
| News/events/earnings dates | Tiingo | Via tiingo client |
| Prediction market odds | Local parquet | Via `tools/prediction_markets/pm_data_loader.py` |

**NEVER use yfinance for individual equity price studies. That is Alpaca's job, always.**

Every script starts with:
```python
import sys, os
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')
```
Non-negotiable. Every time. Missing this causes ModuleNotFoundError.

---

## WHAT I STUDY — THE FULL SCOPE

This lab is not just about earnings. I study any quantifiable edge across:

**Price & Momentum**
- Gap behavior (gap-up/down, held vs faded, pre-market range)
- Indicator validation (does TrendStrength or TTM Squeeze actually produce alpha?)
- Relative strength patterns — when RS(Z) is at certain levels, what follows?
- Breakout behavior, squeeze dynamics, float rotation

**Earnings & Fundamentals**
- Post-earnings price reactions by margin trajectory, guidance type, starting position
- Beat-and-raise vs beat-and-sell patterns
- Revenue growth rate vs fade probability
- Operating leverage signals and forward returns

**Prediction Markets**
- When Polymarket/Kalshi odds shift on macro events, how do specific stocks/sectors react?
- Fed rate cut odds changes → XLF behavior
- Election/policy outcome odds → sector rotation patterns
- 40GB of historical odds data available via pm_data_loader

**Macro & Events**
- Economic data surprises → sector reactions
- OPEX week behavior patterns
- VIX regime changes and stock behavior
- Geopolitical event studies

**Catalyst & Setup Validation**
- Do specific War Room setup classifications (Less Bad Than Feared, Disbelief Squeeze, etc.) have statistically measurable edge?
- Cross-referencing Claude's catalyst scores against actual outcomes over time

---

## THE TWO SACRED MODULES

**DataRouter** — `shared/data_router.py`
Single point of truth for all price data. Returns capitalized columns: `Open, High, Low, Close, Volume`.
```python
from shared.data_router import DataRouter
df = DataRouter.get_price_data('NVDA', '2024-01-01', study_type='indicator')
```

**ChartBuilder** — `shared/chart_builder.py`
Single point of truth for all visualizations. Expects lowercase columns. Always normalize first.
```python
from shared.chart_builder import ChartBuilder
df = ChartBuilder.normalize_columns(df)
fig = ChartBuilder.price_chart(df, 'NVDA')
```
Available: `price_chart()`, `forward_returns()`, `winrate_heatmap()`, `gap_distribution()`, `equity_curve()`, `pm_overlay()`

**Prediction Markets** — `tools/prediction_markets/pm_data_loader.py`
```python
from tools.prediction_markets.pm_data_loader import search_markets, run_event_study
markets = search_markets("federal reserve", source="kalshi")
events, stats = run_event_study(market_id="FED-RATE-DEC-2024", ticker="QQQ", threshold_abs=0.10, window_days=7)
```

---

## INDICATORS — DO NOT TOUCH

These are canonical. Parameters are fixed. Never modify during a study.

**Trend Strength Candles v2 + NR7**
```python
from shared.indicators.trend_strength_nr7 import TrendStrengthNR7, TrendStrengthParams
indicator = TrendStrengthNR7(TrendStrengthParams())
signals = indicator.calculate(price_data)
```
Signal states: `MAX_CONVICTION_BULL (≥70)` | `STRONG_BULL (50-69)` | `MILD_BULL (30-49)` | `NEUTRAL (-9 to 10)` | `MAX_CONVICTION_BEAR (≤-70)`

**TTM Squeeze Advanced** — identifies volatility compression setups with momentum bias.

---

## HOW TO ANSWER MY QUESTIONS

When I ask anything in plain English:

1. **Identify the right data source** — earnings_master.csv? Alpaca price pull? Prediction markets? Existing study output? Indicators?
2. **Query or compute** — filter, group, aggregate. Use pandas. Don't overthink it.
3. **Text summary first** — key numbers, win rates, sample size (n=?), confidence level
4. **Chart second** — save as .html to `scratch/` for quick queries, or `studies/{name}/outputs/charts/` for formal studies
5. **Always flag sample size:**
   - n ≥ 20 → Reliable, state findings with normal confidence
   - n < 20 → FLAG as LOW CONFIDENCE
   - n < 10 → FLAG as INSUFFICIENT — do not trade this

**Example questions I might ask:**
- "When NVDA gaps flat on a beat-and-raise, what happens the next day?"
- "Is there a correlation between revenue growth rate and post-earnings fades?"
- "When Fed rate cut odds drop 10%+ on Kalshi, how does XLF perform over 5 days?"
- "Show me every time TTM Squeeze fired on a stock in my universe that also had RS(Z) > 2"
- "Which of my 239 names have the most consistent beat-and-raise history?"
- "When VIX spikes above 25 intraday and closes below 22, what happens to QQQ the next 3 days?"
- "Does TrendStrength MAX_CONVICTION_BULL actually produce alpha vs random days?"

---

## STUDY FINDINGS — CONFIRMED EDGES
*Append new findings here as studies complete. Never overwrite.*

### Finding #1 — RS Weakness Predicts Earnings Gap Fade
**Date:** February 26, 2026 | **Source:** Beat & Sell Probability Study v1
**Signal:** Stock RS vs SPY ≤ 0 (trailing 20 days) at time of earnings gap-up
**Result:** 54.2% day-of fade rate vs 39.4% baseline (+14.8 ppt, n=190)
**Confidence:** MODERATE — single study, gap proxy used not real earnings dates
**Application:** When pre-earnings RS is negative and stock gaps up, reduce initial size 30-50%. Wait for first 30-min candle before full deployment.
**Status:** Needs V2 with real Tiingo earnings dates to confirm

---

## WHAT YOU NEVER DO

- Use yfinance for individual equity price studies (Alpaca only)
- Modify anything in `shared/indicators/`
- Delete or overwrite existing study outputs
- Return results without stating sample size (n=?)
- Build a whole new study when a simple database query answers the question
- Ask me which library to use — pick the right one and run it
- Give long explanations before answering — answer first, explain second
- Assume every question is about earnings — I study everything

## WHAT YOU ALWAYS DO

- Start every script with the 4 sys.path inserts
- Route all equity price data through DataRouter
- Route all charts through ChartBuilder, output .html
- State confidence level and sample size on every finding
- Append new confirmed edges to Study Findings above
- Read this file at the start of every session
- Save outputs — never return results that aren't persisted somewhere

---

## SESSION START CHECKLIST

When a new session begins, confirm:
1. ✅ AGENT_CONTEXT.md loaded
2. ✅ `get_watchlist()` accessible — print ticker count
3. ✅ `earnings_master.csv` exists — print row count
4. ✅ Prediction markets data accessible
5. ✅ Ready for plain English questions

Then say: **"Lab is ready. What's your question?"**

---
*QuantLab Data Lab | Lakeem's War Room Data Infrastructure | v1.0 | Feb 2026*
