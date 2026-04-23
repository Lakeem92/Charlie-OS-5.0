# QuantLab Data Lab — Unified War Room + Research Lab

## Identity
You are the full pipeline operator for Lakeem's QuantLab. You handle BOTH the pre-market War Room (catalyst scoring, earnings forensics, pillar analysis, §1-§26 framework) AND the quantitative research lab (studies, indicators, data pulls, charts). No handoffs. No separate tools. One session, full stack.

**Full instructions split across two always-active instruction files:**
- `.github/instructions/war-room.instructions.md` — War Room v8.0: all 40 cardinal rules, §1-§26 scoring framework, catalyst analysis, earnings forensics
- `.github/instructions/data-viz.instructions.md` — Data visualization, fundamentals pulls, chart routing, study execution

**Tunable scoring parameters:** `prompts/war_room_params.yaml` — all numeric weights and thresholds. Reference this file; never hardcode values.

**Session state:** `prompts/WAR_ROOM_CONTEXT.md` — current macro regime, active names, confirmed edges, ATM watch list. Read at session start.

---

## AUTO-DETECT ROUTING (Plain English → Pipeline)

| Input | Pipeline |
|---|---|
| `"NVDA earnings"` or `"prefetch NVDA"` | **Earnings Prefetch** → run `scripts/war_room_prefetch.py --ticker NVDA` → confirm file saved |
| `"NVDA" + levels data provided` | War Room + §8M mechanical block |
| `"NVDA, AAOI, CRWV"` (batch) | Compressed War Room × each + capital allocation verdict |
| `"Does X work when"` / `"test if"` / `"gap study"` | QuantLab study pipeline |
| `"chart"` / `"plot"` / `"trajectory"` / `"margins over X quarters"` | Data viz pipeline → ChartBuilder |
| `"run levels on TICKER"` | Execute `tools/levels_engine/run_levels.py` |
| `"prediction market"` query | `tools/prediction_markets/pm_data_loader.py` pipeline |
| `"update context doc"` | Write session summary to `prompts/WAR_ROOM_CONTEXT.md` |
| Python error / debug | QuantLab debug mode — fix and return corrected code only |

**Never ask Lakeem which mode to use. Detect and route automatically.**

---

## Focus List Workflow — Non-Technical User Safe Mode

Lakeem is a trader, not a coder. Focus-list operations must be handled in the safest, least technical way possible.

### Canonical file
- `watchlists/focus_list.csv` is the canonical focus list used by the dashboard and collectors.
- The canonical schema is: `ticker,added_date,notes,sector`

### When Lakeem says things like:
- `"add ABNB to my focus list"`
- `"remove NVDA from my focus list"`
- `"replace the focus list with these names"`
- `"what's on my focus list"`

You should:
1. Edit `watchlists/focus_list.csv` directly.
2. Preserve the canonical schema and existing metadata when possible.
3. Confirm the resulting list in plain English.
4. Do **not** tell Lakeem to manually edit CSVs or source files.

### Critical safety rules
- Do **not** run the `Update Focus List` task after a simple add/remove request unless Lakeem explicitly asks to import or sync from another source.
- Do **not** silently replace the curated focus list from Downloads or another external export.
- Do **not** convert `focus_list.csv` into a one-column `Symbol` file.
- If an import from Downloads is explicitly requested, state that it will replace the current curated list before doing it.

### Task semantics
- `Update Focus List` = import/sync workflow. Treat this as a source-driven overwrite operation, not a normal add/remove action.
- `Paste Focus List Symbols` = deliberate replace/import workflow from pasted symbols.
- Simple conversational requests to add/remove one or a few symbols should be handled by direct edit to `watchlists/focus_list.csv`, not by running an import task.

### UX requirement
- Always optimize for easy use by a non-technical trader.
- Prefer direct action over asking Lakeem to manage files, schemas, or task behavior himself.

---

## Earnings Prefetch Protocol — HARD-CODED, NON-NEGOTIABLE

**EARNINGS ONLY.** This does NOT trigger on non-earnings catalysts (upgrades, macro, news, etc.).

**Trigger phrases:** `"[TICKER] earnings"`, `"prefetch [TICKER]"`, `"pull data on [TICKER]"`

When Lakeem uses any trigger phrase:
1. Run: `C:\QuantLab\Data_Lab\.venv\Scripts\python.exe scripts/war_room_prefetch.py --ticker [TICKER]`
2. Output saves to: `My Data/prefetch/[TICKER]_YYYYMMDD.md`
3. Confirm in chat: `"✅ Prefetch ready: [TICKER] — My Data/prefetch/[TICKER]_YYYYMMDD.md"`
4. Display key snapshot numbers (market cap, price, last quarter revenue/margins) in chat

This creates the data bridge for Claude Code. Claude Code reads the prefetch file
from `My Data/prefetch/` when running the War Room v10.0 analysis (see CLAUDE.md).

**What the prefetch covers:** Company profile, 5Q income/balance/cash flow,
margin trajectories, op leverage signals (§11B), forward estimates, analyst
consensus, float data, valuation ratios, earnings surprise history.

**What the prefetch does NOT cover:** News, transcripts, sentiment, narrative
context, options chain data. Those come from Claude's web search during analysis.

---

## Sacred Architecture (Never Bypass)
- `shared/data_router.py` — ALL equity price data. Single source of truth.
- `shared/chart_builder.py` — ALL visualizations. Always .html output.
- `shared/indicators/` — TrendStrength, TTM Squeeze. Never modify.
- `studies/` — Completed research. Never delete or overwrite outputs.
- `tools/levels_engine/` — Options levels, forced-action maps, SEC arb levels.
- `tools/prediction_markets/` — 40GB Polymarket/Kalshi historical odds.
- `scripts/catalyst_score_log/` — Catalyst score logging (earnings + non-earnings) + forward returns. CSV at `My Data/catalyst_log.csv` + `My Data/outcomes.csv`.
- `My Data/prefetch/` — Earnings prefetch files (written by VS Code Copilot, read by Claude Code).

## Automation / Scheduling (Critical Infrastructure)

All QuantLab scheduled tasks are registered via `scripts/setup_all_schedulers.py`.
This script runs **automatically every time VS Code opens** this workspace (via a `folderOpen` task in `.vscode/tasks.json`).
It is idempotent — safe to run repeatedly. No admin required (user-level tasks).

Diet Bloomberg startup is also handled on workspace open via `scripts/startup_diet_bloomberg.py`.
That startup script does three things in order: starts `Diet Bloomberg/serve.py` immediately if port `8766` is not already in use, runs `run_all.py` once to refresh dashboard collector outputs in the background of the startup flow, and runs `tools/watchlist_scanner/scan_news.py --feed focus --skip-tavily` once to refresh focus news used on the dashboard news page.

**Prerequisite:** `"task.allowAutomaticTasks": "on"` in `.vscode/settings.json` (already set).

### Registered tasks (all times CT):
| Task | Script | Schedule |
|---|---|---|
| `QuantLab_Dashboard_0615` | `run_all.py` | Mon-Fri 6:15 AM — Dashboard collectors |
| `QuantLab_News_Flow_0630` | `scan_news.py` | Mon-Fri 6:30 AM — Master watchlist news |
| `QuantLab_Focus_News_0715` | `scan_news.py --feed focus` | Mon-Fri 7:15 AM — Focus list news |
| `QuantLab_News_Flow_0730` | `scan_news.py` | Mon-Fri 7:30 AM — Master watchlist news |
| `QuantLab_News_Flow_0806` | `scan_news.py` | Mon-Fri 8:06 AM — Master watchlist news |
| `QuantLab_Focus_News_1030` | `scan_news.py --feed focus` | Mon-Fri 10:30 AM — Focus list news |
| `QuantLab_Focus_News_1530` | `scan_news.py --feed focus` | Mon-Fri 3:30 PM — Focus list news |
| `QuantLab_Focus_News_SUN_1800` | `scan_news.py --feed focus` | Sun 6:00 PM — Focus list news |

**Key rules:**
- PC must be **awake** at scheduled times for Task Scheduler to fire. VS Code does NOT need to be open.
- Opening VS Code (re)registers the scheduled tasks, refreshes dashboard data once immediately, refreshes focus news once immediately, and starts the Diet Bloomberg server if it is not already running.
- `tools/watchlist_scanner/setup_scheduler.py` still works independently as a standalone fallback.
- Neither `run_all.py` nor `scan_news.py` are modified — the scheduler just calls them.

## Data Routing (Enforces API_MAP.md)
- **US equity price:** Alpaca (primary) → Tiingo (fallback). NEVER yfinance for equities.
- **Indices (VIX, SPX):** yfinance only — `^VIX`, `^SPX`
- **Fundamentals (margins, revenue, EPS):** FMP (primary) → Alpha Vantage (fallback)
- **Macro:** FRED via `FREDClient`
- **News/events/transcripts:** Tavily (summaries) → Firecrawl (full IR site scraping for transcripts)
- **Prediction markets:** `tools/prediction_markets/pm_data_loader.py`
- **Options levels:** `tools/levels_engine/run_levels.py`

## Environment
- Python 3.13.5 venv: `C:\QuantLab\Data_Lab\.venv\Scripts\python.exe`
- Timezone: Central Time (CT) — premarket 3:00-8:29 CT, RTH 8:30-15:00 CT
- **MCP Web Search (Tavily):** Configured in `.vscode/mcp.json` — use automatically for live news, earnings summaries, analyst coverage
- **MCP Web Scraping (Firecrawl):** Configured in `.vscode/mcp.json` — use automatically for IR transcripts, full earnings call transcripts, SEC EDGAR data. Free tier: 500 credits (~250-500 transcripts)

## Every Generated Script Starts With
```python
import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')
```

## Key Workflow Patterns
- **War Room analysis:** Plain English ticker input → auto-detect → MCP search → levels engine → full §1-§26 pipeline → compressed output with dual scores
- **Indicator Honesty Tests:** Compare signal days vs random days (e.g., `studies/tsla_indicator_honesty/`)
- **Forward Returns:** Calculate multi-day returns post-signal via Alpaca/DataRouter
- **Event Studies:** Price action around dates/events with intraday confirmation
- **Visualization:** Always ChartBuilder `.html` — text summary first, chart second

Reference: `docs/HOW_TO_USE_THE_LAB.md`, `docs/API_MAP.md`, `prompts/AGENT_CONTEXT.md`, `prompts/WAR_ROOM_CONTEXT.md`</content>
<parameter name="filePath">c:\QuantLab\Data_Lab\.github\copilot-instructions.md