# Gap Day Execution Blueprint — Results

## The Question
> "When a stock gaps up 2%+ and the first candle is neutral or bullish with follow-through, what does the REAL trade look like — and when should you enter, hold, and exit?"

This study exists to fix **one problem**: holding winners longer by replacing P&L anxiety with data-backed conviction.

---

## Study Parameters (V3)

| Parameter | Value |
|---|---|
| Universe | 237 watchlist tickers (liquid US equities) |
| Date Range | Jan 2024 – Mar 2026 |
| Gap Threshold | ≥ 2% gap-up (open vs prior close) |
| Quality Filters | **None** (no min price, no min volume) |
| Follow-Through (FT) | First 5-min bar whose **Close** ≥ Open + (ATR₁₄ × 0.40) — see Entry Definition below |
| Entry (E1) | The **close price** of the follow-through bar — see Entry Definition below |
| Excluded | Bearish first candles (close < open, body > 40% of range) |
| Data Source | Alpaca (IEX feed), 5-min bars, no fallback |

### Entry Definition (applies to all metrics in this study)

**"Entry" in this study = the close price of the first 5-minute bar that confirms follow-through (FT).**

Here is the exact mechanic, step by step:
1. Compute the stock's **14-period ATR** on daily bars (true range averaged over 14 days).
2. On the gap day, calculate the **FT level**: `Day's Open + (ATR₁₄ × 0.40)`.
3. Scan each 5-minute bar from the open. The **first bar whose Close ≥ the FT level** is the follow-through bar.
4. **Entry price = that bar's Close.** This is E1 (breakout entry). All returns, MAE, MFE, and win rates in this study are measured from this price unless otherwise noted.

> **Example:** Stock opens at $100. ATR₁₄ = $5. FT level = $100 + ($5 × 0.40) = **$102.00**. The third 5-min bar closes at $102.35 → that $102.35 close is the entry price.

E2 (first pullback) and E3 (deepest pullback) are alternative entries defined in Section C — they also use the FT bar as the reference point.

### Candle Classification
- **BULLISH**: Close > Open AND body > 40% of candle range
- **NEUTRAL**: Body ≤ 40% of range (doji/spinning top)
- **BEARISH**: Close < Open AND body > 40% of range → **excluded from analysis**

---

## Sample Size

| Metric | Count |
|---|---|
| Total gap events scanned | 12,341 |
| Bearish opens (excluded) | 2,053 |
| No follow-through (excluded) | 1,695 |
| No intraday data | 6,423 |
| **Included in V3 analysis** | **2,170** |
| **Included in extended study** | **1,865** |
| Unique tickers | 211 |

> *305 events from V3 were skipped in the extended study due to intraday data gaps on re-pull. All extended metrics use n=1,865.*

---

## Bug Fix — "Price Below Entry After Follow-Through"

The V3 README reported this stat as **0.0%**. That was wrong.

The original code checked `post_entry = session.iloc[ft_bar_idx:]` — which **includes the entry bar itself** (whose close IS the entry price), rather than bars strictly after entry. The entry bar's low was always ≥ entry close by construction, masking the real number.

| Metric | OLD (V3) | CORRECTED |
|---|---|---|
| Price below entry after FT | 0.0% | **94.8%** |

**Reality:** In 94.8% of events, price dips below entry at some point after the follow-through bar. Pullbacks are the norm, not the exception.

---

## V3 Findings (Preserved)

### 🟢 Finding 1: Opening Candle Color Is Noise — Follow-Through Is the Signal

| Metric | BULLISH (n=1,218) | NEUTRAL (n=952) | Combined (n=2,170) |
|---|---|---|---|
| EOD Win Rate | 49.4% | 51.7% | 50.4% |
| EOD Avg Return | +0.35% | +0.37% | +0.36% |
| EOD Median Return | +0.00% | +0.08% | — |
| Avg Winner | +3.98% | +3.22% | — |
| Avg Loser | −3.21% | −2.67% | — |

**Interpretation:** Candle color shows <2.3% win rate difference. The follow-through bar IS the signal.

---

### 🟢 Finding 2: The Low of Day Is Set Early — Median LoD = 5 Minutes From Open

| Metric | BULLISH | NEUTRAL | ALL |
|---|---|---|---|
| **Median LoD time** | **5 min** | **5 min** | **5 min** |
| LoD in first 30 min | 64.1% | 71.4% | 67.3% |
| LoD in first 60 min | 69.4% | 78.6% | 73.4% |

---

### 🟢 Finding 3: The High of Day Comes Later — Median HoD = 2h 40m From Open

| Metric | BULLISH | NEUTRAL | ALL |
|---|---|---|---|
| **Median HoD time** | **112 min (1h 52m)** | **210 min (3h 30m)** | **160 min (2h 40m)** |
| HoD in last hour | 24.1% | 29.9% | 26.7% |

**Key asymmetry:** LoD in first 5 min (52%) vs HoD in last hour (27%). Gaps set their floor fast and their ceiling slow.

---

### 🟡 Finding 4: P&L Profile — Expect a ~2.4% Drawdown, ~1.8% Run

| Metric | BULLISH | NEUTRAL | ALL |
|---|---|---|---|
| **Median MAE** | **−2.76%** | **−1.83%** | **−2.36%** |
| Worst 10% MAE | −7.66% | −6.13% | −7.14% |
| **Median MFE** | **+2.01%** | **+1.62%** | **+1.84%** |
| Median pullback before new high | −0.45% | −0.33% | −0.40% |

---

### 🟡 Finding 5: Gap Size Buckets — 5-8% Gaps Are the Sweet Spot

| Gap Size | n | EOD Win Rate | Avg Return | Avg MAE | LoD in 30 min |
|---|---|---|---|---|---|
| 2–3% | 931 | 51.0% | +0.20% | −2.32% | 69.1% |
| 3–5% | 694 | 46.7% | +0.23% | −3.32% | 65.1% |
| **5–8%** | **294** | **56.1%** | **+0.86%** | **−3.85%** | **69.4%** |
| 8–12% | 128 | 50.0% | +0.17% | −5.41% | 61.7% |
| 12–20% | 79 | 55.7% | +0.64% | −5.95% | 68.4% |
| 20%+ | 43 | 48.8% | +0.12% | −9.61% | 65.1% |

---

# Extended Study — Hold Time & Entry Timing Analysis

> *All results below from `run_extended_analysis.py`, n=1,865 events.*

---

## 🟢 Section A: Pullback Behavior After Follow-Through

### A1 — Pullbacks Are the Norm

**77.9%** of events pull back below entry price before making the session high. This is not failure — it's how gap days work.

### A2 — How Deep Is the Pullback?

| Metric | Value |
|---|---|
| Median pullback | −0.51% |
| Mean pullback | −1.05% |
| 10th percentile (shallow) | +0.00% |
| 90th percentile (deep) | −2.83% |

**Distribution:**

| Bucket | % of Events |
|---|---|
| 0–1% | 66.8% |
| 1–2% | 16.6% |
| 2–3% | 7.6% |
| 3–5% | 6.2% |
| 5%+ | 2.9% |

**Two-thirds of pullbacks stay within 1% of entry.** Only 3% of events pull back more than 5%.

### A3 — When Does the Pullback Happen?

| Window | % of Deepest Pullbacks |
|---|---|
| Within 30 min of entry | **81.3%** |
| 30–60 min after entry | 10.6% |
| After 60 min | 8.2% |

Median deepest pullback = **5 minutes after entry**. If you're going to get shaken out, it happens fast.

### A4 — Recovery After Pullback

**89.5%** of events recover and exceed the follow-through bar's high. The pullback is temporary in nearly 9 out of 10 cases.

---

## 🟢 Section B: Session High Behavior

### B1 — Drawdown From Session High

After the session high is set, how far does price give back before EOD?

| Metric | Value |
|---|---|
| Median drawdown from HoD | −2.87% |
| 25th percentile | −5.71% |
| 75th percentile | −1.18% |
| 90th percentile (danger) | −9.65% |

**Distribution:**

| Bucket | % of Events |
|---|---|
| 0–1% | 21.3% |
| 1–2% | 16.2% |
| 2–3% | 13.8% |
| 3–5% | 18.7% |
| 5–7% | 11.3% |
| 7%+ | 18.6% |

**Interpretation:** If you hold to EOD, you'll give back a median 2.87% from the high. Almost 1 in 5 events give back 7%+ from the high — the "fade" days. This is the cost of not having a trailing stop.

### B2 — Multiple HoD Attempts

Only **9.9%** of events make multiple runs at the session high (touch, retreat >1%, then return). Most gap days are **single-push**: one grind to the high, then fade. If you see the first reversal from HoD, the odds say it's not coming back.

### B3 — HoD Timing Buckets (All Times Central)

| Window | % of HoDs |
|---|---|
| 8:30–9:00 CT | 17.4% |
| 9:00–9:30 CT | 10.7% |
| 9:30–10:00 CT | 7.9% |
| 10:00–10:30 CT | 5.7% |
| 10:30–11:30 CT | 9.3% |
| 11:30+ CT | **48.9%** |
| Final hour (2:00–3:00 CT) | **27.5%** |

**Median HoD: 170 min from open (2h 50m) = ~11:20 CT**

Nearly half of all HoDs happen after 11:30 CT. Over a quarter happen in the final trading hour. If you're selling before lunch, you're selling early more often than not.

### B3 — HoD Timing by Gap Size

| Gap Size | n | Median HoD |
|---|---|---|
| 2–5% | 1,391 | 170 min (~11:20 CT) |
| **5–8%** | **261** | **210 min (~12:00 CT)** |
| 8–12% | 104 | 145 min (~10:55 CT) |
| 12%+ | 108 | 85 min (~9:55 CT) |

**5–8% gaps grind the longest.** Bigger gaps (12%+) tend to top out within the first 90 minutes — the opening spike is often the best you get. The sweet-spot gaps (5–8%) take their time, with median HoD at noon CT.

---

## 🔴 Section C: Entry Timing — Patience Pays

Three entry strategies compared. No indicators — pure price behavior.

| Entry | Definition |
|---|---|
| **E1 — Breakout** | Close of follow-through bar (existing entry) |
| **E2 — First Pullback** | After FT, first bar that closes down → next bar closes up → enter at that close |
| **E3 — Deepest Pullback** | Lowest closing bar between entry and session high → enter at that close |

### The R:R Comparison — All Events

| Metric | E1 Breakout | E2 First PB | E3 Deep PB |
|---|---|---|---|
| Events | 1,865 | 1,836 | 1,488 |
| Win Rate | 51.0% | 50.1% | **69.2%** |
| Avg EOD Return | +0.43% | +0.32% | **+2.22%** |
| Median MAE | −2.29% | −1.67% | **−0.49%** |
| Median MFE | +1.88% | +1.66% | **+3.19%** |
| **Median R:R** | **0.82x** | **1.00x** | **6.47x** |
| Avg Price vs E1 | baseline | −0.11% | **+0.66%** |
| % Cheaper than E1 | N/A | 49.4% | **66.9%** |

**E3 dominates every single metric.** 69% win rate vs 51%. 6.47x R:R vs 0.82x. And you get a better price 67% of the time.

### R:R by Gap Size Bucket

#### 5–8% Gaps — The Best of the Best

| Metric | E1 Breakout | E2 First PB | E3 Deep PB |
|---|---|---|---|
| Events | 261 | 260 | 211 |
| Win Rate | 58.2% | 57.3% | **73.9%** |
| Avg EOD Return | +1.10% | +1.07% | **+3.65%** |
| Median MAE | −2.85% | −2.10% | **−0.57%** |
| Median MFE | +2.80% | +2.65% | **+4.77%** |
| **Median R:R** | **0.98x** | **1.26x** | **8.36x** |

#### 2–5% Gaps

| Metric | E1 Breakout | E2 First PB | E3 Deep PB |
|---|---|---|---|
| Events | 1,391 | 1,365 | 1,109 |
| Win Rate | 49.3% | 48.8% | **68.1%** |
| Avg EOD Return | +0.26% | +0.22% | **+1.65%** |
| Median R:R | 0.78x | 0.98x | **6.36x** |

#### 8–12% Gaps

| Metric | E1 Breakout | E2 First PB | E3 Deep PB |
|---|---|---|---|
| Events | 104 | 102 | 79 |
| Win Rate | 53.8% | 51.0% | **74.7%** |
| Avg EOD Return | +0.20% | −0.13% | **+3.59%** |
| Median R:R | 0.98x | 0.88x | **9.71x** |

#### 12%+ Gaps

| Metric | E1 Breakout | E2 First PB | E3 Deep PB |
|---|---|---|---|
| Events | 108 | 108 | 88 |
| Win Rate | 51.9% | 48.1% | **65.9%** |
| Avg EOD Return | +0.31% | −0.87% | **+3.29%** |
| Median R:R | 0.99x | 0.89x | **4.09x** |

**E3 wins in every single bucket.** The 8–12% gap bucket shows the highest E3 R:R at 9.71x. Even the massive 12%+ gaps — where E2 actually *loses money* — E3 still prints +3.29% average.

---

## 🔴 Section D: Hold Time Analysis

### D1 — MFE Capture by Exit Time (Winners Only, n=951)

| Exit Time | % of Max Favorable Excursion Captured |
|---|---|
| 9:30 CT (10:30 ET) | 10.3% |
| 10:00 CT (11:00 ET) | 10.9% |
| 10:30 CT (11:30 ET) | 16.8% |
| 11:00 CT (12:00 ET) | 19.1% |
| 11:30 CT (12:30 ET) | 23.9% |
| 12:00 CT (1:00 ET) | 27.0% |
| **EOD** | **62.6%** |

At 10:00 CT you've captured only 11% of the available move. Even at noon CT you've only captured 27%. **The bulk of the return is earned in the afternoon.**

### D2 — Early Exit Cost (All Events, n=1,865)

| Exit Time | Avg Return | % of Return Left on Table |
|---|---|---|
| 9:30 CT | +0.09% | **79.8%** |
| 10:00 CT | +0.03% | 93.3% |
| 10:30 CT | +0.07% | 84.0% |
| 11:00 CT | +0.11% | 73.1% |
| 11:30 CT | +0.21% | 50.6% |
| 12:00 CT | +0.26% | 39.6% |
| **EOD** | **+0.43%** | **baseline** |

**Exiting at 9:30 CT leaves 80% of the return on the table.** Even exiting at 11:30 CT still leaves half the return behind. The data is unambiguous: early exits are expensive.

---

## Updated Mid-Trade Conviction Rules

Tape these to your desk. All times Central.

1. **Pullbacks are normal.** 77.9% of events pull back below entry. Median pullback is only −0.51%. Two-thirds stay within 1%. Don't panic.

2. **The pullback is fast.** 81% of deepest pullbacks happen within 30 min of entry. If you survive the first half hour, you're probably fine.

3. **89.5% recover.** After pullback, price exceeds the FT bar's high in 9 out of 10 events. The pullback is temporary.

4. **Wait for the deepest pullback if you can.** E3 entry (patience entry) has 69% win rate vs 51% for breakout, with 6.47x R:R vs 0.82x. Patience isn't just virtue — it's alpha.

5. **5–8% gaps with E3 entry = 74% win rate, 8.36x R:R.** This is the single best setup in the dataset. Period.

6. **Don't exit before noon CT.** At 9:30 CT you've captured 10% of the move. At noon, 27%. The afternoon is where the money is.

7. **Once the high is set, it's probably done.** Only 9.9% of events make a second run at the session high. The first reversal from HoD is usually the real reversal.

8. **Median HoD at 11:20 CT, but 27.5% of HoDs happen in the final hour.** Trailing stop > time-based exit.

9. **Bigger gaps top faster.** 12%+ gaps have median HoD at 9:55 CT (just 85 min from open). 5–8% gaps grind until noon. Adjust hold expectations by gap size.

10. **The danger zone from session high is −9.65%.** That's the 90th percentile drawdown from HoD. Median giveback is −2.87%. A trailing stop of ~3% from HOD would capture most of the move without getting stopped on normal noise.

---

## Output Files

| File | Description |
|---|---|
| `outputs/gap_events_cache.csv` | All 12,341 gap events from Step 1 scan |
| `outputs/all_gap_events_classified.csv` | All events with candle color + follow-through classification |
| `outputs/execution_blueprint_events.csv` | 2,170 included events (V3 base study) |
| `outputs/extended_analysis_results.csv` | 1,865 events with all three entry points, pullback metrics, hold-time data |
| `outputs/extended_summary_stats.txt` | Full printout of Sections A–E results |
| `outputs/rr_comparison_table.csv` | E1/E2/E3 comparison table by gap bucket |

---

## Methodology Notes

- **ATR₁₄** computed on daily bars (rolling 14-day True Range average) as of the gap day
- **Follow-through** = first 5-min bar where Close ≥ Open + (ATR × 0.40). Entry price = that bar's Close.
- **MAE** = Maximum Adverse Excursion = lowest low from entry through close, as % of entry price
- **MFE** = Maximum Favorable Excursion = highest high from entry through close, as % of entry price
- **E2 (First Pullback)** = After FT bar, first bar closing below prior bar → next bar closing higher → enter at that close
- **E3 (Deepest Pullback)** = Lowest closing bar between FT entry and session high → enter at that close
- **Hold time returns** = price at each target time vs entry price
- **LoD/HoD timing** = minutes from 9:30 AM ET market open
- **6,423 events** had no intraday data (Alpaca IEX coverage gaps). Biases sample toward liquid tickers.
- All times US/Eastern in raw data. CT = ET − 1 hour.

## Run
```bash
cd C:\QuantLab\Data_Lab

# V3 base study (22 min)
.venv\Scripts\python.exe studies\gap_execution_blueprint\run_gap_execution_blueprint.py

# Extended analysis — entry timing, hold time, pullback behavior (14 min)
.venv\Scripts\python.exe studies\gap_execution_blueprint\run_extended_analysis.py
```

## Runtime
- V3 base study: 237 tickers, 1,424 API chunks, 0 failures, 22.1 min
- Extended study: 211 tickers, 998 API chunks, 0 failures, 14.3 min
