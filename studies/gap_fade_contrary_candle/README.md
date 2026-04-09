# Gap Fade / Contrary Candle Study
### Source: Gap Fade & Contrary Candle Study + Continuation Day Deep Dive
### Date Range: Jan 2024 – Mar 2026 | 3,821 events | 2,465 FT-confirmed
### Last Updated: March 7, 2026

---

## What This Study Answers

When a stock gaps >= 2% but the first 5-minute candle goes **against** the gap direction, what happens?

- **Gap-up + bearish bar-1:** Does the gap fade? Should you short?
- **Gap-down + bullish bar-1:** Does the gap bounce? Should you go long?

These are the events the continuation studies **excluded** — the "contrary candles" filtered out of the gap execution blueprints. This study asks whether that contrary signal itself has edge.

---

## Study Population

| Metric | Value |
|---|---|
| Date range | Jan 2024 – Mar 2026 |
| Unique tickers | 228 (from watchlist) |
| Total contrary candle events | 3,821 |
| Gap-up + bearish bar-1 | 2,076 |
| Gap-down + bullish bar-1 | 1,745 |
| FT-confirmed (fade or bounce) | 2,465 (64.5%) |

### Definition: Contrary Candle
A candle is "contrary" when:
- **Gap-up day:** Bar-1 is **bearish** — close < open AND body > 40% of range
- **Gap-down day:** Bar-1 is **bullish** — close > open AND body > 40% of range

This is the exact inverse of the continuation study qualification (which requires bar-1 to NOT be contrary).

### Definition: Follow-Through (FT) and Entry

**"Entry" in this study = the close price of the first 5-minute bar that confirms follow-through (FT) in the fade/bounce direction.**

FT is confirmed in the **reverse** direction of the gap:
- **Fade FT (gap-up day, short entry):** First 5-min bar whose **Close ≤ Open − (ATR₁₄ × 0.40)**
- **Bounce FT (gap-down day, long entry):** First 5-min bar whose **Close ≥ Open + (ATR₁₄ × 0.40)**

Here is the exact mechanic, step by step:
1. Compute the stock's **14-period ATR** on daily bars (true range averaged over 14 days).
2. On the gap day, calculate the **FT level** in the direction opposite to the gap:
   - Gap-up fade: `Day's Open − (ATR₁₄ × 0.40)` (price must fall to this level)
   - Gap-down bounce: `Day's Open + (ATR₁₄ × 0.40)` (price must rise to this level)
3. Scan each 5-minute bar from the open. The **first bar whose Close crosses the FT level** is the follow-through bar.
4. **Entry price = that bar's Close.** All returns, MAE, MFE, and win rates in this study are measured from this price.

> **Fade example:** Stock gaps up to $110 open. ATR₁₄ = $5. FT level = $110 − ($5 × 0.40) = **$108.00**. Bar-3 closes at $107.85 → that $107.85 close is the short entry price.
>
> **Bounce example:** Stock gaps down to $90 open. ATR₁₄ = $5. FT level = $90 + ($5 × 0.40) = **$92.00**. Bar-2 closes at $92.15 → that $92.15 close is the long entry price.

---

## PART 1: ALL-EVENTS FINDINGS

### Finding 0: The Raw Signal Is Strong (No FT Required)

| Signal | n | EOD Win Rate | Avg Return | Median Return |
|---|---|---|---|---|
| Gap-up + bearish bar-1 -> fade | 2,076 | **68.4%** | +1.74% | +1.37% |
| Gap-down + bullish bar-1 -> bounce | 1,745 | **66.8%** | +1.79% | +1.37% |

A bearish bar-1 on a gap-up predicts the gap fades by EOD 68% of the time. A bullish bar-1 on a gap-down predicts a bounce 67% of the time. This is the highest-confidence signal in the study — **before** any FT filter.

### Finding 1: FT-Confirmed Trades — Positive but Modest Edge

| Direction | n | WR | Avg Return | Avg Winner | Avg Loser | R:R |
|---|---|---|---|---|---|---|
| Gap-up fade (short) | 1,346 | 51.3% | +0.36% | +3.13% | -2.55% | 1.22:1 |
| Gap-down bounce (long) | 1,119 | 51.4% | +0.26% | +2.66% | -2.28% | 1.17:1 |

FT entry dilutes the raw signal from 68%/67% down to ~51%. By the time FT confirms, the move has started — you're entering with less slack. The edge is in the R:R (winners are bigger than losers), not the WR.

**Forward returns from entry:**

| Timeframe | Fade (short) | Bounce (long) |
|---|---|---|
| 15 min | +0.01% / 49% WR | +0.04% / 50% WR |
| 30 min | +0.02% / 47% WR | +0.10% / 51% WR |
| 1 hour | +0.10% / 49% WR | +0.27% / 53% WR |
| 2 hours | +0.17% / 51% WR | +0.35% / 53% WR |

### Finding 2: Gap Size Buckets — The 8-12% Bounce Is the Trade

**Gap-Up Fades (short):**

| Bucket | n | WR | Avg Return | Med MAE | Med MFE | Med FT |
|---|---|---|---|---|---|---|
| 2-5% | 979 | 51.8% | +0.41% | +1.98% | +1.75% | 20m |
| 5-8% | 220 | 51.4% | +0.65% | +2.98% | +2.53% | 10m |
| **8-12%** | **81** | **45.7%** | **-0.61%** | +4.13% | +3.53% | 5m |
| 12%+ | 65 | 50.8% | -0.08% | +6.67% | +4.98% | 0m |

**8-12% gap-up fades are the worst bucket — 45.7% WR, negative return.** Do NOT short a gap-up fade in this range.

**Gap-Down Bounces (long):**

| Bucket | n | WR | Avg Return | Med MAE | Med MFE | Med FT |
|---|---|---|---|---|---|---|
| 2-5% | 848 | 50.1% | +0.09% | +1.72% | +1.42% | 15m |
| 5-8% | 168 | 51.8% | +0.36% | +2.69% | +2.39% | 18m |
| **8-12%** | **53** | **62.3%** | **+1.10%** | +3.27% | +4.22% | 5m |
| **12%+** | **50** | **60.0%** | **+1.87%** | +4.54% | +5.00% | 5m |

**8-12% gap-down bounces are the sweet spot: 62% WR, +1.10% avg, MFE > MAE.** 12%+ also strong at 60% WR.

### Finding 3: Timing — Destination Takes 2.5 Hours, Adverse Peak Is the Open

**Gap-Up Fades:**

| Metric | LoD (destination) | HoD (adverse) |
|---|---|---|
| Median | 150 min (2h 30m) | 0 min (the open) |
| First 30 min | 21.0% | 71.5% |
| Last hour | 23.0% | 7.7% |

**Gap-Down Bounces:**

| Metric | HoD (destination) | LoD (adverse) |
|---|---|---|
| Median | 150 min (2h 30m) | 0 min (the open) |
| First 30 min | 19.5% | 73.1% |
| Last hour | 18.7% | 7.7% |

The adverse peak (HoD for fades, LoD for bounces) happens immediately at the open. Destination takes ~2.5 hours.

### Finding 4: P&L Profile

| Metric | Fade (short) | Bounce (long) |
|---|---|---|
| Price goes adverse after FT | 94.7% | 94.5% |
| Adverse before destination (median) | +0.67% | +0.60% |
| Adverse before destination (90th) | +2.99% | +2.56% |
| MAE 25th / Median / 75th / 90th | +1.20 / +2.35 / +4.26 / +7.31% | +1.05 / +2.00 / +3.84 / +5.82% |
| MFE Median / Mean | +2.06% / +3.10% | +1.67% / +2.85% |

### Finding 5: Gap Fill

| Metric | Value |
|---|---|
| Gap-up fades close below open | **88.3%** |
| Gap-up fades full fill (low reaches prev close) | **67.6%** |
| Gap-down bounces close above open | 0.1% |
| Gap-down bounces full fill (high reaches prev close) | 61.4% |

### Finding 6: FT Timing

| Metric | Fade | Bounce |
|---|---|---|
| Median FT time | 15 min | 15 min |
| FT in first 5 min | 38.9% | 40.3% |
| FT in first 30 min | 65.8% | 66.2% |
| FT after 2 hours | 12.0% | 14.0% |

### Finding 7: Contrary vs Continuation Comparison

| Setup | WR | n |
|---|---|---|
| Gap-up fade (bearish bar-1, short) | 51.3% | 1,346 |
| Gap-up continuation (bull/neut bar-1, long) | ~51% | 1,865 |
| **Gap-down bounce (bullish bar-1, long)** | **51.4%** | **1,119** |
| Gap-down continuation (bear/neut bar-1, short) | ~45% | 1,861 |

**Gap-down bounces have a +6.4pp edge over gap-down continuation shorts** (51.4% vs 45%). When you see a bullish bar-1 on a gap-down, playing the bounce is significantly better than forcing the short.

---

## PART 2: CONTINUATION DAY DEEP DIVE

### Section 1: Population Split

| Group | Fade (short) | n | Bounce (long) | n |
|---|---|---|---|---|
| **Continuation (trade worked)** | **51.3%** | **690** | **51.4%** | **575** |
| Failed (trade lost) | 48.7% | 656 | 48.6% | 544 |

The split is nearly 50/50 for both sides — unlike gap-down continuation shorts (45.4% continuation, 54.6% V-bottom). This means early identification of which type of day you're on is critical.

### Section 2: Continuation Rate by Gap Bucket

**Gap-Up Fades:**

| Bucket | Total | Cont | Rate | Avg Return | Med MFE | Med MAE |
|---|---|---|---|---|---|---|
| 2-5% | 979 | 507 | 51.8% | +2.81% | +3.25% | +1.37% |
| 5-8% | 220 | 113 | 51.4% | +3.65% | +3.96% | +2.22% |
| 8-12% | 81 | 37 | 45.7% | +3.98% | +4.72% | +3.61% |
| 12%+ | 66 | 33 | 50.0% | +5.26% | +8.23% | +5.37% |

**Gap-Down Bounces:**

| Bucket | Total | Cont | Rate | Avg Return | Med MFE | Med MAE |
|---|---|---|---|---|---|---|
| 2-5% | 848 | 425 | 50.1% | +2.24% | +2.54% | +1.20% |
| 5-8% | 168 | 87 | 51.8% | +3.16% | +3.94% | +2.17% |
| **8-12%** | **53** | **33** | **62.3%** | **+4.42%** | **+6.59%** | **+2.42%** |
| **12%+** | **50** | **30** | **60.0%** | **+5.26%** | **+6.64%** | **+3.92%** |

On continuation days, 8-12% gap-down bounces average +4.42% with 6.59% MFE. The R:R is excellent (MFE/MAE = 2.72x).

---

### Section 3: Destination Timing — THE KEY DIFFERENTIATOR

This is the most important section. Just like the gap-down blueprint found that continuation vs V-bottom days have completely different LoD timing, the contrary candle study shows the same pattern.

#### Gap-Up Fade: LoD Timing (destination for short)

| Metric | Continuation (n=690) | Failed (n=656) |
|---|---|---|
| Median LoD | **290 min (4h 50m)** | 60 min (1h) |
| LoD in first 5 min | 0.9% | 13.7% |
| LoD in first 30 min | 5.8% | **36.9%** |
| LoD in first 60 min | 12.0% | 51.2% |
| LoD in first 2 hrs | 22.9% | 70.7% |
| LoD after 4 hours | **59.0%** | 13.0% |
| LoD in last hour | **41.0%** | 4.1% |
| LoD in last 30 min | **32.6%** | 2.4% |

**Translation:** On continuation fade days, the LoD (your profit destination) comes at 4h 50m. On failed days, the LoD (the brief low before it bounces back) is at 60 min. If LoD is set in the first 30 min, only 5.8% of continuation days do this vs 36.9% of failed days. **If LoD hasn't been refreshed after 2 hours, the fade is probably done.**

#### Gap-Up Fade: HoD Timing (adverse for short)

| Metric | Continuation (n=690) | Failed (n=656) |
|---|---|---|
| Median HoD | **0 min (the open)** | 30 min |
| HoD in first 5 min | **77.4%** | 40.9% |
| HoD in first 30 min | **90.6%** | 51.5% |
| HoD after 4 hours | 0.3% | 25.3% |
| HoD in last hour | **0.1%** | **15.7%** |

**Translation:** On continuation fade days, 77% have their HoD at the open — the gap-up topped immediately. On failed days, HoD is at 30 min (the stock kept pushing higher). **If HoD is in the first 5 min, 77% of the time the fade is real. If HoD is in the last hour, 0.1% of continuation days — the fade is dead.**

#### Gap-Down Bounce: HoD Timing (destination for long)

| Metric | Continuation (n=575) | Failed (n=544) |
|---|---|---|
| Median HoD | **245 min (4h 5m)** | 65 min (1h 5m) |
| HoD in first 5 min | 0.7% | 14.0% |
| HoD in first 30 min | 3.7% | **36.2%** |
| HoD in first 2 hrs | 25.4% | 65.6% |
| HoD after 4 hours | **50.4%** | 16.7% |
| HoD in last hour | **31.0%** | 5.7% |

#### Gap-Down Bounce: LoD Timing (adverse for long)

| Metric | Continuation (n=575) | Failed (n=544) |
|---|---|---|
| Median LoD | **0 min (the open)** | 15 min |
| LoD in first 5 min | **83.3%** | 45.6% |
| LoD in first 30 min | **90.6%** | 54.6% |
| LoD after 4 hours | 0.0% | 25.9% |
| LoD in last hour | **0.0%** | **15.8%** |

**Translation:** On continuation bounce days, 83% have their LoD at the open — the gap-down bottomed immediately. On failed days, LoD is at 15 min and 26% make new lows after 4 hours. **If LoD is in the first 5 min, 83% of the time the bounce is real. If LoD is in the last hour, 0% of continuation days — your bounce is dead.**

---

### Section 4: P&L Profile — Continuation vs Failed

#### Gap-Up Fades

| Metric | Continuation (n=690) | Failed (n=656) |
|---|---|---|
| Median EOD Return | +2.11% | -1.49% |
| Mean EOD Return | +3.13% | -2.55% |
| MAE Median | +1.68% | +3.12% |
| MAE 90th | +5.17% | +8.76% |
| MFE Median | +3.69% | +0.87% |
| MFE 90th | +8.94% | +3.39% |
| **R:R (MFE/MAE median)** | **2.20x** | **0.28x** |

#### Gap-Down Bounces

| Metric | Continuation (n=575) | Failed (n=544) |
|---|---|---|
| Median EOD Return | +1.46% | -1.52% |
| Mean EOD Return | +2.66% | -2.28% |
| MAE Median | +1.43% | +2.89% |
| MAE 90th | +4.56% | +7.19% |
| MFE Median | +2.95% | +0.77% |
| MFE 90th | +8.83% | +3.20% |
| **R:R (MFE/MAE median)** | **2.07x** | **0.27x** |

On continuation days, R:R is 2.07-2.20x. On failed days, it's 0.27-0.28x. **The entire edge is in identifying which day you're on.**

---

### Section 5: Early Warning Filters — This Is Where It Gets Actionable

#### Gap-Up Fade Filters

| Filter | n | Continuation Rate | Avg Return |
|---|---|---|---|
| **No filter (baseline)** | **1,346** | **51.3%** | **+0.36%** |
| LoD in first 30 min | 282 | **14.2%** | — |
| LoD after 30 min | 1,064 | **61.1%** | — |
| **HoD in first 5 min** | **802** | **66.6%** | **+1.70%** |
| HoD after 5 min | 544 | 28.7% | — |
| HoD in first 30 min | 963 | 64.9% | — |
| **HoD after 30 min** | **383** | **17.0%** | — |
| LoD after 4 hours | 492 | **82.7%** | +2.88% |
| **LoD in last hour** | **310** | **91.3%** | **+3.74%** |
| FT in first 5 min | 524 | 53.6% | — |
| **HoD in last hour** | **104** | **1.0%** | — |

**Key Fade Filters:**
- **HoD in first 5 min (topped at open) = 66.6% WR.** This is the #1 early confirmation. You can know this 5 min into the session.
- **HoD after 30 min = only 17.0% continuation.** If the gap-up is still making new highs 30 min in, the fade is dead 83% of the time.
- **LoD still being refreshed after 4 hours = 82.7% WR.** The fade is grinding.
- **LoD in last hour = 91.3% WR.** Monster.
- **HoD in last hour = 1.0% WR.** If the gap-up is making new highs late, EXIT.

#### Gap-Down Bounce Filters

| Filter | n | Continuation Rate | Avg Return |
|---|---|---|---|
| **No filter (baseline)** | **1,119** | **51.4%** | **+0.26%** |
| HoD in first 30 min | 218 | **9.6%** | — |
| HoD after 30 min | 901 | **61.5%** | — |
| **LoD in first 5 min** | **727** | **65.9%** | **+1.41%** |
| LoD after 5 min | 392 | 24.5% | — |
| LoD in first 30 min | 818 | 63.7% | — |
| **LoD after 30 min** | **301** | **17.9%** | — |
| HoD after 4 hours | 381 | **76.1%** | +2.15% |
| **HoD in last hour** | **209** | **85.2%** | **+2.63%** |
| FT in first 5 min | 451 | 56.1% | — |
| **LoD in last hour** | **86** | **0.0%** | — |

**Key Bounce Filters:**
- **LoD in first 5 min (bottomed at open) = 65.9% WR.** The gap-down never made new lows. Strong.
- **LoD after 30 min = only 17.9% continuation.** If the gap-down is still drilling 30 min in, the bounce is dead 82% of the time.
- **HoD still being refreshed after 4 hours = 76.1% WR.** The bounce is grinding.
- **HoD in last hour = 85.2% WR.**
- **LoD in last hour = 0.0% WR.** If the gap-down is making new lows late, EXIT immediately.

---

### Section 6: Combined Filter Stacks — Highest-Edge Setups

#### Gap-Up Fade: Best Setups

| Filter | n | WR | Avg Return | Med MFE | Med MAE |
|---|---|---|---|---|---|
| No filter (baseline) | 1,346 | 51.3% | +0.36% | +2.06% | +2.35% |
| **HoD <= 5 min (topped at open)** | **802** | **66.6%** | **+1.70%** | **+2.87%** | **+2.00%** |
| HoD <= 5 min + gap 2-5% | 585 | 66.7% | +1.58% | +2.48% | +1.66% |
| HoD <= 5 min + gap 5%+ | 217 | 66.4% | +2.04% | +4.03% | +3.19% |
| **HoD <= 5 min + FT <= 5 min** | **358** | **71.2%** | **+2.29%** | **+3.39%** | **+3.09%** |
| LoD >= 240 min | 492 | 82.7% | +2.88% | +2.97% | +1.60% |

**The best real-time trade: HoD in first 5 min + FT in first 5 min = 71.2% WR, +2.29% avg return, n=358.** You can identify this 5 minutes into the session.

#### Gap-Down Bounce: Best Setups

| Filter | n | WR | Avg Return | Med MFE | Med MAE |
|---|---|---|---|---|---|
| No filter (baseline) | 1,119 | 51.4% | +0.26% | +1.67% | +2.00% |
| **LoD <= 5 min (bottomed at open)** | **727** | **65.9%** | **+1.41%** | **+2.24%** | **+1.73%** |
| LoD <= 5 min + gap 2-5% | 535 | 63.9% | +1.08% | +1.84% | +1.46% |
| **LoD <= 5 min + gap 8%+** | **75** | **76.0%** | **+3.13%** | **+6.11%** | **+3.63%** |
| **LoD <= 5 min + FT <= 5 min** | **331** | **73.1%** | **+2.05%** | **+2.98%** | **+2.42%** |
| LoD <= 30 min | 818 | 63.7% | +1.27% | +2.13% | +1.72% |
| HoD >= 240 min | 381 | 76.1% | +2.15% | +2.04% | +1.31% |
| **Gap 8%+ + LoD <= 5 min** | **75** | **76.0%** | **+3.13%** | **+6.11%** | **+3.63%** |

**The best real-time trade: LoD in first 5 min + FT in first 5 min = 73.1% WR, +2.05% avg return, n=331.**

**The best bucket trade: Gap 8%+ + LoD in first 5 min = 76.0% WR, +3.13% avg, MFE +6.11%.** Small sample (n=75) but powerful.

---

### Section 7: Forward Returns — Continuation vs Failed

Can you tell which day you're on from early returns?

**Gap-Up Fades:**

| Timeframe | Continuation Avg | Cont WR | Failed Avg | Failed WR |
|---|---|---|---|---|
| 15 min | +0.49% | **61.2%** | -0.50% | 36.1% |
| 30 min | +0.83% | **65.8%** | -0.83% | 27.0% |
| 1 hour | +1.32% | **73.2%** | -1.18% | 24.4% |
| 2 hours | +1.91% | **81.7%** | -1.66% | 18.6% |

**Gap-Down Bounces:**

| Timeframe | Continuation Avg | Cont WR | Failed Avg | Failed WR |
|---|---|---|---|---|
| 15 min | +0.55% | **65.2%** | -0.50% | 34.7% |
| 30 min | +0.95% | **72.5%** | -0.81% | 27.6% |
| 1 hour | +1.49% | **77.7%** | -1.02% | 25.9% |
| 2 hours | +1.98% | **84.2%** | -1.38% | 21.0% |

**By 30 minutes**, the trade is already positive on continuation days (65-72% WR) and already negative on failed days (27% WR). Forward return at 30 min is probably the best early discriminator.

---

### Section 8: Gap Fill — Continuation vs Failed

**Gap-Up Fades:**

| Metric | Continuation | Failed |
|---|---|---|
| Close below open (reversal) | **100.0%** | 75.9% |
| Full gap fill (low <= prev close) | **79.9%** | 54.7% |

**Gap-Down Bounces:**

| Metric | Continuation | Failed |
|---|---|---|
| Close above open (reversal) | **100.0%** | 71.3% |
| Full gap fill (high >= prev close) | **72.2%** | 50.0% |

By definition, continuation fades always close below open (that's what makes them continuation). Even failed fades close below open 76% of the time — the gap reversal usually happens either way, but the close determines whether the short is profitable.

---

## PART 3: RULES FOR CONTRARY CANDLE TRADES

### RULE 21: The Contrary Signal Is 68/67% — Use It as a Filter

| Stat | Value | Source |
|---|---|---|
| Gap-up + bearish bar-1 -> close below open | 68.4% | Finding 0 |
| Gap-down + bullish bar-1 -> close above open | 66.8% | Finding 0 |
| FT confirmation rate | ~65% | Finding 0 |

**THE RULE:** When you see a contrary candle, the probability of the gap reversing direction is ~68%. This is valuable as a filter even before FT. If the indicator shows "FADE ALERT 68%" or "BOUNCE ALERT 67%", you know the gap is more likely to reverse than continue.

### RULE 22: HoD/LoD at the Open Is the Strongest Confirmation

| Filter | WR | n | Source |
|---|---|---|---|
| Fade: HoD in first 5 min | **66.6%** | 802 | Section 5 |
| Fade: HoD NOT in first 5 min | 28.7% | 544 | Section 5 |
| Bounce: LoD in first 5 min | **65.9%** | 727 | Section 5 |
| Bounce: LoD NOT in first 5 min | 24.5% | 392 | Section 5 |

**THE RULE:** If the gap-up's HoD is the open (no new highs after bar-1), the fade works 67% of the time. If the gap-down's LoD is the open (no new lows), the bounce works 66%. **This is the #1 real-time confirmation you can observe within the first 5 minutes.**

When the adverse peak happens AFTER 30 min, continuation drops to 17%.

### RULE 23: Best Combo — Top at Open + Fast FT = 71-73% WR

| Setup | n | WR | Avg Return | Source |
|---|---|---|---|---|
| Fade: HoD <= 5 min + FT <= 5 min | 358 | **71.2%** | +2.29% | Section 6 |
| Bounce: LoD <= 5 min + FT <= 5 min | 331 | **73.1%** | +2.05% | Section 6 |

**THE RULE:** The highest-edge entry is when BOTH the adverse peak AND FT happen in the first 5 minutes. This means bar-1 reversed the gap AND confirmed the reversal immediately. 71-73% WR with n > 300. You know this within 5 minutes of the open.

### RULE 24: Destination Takes 4-5 Hours on Continuation Days

| Metric | Fade Continuation | Bounce Continuation | Source |
|---|---|---|---|
| Median destination (LoD/HoD) | **290 min (4h 50m)** | **245 min (4h 5m)** | Section 3 |
| Destination after 4 hours | 59.0% | 50.4% | Section 3 |
| Destination in last hour | 41.0% | 31.0% | Section 3 |
| Destination in last 30 min | 32.6% | 23.1% | Section 3 |

**THE RULE:** Don't take profits early on contrary candle trades. The destination on continuation days comes at 4-5 hours. **41% of fade destinations and 31% of bounce destinations are in the last hour.** Patience is the edge.

### RULE 25: Late Destination = Monster Edge

| Filter | WR | Avg Return | Source |
|---|---|---|---|
| Fade: LoD after 4 hours | **82.7%** | +2.88% | Section 5 |
| Fade: LoD in last hour | **91.3%** | +3.74% | Section 5 |
| Bounce: HoD after 4 hours | **76.1%** | +2.15% | Section 5 |
| Bounce: HoD in last hour | **85.2%** | +2.63% | Section 5 |

**THE RULE:** If the trade is still working (making new LoDs/HoDs) after 4 hours, the win rate jumps to 76-83%. In the last hour, it's 85-91%. These are the same dynamics as the gap-down continuation study — the time-based confirmation is massive.

### RULE 26: Kill Signals — When the Trade Is Dead

| Signal | Continuation Rate | Source |
|---|---|---|
| Fade: HoD in last hour | **1.0%** | Section 5 |
| Fade: HoD after 30 min | 17.0% | Section 5 |
| Bounce: LoD in last hour | **0.0%** | Section 5 |
| Bounce: LoD after 30 min | 17.9% | Section 5 |

**THE RULE:**
- **Fade:** If the gap-up is making new highs in the last hour, the fade is dead (1% continuation). EXIT.
- **Bounce:** If the gap-down is making new lows in the last hour, the bounce is dead (0% continuation). EXIT.
- If the adverse move extends past 30 min, continuation drops to 17%. This is an early warning.

### RULE 27: 8-12% Gap-Down Bounce — The Sweet Spot

| Metric | All Events | Continuation Only | Source |
|---|---|---|---|
| WR | **62.3%** | — | Finding 2 |
| Continuation Rate | — | **62.3%** | Section 2 |
| Avg Return (continuation) | — | +4.42% | Section 2 |
| MFE (continuation) | — | +6.59% | Section 2 |
| MAE (continuation) | — | +2.42% | Section 2 |
| Best combo: LoD <= 5 min + gap 8%+ | **76.0%** | +3.13% / MFE +6.11% | Section 6 |

**THE RULE:** The 8-12% gap-down bounce is the best trade in the contrary candle dataset. If you add "LoD in first 5 min" as a filter, it jumps to 76% WR with +6.11% MFE. This is comparable to the E3 entry from the continuation study.

### RULE 28: 30-Minute Forward Return Is the Early Discriminator

| Direction | Continuation 30min WR | Failed 30min WR | Source |
|---|---|---|---|
| Fade | **65.8%** | 27.0% | Section 10 |
| Bounce | **72.5%** | 27.6% | Section 10 |

**THE RULE:** By 30 minutes after entry, continuation trades are green 66-73% of the time and failed trades are already red 73% of the time. If you're red at 30 min, the probability of recovery is low. If you're green at 30 min, the trade is likely on a continuation day.

---

## PART 4: INDICATOR ALIGNMENT

### Current Indicator State (v5.0)

The ThinkScript indicator was updated with contrary candle labels:
- **FADE ALERT 68%** / **BOUNCE ALERT 67%** — pre-FT raw signal
- **FADE FT HOLD** / **BOUNCE FT HOLD** — E3 window after FT
- Time phases: WORKING -> BUILDING -> TARGET ZONE -> TRAIL
- MAE adverse move zones: NORMAL / DEEP / EVALUATE

### What's NOT in the indicator (needs v5.1):

The continuation day deep dive revealed filters that should be added:
1. **HoD/LoD at open confirmation** — If HoD is in first 5 min, label should upgrade to "FADE CONFIRMED 67% | TOPPED AT OPEN". If LoD is in first 5 min, "BOUNCE CONFIRMED 66% | BOTTOMED AT OPEN".
2. **Kill signal** — If HoD extends past 30 min on a fade (or LoD past 30 min on a bounce), label should warn "FADE WEAKENING | NEW HIGHS" or "BOUNCE WEAKENING | NEW LOWS".
3. **Late confirmation** — If still making new LoDs after 4 hours on a fade, "FADE 83% WR | STILL MAKING LOWS". If HoD after 4 hours on bounce, "BOUNCE 76% WR | STILL MAKING HIGHS".
4. **Dead trade** — If HoD in last hour on fade or LoD in last hour on bounce, RED label "FADE DEAD" or "BOUNCE DEAD".
5. **Fresh HoD/LoD tracking** — The indicator tracks HoD/LoD timing for continuation labels (Rules 12-13) but does NOT wire this data into the contrary candle path.

---

## Appendix: Source File Reference

| File | Contents |
|---|---|
| `studies/gap_fade_contrary_candle/run_gap_fade_study.py` | Main study script (3,821 events) |
| `studies/gap_fade_contrary_candle/run_continuation_deep_dive.py` | Continuation day deep dive |
| `studies/gap_fade_contrary_candle/outputs/results_analysis.csv` | 3,821 events x 31 columns |
| `studies/gap_fade_contrary_candle/outputs/summary_stats.txt` | Findings 0-7 (all events) |
| `studies/gap_fade_contrary_candle/outputs/continuation_deep_dive.txt` | Sections 1-10 (continuation vs failed) |
| `prompts/thinkscript/CUSTOM_INDICATOR_TOS.thinkscript` | Indicator v5.0 (needs v5.1 update) |
| `prompts/thinkscript/GAP_CONTINUATION_RULES.md` | Parts 1-4 (needs Part 5 for contrary rules) |
