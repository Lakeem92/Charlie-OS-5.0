---
applyTo: "**"
---

# DATA VISUALIZATION & QUANTITATIVE ANALYSIS INSTRUCTIONS
# Governs all chart, visual, and multi-period data requests in QuantLab

# ─────────────────────────────────────────────────────────────────
# TRIGGER DETECTION — ROUTE TO THIS PIPELINE WHEN YOU SEE:
# ─────────────────────────────────────────────────────────────────

Activate this pipeline automatically when the input contains any of:

**Visualization keywords:**
"chart", "plot", "graph", "show me", "visualize", "display", "draw"

**Trajectory / time-series keywords:**
"trajectory", "over X quarters", "over X months", "over X years", "trend",
"how did X move", "what did X do", "history of", "historical", "progression"

**Comparative analysis keywords:**
"compare", "vs", "versus", "side by side", "head to head", "which one",
"top gainers", "top losers", "best performers", "worst performers", "ranked by"

**Fundamental data keywords:**
"gross margin", "operating margin", "revenue growth", "EPS trajectory",
"margins", "earnings history", "guidance history", "FCF", "EBITDA trend"

**Distribution / statistical keywords:**
"distribution", "histogram", "scatter", "correlation", "regression",
"win rate", "frequency", "heatmap", "by sector", "breakdown"

**Study / research keywords:**
"test if", "does X work when", "what happens when", "study", "backtest",
"is there an edge", "what's the edge", "analyze the pattern"

# ─────────────────────────────────────────────────────────────────
# PIPELINE RULES — NON-NEGOTIABLE
# ─────────────────────────────────────────────────────────────────

## RULE 1: TEXT SUMMARY FIRST, CHART SECOND
Always return the key numbers in plain text before building the chart.
Format: key metric, n= sample size, confidence level, then chart.
Never return a chart with no accompanying interpretation.

## RULE 2: CHARTBUILDER IS SACRED
ALL visualizations route through `shared/chart_builder.py`. Never use matplotlib directly.
Always normalize columns first: `df = ChartBuilder.normalize_columns(df)`
Always output `.html` — never `.png`, `.jpg`, or inline matplotlib.
Save quick queries to `scratch/` — formal studies to `studies/{name}/outputs/charts/`

## RULE 3: DATA SOURCE HIERARCHY (MATCH API_MAP.MD)
| Data Need | Primary Source | Fallback |
|---|---|---|
| US equity price (OHLCV) | Alpaca via `DataRouter.get_price_data()` | Tiingo |
| Index data (VIX, SPX, MOVE) | yfinance (`^VIX`, `^SPX`) | FRED |
| Fundamentals (margins, revenue, EPS, guidance) | FMP via `api_clients.FMPClient` | Alpha Vantage |
| Macro series | FRED via `api_clients.FREDClient` | yfinance (proxies) |
| Prediction market odds | `tools/prediction_markets/pm_data_loader.py` | N/A |
| News / events | Tiingo | MCP web search |

NEVER use yfinance for individual equity price studies — that is Alpaca's exclusive domain.

## RULE 4: SAMPLE SIZE ALWAYS STATED
n ≥ 20 → Reliable. State findings with confidence.
n < 20 → Flag: ⚠️ LOW CONFIDENCE (n=[X])
n < 10 → Flag: ❌ INSUFFICIENT — do not trade this finding.

## RULE 5: EVERY SCRIPT STARTS WITH THE 4 SYS.PATH INSERTS
```python
import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')
```
Non-negotiable. Every time. Missing this causes ModuleNotFoundError.

# ─────────────────────────────────────────────────────────────────
# CHART TYPE ROUTING — WHAT TO BUILD FOR WHAT QUESTION
# ─────────────────────────────────────────────────────────────────

| Question Type | Chart Type | ChartBuilder Method |
|---|---|---|
| Price over time | Candlestick with volume | `ChartBuilder.price_chart()` |
| Forward returns by group | Grouped bar (multi-day) | `ChartBuilder.forward_returns()` |
| Win rate by condition | Color matrix | `ChartBuilder.winrate_heatmap()` |
| Gap magnitude vs outcome | Scatter + histogram | `ChartBuilder.gap_distribution()` |
| Strategy cumulative returns | Equity curve with benchmark | `ChartBuilder.equity_curve()` |
| Odds vs price overlay | Dual y-axis | `ChartBuilder.pm_overlay()` |
| Margin trajectory multi-quarter | Multi-line time series | Build via plotly in script, save .html |
| Sector/group comparison | Grouped bars or faceted lines | Build via plotly in script, save .html |
| Distribution of returns | Histogram + KDE | Build via plotly in script, save .html |
| Correlation matrix | Heatmap | Build via plotly in script, save .html |

# ─────────────────────────────────────────────────────────────────
# FUNDAMENTALS QUERIES — HOW TO HANDLE THEM
# ─────────────────────────────────────────────────────────────────

When the question requires fundamental data (margins, revenue, EPS, guidance):

1. Use FMP (Financial Modeling Prep) as primary:
   ```python
   from shared.config.api_clients import FMPClient
   fmp = FMPClient()
   ```

2. Pull quarterly income statement / balance sheet data from FMP API.
   Endpoints: `/income-statement/`, `/cash-flow-statement/`, `/balance-sheet-statement/`
   Use `period=quarter` for quarterly trajectory questions.

3. Fallback to Alpha Vantage if FMP fails:
   ```python
   from shared.config.api_clients import AlphaVantageClient
   ```

4. For multi-ticker fundamental comparisons (e.g., "top gainers, gross margin trajectory"):
   - Step 1: Pull YTD price returns via Alpaca/DataRouter to identify top gainers
   - Step 2: Pull quarterly fundamentals for each name via FMP
   - Step 3: Align to the same quarter timeline
   - Step 4: Build multi-line or grouped bar chart showing trajectory
   - Step 5: Annotate with earnings dates where available

## EXAMPLE: "For the top gaining stocks this year, what was the trajectory of their gross margins over the past 4 quarters — anything interesting?"

```
EXECUTION PLAN:
1. DataRouter.get_price_data() on watchlist (or S&P 500 proxy) — pull YTD returns
2. Rank by YTD return — take top N (default 10)
3. FMPClient.get_income_statement(ticker, period='quarter', limit=5) for each
4. Extract gross_margin across 4 most recent quarters
5. Build multi-line chart: x=quarter, y=gross_margin%, one line per ticker
6. Flag tickers where gross margin is ACCELERATING vs DECELERATING vs STABLE
7. Text summary: rank order by margin momentum, call out any inflection stories
8. Save chart to scratch/viz_[date]_top_gainers_margins.html
```

# ─────────────────────────────────────────────────────────────────
# MULTI-PANEL CHART STANDARDS
# ─────────────────────────────────────────────────────────────────

For "data nerd" multi-layered questions, build multi-panel layouts:

PANEL STRUCTURE:
- Panel 1 (top, 60% height): Primary metric — price, returns, or main KPI
- Panel 2 (middle, 25% height): Secondary metric — volume, margin, indicator
- Panel 3 (bottom, 15% height): Signal or annotation layer

Always use:
- `plotly.subplots.make_subplots()` with `shared_xaxes=True`
- Consistent x-axis (date or quarter) across all panels
- Color scheme: green (#26a69a) = bullish/positive, red (#ef5350) = bearish/negative, blue (#42a5f5) = neutral/volume
- Annotation markers for key events (earnings dates, signal fires, regime changes)

# ─────────────────────────────────────────────────────────────────
# SECTOR COMPARISON RULES
# ─────────────────────────────────────────────────────────────────

When comparing across sectors:
- Normalize metrics where units differ (e.g., margin % is already normalized; raw $ revenue is not)
- Use sector ETF proxies for relative comparison when individual stock data is sparse
- Flag when n < 5 per sector: ⚠️ INSUFFICIENT SECTOR SAMPLE
- Always include sample size per group in chart annotations

# ─────────────────────────────────────────────────────────────────
# INDICATOR VISUALIZATION RULES
# ─────────────────────────────────────────────────────────────────

When plotting indicators (TrendStrength, TTM Squeeze):

NEVER modify indicator logic — import from `shared/indicators/` as-is.

Standard indicator chart layout:
- Panel 1: Price candlestick + volume
- Panel 2: TrendStrength consensusClamped line (-100 to +100) with zero line
- Horizontal bands: ≥70 (MAX_CONVICTION_BULL), ≤-70 (MAX_CONVICTION_BEAR)
- Panel 3: TTM Squeeze momentum histogram (green/red bars) + squeeze dots (red=compressed, green=firing)

NR7 overlay: mark NR7 days with vertical grey shading on price panel.

# ─────────────────────────────────────────────────────────────────
# PREDICTION MARKET OVERLAYS
# ─────────────────────────────────────────────────────────────────

When the question involves prediction market odds + price:
```python
from tools.prediction_markets.pm_data_loader import search_markets, run_event_study
```

Use `ChartBuilder.pm_overlay()` for dual y-axis (price left, odds % right).
Always note: "Prediction market data represents crowd probability, not options pricing."

# ─────────────────────────────────────────────────────────────────
# OUTPUT STANDARDS
# ─────────────────────────────────────────────────────────────────

Every data/visualization response follows this structure:

```
📊 [QUERY INTERPRETATION — 1 sentence: what you understood the question to be]

KEY FINDINGS:
• [Most important number or pattern — lead with it]
• [Second finding]
• [Third finding — if relevant]
Sample: n=[X] | Confidence: [HIGH / MODERATE / LOW] | Period: [date range]

⚠️ [Caveats if any — sample size, data gaps, proxy limitations]

[Chart: saved to scratch/viz_YYYYMMDD_description.html]
[One-liner on how to interpret the chart]
```

Never pad with methodology explanations unless Lakeem asks.
Answer first. Explain only what's non-obvious.
