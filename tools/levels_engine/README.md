# QuantLab Data Lab

A **momentum trader's research lab** — ask natural-language questions about
market patterns and get back deterministic, data-backed answers. The system
is agent-driven: you describe what you want to know, and the lab maps your
query to the right study, fetches real data, runs the analysis, and saves
structured results. No opinions. No guessing. Everything is sourced and
reproducible.

---

## What's In the Lab

### 1. Levels Engine (Forced-Action Map) — `tools/levels_engine/`

The flagship tool. Tells you where **real options positioning** creates forced
mechanical action — call walls, put walls, strike-to-strike paths, and
verified SEC contractual levels — for any US equity. Produces a
**Forced-Action Momentum Map** across two time lenses (front week + closest
monthly OPEX). No chart levels. No AI guessing. No trade advice.

| Capability | Details |
|:-----------|:--------|
| **Options key levels from real strikes** | Uses open interest and volume from Alpaca — only strikes that actually exist on the chain. |
| **Two lenses** | **Front Week** (nearest expiry ≤ 7 days out) and **Closest Monthly** (next 3rd-Friday OPEX). Each lens is kept separate. |
| **Strike tags** | Call Wall · Put Wall · Step-Change · Pin/Magnet · Near-Spot Bracket · High Volume — each with mechanical commentary (who is forced, breach, rejection). |
| **Strike-to-strike paths** | Upside and downside chains from spot through the next 5 options concentrations. |
| **Verified SEC arb / contractual levels** | Conversion prices, exercise prices, offering prices, etc. from SEC EDGAR filings with source URLs. |
| **Desk snippet (`--summary`)** | Prints only walls + paths + verified arb — paste-ready for a desk chat. |
| **Natural-language router** | Hand it a plain-English question; it detects intent and tickers automatically. |
| **Full report** | Complete markdown forced-action map + structured JSON for every run. |

### 2. Research Studies — `studies/`

Each subfolder is a self-contained, reproducible study with its own data,
script, and outputs. Studies are run by the agent when you ask a research
question, or you can run them directly.

| Study | What it answers |
|:------|:----------------|
| **alab_gapdown_study** | Does ALAB mean-revert after ≥10% pre-market gap-downs? (Yes — +2–6% avg 1–5 day bounce, 67% win rate.) |
| **baba_compression_breakdown** | Are BABA breakdowns below tight 20-day compression ranges bearish? (No — they're bullish shakeouts, +5.5% at 10 days.) |
| **baba_nbs** | How does BABA react to China NBS press conferences? (Consistent bearish drift: −1.6% at Day+2, −2.6% at Day+3.) |
| **baba_nbs_nov_data** | Do annual NBS November data releases move BABA? (Intraday vol nearly doubles, mean −1.74% OTC selloff, no edge after.) |
| **cannabis_rallies** | TLRY/CGC 2018 mania vs. MSOS 2021 — which was tradeable? (MSOS: +83%, −32% drawdown. TLRY: +235%, −69% — untradeable.) |
| **iwm_1pct_followup** | What does IWM do the day after a ≥1% move? (Next-day stats from 2010+.) |
| **iwm_fed_cuts_pause** | How does IWM behave around Fed rate-cut-then-pause events? (30 days before/after analysis.) |
| **mu_intraday_earnings** | Is MU the best intraday vol vehicle on its own earnings days, or are NVDA/AMD/AVGO better? (5-min ATR-normalized comparison.) |
| **mu_intraday_earnings_liquid_v2** | V2 restricted to liquid substitutes only (NVDA, AMD, SMCI) + MU diagnostics. |
| **tlry_rescheduling_events** | Do cannabis rescheduling headlines create a repeatable TLRY edge? (Large gaps + intraday extension → weak T+1 reversion.) |
| **tsla_indicator_honesty** | Does the Cap Finder oversold extreme signal work on TSLA? (No — it's a momentum trap, −7.6% avg 5-day return.) |

**To create a new study**, copy the `_TEMPLATE/` folder and follow the
research design template inside.

### 3. Shared Infrastructure — `shared/`

| Component | What it does |
|:----------|:-------------|
| **DataRouter** (`shared/data_router.py`) | Central data routing. `DataRouter.get_price_data()` auto-routes to Alpaca for most study types, with yfinance/Tiingo fallback. Enforces API_MAP.md rules. |
| **TrendStrengthNR7** (`shared/indicators/trend_strength_nr7.py`) | Z-scored trend metrics, consensus score (−100 to +100), NR7 compression detection, Cap Finder momentum extremes (RSI + MA distance + volume spike). |
| **TTM Squeeze Advanced** (`shared/indicators/ttm_squeeze_adv.py`) | Bollinger-inside-Keltner squeeze detection (tight + soft), momentum value, acceleration, and release signals. |
| **API Clients** (`shared/config/api_clients.py`) | Alpaca (primary), yfinance, Tiingo wrappers. |

---

## What It Will NOT Do (Guardrails)

- **No VWAP, highs/lows, moving averages, fibs, pivots, trendlines, or S/R**
  in the Levels Engine. Every level comes from a real options strike or a
  verified SEC filing.
- **No trade advice, no directional bias, no scoring.**
  Language is always conditional ("can", "may") — never predictive.
- **No unverified decimal "arb" levels.**
  SEC levels must pass a mechanical confidence threshold (≥ 0.65) with a
  source URL, or they are excluded.
- **No merging the two lenses.**
  Front week and monthly are always presented separately.
- **No parameter tuning** across studies. Each study is locked to its
  original design. If you want different parameters, create a new study.
- **No inventing studies.** The agent runs defined studies or asks you to
  define a new one — it doesn't make up analysis.

---

## Setup (Windows — 3 Steps)

### 1. Copy the env template and add your keys

```powershell
copy tools\levels_engine\.env.example tools\levels_engine\.env
notepad tools\levels_engine\.env
```

Fill in your **Alpaca live keys** (options data requires a live account):

```
ALPACA_API_KEY_LIVE=AKxxxxxxxxxxxxxxxxxx
ALPACA_API_SECRET_LIVE=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SEC_USER_AGENT=YourName yourname@email.com
```

Paper keys (`_PAPER`) are optional — fill them in only if you paper-trade.

> **Rules:** No quotes around values. No trailing spaces.
> Live keys start with `AK…`. Paper keys start with `PK…`.
> **Never** paste secrets into code or committed files — only in `.env`.

### 2. Activate your venv

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Run the doctor to verify everything works

```powershell
python tools\levels_engine\doctor.py
```

You should see three green checks: stocks ✅, options snapshots ✅, options
contracts ✅. If anything fails, see **Troubleshooting** below.

---

## Quick Commands

### Levels Engine

| Command | What it does |
|:--------|:-------------|
| `python tools\levels_engine\doctor.py` | Health check — verifies API keys and endpoints |
| `python tools\levels_engine\query_levels.py TSLA` | Full forced-action map (two lenses, all strikes, verdict) |
| `python tools\levels_engine\query_levels.py TSLA --summary` | Desk snippet — compact walls + paths + verified arb |
| `python tools\levels_engine\route_query.py "key levels for TSLA"` | Natural-language router (auto-detects intent + tickers) |
| `python tools\levels_engine\run_levels.py SPY TSLA NVDA` | Full pipeline — all expirations + SEC scan |

All commands accept **1–3 tickers**.

### Studies

```powershell
# Run any study directly
cd studies\alab_gapdown_study
python run_alab_gapdown_study.py

# Or from repo root
python studies\tsla_indicator_honesty\tsla_honesty_test.py
```

Studies save outputs (CSV, TXT, MD) to their own `outputs/` subfolder.

---

## How to Ask the Agent (Natural Language)

Just type your question. The agent figures out what to run.

### Options Levels Examples

| What you type | What happens |
|:--------------|:-------------|
| "What are the key levels on TSLA?" | Runs `--summary` for TSLA |
| "Call wall and put wall for NVDA" | Runs `--summary` for NVDA |
| "Forced-action map for SPY, include verified SEC arb levels" | Runs full query for SPY |
| "Key levels this week + closest monthly for TSLA and NVDA" | Runs `--summary` for TSLA + NVDA |
| "Where are the walls on SPY?" | Runs `--summary` for SPY |
| "OI levels on AAPL" | Runs `--summary` for AAPL |
| "Gamma levels and paths for TSLA" | Runs `--summary` for TSLA |
| "Show me the full strike table for NVDA" | Runs full query (no `--summary`) for NVDA |
| "Key levels this week" | Agent will ask you for a ticker |
| "Options levels for $TSLA $NVDA $SPY" | Runs `--summary` for all three |

**Keywords the router recognises:** key levels · call wall · put wall ·
forced-action map · options levels · walls · OI levels · gamma levels

### Research / Study Examples

| What you type | What the agent does |
|:--------------|:--------------------|
| "Does ALAB bounce after big gap-downs?" | Runs or references the alab_gapdown_study |
| "How does BABA react to NBS conferences?" | Runs or references the baba_nbs study |
| "Is the Cap Finder oversold signal reliable on TSLA?" | Runs or references tsla_indicator_honesty |
| "Best intraday vol vehicle on MU earnings?" | Runs or references mu_intraday_earnings |
| "TLRY edge on rescheduling headlines?" | Runs or references tlry_rescheduling_events |
| "What does IWM do the day after a 1% move?" | Runs or references iwm_1pct_followup |

---

## Output Files

### Levels Engine outputs → `data/levels/YYYY-MM-DD/`

| File | Contents |
|:-----|:---------|
| `QUERY_REPORT_<TICKER>.md` | Full Forced-Action Momentum Map (two lenses, strike tables, arb, paths, verdict) |
| `DESK_SNIPPET_<TICKER>.txt` | Compact walls + paths + verified arb (the `--summary` output) |
| `query_output_<TICKER>.json` | Structured JSON of everything above (machine-readable) |
| `options_levels_<TICKER>.json` | Per-strike OI data from full pipeline (`run_levels.py`) |
| `options_levels_<TICKER>.csv` | Same as above, CSV format |
| `arb_levels_<TICKER>.json` | SEC contractual levels with confidence scores |
| `LEVELS_REPORT_<TICKER>.md` | Combined pipeline report (`run_levels.py`) |
| `levels_engine.log` | Full run log for debugging |

### Study outputs → `studies/<study_name>/outputs/`

Each study saves its own CSVs, text summaries, and/or charts to its
`outputs/` folder. Check the study's README for specifics.

---

## Desk Snippet Format

When you run with `--summary`, the output looks exactly like this:

```
TSLA (as-of 2026-02-14T20:36:08Z, spot $417.75):
FRONT WEEK (EXP 2026-02-18):
  PUT WALL: $380.00 (OI 2,995) | CALL WALL: $447.50 (OI 3,759)
  UPSIDE PATH: $417.75 -> $420.00 -> $425.00 -> $430.00 -> $435.00 -> $440.00
  DOWNSIDE PATH: $417.75 -> $417.50 -> $415.00 -> $410.00 -> $400.00 -> $390.00
MONTHLY (EXP 2026-02-20):
  PUT WALL: $375.00 (OI 26,262) | CALL WALL: $450.00 (OI 19,310)
  UPSIDE PATH: $417.75 -> $420.00 -> $425.00 -> $430.00 -> $435.00 -> $440.00
  DOWNSIDE PATH: $417.75 -> $417.50 -> $410.00 -> $405.00 -> $400.00 -> $395.00
ARB/CONTRACTUAL (VERIFIED):
  - $176.00 (cap_floor) | Filing: 10-K 2026-01-29 | Source: <url>
```

This is what the agent pastes back by default — no full tables unless you ask.

---

## Definitions

### Call Wall
The strike with the **highest call open interest** in a given expiration lens.
Dealers hedging call exposure here can create upside resistance; a breach
can trigger accelerated hedging demand above.

### Put Wall
The strike with the **highest put open interest** in a given expiration lens.
Dealers hedging put exposure here can create downside support; a breach
can trigger accelerated selling pressure below.

### Step-Change
A strike where open interest jumps significantly versus its neighbours —
a discrete positioning cliff where hedging intensity changes abruptly.

### Pin / Magnet
A strike where call OI and put OI are roughly balanced (within ±25%) and
total OI is at or above the 70th percentile. Dealer gamma offsets here can
dampen movement and pull price toward this strike, especially into expiry.

### High Volume
A strike with outsized daily volume, indicating active trading / hedging
interest that day. Can act as a battle-line where speculation concentrates.

### Near-Spot Bracket
The closest strikes to current spot with meaningful OI — defines the
immediate contested zone.

### Closest Monthly
The next standard monthly options expiration (3rd Friday). If the 3rd Friday
is less than 2 days away and there is a nearer weekly, the engine may use
the next month instead (flagged as **MONTHLY PROXY** in output).

### Verified Arb / Contractual Level
A price extracted from an SEC EDGAR filing (10-K, S-1, 8-K, etc.) that
matches a known pattern: conversion price, exercise price, offering price,
redemption price, VWAP cap/floor. Each level includes the filing type, date,
and source URL. Only levels scoring ≥ 0.65 confidence are shown.

### Indicator Honesty Test
A study design that compares forward returns on signal days vs. random days
to determine if an indicator produces a statistically meaningful edge. Used
for TrendStrengthNR7 Cap Finder signals, adaptable to any indicator.

### Forward Returns
Multi-day returns (typically 1, 2, 3, 5, 10 days) measured from a trigger
event — used across most studies to quantify the size and reliability of
an edge.

---

## Troubleshooting

| Symptom | Cause | Fix |
|:--------|:------|:----|
| Stocks 200 ✅, Options 403 ❌ | Alpaca plan does not include options data, or hitting OPRA on indicative feed | Set `ALPACA_DATA_FEED=indicative` in `.env`. The engine uses `/v2/options/contracts` for OI (works on free tier). |
| Options 404 | Wrong endpoint path | Run `python tools\levels_engine\doctor.py` — should not happen on current code. |
| 401 on any endpoint | Keys not loaded or wrong keys | Check `.env` values match your Alpaca dashboard. No quotes, no spaces. Re-run doctor. |
| All OI values are 0 | Indicative feed snapshots do not return OI | Already handled — the engine merges OI from `/v2/options/contracts` automatically. |
| "ARB/CONTRACTUAL (VERIFIED): NONE" | No contractual levels found in the SEC lookback window | Not an error — no filings with recognisable price levels were found recently. |
| "No ticker detected" from router | Query had intent keywords but no recognisable ticker | Include 1–3 tickers like TSLA, NVDA, SPY in your question. |
| "Not an options-levels request" | Router did not find any intent keywords | Use phrases like "key levels", "call wall", "put wall", "options levels", etc. |
| Study script fails with import error | Venv not activated or missing dependency | Run `.venv\Scripts\Activate.ps1` then `pip install -r requirements.txt` |

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `ALPACA_API_KEY_LIVE` | Yes | — | Alpaca live API key (options data) |
| `ALPACA_API_SECRET_LIVE` | Yes | — | Alpaca live API secret |
| `ALPACA_API_KEY_PAPER` | No | — | Alpaca paper key (for trading) |
| `ALPACA_API_SECRET_PAPER` | No | — | Alpaca paper secret |
| `ALPACA_OPTIONS_AUTH` | No | `live` | Which key pair for options data |
| `ALPACA_TRADING_AUTH` | No | `paper` | Which key pair for trading |
| `ALPACA_DATA_FEED` | No | `indicative` | `indicative` or `opra` |
| `SEC_USER_AGENT` | Yes | — | Required by SEC (your name + email) |
| `SEC_LOOKBACK_DAYS` | No | `45` | How far back to scan filings |

---

## Architecture

```
QuantLab/Data_Lab/
├── tools/
│   └── levels_engine/
│       ├── query_levels.py          # Query mode CLI (--summary)
│       ├── route_query.py           # Natural-language router
│       ├── run_levels.py            # Full pipeline CLI
│       ├── doctor.py                # API health check
│       ├── .env.example             # Template for secrets
│       └── levels_engine/
│           ├── config.py            # Config loader + defaults
│           ├── query_compute.py     # Two-lens analysis + verdict
│           ├── query_report.py      # Markdown + JSON renderers
│           ├── providers/
│           │   └── alpaca_options.py # Alpaca options + OI enrichment
│           ├── sec/
│           │   ├── edgar_fetch.py   # EDGAR filing downloader
│           │   └── arb_extract.py   # Contractual price extractor
│           └── utils/
├── studies/
│   ├── _TEMPLATE/                   # Copy this to create a new study
│   ├── alab_gapdown_study/
│   ├── baba_compression_breakdown/
│   ├── baba_nbs/
│   ├── baba_nbs_nov_data/
│   ├── cannabis_rallies/
│   ├── iwm_1pct_followup/
│   ├── iwm_fed_cuts_pause/
│   ├── mu_intraday_earnings/
│   ├── mu_intraday_earnings_liquid_v2/
│   ├── tlry_rescheduling_events/
│   └── tsla_indicator_honesty/
├── shared/
│   ├── data_router.py               # Central data routing (Alpaca primary)
│   ├── config/                       # API clients, env loading, keys
│   └── indicators/
│       ├── trend_strength_nr7.py     # TrendStrengthNR7 + Cap Finder
│       └── ttm_squeeze_adv.py        # TTM Squeeze (tight + soft)
├── docs/                             # API_MAP, HOW_TO_USE, STUDY_PROMPT_LIBRARY
├── prompts/                          # Agent context, ThinkScript refs
└── data/levels/YYYY-MM-DD/           # Levels Engine daily output
```
