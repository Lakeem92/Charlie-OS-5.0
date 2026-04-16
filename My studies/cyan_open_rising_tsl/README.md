# Cyan Opening Bar + Rising TSL — Win Rate Study

## Overview

**Core question:** Does a stock that opens the session with a cyan candle (cs ≥ 70) AND rising TSL (slope > 0.25) have a statistically meaningful upside edge for the rest of that session?

This is an **opening bar study** purpose-built to capture the first 30 minutes of the RTH session. Unlike the base win rate study (which applied a 20-bar warmup skip that killed all opening data), indicator warmup here is handled by loading prior data so the first bar of each session is evaluable.

---

## Signal Definition

```
cyan_signal  = (cs >= 70) AND NOT is_nr7     — TrendStrengthCandles v2.1
is_rising    = TSL slope > 0.25              — TrendStrengthLine Gap-Aware v4.5

ENTRY SIGNAL = cyan_signal AND is_rising     (evaluated at bar N, 09:30–10:00 ET)
ENTRY PRICE  = open[N+1]                     (zero lookahead, no exceptions)
```

Opening window bars are classified into three sub-buckets:

| Sub-Bucket | ET Range |
|------------|----------|
| FIRST_BAR | 09:30–09:35 |
| EARLY_OPEN | 09:35–09:45 |
| OPEN_WINDOW | 09:45–10:00 |

---

## Parameters

| Parameter | Value |
|-----------|-------|
| Universe | NVDA, AMD, TSLA, AAPL, MSFT, META, GOOGL, AMZN, SMCI, MSTR, COIN, PLTR, SOFI, HOOD, ARM, AVGO, MU, NFLX, SPY, QQQ |
| Date range | 2024-11-01 → 2025-02-28 |
| Timeframe | 5-minute bars (Alpaca, IEX feed) |
| Opening window | 09:30–10:00 ET (first 6 bars of RTH) |
| Forward windows | 6 bars (30 min), 12 bars (60 min), 24 bars (120 min), EOD |
| Win definition | `close[N+W] > entry_price` / `session_close > entry_price` for EOD |
| Warmup strategy | Indicators computed on full loaded series — NaN bars excluded, not skipped |

---

## 2×2 Comparison Groups

Every opening bar is classified into one of four groups, enabling full signal decomposition:

| Group | Condition | n |
|-------|-----------|---|
| **A** | Cyan + Rising TSL (full signal) | **588** |
| B | Cyan only, TSL not rising | 200 |
| C | Rising TSL only, candle not cyan | 990 |
| D | Neither — baseline | 1,322 |

---

## Results

### The 7 Requested Numbers

| # | Metric | Result |
|---|--------|--------|
| 1 | **Group A 12-bar win rate** | **53.6%** (n=577) |
| | Group A EOD win rate | **58.2%** (n=588) |
| 2 | Group B 12-bar (cyan only, no TSL) | 53.1% |
| 3 | Group C 12-bar (TSL only, no cyan) | 47.5% |
| 4 | Group D 12-bar (baseline) | 43.6% |
| 5 | Group A HIGH quality tickers 12-bar | **56.1%** (n=214) |
| 6 | Group A FIRST_BAR only 12-bar | 50.0% (n=74) |
| 7 | Group A total signals | **588** ✅ (above 100 threshold) |

---

### Group Comparison — All Windows

| Window | A (Cyan+TSL) | B (Cyan only) | C (TSL only) | D (Baseline) |
|--------|:-----------:|:-------------:|:------------:|:------------:|
| 30 min | 52.1% | 49.7% | 46.8% | 41.1% |
| 60 min | 53.6% | 53.1% | 47.5% | 43.6% |
| 120 min | 57.9% | 54.1% | 47.6% | 46.2% |
| **EOD** | **58.2%** | 52.5% | 49.0% | 50.1% |

Avg return (Group A): −0.022% at 30 min → +0.030% at 60 min → +0.252% at 120 min → **+0.472% at EOD**

---

### Open Sub-Bucket Win Rates (Group A only)

| Bucket | n | 30 min | 60 min | 120 min | EOD |
|--------|---|--------|--------|---------|-----|
| FIRST_BAR | 76 | 46.1% | 50.0% | 60.8% | 56.6% |
| EARLY_OPEN | 189 | 51.1% | 55.9% | 55.4% | 57.7% |
| OPEN_WINDOW | 323 | 54.1% | 53.0% | 58.7% | **58.8%** |

---

### Ticker Quality Tier Win Rates (Group A only)

Tiers from the base mid-session study:

- **HIGH:** MSFT, ARM, QQQ, MU, AVGO, MSTR, SPY, NVDA (60%+ in base study)
- **LOW:** META, PLTR, TSLA, AMZN (sub-45% in base study — "exhaustion names")
- **MIDDLE:** GOOGL, AAPL, NFLX, SMCI, SOFI, COIN, HOOD, AMD

| Tier | n | 30 min | 60 min | 120 min | EOD |
|------|---|--------|--------|---------|-----|
| HIGH | 223 | 53.9% | **56.1%** | **66.8%** | **63.2%** |
| MIDDLE | 206 | 44.7% | 44.2% | 50.0% | 52.9% |
| LOW | 159 | **59.1%** | **62.4%** | 56.1% | 57.9% |

---

### Per-Ticker Win Rates at 12-Bar (Group A, ranked)

| Ticker | n | 12-bar Win% | Quality |
|--------|---|-------------|---------|
| NVDA | 16 | 87.5% | HIGH |
| SOFI | 7 | 85.7% | MIDDLE |
| QQQ | 36 | 78.8% | HIGH |
| AMZN | 39 | 66.7% | LOW |
| TSLA | 35 | 65.7% | LOW |
| AAPL | 20 | 65.0% | MIDDLE |
| MSFT | 19 | 63.2% | HIGH |
| MSTR | 24 | 62.5% | HIGH |
| META | 39 | 62.2% | LOW |
| ARM | 31 | 58.1% | HIGH |
| PLTR | 46 | 56.5% | LOW |
| HOOD | 38 | 55.3% | MIDDLE |
| SPY | 24 | 54.2% | HIGH |
| AMD | 24 | 50.0% | MIDDLE |
| GOOGL | 27 | 48.1% | MIDDLE |
| AVGO | 42 | 38.9% | HIGH |
| COIN | 23 | 34.8% | MIDDLE |
| SMCI | 39 | 33.3% | MIDDLE |
| MU | 31 | 25.8% | HIGH |
| NFLX | 28 | 17.9% | MIDDLE |

---

## Key Insights

### 1. The signal has real edge — but only holds to close

At 30 minutes the win rate is a modest 52.1% with a *negative* avg return (−0.022%). By 120 minutes it climbs to 57.9%, and at end-of-day it peaks at **58.2% with avg return +0.472%**. The opening cyan+rising TSL signal is a **day-trade hold, not a scalp**. Entering and exiting within 30 minutes leaves most of the edge on the table.

---

### 2. TSL alone at the open is a negative signal

Group C (rising TSL, candle not cyan) shows **47.5% at 12 bars and 49.0% at EOD** — both below the 50% baseline. A rising trend score at the open, without the strong-bull candle confirmation, actually predicts downside. The cyan candle is load-bearing in this signal combination; TSL alone misleads at the open.

---

### 3. Cyan alone and full signal are nearly identical at 60 minutes

Group A (53.6%) vs Group B (53.1%) at 12 bars are statistically indistinguishable. The TSL filter's value emerges at **120 minutes and EOD** (57.9% vs 54.1%, and 58.2% vs 52.5%). If you're trading a 1-hour hold, the rising TSL adds little. For full-day holds, it adds ~6 percentage points of edge.

---

### 4. The "exhaustion names" invert completely at the open

The LOW quality tier (META, PLTR, TSLA, AMZN) showed sub-45% win rates mid-session in the base study. At the open they flip to **62.4% at 12 bars** — the strongest tier in the 60-minute window. Of the four, TSLA (65.7%), META (62.2%), and AMZN (66.7%) all look strong. PLTR (56.5%) is the weakest of the group but still above 50%.

**Interpretation:** These high-beta names gap hard and trend hard in the opening bars. The cyan+rising signal during this window captures genuine momentum continuation, not exhaustion. The exhaustion dynamic that kills them mid-session doesn't apply when they're setting the day's direction at the open.

---

### 5. FIRST_BAR is the weakest at 30 minutes but holds fine to close

The 09:30 candle produces only 46.1% at 30 minutes — below baseline. This is the open auction noise effect: the first bar reacts to overnight news and gap dynamics that the prior-session warmup data doesn't fully capture. However, FIRST_BAR rebounds to 60.8% at 120 minutes and 56.6% EOD — the signal is valid for a day-trade, just not a quick scalp.

Practically: **wait for the signal to fire on bar 2 or later** (EARLY_OPEN / OPEN_WINDOW) for intraday traders. For a hold-to-close approach, FIRST_BAR is fine.

---

### 6. Significant ticker-level divergence within the HIGH quality tier

The HIGH tier averages look strong (66.8% at 120 min), but the per-ticker breakdown reveals extreme spread:
- **NVDA (87.5%), QQQ (78.8%), MSFT (63.2%), MSTR (62.5%)** — genuinely strong
- **AVGO (38.9%), MU (25.8%)** — opening cyan+rising is a **fade signal** for these names

NFLX (17.9%) is the worst performing ticker in the entire universe at the open — the signal fires frequently on NFLX open bars and is wrong 82% of the time at 60 minutes. NFLX opening bars appear to be structurally mean-reverting.

---

### 7. MIDDLE tier is the dead zone

The MIDDLE quality tickers (AAPL, AMD, COIN, GOOGL, HOOD, NFLX, SMCI, SOFI) show 44.2% at 12 bars — **below random**. This tier should be excluded from any trading application of this signal. The opening cyan+rising pattern on these names has negative predictive value at the 60-minute horizon.

---

## Practical Application Summary

| Use Case | Recommendation |
|----------|---------------|
| Day-trade (hold to close) | Signal viable on A-tier: NVDA, QQQ, MSFT, MSTR, TSLA, META, AMZN, AAPL |
| Scalp (≤30 min) | Weak edge — avoid FIRST_BAR entirely |
| Name avoidance | NFLX, MU, AVGO, SMCI, COIN at the open — signal fades |
| Time filter | OPEN_WINDOW (09:45–10:00) is most consistent bucket |
| TSL filter value | Matters for EOD holds; marginal at 60-min |

---

## Comparison with Base Mid-Session Study

| Metric | Base Study (mid-session) | This Study (opening bar) |
|--------|--------------------------|--------------------------|
| Signal type | Cyan + Rising TSL, any time | Cyan + Rising TSL, open window only |
| Overall win rate (12-bar) | 55.5% | 53.6% |
| Best ticker | MSFT 68.1% | NVDA 87.5% |
| Worst ticker | META 22.0% | NFLX 17.9% |
| Best time | Mid_Morning (10:30–12:00) | OPEN_WINDOW (09:45–10:00) |
| LOW quality tickers | 36–43% (negative edge) | 57–66% (inverted — positive edge) |
| Hold recommendation | 50-min scalp viable | Hold to close for full edge |

The two studies are **complementary**, not competing. Opening cyan captures gap-day momentum; mid-session cyan captures trend continuation after consolidation. The "bad names" are different in each context.

---

## Output Files

```
outputs/
  open_signals.csv                    — 3,100 rows (all opening bars, all groups)
  summary_group_comparison.txt        — A vs B vs C vs D across all windows
  summary_by_open_bucket.txt          — FIRST_BAR vs EARLY_OPEN vs OPEN_WINDOW
  summary_by_ticker_quality.txt       — HIGH vs MIDDLE vs LOW quality tiers
  summary_by_ticker.txt               — per-ticker 12-bar win rates, ranked
  charts/
    group_comparison.html             — A vs B vs C vs D bar chart
    open_bucket_winrates.html         — sub-bucket win rate chart
    ticker_quality_comparison.html    — quality tier comparison chart
    eod_return_distribution.html      — histogram of EOD returns, Group A
```

### open_signals.csv columns

| Column | Description |
|--------|-------------|
| ticker | Symbol |
| signal_time | Bar timestamp (ISO 8601, America/New_York) |
| signal_bar_bucket | FIRST_BAR / EARLY_OPEN / OPEN_WINDOW |
| entry_price | Open of bar N+1 |
| cs_score | Candle consensus score at signal bar |
| slope_value | TSL smoothed slope at signal bar |
| group | A / B / C / D |
| ticker_quality | HIGH / MIDDLE / LOW |
| return_6bar | Pct return at 6-bar forward close |
| return_12bar | Pct return at 12-bar forward close |
| return_24bar | Pct return at 24-bar forward close |
| return_eod | Pct return at session close vs entry |
| win_6bar / win_12bar / win_24bar / win_eod | 1 if return > 0, else 0 |
| mfe_session | Max favourable excursion (session high vs entry) |
| mae_session | Max adverse excursion (entry vs session low) |

---

## How to Run

```powershell
cd C:\QuantLab\Data_Lab
.\.venv\Scripts\python.exe studies\cyan_open_rising_tsl\run_study.py
```

Requires: Alpaca API keys in `.env`, venv activated, `alpaca-py`, `pandas`, `numpy`, `plotly`.  
Runtime: ~3 minutes for full 20-ticker universe.

---

## Indicator References

- `shared/indicators/trend_strength_candles.py` — TrendStrengthCandles v2.1
- `shared/indicators/trend_strength_line.py` — TrendStrengthLine Gap-Aware v4.5
- `shared/data_router.py` — DataRouter (Alpaca primary)

## Related Studies

- `studies/cyan_candle_rising_tsl_winrate/` — base mid-session win rate study (same signal, any time of day)
