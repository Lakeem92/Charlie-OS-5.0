# Magenta Opening Bar + Catalyst Proxy Study

## Overview

**Core question:** When a magenta candle (cs ≤ −70) fires at the open AND a catalyst proxy is present (gap down ≥ 3% OR earnings overnight), does the short-side edge materialize that was absent in the naked magenta study?

**Hypothesis:** The naked magenta study showed a 49.5% EOD win rate — below 50%. The missing ingredient is catalyst. This study isolates magenta opens where something REAL is driving the weakness. Expected result: EOD win rate jumps to 60%+ on catalyst-confirmed signals.

**Builds on:** `studies/magenta_open_winrate/`

---

## Signal Definition

```
MAGENTA CATALYST SIGNAL fires when ALL of the following are true:

  1. Opening window bar — 09:30–10:00 ET

  2. cs <= -70 (MAX BEAR / magenta candle), NOT NR7

  3. CATALYST PROXY — at least ONE of:
       PROXY A — GAP DOWN: gap_pct <= -3.0%
                 (daily_open - prev_daily_close) / prev_daily_close
       PROXY B — EARNINGS OVERNIGHT
                 Report filed after prior close OR before current open

  ENTRY: Open of bar N+1  (SHORT entry, zero lookahead)
```

### Catalyst Strength Buckets

| Bucket | Condition |
|--------|-----------|
| GAP_SMALL | gap −3% to −5% |
| GAP_LARGE | gap −5% to −10% |
| GAP_EXTREME | gap < −10% |
| EARNINGS_GAP | earnings date AND gap ≤ −3% |
| EARNINGS_FLAT | earnings date AND gap > −3% |

---

## Parameters

| Parameter | Value |
|-----------|-------|
| Universe | NVDA, AMD, TSLA, AAPL, MSFT, META, GOOGL, AMZN, SMCI, MSTR, COIN, PLTR, SOFI, HOOD, ARM, AVGO, MU, NFLX, SPY, QQQ |
| Date range | 2024-11-01 → 2025-02-28 |
| Timeframe | 5-minute bars (Alpaca primary) |
| Opening window | 09:30–10:00 ET (first 6 bars of RTH) |
| Forward windows | 6 bars (30 min), 12 bars (60 min), 24 bars (120 min), EOD |
| Win definitions | **win_raw**: any lower close; **win_thr**: lower by ≥ 0.1% |
| Return convention | `(entry_price − forward_close) / entry_price` — positive = won |

---

## Comparison Groups

| Group | Condition |
|-------|-----------|
| **A** | Magenta + ANY catalyst (gap OR earnings) — primary signal |
| B | Magenta + gap-down only (no earnings) |
| C | Magenta + earnings only (gap < −3%) |
| D | Magenta + BOTH earnings AND gap ≥ −3% (double trigger) |
| E | Naked magenta — no catalyst proxy |

---

## Ticker Quality Tiers (Short-Side)

| Tier | Tickers | Basis |
|------|---------|-------|
| STRONG_SHORT | TSLA, MSFT, ARM, QQQ, NVDA, MU | Showed real short follow-through in naked study |
| WEAK_SHORT | PLTR, NFLX, AVGO | Bounce names — magenta = buy signal |
| UNKNOWN | all others | Unclassified on short side |

---

## Output Files

```
outputs/
  magenta_catalyst_signals.csv          — all magenta open bars (all groups)
  summary_group_comparison.txt          — A vs B vs C vs D vs E, all windows
  summary_gap_size_buckets.txt          — GAP_SMALL vs GAP_LARGE vs GAP_EXTREME
  summary_by_open_bucket.txt            — FIRST_BAR vs EARLY_OPEN vs OPEN_WINDOW (Group A)
  summary_by_ticker.txt                 — per-ticker EOD win rates, Group A, ranked
  summary_catalyst_lift.txt             — THE PAYOFF TABLE: naked vs catalyst-confirmed
  earnings_detection_log.txt            — which earnings method succeeded per ticker
  charts/
    group_comparison.html
    gap_size_vs_winrate.html            — scatter: gap size vs EOD return
    catalyst_lift_summary.html          — bar: naked vs catalyst-confirmed EOD win rates
    ticker_winrates_catalyst.html       — horizontal bar: per-ticker, Group A
```

### magenta_catalyst_signals.csv columns

| Column | Description |
|--------|-------------|
| ticker | Symbol |
| signal_time | Bar timestamp (ISO 8601, America/New_York) |
| signal_bar_bucket | FIRST_BAR / EARLY_OPEN / OPEN_WINDOW |
| entry_price | Open of bar N+1 |
| cs_score | Candle consensus score at signal bar |
| gap_pct | (daily_open − prev_daily_close) / prev_daily_close × 100 |
| is_earnings | True/False |
| catalyst_proxy | GAP / EARNINGS / BOTH / NONE |
| catalyst_strength_bucket | GAP_SMALL / GAP_LARGE / GAP_EXTREME / EARNINGS_GAP / EARNINGS_FLAT |
| group | A / B / C / D / E |
| ticker_quality | STRONG_SHORT / WEAK_SHORT / UNKNOWN |
| return_6bar, return_12bar, return_24bar | Short-side returns at fixed windows |
| return_eod | Short-side return at session close |
| win_raw_6bar … win_raw_eod | 1 if return > 0 |
| win_thr_6bar … win_thr_eod | 1 if return ≥ 0.001 (0.1% filter) |
| mfe_session | (entry − session_low) / entry — max fav excursion |
| mae_session | (session_high − entry) / entry — max adverse excursion |

---

## Earnings Detection

Earnings dates are identified per ticker using:
1. **yfinance `earnings_dates`** (preferred — tz-aware timestamps, classified as AM / PM)
2. **yfinance `calendar`** (fallback)
3. **Hardcoded dates** (final fallback for the 20-ticker universe, Nov 2024 – Feb 2025)

Results logged to `outputs/earnings_detection_log.txt`.

AM reports (< 09:30 ET) apply to that session's opening bar.
PM reports (≥ 16:00 ET) apply to the NEXT session's opening bar.

---

## How to Run

```powershell
cd C:\QuantLab\Data_Lab
.\.venv\Scripts\python.exe studies\magenta_catalyst_proxy\run_study.py
```

Requires: Alpaca API keys in `.env`, venv activated, `alpaca-py`, `pandas`, `numpy`, `plotly`, `yfinance`.  
Runtime: ~4–5 minutes for full 20-ticker universe (includes daily gap data fetch).

---

## Indicator References

- `shared/indicators/trend_strength_candles.py` — TrendStrengthCandles v2.1
- `shared/data_router.py` — DataRouter (Alpaca primary)

## Related Studies

- `studies/magenta_open_winrate/` — naked magenta opening bar study (49.5% EOD benchmark)
- `studies/cyan_open_rising_tsl/` — long-side mirror study
