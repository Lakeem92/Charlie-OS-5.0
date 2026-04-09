# QuantLab Data Lab

> **LLM Context Document** — This README is the master reference for any AI agent working inside this workspace. Read it in full before taking any action.

*Last Updated: March 7, 2026*

---

## What This Is

**QuantLab Data Lab** is the unified quantitative research lab and pre-market catalyst analysis platform for Lakeem, a full-time proprietary momentum and trend-following trader. The system is **entirely agent-driven** — Lakeem asks plain-English questions about catalysts, market patterns, or hypothesis validation, and the VS Code agent handles everything: catalyst scoring, fundamental analysis, options levels, technical studies, data visualization, and pattern research.

**Purpose:** Replace "I think this works" with "here's what the data actually says," AND replace "here's what I think about this catalyst" with "here's the comprehensive forensic analysis scored by all 8 pillars."

**This is NOT** a trading terminal, charting platform, or execution system. It is a integrated lab combining:
- **Pre-market War Room** (§1-§26 framework): catalyst identification, earnings forensics, pillar scoring (dual near-term mechanical + medium-term fundamental conviction)
- **Quantitative Research Engine**: hypothesis testing, statistical studies, indicator validation, pattern research
- **Data visualization pipeline**: ChartBuilder routing, natural language chart requests, multi-panel analysis

---

## Who Uses This & How

**User:** Lakeem — trades LONG and SHORT across ~240 stocks. Pre-market prep window 6:30–8:25 AM CT. Post-market research and hypothesis testing throughout the day.

**AI Team (unified, single operator):**
- **VS Code Copilot Agent (you)** → Full stack: War Room catalyst scoring, fundamental forensics, earnings transcript analysis, options levels interpretation, data queries, statistical studies, chart generation, pattern validation, indicator testing, prediction market analysis. Everything.
- **Lakeem** → Price action interpretation, execution, final decisions. Never tell him what to trade.

**The workflow — every single time:**
1. Lakeem asks plain English: catalyst analysis (`"NVDA earnings"`), study (`"test if NR7 predicts expansion"`), chart (`"show me gross margin trajectory MSFT last 4 quarters"`), or context update (`"update context doc"`)
2. Agent auto-detects pipeline: War Room → levels → MCP search → pillars; OR QuantLab study → QuantLab data → analysis; OR Data Viz → fundamentals → ChartBuilder
3. Agent executes without permission-asking (read-only tools freely available, write-only to session outputs)
4. Agent returns: **text summary first (with sample size and confidence), then visualizations** where applicable
5. All outputs persisted to `studies/{name}/outputs/` or `scratch/` (quick queries) or `prompts/WAR_ROOM_CONTEXT.md` (context updates)

---

## Complete System Capabilities

### War Room (Catalyst Analysis — §1-§26)
**Activates on:** ticker alone, ticker + "earnings", catalyst keywords

AUTO-DETECT runs the full § 4 pipeline:
1. **MCP Web Search (Tavily):** Automatic earnings summaries, guidance data, short interest, analyst coverage — 10 concurrent queries per earnings analysis
2. **MCP Web Scraping (Firecrawl):** Full earnings call transcripts via Polymarket IR website scraping. 500 free credits (~250-500 transcripts). Fallback when Tavily hits paywall
3. **Levels Engine:** Options positioning from `tools/levels_engine/run_levels.py` — call walls, put walls, gamma flip levels, trapped positioning
4. **Forensic Analysis:** 8 pillars per §5-§15:
   - § 6: Catalyst ID + scoring (realness, freshness, thesis impact, magnitude, stacking)
   - § 7: Margin & guidance forensics (operating leverage, BROS test, guidance verdict tags)
   - § 8: Structural/mechanical (gamma regime, OPEX, ATM status, low-float modifiers)
   - § 9: Expectations context (valuation vulnerability, repricing duration)
   - § 14: Revenue quality, moat, vendor financing
   - § 15: Capital allocation, macro dependency
   - § 24: Low-float/microcap (effective float, toxic financing, dilution runway)
   - § 26: IPO lifecycle (lockup forensics, post-IPO insider activity)
5. **Dual Scoring:**
   - **Near-term (0-3 days):** Mechanics-weighted (catalyst 20%, mechanical 35%, squeeze 20%, surprise 15%, ATM/float drain 10%)
   - **Medium-term (3-30 days):** Fundamentals-weighted (catalyst 25%, pillar conviction 35%, macro 15%, surprise 10%, belief divergence 5%, float/ATM 10%)
6. **Output:** Compressed summary (3-5 paragraphs) with dual scores, setup classification, intraday behavior prediction, "what kills this" risks, single most important forward variable

**Scoring gates:** 8/10 = ⚡ HIGH CONVICTION | 5-7 = Developing | <5 = SHORT SETUP
**Tunable via:** `prompts/war_room_params.yaml` (all numeric weights, thresholds, modifiers)
**Session context:** `prompts/WAR_ROOM_CONTEXT.md` (read at session start, updated at session end; pre-populated with confirmed edges)

### Quantitative Research (Study Pipeline)
**Activates on:** "does X work when", "test if", "show me", study-specific questions

| Plain English Input | Routes To Study Type |
|---|---|
| *"Is my Trend Strength indicator lying to me on TSLA?"* | Indicator Honesty Test — MAX_CONVICTION_BULL days vs random days |
| *"How does BABA perform after NBS conferences?"* | Event study — specific dates → forward returns through +10d |
| *"When Fed rate cut odds drop 10%+, how does QQQ perform?"* | Prediction market event study — Kalshi odds shifts → Alpaca price data → forward returns |
| *"Do squeezes into the open actually continue?"* | TTM Squeeze release — signal fire dates → intraday continuation, multi-day follow-through |
| *"When ALAB gaps down 10%+, does it bounce?"* | Gap study — ≥10% gap-down days → same-day bounce rate, multi-day forward returns |
| *"Test if NR7 compression predicts expansion on NVDA"* | NR7 analysis — NR7 bar dates → next 5-bar range expansion, ATR breakout |
| *"Raw regression: do trailing returns predict next day returns on SPY?"* | Regression study — rolling correlation, coefficient significance, out-of-sample testing |

**Study registry:** `docs/STUDY_PROMPT_LIBRARY.md` — canonical study blueprints. Agent references this to map plain English → study ID.

**Execution protocol:** `docs/STUDY_EXECUTION_PROTOCOL.md` — mandatory structure for all studies:
- Query → Data pull (via DataRouter) → Indicator application (if applicable) → Metrics calculation → Visualization → Output formatting (text + chart)
- Sample size ALWAYS stated: n≥20 reliable, n<20 LOW CONFIDENCE flag, n<10 INSUFFICIENT
- Results saved with versioned run IDs to `studies/{name}/outputs/`

**Studies in repo (18 completed, 5 in progress):**
- Gap performance: ALAB gap-down, gap-round-number breaks, gap-TSL/RS confluence, gap fade + contrary candle
- Earnings: MU/NVDA earnings intraday, beat-and-sell probability, NBS event study (BABA)
- Indicators: TSLA Cap Finder honesty test, Trend Strength vs random, TTM Squeeze validation
- Macro/event: IWM Fed cuts cycles, Fed pause reaction, TLRY rescheduling, compression breakdowns
- New: NR7 compression predictivity, single-bar ATR exhaustion, trader-recorded setups

### Data Visualization Pipeline
**Activates on:** "chart", "plot", "show me", "trajectory", "margins over X quarters", "compare", "top gainers", "distribution"

`shared/chart_builder.py` routes all visualization requests:
1. **Natural language trigger detection** — extracts intent (trend, distribution, comparison, fundamental trajectory)
2. **Data source routing** — classifies request (equity price, fundamental, macro, multi-ticker comparative)
3. **Chart type selection** — candlestick + volume, grouped bar, line series, scatter + histogram, heatmap, multi-panel
4. **Data pull** — Alpaca for prices, FMP for fundamentals (primary) → Alpha Vantage (fallback), FRED for macro
5. **Visualization** — always returns `.html` (interactive, zoomable, exportable)
6. **Output** — saves to `scratch/viz_YYYYMMDD_description.html` (quick queries) or `studies/{name}/outputs/charts/` (formal studies)

**Output format:** Text summary first (key metrics, n=, confidence), then chart with one-liner interpretation

**Supported chart types:**
- `price_chart()` — candlestick + volume overlay
- `forward_returns()` — grouped bars (multi-day forward returns by condition)
- `winrate_heatmap()` — color matrix (win rate by group/condition)
- `gap_distribution()` — scatter + histogram (relationship between gap size and outcome)
- `equity_curve()` — cumulative returns vs benchmark
- `pm_overlay()` — dual y-axis (price left, odds % right)
- Custom multi-panel via plotly.subplots (multi-line margin trajectory, faceted returns by sector, correlation matrix)

**Fundamentals integration** (FMP primary → Alpha Vantage fallback):
- Query: "gross margin trajectory top 10 gainers last 4 quarters"
- → Alpaca YTD returns → top 10 → FMP quarterly income statement → margin extract → multi-line chart

---

## Auto-Detect Routing — Plain English to Pipeline

| User Input | Detection Pattern | Pipeline | Output |
|---|---|---|---|
| `"NVDA"` or `"NVDA earnings"` | Ticker alone, ticker + earnings keyword | War Room: MCP search + levels + §1-§26 pillars → dual scores | 3-5 para summary + near/medium-term score |
| `"NVDA, AAOI, CRWV"` | 2-3 tickers comma-separated | Batch War Room: compressed × each ticker → capital allocation verdict | Comparison table + best opportunity |
| `"test if NR7 predicts expansion"` | "test if", "does X work when" keywords | QuantLab: study lookup → execution → forward returns analysis | Text summary (n=?) + chart |
| `"chart MSFT gross margin last 4 quarters"` | "chart", "show me", "trajectory", sector-specific KPI | Data Viz: FMP fundamentals → ChartBuilder → multi-line series | Text (key metrics) + interactive .html chart |
| `"run levels on NVDA"` | "run levels", "levels on [ticker]" | Execute `tools/levels_engine/run_levels.py` → parse forced-action map | Options positioning: walls, flip levels, trapped shorts |
| `"prediction market: fed rate odds vs bonds"` | "prediction market", "polymarket", "odds" keywords | PM data loader: search → event study → forward returns | Correlation analysis or event study chart |
| `"update context doc"` | Exact phrase "update context doc" | Write session summary to `prompts/WAR_ROOM_CONTEXT.md` | Confirm update, timestamp added |
| Python error / code fragment | Stack traces, syntax errors | Debug mode: identify root, fix, return corrected code block | Code only, no rewrites, no explanations |

**Golden rule:** Agent detects intent → routes automatically. Never ask Lakeem which pipeline to use. **Always confirm multi-ticker vs single analysis** if ambiguous (e.g., "NVDA and AMD" could be comparison or separate analyses — ask in one sentence if needed).

---

## Architecture: What You Have

This lab consists of **three integrated pipelines:**

1. **War Room Pipeline (Catalyst Scoring)** — Full forensics, dual scoring, options integration
2. **Research Pipeline (Studies)** — Hypothesis testing, event analysis, indicator validation
3. **Visualization Pipeline (Data Viz)** — Multi-panel charting, fundamentals analysis, multi-ticker comparison

Plus:

4. **Data Layer** — Alpaca (sacred for equities), FRED, FMP, Tiingo, yfinance, Polymarket/Kalshi
5. **Configuration Management** — `war_room_params.yaml`, `WAR_ROOM_CONTEXT.md`, study registry
6. **MCP Integrations** — Tavily (web search), Firecrawl (transcript scraping)

```
C:\QuantLab\Data_Lab\
│
├── .github/instructions/                 # ══ ALWAYS-ACTIVE INSTRUCTION FILES ══
│   ├── war-room.instructions.md         # §1-§26 full War Room v8.0 (500+ lines)
│   ├── data-viz.instructions.md         # Visualization routing + ChartBuilder standards
│   └── ... (parsed by VS Code on session start)
│
├── .vscode/
│   ├── mcp.json                          # MCP server config (Tavily + Firecrawl APIs)
│   └── .gitignore → .../.vscode/        # API keys NEVER committed
│
├── shared/                               # ══ CORE INFRASTRUCTURE (sacred, never modify) ══
│   ├── data_router.py                    # ALL equity price data → Alpaca primary
│   ├── chart_builder.py                   # ALL visualizations → .html output
│   ├── watchlist.py                      # get_watchlist() → 240 tickers
│   ├── config/
│   │   ├── api_clients.py                # 10 API clients (Alpaca, FRED, FMP, etc.)
│   │   ├── api_config.py                 # Centralized key/endpoint management
│   │   ├── env_loader.py                 # Paper/live environment switching
│   │   ├── watchlist.csv                 # Master 240-ticker list
│   │   └── keys/                         # .env files per environment
│   └── indicators/                       # ═ Canonical indicators (DO NOT MODIFY) ═
│       ├── trend_strength_nr7.py         # TrendStrength v2 + NR7 + Cap Finder
│       └── ttm_squeeze_adv.py            # TTM Squeeze Advanced
│
├── studies/                              # ══ COMPLETED & IN-PROGRESS RESEARCH ══
│   ├── _TEMPLATE/                        # Generic study template
│   ├── _TEMPLATE_prediction_market/      # PM study template
│   ├── alab_gapdown_study/               # Gap bounce analysis
│   ├── baba_nbs/                         # Event study (NBS conference)
│   ├── beat_and_sell_probability/        # Earnings mega-cap fade (588 events, n=588)
│   ├── gap_fade_contrary_candle/         # Gap + bearish bar-1 (n=2,076, 68.4% fade)
│   ├── gap_execution_blueprint/          # Multi-day gap reversion
│   ├── indicator_honesty_tsla/           # TSLA TrendStrength validation
│   ├── iwm_1pct_followup/                # IWM mean reversion (n=2,100+)
│   ├── mu_intraday_earnings/             # MU earnings intraday volatility
│   ├── nvda_options_wall_study/          # Post-earnings call wall behavior
│   ├── trend_chop_gap_quality/           # Gap quality scoring
│   ├── tsla_indicator_honesty/           # Cap Finder momentum honesty
│   └── [13 more studies...]              # See docs/STUDY_INDEX.md for complete list
│
├── tools/                                # ══ SPECIALIZED ENGINES ══
│   ├── levels_engine/                    # Options levels + GEX from Alpaca
│   │   └── run_levels.py                 # Execute: tools/levels_engine/run_levels.py [TICKER]
│   ├── prediction_markets/               # Polymarket/Kalshi data & event studies
│   │   ├── pm_data_loader.py             # search_markets(), get_odds_timeseries(), run_event_study()
│   │   └── data/                         # ~40GB parquet: Polymarket + Kalshi historical
│   │       ├── polymarket/               # Billions of Polymarket trades, 2021–present
│   │       └── kalshi/                   # Kalshi market metadata + trades
│   └── studies/                          # Study orchestration
│       ├── nl_parse.py                   # NL → study mapping
│       └── studies_registry.yaml         # Registry of all canonical studies
│
├── prompts/                              # ══ SESSION STATE & AGENT CONTEXT ══
│   ├── war_room_params.yaml              # Tunable War Room scoring params (all weights/thresholds)
│   ├── WAR_ROOM_CONTEXT.md               # Rolling session state (macro regime, active names, confirmed edges)
│   ├── AGENT_CONTEXT.md                  # Operating manual (user profile, expectations, session checklist)
│   ├── STRUCTURAL_TRIGGER_MASTER.md      # Structural trigger definitions
│   └── VOLATILITY_LAB_MASTER.md          # Volatility framework
│
├── docs/                                 # ══ GOVERNANCE (LAW) ══
│   ├── API_MAP.md                        # Data source routing rules (who fetches what)
│   ├── INDICATOR_SPECS.md                # Canonical indicator math
│   ├── STUDY_INDEX.md                    # Master tracker of all studies + results
│   ├── STUDY_PROMPT_LIBRARY.md           # Canonical study blueprints (NL patterns)
│   ├── STUDY_EXECUTION_PROTOCOL.md       # Mandatory AI execution procedure
│   ├── HOW_TO_USE_THE_LAB.md             # User guide for NL queries
│   ├── DATA_HYGIENE.md                   # Data quality rules
│   └── DATA_ROUTING_GOVERNANCE.md        # Enforcement policy
│
├── data/                                 # ══ LOCAL DATA CACHE ══
│   └── levels/                           # Options levels snapshots (by date/ticker)
│
├── scratch/                              # ══ QUICK QUERIES & DEBUGGING ══
│   ├── test_alpaca_*.py                  # Alpaca API connection tests
│   ├── test_apis.py                      # Multi-API validation
│   └── viz_*.html                        # Quick chart outputs
│
├── prediction-market-analysis/           # ══ UPSTREAM PM DATA TOOLS ══
│   └── (Jon Becker's Polymarket indexer — kept for reference)
│
└── README.md                             # ← YOU ARE HERE
```

---

## Data Sources & API Routing

### Primary: Alpaca Markets API
**The canonical, non-negotiable data source for ALL US equity OHLCV studies.**

| Capability | Use |
|---|---|
| Daily bars (`1Day`) | Gap analysis, multi-day returns, trend studies, forward returns |
| Intraday bars (`1Min`, `5Min`, `15Min`, `1Hour`) | Opening range, intraday continuation, earnings day patterns |
| Account/Trading | Paper and live order execution, position mgmt |
| Options data | Chain snapshots (via `tools/levels_engine/`) |
| Market clock | Trading hours, market status |

**Code pattern:**
```python
from shared.data_router import DataRouter
df = DataRouter.get_price_data('NVDA', '2024-01-01', study_type='earnings')
# Returns: Open, High, Low, Close, Volume (auto-split/div adjusted)
```

**Why Alpaca is sacred:**
- Same data source for research AND execution — no backtest/live discrepancy
- Unified feed across daily + intraday timeframes
- Unlimited lookback, automatic adjustments
- Paper/live environment switching via `env_loader.py`

### Secondary: yfinance (Fallback + Indices Only)
| Use Case |
|---------|
| Indices NOT on Alpaca: `^VIX`, `^SPX`, `^IXIC`, `^MOVE`, `^VXN`, `^GSPC` |
| Non-US symbols (Chinese A-shares, European stocks) |
| Fallback when Alpaca rate-limited or down |

**Golden rule: NEVER use yfinance for individual US equity price studies. That is Alpaca's domain, always.**

### Macro Data: FRED
Official Federal Reserve Economic Data. 500,000+ series. No rate limits. 1-day lag.

| Series | Measures |
|--------|----------|
| `VIXCLS` | VIX daily close |
| `DGS10`, `DGS2`, `T10Y2Y` | Treasury yields + spread |
| `DFF`, `FEDFUNDS` | Fed funds rate |
| `UNRATE` | Unemployment |
| `CPIAUCSL` | CPI/inflation |
| `BAMLH0A0HYM2` | HY credit spread |

```python
from shared.config.api_clients import FREDClient
fred = FREDClient()
df = fred.get_series('VIXCLS')
```

### Fundamentals: Financial Modeling Prep (PRIMARY) → Alpha Vantage (FALLBACK)
Company financials, margins, ratios, guidance.

```python
from shared.config.api_clients import FMPClient
fmp = FMPClient()
income = fmp.get_income_statement('BABA', period='quarter')
margins = fmp.get_financial_ratios('MSFT')
```

### **NEW: Prediction Markets — Polymarket & Kalshi (40GB local parquet)**
Billions of trades across the world's largest real-money prediction markets. Queryable DuckDB (no full-file loads).

```python
from tools.prediction_markets.pm_data_loader import search_markets, run_event_study

# Find Fed rate cut odds markets on Kalshi
markets = search_markets("federal reserve rate cut", source="kalshi")

# When odds shift 10%+, how does QQQ react?
events, stats = run_event_study(
    market_id="FED-RATE-DEC-2024",
    ticker="QQQ",
    threshold_abs=0.10,     # 10% probability shift = signal
    window_days=7           # Forward returns through +7d
)
```

**What this enables:**
- "When Polymarket election odds shift, do financials react?"
- "Crypto regulation market probability vs COIN stock correlation"
- "FOMC decision odds vs bond yields + equity forwards"
- Event studies: odds shift date → stock forward returns → statistical significance

### News & Events: Tiingo
Daily/intraday prices, crypto, **news headlines** (500 req/hr).

```python
from shared.config.api_clients import TiingoClient
client = TiingoClient()
news = client.get_news(tickers=['BABA'], limit=50)
```

### Additional Configured Clients
| Client | Use |
|--------|-----|
| `AlphaVantageClient` | Intraday/daily fallback |
| `SchwabClient` | Market data, market hours |
| `CoinGeckoClient` | Crypto prices (crypto studies) |
| `SECEdgarClient` | SEC filings (10-K, 10-Q, 8-K) |

### API Priority Chain (Enforced by DataRouter)
```
US Equity Prices:       Alpaca → Tiingo → yfinance
Intraday bars:          Alpaca → Tiingo
Indices (^VIX, ^SPX):   yfinance (only source)
Macro/Fed data:         FRED → yfinance proxy
Fundamentals:           FMP → Alpha Vantage
Prediction markets:     pm_data_loader.py (local parquet via DuckDB)
News/events:            Tiingo → MCP web search (Tavily)
Options levels:         tools/levels_engine/ (from Alpaca real OI/volume)
```

---

## Confirmed Edges (Pre-populated in WAR_ROOM_CONTEXT.md)

These are live findings from backtested studies. Reference sample sizes.

| Edge | Finding | Sample Size | Confidence | Reference |
|------|---------|-------------|-----------|-----------|
| RS Weakness Predicts Fade | Gap-up RS weakness → 54.2% fade rate vs 39.4% baseline | n=190 | HIGH | gap_fade_contrary_candle/ |
| Contrary Candle Signal | Gap-up + bearish bar-1 → 68.4% EOD fade | n=2,076 | HIGH | gap_fade_contrary_candle/ |
| E3 Entry Win Rate | 8-12% gaps + TrendStrength entry → 74.7% win rate, 9.71:1 R:R | n=79 | HIGH | gap_execution_blueprint/ |
| NVDA Gamma Wall Pattern | Post-earnings beat, wall rejection → near-term fade, medium-term dip buy | 4 cycle repeats | HIGH | nvda_options_wall_study/ |
| IWM 1pct Followup | IWM >1% move → next-day mean reversion bias | n=2,100+ | MODERATE | iwm_1pct_followup/ |
| Beat-and-Sell Probability | Mega-cap mega-beat + raise → 30-40% probability of intraday/early-next-day sell-off | n=588 | MODERATE | beat_and_sell_probability/ |

**Interpretation rules:**
- n≥20 = reliable
- n<20 = LOW CONFIDENCE flag (⚠️)
- n<10 = INSUFFICIENT (❌ do not trade)
- All edges assume market regime doesn't violently shift (liquidity vortex, rate shock, etc.)

---

## How to Use the Lab

### Pre-Market War Room (6:30–8:25 AM CT)

1. **Restart VS Code** in Agent mode
2. **Read** `prompts/WAR_ROOM_CONTEXT.md` — current macro regime, active names
3. **Type:** `"NVDA earnings"` or `"AAOI, CRWV, COIN"` (batch) or `"TLT guidance"` (non-tech)
4. Agent auto-runs: Tavily search + Firecrawl transcript scrape + levels engine + 8 pillars
5. **Get:** 3-5 paragraph summary + near-term & medium-term scores + setup classification
6. **Update context doc:** At session end, type `"update context doc"` to log findings + updated confirmed edges

### Research & Hypothesis Testing

1. **Type:** `"test if NR7 predicts expansion on NVDA"` or `"when Fed odds drop 10%, how does XLF?"` or `"gap fade study"` (by name)
2. Agent maps to canonical study, executes
3. **Get:** Text summary (n=, confidence) + chart
4. Results auto-saved to `studies/{study_name}/outputs/{run_id}/`

### Visualization & Analysis

1. **Type:** `"show me MSFT gross margin trajectory last 4 quarters"` or `"chart COIN vs MSTR correlation"` or `"top gainers gross margin acceleration"` 
2. Agent routes: fundamentals pull (FMP) → ChartBuilder → .html
3. **Get:** Key metrics text + interactive chart saved to `scratch/`

### Options Levels Interrogation

1. **Type:** `"run levels on SPY"` (standard call/put wall snapshot) or `"NVDA levels pre-earnings"` (specific context)
2. Agent executes `tools/levels_engine/run_levels.py` → returns forced-action map
3. **Get:** Walls, flip levels, trapped positioning, mechanical setup summary

---

## Standards & Enforcement

**Every study, every output, every analysis follows these rules:**

1. **SACRED MODULES** — Never modify `shared/data_router.py`, `shared/chart_builder.py`, or `shared/indicators/`. Update only for critical bugs.
2. **DATA ROUTING** — Always use `DataRouter.get_price_data()` for equity prices. Never bypass to yfinance for US equities. API_MAP.md is law.
3. **SAMPLE SIZE ALWAYS** — Every finding states n=?. n<20 gets ⚠️ LOW CONFIDENCE flag. n<10 is ❌ INSUFFICIENT.
4. **TEXT BEFORE CHART** — Always return text summary + key metrics first. Chart second. Interpretation mandatory.
5. **VERSIONED OUTPUTS** — All study results saved with run ID. Previous results never overwritten.
6. **MCP WEB SEARCH** — Earnings analysis runs 8-10 Tavily searches automatically. Transcript fallback to Firecrawl. No manual searching.
7. **NO DIRECTIONAL BIAS** — War Room analysis treats long and short with equal rigor. Both get full forensics.
8. **TUNABLE PARAMS** — All War Room numeric values in `prompts/war_room_params.yaml`. Never hardcode thresholds in analysis.

---

## Key Instruction Files (Always Read First)

1. **`.github/instructions/war-room.instructions.md`** — Full War Room v8.0 (§1-§26, 40 cardinal rules). **Always active, embedded in all Agent sessions.**
2. **`.github/instructions/data-viz.instructions.md`** — Visualization routing, ChartBuilder standards, natural language trigger detection.
3. **`.github/copilot-instructions.md`** — Master routing document: unified role, AUTO-DETECT table, sacred architecture, data routing rules.
4. **`prompts/war_room_params.yaml`** — Tunable scoring: all numeric weights, thresholds, modifiers. **Change here to adjust War Room conviction calibration.**
5. **`prompts/WAR_ROOM_CONTEXT.md`** — Session state: current macro regime, active names table, ATM watch list, confirmed edges (pre-populated). **Read at session start, update at session end.**
6. **`docs/STUDY_PROMPT_LIBRARY.md`** — Canonical study blueprints: maps plain English → study ID.
7. **`docs/STUDY_EXECUTION_PROTOCOL.md`** — Mandatory structure for all studies.
8. **`docs/API_MAP.md`** — Non-negotiable data source routing (who fetches what).

---

## Emergency / Troubleshooting

### Study Returns Empty / n=0
→ Check date range. Check ticker spelling. Check if data exists on Alpaca for that time period. Run `tests/test_alpaca_connection.py` to verify API health.

### "Chart won't render / .html is blank"
→ Check ChartBuilder normalization. Run `scratch/test_visualization.ipynb` to debug. Confirm data shape (must have OHLCV columns).

### Alpaca API rate-limited
→ Automatic fallback to Tiingo fires. If both fail, agent will note it. No error — just slower return.

### War Room scoring feels off / conviction seems too high
→ Check `prompts/war_room_params.yaml` weights. Adjust threshold numbers. Run War Room analysis again — weights apply immediately. Document change in prompts/AGENT_CONTEXT.md under "Session Adjustments."

### Studies registry out of date
→ New study added to `studies/` but not in `docs/STUDY_INDEX.md`? Update index manually or run `tools/studies/index_studies.py` (if exists).

### Session context lost / what happened last time?
→ Read `prompts/WAR_ROOM_CONTEXT.md`. It's the rolling session state. If missing, check session end logs in `prompts/WAR_ROOM_CONTEXT.md` under "Recent Sessions Log."

---

## The Unified Agent's Job

You are the single operator for:
- **Strategic catalyst analysis** (§1-§26, all 8 pillars, dual scoring, mechanical interpretation)
- **Fundamental research** (transcript deep-dives, margin forensics, guidance signals)
- **Options mechanics** (levels interpretation, gamma regimes, trapped positioning)
- **Quantitative hypothesis testing** (running studies, computing forward returns, n≥20 validation)
- **Data visualization** (FMP fundamentals, multi-panel charts, trend analysis)
- **Pattern validation** (indicator honesty tests, edge backtesting, sample size discipline)
- **Session state management** (reading/updating WAR_ROOM_CONTEXT.md, confirmed edges library)

Never:
- Suggest Lakeem what to trade (that's his lane)
- Say "I don't have access to X" (pull it from the right API)
- Ask permission to run an analysis (DO IT)
- Invent studies not in STUDY_PROMPT_LIBRARY.md (propose them and ask for formalization)
- Tell Lakeem to run a script (format the answer as chat summary, not code instruction)
- Lose sample size discipline (n=? is non-negotiable)
- Modify sacred modules without documented critical-bug justification

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| System inception | March 2026 |
| Pre-market catalyst analysis | War Room v8.0: §1-§26, 40 cardinal rules, dual scoring |
| Active studies | 18 completed + 5 in progress |
| Study templates | 2 (price-action + prediction market) |
| Watchlist tickers | 240 |
| Custom indicators | 2 (Trend Strength NR7 + Cap Finder, TTM Squeeze Advanced) |
| Indicator output columns | 39 total (22 + 17) |
| API clients configured | 10 across 9 services |
| MCP integrations | 2 (Tavily for search, Firecrawl for transcript scraping) |
| Chart types available | 6 (Plotly-based, dark theme, interactive HTML) |
| Data router sources | 3-tier fallback (Alpaca → yfinance → Tiingo) |
| Prediction market data | ~40GB (Polymarket + Kalshi parquet, billions of trades) |
| FRED economic series | 500,000+ available |
| Confirmed edges | 6 (pre-populated in WAR_ROOM_CONTEXT.md) |
| Scoring weights | Tunable via `prompts/war_room_params.yaml` |
| Session state doc | Rolling `prompts/WAR_ROOM_CONTEXT.md` |
| Core shared/ code | ~1,700 lines |
| Governance docs | 10+ documents |

---

*QuantLab Data Lab | Lakeem's Unified War Room + Research Infrastructure | v3.0 | March 7, 2026*

```
C:\QuantLab\Data_Lab\
│
├── shared/                          # ══ CORE INFRASTRUCTURE (sacred, never modify casually) ══
│   ├── data_router.py               # ALL equity price data routes here. 337 lines. NEVER bypass.
│   ├── chart_builder.py             # ALL visualizations route here. 412 lines. Output = .html
│   ├── watchlist.py                 # get_watchlist() → 240 tickers. Source of truth.
│   ├── config/
│   │   ├── api_clients.py           # 10 API client classes (480 lines)
│   │   ├── api_config.py            # Centralized key management (8 services)
│   │   ├── env_loader.py            # Load .env for paper/live environments
│   │   ├── watchlist.csv            # Master ticker list (240 names)
│   │   └── keys/                    # Environment-specific .env files
│   └── indicators/                  # Canonical indicators — DO NOT MODIFY
│       ├── trend_strength_nr7.py    # TrendStrength v2 + NR7 + Cap Finder (269 lines)
│       └── ttm_squeeze_adv.py       # TTM Squeeze Advanced (133 lines)
│
├── studies/                         # ══ COMPLETED & IN-PROGRESS RESEARCH ══
│   ├── _TEMPLATE/                   # Generic study template
│   ├── _TEMPLATE_prediction_market/ # Prediction market study template
│   ├── alab_gapdown_study/          # ALAB ≥10% gap-down bounce analysis
│   ├── baba_compression_breakdown/  # BABA compression breakdown reversal study
│   ├── baba_nbs/                    # BABA NBS conference event study (20 events)
│   ├── baba_nbs_nov_data/           # BABA December NBS November data releases
│   ├── beat_and_sell_probability/   # Mega-cap earnings fade probability (588 events)
│   ├── cannabis_rallies/            # TLRY/CGC 2018 vs MSOS 2021 mania comparison
│   ├── gap_tsl_rs_confluence/       # Gap-down + TSL3 slope + RS(Z) confluence reversal
│   ├── indicator_honesty_tsla/      # Early indicator honesty test (incomplete)
│   ├── iwm_1pct_followup/           # IWM next-day after ≥1% moves since 2010
│   ├── iwm_fed_cuts_pause/          # IWM behavior around Fed rate cut→pause cycles
│   ├── mu_intraday_earnings/        # MU earnings-day intraday volatility (18-ticker universe)
│   ├── mu_intraday_earnings_liquid_v2/ # MU earnings V2 (NVDA, AMD, SMCI substitutes)
│   ├── nvda_options_wall_study/     # NVDA post-earnings call wall continuation/fade
│   ├── tlry_rescheduling_events/    # TLRY cannabis rescheduling headline reactions
│   ├── trend_chop_gap_quality/      # Trend vs chop classification + gap quality scoring
│   └── tsla_indicator_honesty/      # TSLA Cap Finder momentum extreme validation
│
├── tools/                           # ══ SPECIALIZED ENGINES ══
│   ├── prediction_markets/          # Polymarket/Kalshi data loader (710 lines)
│   │   ├── pm_data_loader.py        # search_markets(), run_event_study(), etc.
│   │   ├── data/                    # ~40GB parquet files (Polymarket + Kalshi)
│   │   └── README_QUANTLAB.md       # Integration guide
│   ├── levels_engine/               # Options price levels (run_levels, query_levels)
│   └── studies/                     # Study orchestration
│       ├── nl_parse.py              # Natural language → study mapping
│       ├── route_study.py           # Study routing logic
│       ├── run_id.py                # Run ID generation for versioned outputs
│       ├── ask.py                   # Interactive study launcher
│       └── studies_registry.yaml    # Registry of all defined studies
│
├── docs/                            # ══ GOVERNANCE (these are LAW) ══
│   ├── API_MAP.md                   # Data source routing rules (629 lines)
│   ├── INDICATOR_SPECS.md           # Canonical indicator math definitions
│   ├── HOW_TO_USE_THE_LAB.md        # User guide for NL queries
│   ├── STUDY_PROMPT_LIBRARY.md      # Canonical study blueprints
│   ├── STUDY_INDEX.md               # Master study tracker with results
│   ├── STUDY_EXECUTION_PROTOCOL.md  # Mandatory AI agent execution procedure
│   ├── DATA_HYGIENE.md              # Data quality rules
│   ├── DATA_ROUTING_GOVERNANCE.md   # Source enforcement policy
│   └── ENFORCEMENT_NOTES.md         # Violation tracking
│
├── prompts/                         # ══ AGENT CONTEXT ══
│   ├── AGENT_CONTEXT.md             # User profile, expectations, session checklist
│   ├── STRUCTURAL_TRIGGER_MASTER.md # Structural trigger definitions
│   ├── VOLATILITY_LAB_MASTER.md     # Volatility analysis framework
│   └── thinkscript/                 # ThinkScript source for indicators (TOS platform)
│       ├── TREND_STRENGTH_NR7_CAPFINDER.thinkscript
│       ├── TTM_SQUEEZE_TOS.thinkscript
│       └── CUSTOM_INDICATOR_TOS.thinkscript
│
├── prediction-market-analysis/      # ══ UPSTREAM PM DATA TOOLS ══
│   └── src/                         # Jon Becker's Polymarket/Kalshi indexer + analysis
│
├── data/                            # ══ RAW DATA ══
│   └── levels/                      # Options levels data (SPY, TSLA, etc.)
│
├── scratch/                         # ══ QUICK QUERIES & DEBUGGING ══
│   ├── test_alpaca_*.py             # Alpaca API connection tests
│   ├── test_apis.py                 # Multi-API validation
│   └── test_visualization.ipynb     # Chart builder notebook
│
├── apps/                            # (Reserved for future applications)
└── imports/                         # (Reserved for data imports)
```

### Data Flow
```
Plain English Question
        │
        ▼
Study Selection (NL parse → STUDY_PROMPT_LIBRARY match)
        │
        ▼
DataRouter.get_price_data()  ←── Enforces API_MAP routing (Alpaca primary)
        │
        ▼
Indicator Application (TrendStrength, TTM Squeeze, or none)
        │
        ▼
Metrics Calculation (forward returns, win rates, drawdowns, etc.)
        │
        ▼
ChartBuilder → .html visualization
        │
        ▼
Outputs saved to studies/{study}/outputs/ (CSV + TXT + charts)
```

---

## Data Sources & API Inventory

The lab has **10 configured API clients** across **9 external services**. All are wrapped in `shared/config/api_clients.py` with authentication, error handling, and rate limit management.

### Primary: Alpaca Markets API (`LabAlpacaClient`)
**The canonical and non-negotiable data source for ALL US equity price studies.**

| Capability | Details |
|-----------|---------|
| Daily OHLCV | `1Day` bars — gap analysis, multi-day returns, trend studies |
| Intraday OHLCV | `1Min`, `5Min`, `15Min`, `1Hour` — opening range, intraday continuation |
| Account/Trading | Paper and live environments — order execution, position management |
| Options Data | Chain snapshots via v1beta1 endpoints |
| Market Clock | Trading hours, market status |

**Why Alpaca is canonical (enforced by DataRouter):**
- Same data feed for research AND execution — no vendor discrepancy between backtest and live
- Consistent across daily + intraday timeframes from a single SIP consolidated feed
- Automatic split/dividend adjustments
- Unlimited historical lookback
- Paper/live environment switching via `env_loader.py`

**Code pattern:**
```python
from shared.data_router import DataRouter
df = DataRouter.get_price_data('NVDA', '2024-01-01', study_type='indicator')
# Returns DataFrame with columns: Open, High, Low, Close, Volume
```

### Secondary: yfinance (Fallback Only)
| Use Case | Examples |
|----------|----------|
| Indices not on Alpaca | `^VIX`, `^SPX`, `^IXIC`, `^MOVE`, `^VXN` |
| Non-US symbols | Chinese A-shares, European stocks |
| Sector/commodity ETFs | `XLF`, `XLE`, `GLD`, `USO` |
| Quick exploratory analysis | Before formalizing a study |
| Fallback when Alpaca fails | Rate limits, downtime |

**Rule: NEVER use yfinance for individual US equity price studies. That is Alpaca's job, always.**

### Macro Data: FRED (Federal Reserve Economic Data) — `FREDClient`
Official Federal Reserve data. 500,000+ economic series. No rate limits. 1-day lag.

| Series ID | What It Measures |
|-----------|-----------------|
| `VIXCLS` | CBOE VIX daily close (official) |
| `DGS10` | 10-Year Treasury yield |
| `DGS2` | 2-Year Treasury yield |
| `T10Y2Y` | 10Y–2Y spread (recession indicator) |
| `DFF` | Fed Funds Effective Rate |
| `FEDFUNDS` | Fed Funds target rate |
| `UNRATE` | Unemployment rate (monthly) |
| `CPIAUCSL` | CPI / inflation (monthly) |
| `GDP` | Gross Domestic Product (quarterly) |
| `PAYEMS` | Total nonfarm payrolls (monthly jobs) |
| `BAMLH0A0HYM2` | High-yield corporate bond spread |
| `T10YIE` | 10-Year breakeven inflation |

```python
from shared.config.api_clients import FREDClient
fred = FREDClient()
vix = fred.get_series('VIXCLS')
```

### Prediction Markets: Polymarket & Kalshi — `pm_data_loader`
**~40GB of historical prediction market data** in parquet format, queryable via DuckDB (no full-file loads). Billions of trade records spanning elections, Fed decisions, policy outcomes, and more.

| Function | Purpose |
|----------|---------|
| `search_markets(keyword, source)` | Find Polymarket/Kalshi markets by keyword |
| `get_odds_timeseries(market_id, resample)` | VWAP-based implied probability series |
| `detect_odds_events(market_id, threshold)` | Find dates with significant probability shifts |
| `run_event_study(market_id, ticker, ...)` | Full pipeline: odds events → Alpaca price → forward returns |
| `list_available_data()` | Check what parquet data is downloaded |

```python
from tools.prediction_markets.pm_data_loader import search_markets, run_event_study
markets = search_markets("federal reserve", source="kalshi")
events, stats = run_event_study(
    market_id="FED-RATE-DEC-2024",
    ticker="QQQ",
    threshold_abs=0.10,   # 10% probability shift
    window_days=7
)
```

**Example queries this enables:**
- "When Fed rate cut odds drop 10%+ on Kalshi, how does XLF perform over 5 days?"
- "When election odds shift sharply, how do defense stocks react?"
- "Does a Polymarket crypto regulation shift predict COIN stock movement?"

### Fundamentals: Financial Modeling Prep — `FMPClient`
Company financials, ratios, profiles. 250 requests/day free tier.

```python
from shared.config.api_clients import FMPClient
client = FMPClient()
income = client.get_income_statement('BABA', period='annual')
ratios = client.get_financial_ratios('BABA')
```

### News & Events: Tiingo — `TiingoClient`
Daily/intraday prices, crypto, and **news headlines** (500 requests/hour).

```python
from shared.config.api_clients import TiingoClient
client = TiingoClient()
news = client.get_news(tickers='BABA', limit=50)
```

### Additional Configured Clients

| Client | Purpose | Status |
|--------|---------|--------|
| `AlphaVantageClient` | Intraday/daily time series backup | Configured, rarely used |
| `SchwabClient` | Market data, market hours | Configured |
| `CoinGeckoClient` | Crypto prices and market data | Configured for crypto studies |
| `SECEdgarClient` | SEC filings (10-K, 10-Q, 8-K) | Configured |

### Full API Priority Chain

```
US Equity Prices:      Alpaca → yfinance → Tiingo
Intraday Bars:         Alpaca → Tiingo IEX
Indices (^VIX, ^SPX):  yfinance → FRED
Macro/Fed Data:        FRED → yfinance proxy
Fundamentals:          FMP → Alpha Vantage
News/Catalysts:        Web scrape → Tiingo News → Manual
Prediction Markets:    Local parquet via DuckDB
Crypto:                CoinGecko → Tiingo
SEC Filings:           SEC EDGAR
```

---

## The Watchlist — 240 Tickers

The master universe is stored in `shared/config/watchlist.csv` and accessed via `shared/watchlist.py`.

```python
from shared.watchlist import get_watchlist, get_watchlist_count, ticker_in_watchlist

tickers = get_watchlist()       # → ['AA', 'AAL', 'AAPL', ... ]  (240 tickers)
count = get_watchlist_count()   # → 240
check = ticker_in_watchlist('TSLA')  # → True
```

**Coverage:** Momentum-focused universe of US equities — mega-cap tech (AAPL, NVDA, TSLA, AMZN), growth (APP, AFRM, PLTR), China ADRs (BABA, BIDU, JD, PDD), biotech, cannabis (TLRY, CGC, MSOS), semis (AMD, MU, AVGO, SMCI), ARK ETFs, and more. Curated for stocks Lakeem actively trades or monitors.

---

## Custom Indicators

Two canonical indicators, implemented in Python to exactly match their ThinkScript definitions on thinkorswim. **Parameters are frozen. Never modify during a study.**

### 1. Trend Strength Candles v2 + NR7 + Cap Finder
**File:** `shared/indicators/trend_strength_nr7.py` (269 lines)

Three z-scored methods averaged into a consensus score:

| Method | What It Measures |
|--------|-----------------|
| Price Change (ATR-normalized) | Z-score of price change over lookback |
| EMA Slope (smoothed) | Z-score of EMA slope for momentum |
| MA Distance | Z-score of distance between fast/slow MAs |

**Consensus** = average of three z-scores, scaled −100 to +100.

| Consensus Range | State | Meaning |
|----------------|-------|---------|
| ≥ 70 | `MAX_CONVICTION_BULL` | Strongest bullish signal |
| 50 to 69 | `STRONG_BULL` | Strong bullish trend |
| 30 to 49 | `MILD_BULL` | Moderate bullish |
| 10 to 29 | `WEAK_BULL` | Slight bullish lean |
| −9 to 9 | `NEUTRAL` | No directional bias |
| −29 to −10 | `WEAK_BEAR` | Slight bearish lean |
| −49 to −30 | `MILD_BEAR` | Moderate bearish |
| −69 to −50 | `STRONG_BEAR` | Strong bearish trend |
| ≤ −70 | `MAX_CONVICTION_BEAR` | Strongest bearish signal |

**Additional outputs:** `agreement` (0–1 fraction of methods agreeing), `is_nr7` (Narrow Range 7 flag), plus **Cap Finder** momentum extreme detection (RSI + MA distance + volume spikes → `oversoldExtreme` / `overboughtExtreme`).

**22 total output columns.**

```python
from shared.indicators.trend_strength_nr7 import TrendStrengthNR7, TrendStrengthParams
indicator = TrendStrengthNR7(TrendStrengthParams())
signals = indicator.calculate(price_data)
max_bull = signals[signals['trend_state'] == 'MAX_CONVICTION_BULL']
```

### 2. TTM Squeeze Advanced
**File:** `shared/indicators/ttm_squeeze_adv.py` (133 lines)

Identifies volatility compression (Bollinger Bands inside Keltner Channels) with momentum direction.

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `length` | 20 | Lookback period |
| `nK` | 1.5 | KC multiplier |
| `nBB_tight` | 2.0 | Tight BB multiplier |
| `nBB_soft` | 1.7 | Soft BB multiplier |

**Outputs:** `squeeze_tight_on`, `squeeze_soft_on`, `squeeze_any_on`, `squeeze_release`, `momentum`, `momentum_sign`, `momentum_accel` (17 columns total).

```python
from shared.indicators.ttm_squeeze_adv import compute_ttm_squeeze_adv, TTMSqueezeParams
result = compute_ttm_squeeze_adv(price_data, TTMSqueezeParams())
releases = result[result['squeeze_release'] == True]
```

---

## Visualization — ChartBuilder

All charts route through `shared/chart_builder.py` (412 lines). Plotly-based, dark theme, saved as interactive `.html` files.

| Method | Description |
|--------|-------------|
| `price_chart(df, ticker, events)` | Candlestick + volume subplot with optional event markers |
| `forward_returns(stats, study_name)` | Grouped bar chart comparing forward returns across groups |
| `winrate_heatmap(df, study_name)` | Win rate heatmap (RdYlGn scale, zmid=0.5) |
| `gap_distribution(events_df, study_name)` | Gap size histogram + scatter vs day return |
| `equity_curve(returns, study_name, benchmark)` | Cumulative returns with optional benchmark overlay |
| `pm_overlay(price_df, odds_df, ticker, market_name)` | Dual-axis: stock price + prediction market probability |

```python
from shared.chart_builder import ChartBuilder
df = ChartBuilder.normalize_columns(df)  # DataRouter returns capitalized; ChartBuilder needs lowercase
fig = ChartBuilder.price_chart(df, 'NVDA')
```

---

## Completed Studies & Findings

### 16 Active Studies

| # | Study | Ticker(s) | Type | Key Finding |
|---|-------|-----------|------|-------------|
| 1 | `alab_gapdown_study` | ALAB | Gap Study | 3 events of ≥10% gap-down since Mar 2024. Day-of mean return +2.80%, strong bounce-back tendency at +3–5d. |
| 2 | `baba_compression_breakdown` | BABA | Compression | **Counter-intuitive:** Compression breakdowns are BULLISH (+5% median at 10d). Shakeout/mean-reversion effect. 16 events. |
| 3 | `baba_nbs` | BABA | Event Study | 20 NBS conferences (Apr 2023–Nov 2024). Consistent **bearish drift**: −1.61% at Day+2, −2.56% at Day+3. |
| 4 | `baba_nbs_nov_data` | BABA | Event Study | December NBS Nov data releases (2020–2024, 5 events). Event-day range nearly doubles (~4% vs 2.7%). Mean intraday return −1.74%. |
| 5 | `beat_and_sell_probability` | 25 mega-caps | Earnings | 588 gap-up events. Composite score didn't predict fades, but **RS Weakness** (+14.8 ppt fade rate, n=190) and **Range Compression** individually show signal. |
| 6 | `cannabis_rallies` | TLRY, CGC, MSOS | Comparison | MSOS 2021 had superior risk-adjusted return (+83%, −32% DD) vs TLRY 2018 mania (+235%, −69% DD). |
| 7 | `gap_tsl_rs_confluence` | Multi | Confluence | Gap-down + rising TSL3 slope + crushed RS(Z) ≤ −1.0 → modular pipeline for intraday reversal detection. |
| 8 | `iwm_1pct_followup` | IWM | Returns | Next-day performance after ≥1% moves (up and down) since 2010. |
| 9 | `iwm_fed_cuts_pause` | IWM | Macro Event | IWM around Fed rate cut → pause cycles (Sep 2024, Nov 2022). |
| 10 | `mu_intraday_earnings` | MU + 17 semis | Intraday | Whether MU is the best intraday volatility vehicle on its own earnings days, or correlated semis (NVDA, AMD, AVGO) show earlier/larger ATR expansion. 5-min bars, 1,215 lines. |
| 11 | `mu_intraday_earnings_liquid_v2` | MU, NVDA, AMD, SMCI | Intraday | V2 restricted to liquid substitutes only. |
| 12 | `nvda_options_wall_study` | NVDA | Options/Earnings | Tests whether overnight move clearing nearest major call strike predicts gap continuation vs fade. 12 earnings dates. |
| 13 | `tlry_rescheduling_events` | TLRY | Event Study | Edge around U.S. federal cannabis rescheduling headlines — gap behavior, extension, next-day reversion. |
| 14 | `trend_chop_gap_quality` | Multi | Classification | 4-part: trend/chop day classification, gap close strength by bin, first-hour failure rubric, forward horizon returns. YAML config + run archive. |
| 15 | `tsla_indicator_honesty` | TSLA | Indicator Test | **Key finding:** Oversold signals → −7.59% avg 5d (NOT buying opportunities). Overbought → +3.21% avg 5d (momentum continuation). 252 trading days. |
| 16 | `indicator_honesty_tsla` | TSLA | Indicator Test | Early/incomplete version of the above. |

### Confirmed Edge (from AGENT_CONTEXT.md)

**RS Weakness Predicts Earnings Gap Fade** (Feb 2026)
- Signal: Stock RS vs SPY ≤ 0 (trailing 20d) at time of earnings gap-up
- Result: 54.2% day-of fade rate vs 39.4% baseline (+14.8 ppt, n=190)
- Confidence: MODERATE — needs V2 with real Tiingo earnings dates

---

## Study Types the Lab Supports

### 1. Indicator Honesty Tests
*"Does my indicator actually produce alpha, or just look good visually?"*
- Identify signal days (e.g., `consensusClamped ≥ 70`)
- Calculate forward returns at +1d, +3d, +5d, +10d
- Compare to random days and moderate-conviction days
- Measure win rates, max drawdown, MFE/MAE, ATR expansion
- Output: event table, aggregated stats, behavioral separation analysis

### 2. Gap Studies
*"How do stocks behave after specific gap conditions?"*
- Gap identification (up/down, size bins)
- Day-of return (close vs open)
- Multi-day forward returns (1–5d, 10–20d)
- Win rates, expectancy, timing distributions

### 3. Event Studies
*"How does price react to a specific catalyst?"*
- Collect event dates (earnings, conferences, economic releases, rescheduling, NBS)
- Measure pre/post-event returns
- Intraday session analysis (premarket 3:00–8:29 CT, RTH 8:30–15:00 CT)
- Actionable trading rules with sample sizes

### 4. Prediction Market Event Studies
*"When prediction market odds shift, how do stocks react?"*
- Detect odds threshold events (e.g., +10% probability shift)
- Align with Alpaca stock price data
- Calculate forward returns from odds events
- Statistical significance and win rates

### 5. Earnings & Fundamental Studies
*"Do beat-and-raise stocks with weak RS fade?"*
- Post-earnings gap analysis by margin trajectory, guidance type, RS position
- Beat-and-sell pattern detection
- Revenue growth rate vs fade probability
- Operating leverage signals

### 6. Macro & Regime Studies
*"Does this strategy work better when VIX is low?"*
- VIX regime filters (FRED VIXCLS or yfinance ^VIX)
- Fed rate environment overlays
- OPEX week behavior
- Treasury yield curve context

### 7. Intraday Studies
*"Is MU actually the best vehicle for semi earnings volatility?"*
- 1-min / 5-min bar analysis via Alpaca
- ATR-normalized expansion measurement
- Session window analysis (premarket, opening range, RTH)
- Multi-ticker comparison

### 8. Compression & Squeeze Studies
*"Do NR7 days predict expansion?"*
- Narrow Range 7 identification
- TTM Squeeze fire/release detection
- Forward volatility and direction measurement
- Breakout vs breakdown classification

---

## Creating New Studies

### From Template (Price Action)
```bash
# Copy template
cp -r studies/_TEMPLATE/ studies/my_new_study/
# Edit and implement
```

### From Template (Prediction Market)
```bash
cp -r studies/_TEMPLATE_prediction_market/ studies/my_pm_study/
# Pre-configured with pm_data_loader imports
```

### Study Output Structure
```
studies/my_study/
├── run_my_study.py          # Main entry point
├── README.md                # Study documentation
├── config.yaml              # Parameters (optional)
└── outputs/
    ├── events.csv           # One row per signal/event
    ├── summary_stats.txt    # Win rates, returns, sample size
    ├── metadata.txt         # Study ID, date range, source
    └── charts/              # Interactive HTML charts
```

### Every Script Starts With
```python
import sys, os
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')
```

---

## Data Routing — Non-Negotiable Rules

The `DataRouter` (337 lines) enforces all routing. These rules are law:

| Study Type | Required Source | Override Allowed? |
|------------|----------------|-------------------|
| `volatility` | Alpaca | Only with explicit `source='yfinance'` + logged warning |
| `returns` | Alpaca | Only with explicit override + warning |
| `indicator` | Alpaca | Only with explicit override + warning |
| `honesty_test` | Alpaca | Only with explicit override + warning |
| `ttp` | Alpaca | Only with explicit override + warning |
| Indices (`^VIX`, `^SPX`) | yfinance | N/A — not available on Alpaca |
| Macro series | FRED | yfinance index proxy as fallback |

**Fallback chain:** Alpaca → yfinance → Tiingo (automatic if primary fails).

---

## Timezone Convention

| Session | Central Time (CT) | Eastern Time (ET) |
|---------|-------------------|-------------------|
| Premarket | 3:00 AM – 8:29 AM | 4:00 AM – 9:29 AM |
| Regular Trading Hours (RTH) | 8:30 AM – 3:00 PM | 9:30 AM – 4:00 PM |
| Full session (default) | 3:00 AM – 3:00 PM | 4:00 AM – 4:00 PM |

**All analysis timestamps are Central Time.** Premarket is included by default — never silently excluded.

---

## Tools & Engines

### Levels Engine (`tools/levels_engine/`)
Options-based price levels analysis:
- `run_levels.py` — Generate levels for a ticker
- `query_levels.py` — Query existing levels data
- `route_query.py` — Route NL queries to levels
- Outputs stored in `data/levels/`

### Study Orchestration (`tools/studies/`)
- `nl_parse.py` — Parse natural language queries into study parameters
- `route_study.py` — Map parsed intent to a canonical study
- `run_id.py` — Generate versioned run IDs for output deduplication
- `ask.py` — Interactive study launcher
- `studies_registry.yaml` — Registry of all defined studies

### Prediction Market Analysis (`prediction-market-analysis/`)
Upstream repository (Jon Becker) providing the raw data pipeline:
- Polymarket and Kalshi trade/market indexers
- ~36GB compressed dataset
- Analysis framework for odds data
- Feeds into `tools/prediction_markets/pm_data_loader.py` for lab integration

---

## Environment Setup

### Requirements
- Python 3.13.5 with venv
- Core: `pandas`, `numpy`, `alpaca-py`, `yfinance`, `requests`, `fredapi`
- Visualization: `plotly`, `matplotlib`, `seaborn`
- Prediction markets: `duckdb`, `pyarrow`
- Install: `pip install -r requirements.txt`

### API Keys
Stored in `shared/config/keys/{env}.env` and loaded via `env_loader.py`:
```python
from shared.config.env_loader import load_keys
load_keys('paper')  # or 'live'
```

Required keys:
- `ALPACA_API_KEY` + `ALPACA_API_SECRET` (paper and/or live)
- `FRED_API_KEY`
- `TIINGO_API_KEY`
- `FMP_API_KEY`
- Optional: Alpha Vantage, Schwab, CoinGecko, SEC EDGAR

### Running Studies
```bash
cd C:\QuantLab\Data_Lab
.venv\Scripts\activate
cd studies/alab_gapdown_study
python run_alab_gapdown_study.py
# Outputs → studies/alab_gapdown_study/outputs/
```

---

## Agent Behavior Rules

### ALWAYS
- Route all equity price data through `DataRouter.get_price_data()`
- Route all charts through `ChartBuilder`, output `.html`
- Start every script with the 4 `sys.path` inserts
- State sample size (n=?) and confidence level on every finding
- Save all outputs — never return results that aren't persisted
- Include premarket data by default
- Read `AGENT_CONTEXT.md` at session start
- Answer first, explain second

### NEVER
- Use yfinance for individual US equity price studies
- Modify anything in `shared/indicators/`
- Delete or overwrite existing study outputs
- Tune indicator parameters without explicit permission
- Switch data sources away from Alpaca without explicit override + warning
- Invent a study that doesn't exist in `STUDY_PROMPT_LIBRARY.md`
- Give long preambles before answering
- Assume every question is about earnings — the lab studies everything

---

## Governance Documents

| Document | Purpose | Lines |
|----------|---------|-------|
| `docs/API_MAP.md` | Exhaustive data source routing rules | 629 |
| `docs/INDICATOR_SPECS.md` | Mathematical definitions of all indicators | 347 |
| `docs/STUDY_PROMPT_LIBRARY.md` | Canonical study blueprints (trigger, metrics, output) | Active |
| `docs/STUDY_EXECUTION_PROTOCOL.md` | Mandatory agent execution procedure | 549 |
| `docs/STUDY_INDEX.md` | Master tracker of all studies + results | Active |
| `docs/HOW_TO_USE_THE_LAB.md` | User guide for NL queries | 169 |
| `docs/DATA_HYGIENE.md` | Data quality and cleaning rules | Active |
| `docs/DATA_ROUTING_GOVERNANCE.md` | Source enforcement policy | Active |
| `docs/ENFORCEMENT_NOTES.md` | Violation tracking | Active |
| `prompts/AGENT_CONTEXT.md` | User profile, trading style, expectations, session checklist | 255 |

---

## Quick Reference Card

### Get Price Data
```python
from shared.data_router import DataRouter
df = DataRouter.get_price_data('TICKER', 'YYYY-MM-DD', study_type='indicator')
```

### Apply Indicator
```python
from shared.indicators.trend_strength_nr7 import TrendStrengthNR7, TrendStrengthParams
signals = TrendStrengthNR7(TrendStrengthParams()).calculate(df)
```

### Build Chart
```python
from shared.chart_builder import ChartBuilder
fig = ChartBuilder.price_chart(ChartBuilder.normalize_columns(df), 'TICKER')
```

### Search Prediction Markets
```python
from tools.prediction_markets.pm_data_loader import search_markets, run_event_study
markets = search_markets("fed rate", source="kalshi")
```

### Get Watchlist
```python
from shared.watchlist import get_watchlist
tickers = get_watchlist()  # 240 tickers
```

### Get Macro Data
```python
from shared.config.api_clients import FREDClient
vix = FREDClient().get_series('VIXCLS')
```
