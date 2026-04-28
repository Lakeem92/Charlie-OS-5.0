# Diet Bloomberg Dashboard Context

Last updated: 2026-04-28

## What It Is

This document is scoped to the Diet Bloomberg dashboard only, not the broader QuantLab workspace.

Diet Bloomberg is the local dashboard that turns the morning collector stack into a single browser-based terminal at `http://localhost:8766`.

It is not a broker, scanner, or execution engine. It is a context board for pre-market decision support. The job of the dashboard is to compress the macro regime, AI supply-chain rotation, ETF squeeze structure, and watchlist news flow into a page set that can be checked quickly before the open.

## How It Runs

- Server: `Diet Bloomberg/serve.py`
- Startup wrapper: `scripts/startup_diet_bloomberg.py`
- Collector refresh: `run_all.py`
- Local data store: `catalyst_analysis_db/`
- Focus news source: `News_flow/`
- Port: `8766`

The startup wrapper does three things:

1. Confirms the dashboard server is healthy.
2. Starts or restarts it if the listener is stale or the pages fail to render.
3. Refreshes collector outputs and focus-list news.

## What Pages Exist Right Now

### 1. Macro Page

Route: `/` and `/macro`

Purpose: a top-down regime board for liquidity, rates, credit, risk appetite, and market structure.

What it tracks:

- Macro regime banner with score and regime details
- Fed net liquidity versus S&P 500
- XLY/XLP tactical risk appetite ratio
- VIX term structure
- Fed rate cut odds
- Rates and repo plumbing: SOFR, EFFR, IORB
- Yield curve: 10Y minus 2Y
- M2 money supply
- CFTC COT positioning
- SLOOS credit-spigot signal
- Heavy truck sales as a real-economy pulse
- Retail money market funds as dry-powder gauge
- Sticky CPI structure
- STLFSI4 financial-stress filter
- Overnight reverse repo balance
- Onshoring efficiency: manufacturing capex versus industrial output
- Copper/gold ratio plus real yields
- Foreign custody assets at the Fed as a global-liquidity stress signal
- Temp-help ratio as an early labor-cycle signal
- ACM 10Y term premium
- S&P 500 bellwether EPS growth
- High-yield option-adjusted spread
- Core capex / new orders as future earnings engine
- BTC/gold ratio
- BTC versus high-yield spread exhaustion signal
- Real-yield trap panel
- Gold commercials COT
- Put/call ratio and PCR RSI
- SPX options regime: vol structure and gamma context
- Sector rotation versus SPY
- Quick-reference implication cards
- War Room macro brief summary

What the macro page is trying to answer:

- Is liquidity expanding or tightening?
- Is the market in risk-on, fear, or transition?
- Are credit and rates confirming the tape or warning against it?
- Is the macro backdrop supportive for momentum, rotation, or defense?

Primary sources behind this page:

- FRED
- yfinance for index and volatility proxies
- CFTC positioning data
- prediction-market odds where available

### 2. AI Cascade Page

Route: `/ai`

Purpose: track whether the AI infrastructure trade is broad, narrow, or rolling from one layer of the stack to another.

What it tracks:

- 4-flow convergence meter
- Per-flow status cards for the AI stack:
  - Silicon
  - Optical
  - Power
  - Demand
- Per-flow price and return tables for constituent names
- Flow-level implication text
- Google Trends search-interest cascade for AI supply-chain terms
- Institutional picks for obscure supply-chain names

What the AI page is trying to answer:

- Are multiple layers of the AI trade confirming at once?
- Which layer is leading and which is lagging?
- Is search interest accelerating before price follows?
- Are there less obvious suppliers getting institutional attention?

Primary sources behind this page:

- `data_collectors/ai_cascade_collector.py`
- pytrends
- SEC / EDGAR-derived context
- local collector outputs in `catalyst_analysis_db/daily_briefing/`

### 3. ETF Page

Route: `/etf`

Purpose: monitor leveraged and structural squeeze conditions in ETFs while also keeping a simple momentum leaderboard.

What it tracks:

- KORU signal and implication block when active
- Tier 2 momentum leaderboard
- Tier 1 structural squeeze cards

The squeeze cards score several drivers:

- Short interest
- Options / GEX / max-pain pressure
- Dark-pool behavior when available
- Valuation context

What the ETF page is trying to answer:

- Which ETFs are leading on pure momentum?
- Which ETFs have squeeze structure, not just price strength?
- Is there a structural setup forming that can drive an outsized move?

Primary sources behind this page:

- `data_collectors/etf_collector.py`
- FINRA
- options data used by the collector
- FMP and related enrichment used by the collector

### 4. News Page

Route: `/news`

Purpose: compress the morning news flow so the focus list gets priority over the broad watchlist.

What it tracks:

- Focus-list news feed
- Master watchlist feed
- Market wire / RSS feed
- Freshness chips for macro, AI, ETF, news, and focus news

What the news page is trying to answer:

- What matters right now for the curated names?
- What is new on the broad watchlist?
- Is the terminal working with fresh or stale inputs?

Primary sources behind this page:

- `data_collectors/news_collector.py`
- `tools/watchlist_scanner/scan_news.py`
- `News_flow/YYYY-MM-DD.json`

## What Refreshes The Dashboard

`run_all.py` runs the collector stack in sequence. In this workspace, the refresh flow includes:

- Macro collector
- ETF collector
- Commodities collector
- Catalyst collector
- Focus-list collector
- AI cascade collector
- News collector

Not every collector has a live page today, but the dashboard is part of a broader collector system and reads from the same shared store.

## Where The Data Lives

- `catalyst_analysis_db/macro_regime/` holds macro outputs
- `catalyst_analysis_db/etf_structural/` holds ETF outputs
- `catalyst_analysis_db/daily_briefing/ai_cascade.json` feeds the AI page
- `catalyst_analysis_db/daily_briefing/news.json` feeds the News page
- `News_flow/` holds date-stamped focus-news outputs

## How To Explain It To Another LLM

If you need to give ChatGPT or another model context, the shortest accurate description is:

"Diet Bloomberg is a local QuantLab dashboard served on port 8766. It has four live pages: Macro, AI Cascade, ETF Structure, and News. The Macro page is a regime board for liquidity, rates, credit, sentiment, options structure, and market internals. The AI page tracks four supply-chain flows: silicon, optical, power, and demand, plus Google Trends and obscure supplier picks. The ETF page tracks momentum leaders and structural squeeze setups. The News page prioritizes focus-list headlines, then broader watchlist and market wire headlines. Data is refreshed by `run_all.py` into `catalyst_analysis_db/`, and the server is started by `scripts/startup_diet_bloomberg.py`."

## Weekly Summary Format

When you want the dashboard compressed into a Monday-morning regime note, use this exact template.

```text
DIET BLOOMBERG WEEKLY SUMMARY

Date / Time:
Overall Macro Regime:
Macro Score:
Fed Net Liquidity:
XLY/XLP:
VIX Term Structure:
Fed Cut Odds:
Rates / Repo Plumbing:
Yield Curve:
M2:
COT / CTA / Systematic Positioning:
SLOOS / Credit Spigot:
HY Spreads:
Real Yields:
DXY / Global Liquidity:
Put/Call + SPX Options Regime:
Sector Rotation:
AI Cascade Status:
ETF Structural Squeeze Signals:
Focus-List News Themes:
Final Overlay:
+1 / +0.5 / +0.25 / 0 / -0.25 / -0.5 / -1

Key Bullish Evidence:
Key Bearish Evidence:
What Would Flip the Regime:
Names Most Helped:
Names Most Hurt:
```

Interpretation notes:

- Read the live Macro, AI, ETF, and News pages first.
- Use Diet Bloomberg terms directly when the page already provides them.
- If a field is missing from the live dashboard, write `Unavailable in current dashboard feed`.
- `Final Overlay` must be one of the seven fixed values shown above.

## Operational Notes

- The server now exposes `/health`, which renders all live pages and fails if any page is broken.
- `scripts/startup_diet_bloomberg.py` should treat an unhealthy listener as stale and restart it.
- Template formatting should degrade gracefully when a collector field is missing instead of taking down the whole page.

## Files That Matter

- `Diet Bloomberg/serve.py`: local HTTP server and route renderer
- `Diet Bloomberg/templates/`: page templates
- `scripts/startup_diet_bloomberg.py`: startup, health check, and restart logic
- `run_all.py`: collector refresh entry point
- `data_collectors/`: source collectors for the dashboard payloads
- `catalyst_analysis_db/`: rendered JSON payload store