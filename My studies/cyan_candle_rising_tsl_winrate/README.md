# Cyan Candle + Rising TSL — Win Rate Study

## Overview

Measures the forward win rate of a combined signal:
**Cyan Candle** (TrendStrengthCandles `cs ≥ 70` AND NOT NR7) **+** **Rising TSL** (TrendStrengthLine `slope > 0.25`) on 5-minute bars across a 20-ticker universe.

Signal is evaluated at bar N with zero lookahead — entry is taken at the **open of bar N+1**.

---

## Parameters

| Parameter | Value |
|-----------|-------|
| Universe | NVDA, AMD, TSLA, AAPL, MSFT, META, GOOGL, AMZN, SMCI, MSTR, COIN, PLTR, SOFI, HOOD, ARM, AVGO, MU, NFLX, SPY, QQQ |
| Date range | 2024-11-01 → 2025-02-28 |
| Timeframe | 5-minute bars (Alpaca, IEX feed) |
| Warmup skip | First 20 bars of each session |
| Tail skip | Last 20 bars of each session (no full forward window available) |
| Forward windows | 5 bars (25 min), 10 bars (50 min), 20 bars (100 min) |
| Win definition | `close[N+W] > entry_price` |

---

## Signal Definition

```
cyan_signal = (cs >= 70) AND NOT is_nr7
is_rising   = TSL slope > 0.25

ENTRY SIGNAL = cyan_signal AND is_rising   (evaluated at bar N)
ENTRY PRICE  = open[N+1]                   (zero lookahead)
```

**cs** is the TrendStrengthCandles consensus score (three-method z-score average, clamped to [-100, +100]).  
**slope** is the smoothed 5-bar slope of the TrendStrengthLine trend score (EMA-3 of raw slope).  
The two indicators use **independent** normalization windows — candle uses 200-bar population std; TSL uses 100-bar clamped z-score.

---

## Results Summary

### Overall Win Rates (n = 2,084 signals, 20 tickers)

| Window | Win Rate | Avg Return | Median Return |
|--------|----------|------------|---------------|
| 5-bar (25 min) | **54.0%** | +0.040% | +0.028% |
| 10-bar (50 min) | **55.5%** | +0.074% | +0.047% |
| 20-bar (100 min) | **55.2%** | +0.129% | +0.068% |

All three windows show a consistent positive edge above the 50% baseline.

---

### Win Rate by Time Bucket (ET)

| Bucket | ET Range | n | 5-bar | 10-bar | 20-bar |
|--------|----------|---|-------|--------|--------|
| Open_Bar | 09:30–09:35 | 0 | — | — | — |
| First_Hour | 09:35–10:30 | 0 | — | — | — |
| **Mid_Morning** | 10:30–12:00 | **526** | 55.1% | **58.6%** | **61.6%** |
| Midday | 12:00–14:00 | 1,337 | 53.9% | 54.8% | 52.5% |
| Power_Hour | 14:00–15:00 | 221 | 51.6% | 52.5% | 56.1% |
| Last_30 | 15:00–15:30 | 0 | — | — | — |

> **Open_Bar / First_Hour / Last_30 produce zero qualifying signals** because the 20-bar head/tail warmup filter removes those session segments entirely on a standard ~78-bar RTH session.

**Key finding:** Mid_Morning (10:30–12:00 ET) is the strongest bucket — 58.6% at 10 bars and 61.6% at 20 bars. Midday is the highest-volume bucket (64% of all signals) but shows the weakest follow-through at the 20-bar window.

---

### Win Rate by Score Bucket

| Bucket | cs Range | n | 5-bar | 10-bar | 20-bar |
|--------|----------|---|-------|--------|--------|
| Strong_Bull | 70–85 | 339 | 54.6% | **59.6%** | 57.2% |
| Max_Bull | > 85 | 1,745 | 53.9% | 54.7% | 54.8% |

Strong_Bull (lower-conviction cyan candles) slightly outperforms Max_Bull at the 10-bar window. Max_Bull is ~84% of all signals — the signal fires frequently even at extreme scores.

---

### Win Rate by Ticker (10-bar)

| Ticker | Signals | 10-bar Win% |
|--------|---------|-------------|
| MSFT | 119 | 68.1% |
| ARM | 138 | 66.7% |
| QQQ | 105 | 64.8% |
| MU | 118 | 63.6% |
| AVGO | 84 | 61.9% |
| MSTR | 111 | 60.4% |
| SPY | 86 | 60.5% |
| NVDA | 92 | 59.8% |
| NFLX | 221 | 57.5% |
| SMCI | 82 | 57.3% |
| GOOGL | 112 | 56.2% |
| SOFI | 124 | 54.8% |
| AAPL | 81 | 54.3% |
| COIN | 137 | 54.0% |
| HOOD | 84 | 51.2% |
| AMD | 92 | 50.0% |
| META | 91 | 22.0% |
| AMZN | 83 | 43.4% |
| TSLA | 66 | 39.4% |
| PLTR | 58 | 36.2% |

Notable: MSFT, ARM, QQQ, MU well above 60%. META (22%), PLTR (36%), TSLA (39%) show the signal has **negative predictive value** for those names in this period — the cyan+rising combination fires during momentum exhaustion rather than continuation.

---

## Edge Analysis

### Is there a real edge?

**Yes, but it's modest and highly ticker-dependent.**

The aggregate 55.5% win rate at 10 bars (2,084 signals) is statistically above random, but the average return per signal is only +0.074% — roughly $0.74 on a $1,000 position before commissions. The edge is real only if:
- Slippage on entry (next-bar open) is small
- The signal is applied selectively (right tickers, right time of day)

The distribution is heavily right-skewed (median +0.047% vs mean +0.074%), meaning a minority of large winners pulls the average up. Most signals are small winners or small losers.

---

### Where the edge concentrates

**1. Time of day matters most.**

Mid_Morning (10:30–12:00 ET) is the only bucket with a meaningful edge — 58.6% at 10 bars and **61.6% at 20 bars**. This makes structural sense: by 10:30 the open volatility has settled, the trend indicators have enough warm bars to be reliable, and institutional order flow resumes after the initial gap-fill activity. Midday signals (64% of the dataset) barely clear 50% at the 20-bar window.

**2. Strong tickers only.**

The signal has a **wide performance spread by ticker**:
- Top half (MSFT, ARM, QQQ, MU, AVGO, MSTR, SPY, NVDA): 10-bar win rates of 60–68%
- Bottom quartile (META 22%, PLTR 36%, TSLA 39%, AMZN 43%): the signal actively fires at momentum exhaustion points for these names

This suggests the cyan+rising TSL combination works best on **trending large-caps and indices** where the three-method consensus is genuinely capturing momentum continuation. For high-beta, narrative-driven names (PLTR, TSLA, META), the signal appears to mark local tops rather than continuation points.

**3. Score bucket is a weak filter.**

Strong_Bull (cs 70–85) beats Max_Bull (>85) at 10 bars (59.6% vs 54.7%), which is counter-intuitive — the highest-conviction candles don't follow through better. This may reflect that cs > 85 often coincides with vertical extensions where mean-reversion dominates over the 50-minute horizon.

---

### Practical edge estimate (filtered signal)

Applying two filters — **Mid_Morning only** + **top-8 tickers by win rate** (MSFT, ARM, QQQ, MU, AVGO, MSTR, SPY, NVDA) — would concentrate the signal into the highest-probability subset. Based on the full-universe results, a realistic expectation for that filtered universe is:

| Metric | Estimate |
|--------|----------|
| Win rate (10-bar) | ~62–65% |
| Avg return per signal | ~+0.12–0.15% |
| Signals per day (8 tickers) | ~2–4 |
| MFE > MAE ratio | Positive (see mfe_20bar / mae_20bar columns in CSV) |

This is a directional setup, not a system. It should be evaluated in the context of position sizing, stop placement (MAE data in the CSV supports this), and whether the edge persists after the study window.

---

### Caveats

- **Study window is 4 months (Nov 2024 – Feb 2025)** — includes a strong post-election bull run. Results may degrade in choppy or bear regimes.
- **No transaction costs modelled** — at 5-min bars, bid/ask spread on entry can materially impact a +0.074% average return.
- **IEX feed** — Alpaca IEX is a sampled feed, not full SIP. In-fill price accuracy on 5-min bars is good but not identical to exchange data.
- **NR7 filter removes relatively few bars** — the cyan signal fires even in compression setups not tagged as NR7; this warrants further inspection.
- **META and PLTR negative edge is worth investigating** — may reflect specific events in the study window rather than a structural property of those tickers.

---

## Output Files

```
outputs/
  all_signals.csv                 — every signal row (2,084 rows)
  summary_by_window.txt           — overall win rates at 5/10/20 bars
  summary_by_time_bucket.txt      — win rate per ET time bucket
  summary_by_score_bucket.txt     — Strong_Bull vs Max_Bull
  charts/
    winrate_by_time_bucket.html   — grouped bar chart (3 windows × 6 buckets)
    winrate_by_score_bucket.html  — grouped bar chart (3 windows × 2 buckets)
    return_distribution.html      — histogram of 10-bar returns
```

### all_signals.csv columns

| Column | Description |
|--------|-------------|
| ticker | Symbol |
| signal_time | Bar timestamp (ISO 8601, America/New_York) |
| entry_price | Open of bar N+1 |
| cs_score | Candle consensus score at signal bar |
| slope_value | TSL smoothed slope at signal bar |
| return_5bar | Pct return at 5-bar forward close vs entry |
| return_10bar | Pct return at 10-bar forward close vs entry |
| return_20bar | Pct return at 20-bar forward close vs entry |
| win_5bar | 1 if return_5bar > 0, else 0 |
| win_10bar | 1 if return_10bar > 0, else 0 |
| win_20bar | 1 if return_20bar > 0, else 0 |
| mfe_20bar | Max favourable excursion over 20 bars (pct, using High) |
| mae_20bar | Max adverse excursion over 20 bars (pct, using Low) |
| time_bucket | ET session bucket |
| score_bucket | Strong_Bull / Max_Bull |

---

## How to Run

```powershell
cd C:\QuantLab\Data_Lab
.\.venv\Scripts\python.exe studies\cyan_candle_rising_tsl_winrate\run_study.py
```

Requires: Alpaca API keys in `.env`, venv activated, `alpaca-py`, `pandas`, `numpy`, `plotly`.  
Runtime: ~2 minutes for full 20-ticker universe.

---

## Indicator References

- `shared/indicators/trend_strength_candles.py` — TrendStrengthCandles v2.1
- `shared/indicators/trend_strength_line.py` — TrendStrengthLine Gap-Aware v4.5
- `shared/data_router.py` — DataRouter (Alpaca primary, yfinance fallback)
