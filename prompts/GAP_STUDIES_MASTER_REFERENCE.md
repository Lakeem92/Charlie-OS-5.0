# Gap Studies Master Reference -- All Key Stats for LLM Context
### Consolidated from: Gap Execution Blueprint (Long), Gap-Down Execution Blueprint (Short), Gap Fade / Contrary Candle Study, Opening Candle Strength, and supporting gap studies
### Date Range: Jan 2024 -- Mar 2026
### Last Updated: March 9, 2026

---

## HOW THIS DOCUMENT IS ORGANIZED

This consolidates the canonical gap-study stack into one machine-readable reference. An LLM or analyst can read this single file and have full context for gap-related questions, indicator interpretation, and annual refresh workflow.

**Primary study populations:**

| Study | Direction | Bar-1 Requirement | FT Direction | n (FT-confirmed) |
|---|---|---|---|---|
| Gap Continuation Long | Gap-up >= 2% | NOT bearish | Long (close >= Open + 40% ATR) | 1,865 |
| Gap Continuation Short | Gap-down >= 2% | NOT bullish | Short (close <= Open - 40% ATR) | 1,861 |
| Contrary Candle Fade | Gap-up >= 2% | Bearish (body > 40% range) | Short (close <= Open - 40% ATR) | 1,346 |
| Contrary Candle Bounce | Gap-down >= 2% | Bullish (body > 40% range) | Long (close >= Open + 40% ATR) | 1,119 |
| Opening Candle Strength | Gap abs >= 2% | Any 5-tier opening candle | Regime classification / reverse FT | 11,733 |

**Key definitions:**
- **Gap**: (today's open - yesterday's close) / yesterday's close * 100. Must be >= 2% absolute.
- **Follow-Through (FT)**: A 5-min bar closes beyond Open +/- (ATR14 x 0.40) in the expected direction.
- **Contrary Candle**: Bar-1 goes AGAINST the gap (bearish on gap-up, bullish on gap-down). Body > 40% of range.
- **Continuation Day**: Trade is profitable at EOD (price closes beyond entry in the trade direction).
- **Entry**: Close of the 5-min bar that triggered FT.

**Annual maintenance note:** The canonical gap stack is expected to be rerun roughly once per year. The operating checklist and exact rerun commands live in `docs/GAP_STUDIES_README.md`.

---

## SECTION 1: HEADLINE STATS -- WHAT WORKS AND WHAT DOESN'T

### Win Rates at a Glance

| Setup | WR (all) | WR (best filter) | Best Filter Description | n |
|---|---|---|---|---|
| Gap-up continuation (long) | 51.0% | **74.7%** | E3 entry on 8-12% gap | 79 |
| Gap-down continuation (short) | 45.4% | **64.7%** | Gap 12-20% + bearish candle + FT < 15m | 33 |
| Gap-up fade (contrary, short) | 51.3% | **71.2%** | HoD <= 5 min + FT <= 5 min | 358 |
| Gap-down bounce (contrary, long) | 51.4% | **76.0%** | LoD <= 5 min + gap 8%+ | 75 |

### Raw Signal (No FT Required)

| Signal | EOD WR | Avg Return | n |
|---|---|---|---|
| Gap-up + bearish bar-1 = fade | **68.4%** | +1.74% | 2,076 |
| Gap-down + bullish bar-1 = bounce | **66.8%** | +1.79% | 1,745 |

The contrary candle raw signal (no FT filter) is the highest-confidence single indicator in the entire dataset. A bearish bar-1 on a gap-up predicts the gap reverses by EOD 68% of the time.

### The E3 Entry (Long Continuation)

| Gap Bucket | n | WR | Avg Return | R:R |
|---|---|---|---|---|
| 2-5% | 1,109 | 68.1% | +1.65% | 6.36x |
| **5-8%** | **211** | **73.9%** | **+3.65%** | **8.36x** |
| **8-12%** | **79** | **74.7%** | **+3.59%** | **9.71x** |
| 12%+ | 88 | 65.9% | +3.29% | 4.09x |

The E3 entry (deep pullback between FT and session high) on gap-up continuation days is the single best trade in the long dataset: 69.2% WR overall with 6.47x R:R. The 5-12% bucket is the sweet spot.

### Opening Candle Strength Headline Findings

| Finding | Result | n |
|---|---|---|
| Gap-down MAX_BULLISH open | 66.7% WR | 78 |
| Gap-down BULLISH open | 67.6% WR | 1,547 |
| Gap-up MAX_BEARISH open | 66.4% WR | 131 |
| Gap-up BEARISH open | 67.3% WR | 2,030 |
| Neutral open, gap-down | 53.2% WR | 2,013 |
| Neutral open, gap-up | 50.6% WR | 2,569 |

Interpretation: the opening candle matters a lot, but the MAX tiers did not beat the regular bullish/bearish tiers enough to justify treating them as separate edge classes on their own. Neutral opens remain low-edge and should be treated as informational, not actionable.

### Reverse FT Headline Findings

| Setup | Result | n |
|---|---|---|
| Gap-down bearish reversed to long | 84.6% WR | 428 |
| Gap-up bullish reversed to short | 83.7% WR | 471 |
| Gap-down bullish reversed to short | 10.9% WR for bounce | 321 |
| Gap-up bearish reversed to long | 15.6% WR for fade | 525 |

Interpretation: reverse FT is the cleanest invalidation mechanic in the stack. Once the opposite FT level is reached, the original setup is usually dead.

### TS Level Filter on Reverse FT

| Reverse Setup | TS Level at Trigger | WR | n |
|---|---|---|---|
| Gap-down bearish reversed to long | BULLISH (cs >= 40) | 90.7% | 150 |
| Gap-down bearish reversed to long | NEUTRAL (-15 to 40) | 90.0% | 70 |
| Gap-down bearish reversed to long | BEARISH (cs <= -15) | 76.0% | 146 |
| Gap-up bullish reversed to short | BEARISH (cs <= -15) | 87.0% | 208 |
| Gap-up bullish reversed to short | NEUTRAL (-15 to 40) | 79.8% | 94 |
| Gap-up bullish reversed to short | BULLISH (cs >= 40) | 76.0% | 104 |

Interpretation: reverse FT is strongest when TrendScore level agrees with the new direction at the trigger bar.

---

## SECTION 2: GAP-UP CONTINUATION (LONG) -- 1,865 events

### Population
- 12,341 gap-up events scanned -> 1,865 qualified (non-contrary bar-1 + FT confirmed)
- 211 unique tickers, Jan 2024 - Mar 2026

### Core Stats

| Metric | Value |
|---|---|
| EOD Win Rate | 51.0% |
| Avg EOD Return | +0.43% |
| Avg Winner | +3.24% |
| Avg Loser | -2.64% |
| R:R | 1.23:1 |
| Price dips below entry at some point | 94.8% |
| Median pullback depth from entry | -0.51% |
| 66.8% of pullbacks stay within | 1.0% |
| Recovery rate (exceeds FT high) | 89.5% |

### Timing

| Metric | Value |
|---|---|
| Median LoD (floor sets fast) | 5 min from open |
| LoD in first 30 min | 67.3% |
| Median HoD (ceiling sets slow) | 170 min (~11:20 CT) |
| HoD after 11:30 CT | 48.9% |
| HoD in final hour | 27.5% |
| Deepest pullback within 30 min | 81.3% |
| Only 9.9% make a second run at HoD | after >1% pullback from HoD |

### HoD by Gap Size

| Gap Bucket | n | Median HoD | Translation (CT) |
|---|---|---|---|
| 2-5% | 1,391 | 170 min | ~11:20 CT |
| 5-8% | 261 | 210 min | ~12:00 CT |
| 8-12% | 104 | 145 min | ~10:55 CT |
| 12%+ | 108 | 85 min | ~9:55 CT |

### MFE Capture (Winners Only)

| Exit Time (CT) | % of Max Move Captured |
|---|---|
| 9:30 CT | 10.3% |
| 10:00 CT | 10.9% |
| 11:00 CT | 19.1% |
| 12:00 CT | 27.0% |
| EOD | 62.6% |

Even holding to EOD only captures 63% of the max move. Exiting at 10 AM CT captures just 11%.

### Pullback Zones from Entry

| Depth | Meaning | % of Events | Action |
|---|---|---|---|
| 0-0.51% | Below median | ~50% | HOLD |
| 0.51-1.18% | Median to 75th pctl | ~17% | HOLD |
| 1.18-2.83% | 75th to 90th pctl | ~16% | MONITOR |
| 2.83%+ | Past 90th pctl | ~9% | EVALUATE EXIT |

### Trail Stops from HoD (by Gap Size)

| Gap Bucket | Trail Stop | Median MAE at E1 |
|---|---|---|
| 2-5% | 3.5% | - |
| 5-8% | 5.0% | -2.85% |
| 8-12% | 6.5% | -4.09% |
| 12%+ | 5.0% | -5.44% |

---

## SECTION 3: GAP-DOWN CONTINUATION (SHORT) -- 1,861 events

### Population
- 1,861 qualified events (non-contrary bar-1 + FT confirmed)
- 844 continuation days (45.4%), 1,017 V-bottom days (54.6%)
- 228 unique tickers

### Core Stats

| Metric | All Events | Continuation Only (n=844) |
|---|---|---|
| EOD Win Rate | 45.4% | 100% (by definition) |
| Avg EOD Return | -0.28% (profit) | +2.58% |
| Median EOD Return | — | +1.58% |
| Avg Winner | +2.58% | — |
| Avg Loser | -2.65% | — |
| R:R | 0.97:1 | 2.37x (MFE/MAE) |
| Price bounces above entry | 93.9% | 84.7% |
| Median bounce before LoD | +0.59% | +0.66% |

### The #1 Differentiator: LoD Timing

| Metric | Continuation (n=844) | V-Bottom (n=1,017) |
|---|---|---|
| Median LoD | **315 min (5h 15m)** | 65 min |
| LoD < 30 min | 2.5% | 33.9% |
| LoD > 4 hours | **68.4%** | 18.1% |
| LoD in last hour | **46.3%** | 8.7% |

### HoD Timing (Adverse for Short)

| Metric | Continuation (n=844) | V-Bottom (n=1,017) |
|---|---|---|
| Median HoD | **0 min (the open)** | 35 min |
| HoD in first 5 min | **71.9%** | 37.4% |
| HoD in first 30 min | **87.7%** | 49.1% |
| HoD in last hour | **0.0%** | 16.7% |

### Gap Size Breakdown

| Gap Bucket | n | WR | Avg Return | Med MAE | Med MFE |
|---|---|---|---|---|---|
| 2-3% | 820 | 44.0% | -0.41% | +1.69% | +1.11% |
| 3-5% | 630 | 44.8% | -0.36% | +2.18% | +1.47% |
| 5-8% | 248 | 43.5% | -0.47% | +2.76% | +1.98% |
| **8-12%** | **91** | **56.0%** | **+0.99%** | +3.44% | +3.97% |
| **12-20%** | **51** | **64.7%** | **+1.60%** | +4.72% | +4.07% |
| 20%+ | 21 | 42.9% | -0.42% | +6.87% | +3.80% |

### Short Bounce Thresholds

| Depth | Meaning | Action |
|---|---|---|
| < 0.59% | Below median pre-LoD bounce | HOLD |
| 0.59-2.15% | Median to median MAE | HOLD (86% bounce before LoD) |
| 2.15-3.12% | Median to mean MAE | MONITOR |
| 3.12%+ | Above mean MAE | TIGHTEN |

### Cover Stops by Gap Size

| Gap Bucket | Cover Stop | Median MAE |
|---|---|---|
| 2-3% | 4.0% | +1.69% |
| 3-5% | 4.5% | +2.18% |
| 5-8% | 5.5% | +2.76% |
| 8-12% | 7.0% | +3.44% |
| 12-20% | 7.5% | +4.72% |
| 20%+ | 5.5% | +6.87% |

### V-Bottom Detection Signals

| Signal | Implication |
|---|---|
| LoD set in first 30 min | 86.9% are V-bottoms -- EXIT |
| Price above open within 30 min | V-bottom forming -- EXIT |
| HoD NOT in first 5 min | Drops continuation odds |
| No new lows after 60 min with LoD < 30 min | 87% V-bottom -- EXIT |

### Time to Hold a Short (Continuation Days)

| Metric | Value |
|---|---|
| Median time FT to LoD | 200 min (3h 20m) |
| < 30 min after FT | 2.5% of LoDs |
| < 2 hours after FT | 31.9% |
| > 4 hours after FT | 41.8% |
| WR when LoD > 4 hours | 75.8% |

---

## SECTION 4: GAP-UP FADE / CONTRARY CANDLE (SHORT) -- 1,346 FT-confirmed

### Population
- 2,076 gap-up days with bearish bar-1 (68.4% close below open by EOD)
- 1,346 with FT confirmed (fade FT = close <= Open - 40% ATR)
- 690 continuation (51.3%), 656 failed (48.7%)

### Core Stats (FT-confirmed)

| Metric | All (n=1,346) | Continuation (n=690) | Failed (n=656) |
|---|---|---|---|
| WR | 51.3% | — | — |
| Avg Return | +0.36% | +3.13% | -2.55% |
| Median Return | +0.10% | +2.11% | -1.49% |
| MAE Median | +2.35% | +1.68% | +3.12% |
| MFE Median | +2.06% | +3.69% | +0.87% |
| R:R (MFE/MAE) | — | **2.20x** | 0.28x |

### Timing (Continuation vs Failed)

#### LoD (Destination for Short)

| Metric | Continuation (n=690) | Failed (n=656) |
|---|---|---|
| Median LoD | **290 min (4h 50m)** | 60 min |
| LoD first 30 min | 5.8% | 36.9% |
| LoD after 4 hours | **59.0%** | 13.0% |
| LoD in last hour | **41.0%** | 4.1% |

#### HoD (Adverse for Short)

| Metric | Continuation (n=690) | Failed (n=656) |
|---|---|---|
| Median HoD | **0 min (the open)** | 30 min |
| HoD in first 5 min | **77.4%** | 40.9% |
| HoD in first 30 min | **90.6%** | 51.5% |
| HoD after 4 hours | 0.3% | 25.3% |
| HoD in last hour | **0.1%** | **15.7%** |

### Key Filters

| Filter | n | WR | Avg Return |
|---|---|---|---|
| No filter (baseline) | 1,346 | 51.3% | +0.36% |
| HoD <= 5 min (topped at open) | 802 | **66.6%** | +1.70% |
| HoD <= 5 min + FT <= 5 min | 358 | **71.2%** | +2.29% |
| HoD after 30 min | 383 | 17.0% | — |
| LoD after 4 hours | 492 | **82.7%** | +2.88% |
| LoD in last hour | 310 | **91.3%** | +3.74% |
| HoD in last hour (DEAD) | 104 | **1.0%** | — |

### Gap Bucket Breakdown

| Bucket | n | WR | Avg Return | Med MAE | Med MFE |
|---|---|---|---|---|---|
| 2-5% | 979 | 51.8% | +0.41% | +1.98% | +1.75% |
| 5-8% | 220 | 51.4% | +0.65% | +2.98% | +2.53% |
| **8-12%** | **81** | **45.7%** | **-0.61%** | +4.13% | +3.53% |
| 12%+ | 65 | 50.8% | -0.08% | +6.67% | +4.98% |

**WARNING: 8-12% gap-up fades have the worst WR (45.7%) and negative avg return. Do NOT short fades in this range.**

### Adverse Move Zones (Bounce Against Short)

| Depth | Meaning | Action |
|---|---|---|
| < 0.67% | Below median | Normal |
| 0.67-2.35% | Median adverse | Normal -- hold |
| 2.35-4.26% | Median to 75th MAE | Deep -- monitor |
| 4.26%+ | Past 75th MAE | Evaluate exit |
| 7.31%+ | Past 90th MAE | Extreme |

### Gap Fill

| Metric | Continuation | Failed |
|---|---|---|
| Close below open (reversal) | 100.0% | 75.9% |
| Full gap fill (low <= prev close) | 79.9% | 54.7% |

---

## SECTION 5: GAP-DOWN BOUNCE / CONTRARY CANDLE (LONG) -- 1,119 FT-confirmed

### Population
- 1,745 gap-down days with bullish bar-1 (66.8% close above open by EOD)
- 1,119 with FT confirmed (bounce FT = close >= Open + 40% ATR)
- 575 continuation (51.4%), 544 failed (48.6%)

### Core Stats (FT-confirmed)

| Metric | All (n=1,119) | Continuation (n=575) | Failed (n=544) |
|---|---|---|---|
| WR | 51.4% | — | — |
| Avg Return | +0.26% | +2.66% | -2.28% |
| Median Return | +0.06% | +1.46% | -1.52% |
| MAE Median | +2.00% | +1.43% | +2.89% |
| MFE Median | +1.67% | +2.95% | +0.77% |
| R:R (MFE/MAE) | — | **2.07x** | 0.27x |

### Timing (Continuation vs Failed)

#### HoD (Destination for Long)

| Metric | Continuation (n=575) | Failed (n=544) |
|---|---|---|
| Median HoD | **245 min (4h 5m)** | 65 min |
| HoD first 30 min | 3.7% | 36.2% |
| HoD after 4 hours | **50.4%** | 16.7% |
| HoD in last hour | **31.0%** | 5.7% |

#### LoD (Adverse for Long)

| Metric | Continuation (n=575) | Failed (n=544) |
|---|---|---|
| Median LoD | **0 min (the open)** | 15 min |
| LoD in first 5 min | **83.3%** | 45.6% |
| LoD in first 30 min | **90.6%** | 54.6% |
| LoD after 4 hours | 0.0% | 25.9% |
| LoD in last hour | **0.0%** | **15.8%** |

### Key Filters

| Filter | n | WR | Avg Return |
|---|---|---|---|
| No filter (baseline) | 1,119 | 51.4% | +0.26% |
| LoD <= 5 min (bottomed at open) | 727 | **65.9%** | +1.41% |
| LoD <= 5 min + FT <= 5 min | 331 | **73.1%** | +2.05% |
| LoD <= 5 min + gap 8%+ | 75 | **76.0%** | +3.13% |
| LoD after 30 min | 301 | 17.9% | — |
| HoD after 4 hours | 381 | **76.1%** | +2.15% |
| HoD in last hour | 209 | **85.2%** | +2.63% |
| LoD in last hour (DEAD) | 86 | **0.0%** | — |

### Gap Bucket Breakdown

| Bucket | n | WR | Avg Return | Med MAE | Med MFE |
|---|---|---|---|---|---|
| 2-5% | 848 | 50.1% | +0.09% | +1.72% | +1.42% |
| 5-8% | 168 | 51.8% | +0.36% | +2.69% | +2.39% |
| **8-12%** | **53** | **62.3%** | **+1.10%** | +3.27% | +4.22% |
| **12%+** | **50** | **60.0%** | **+1.87%** | +4.54% | +5.00% |

**SWEET SPOT: 8-12% gap-down bounces are 62% WR with MFE > MAE. With "bottomed at open" filter, jumps to 76% WR.**

### Adverse Move Zones (Pullback Against Long)

| Depth | Meaning | Action |
|---|---|---|
| < 0.60% | Below median | Normal |
| 0.60-2.00% | Median adverse | Normal -- hold |
| 2.00-3.84% | Median to 75th MAE | Deep -- monitor |
| 3.84%+ | Past 75th MAE | Evaluate exit |
| 5.82%+ | Past 90th MAE | Extreme |

### Gap Fill

| Metric | Continuation | Failed |
|---|---|---|
| Close above open (reversal) | 100.0% | 71.3% |
| Full gap fill (high >= prev close) | 72.2% | 50.0% |

---

## SECTION 6: UNIVERSAL PATTERNS ACROSS ALL STUDIES

### Pattern 1: Adverse Peak Happens at the Open, Destination Takes Hours

Every study shows the same pattern:
- The **worst move against you** (HoD for shorts, LoD for longs) happens at or near the open
- The **destination** (LoD for shorts, HoD for longs) takes 3-5 hours on continuation days
- **~95% of all trades go adverse** at some point -- this is normal, not a failure

| Study | Adverse Peak | Destination |
|---|---|---|
| Long continuation | LoD at 5 min | HoD at 170 min |
| Short continuation | HoD at 0 min (open) | LoD at 315 min |
| Fade (contrary short) | HoD at 0 min (open) | LoD at 290 min |
| Bounce (contrary long) | LoD at 0 min (open) | HoD at 245 min |

### Pattern 2: Timing Is the #1 Differentiator

Across all studies, WHEN the adverse peak and destination occur is the strongest predictor of success:

| Signal | Continuation Rate | Failed Rate |
|---|---|---|
| Adverse in first 5 min | 72-83% | — |
| Adverse after 30 min | — | 83-87% failed |
| Destination after 4 hours | 59-68% | Only 13-18% |
| Destination in last hour | 31-46% | Only 4-9% |
| Adverse in last hour | **0-1%** (trade is DEAD) | — |

### Pattern 3: The 94% Retrace Is Normal

Both long and short FT entries see price go adverse ~94% of the time. The median adverse move is small:
- Longs: median pullback -0.51% (66.8% stay within 1%)
- Short continuation: median bounce +0.59% (50% under 0.5%)
- Fade (short): median adverse before destination +0.67%
- Bounce (long): median adverse before destination +0.60%

**The brief adverse excursion IS the continuation setup forming, not the continuation failing.**

### Pattern 4: R:R Separates Continuation from Failed Days

| Day Type | Fade R:R | Bounce R:R | Long Cont R:R | Short Cont R:R |
|---|---|---|---|---|
| Continuation | 2.20x | 2.07x | ~2x (E3: 6.47x) | 2.37x |
| Failed | 0.28x | 0.27x | — | — |

The entire edge is in identifying which type of day you're on. On continuation days, R:R is 2x+. On failed days, it's 0.27x. The win rate barely matters -- what matters is catching continuation days and cutting failed days.

### Pattern 5: Gap Size Creates Distinct Behavioral Regimes

| Gap Bucket | Long Cont Edge | Short Cont Edge | Fade Edge | Bounce Edge |
|---|---|---|---|---|
| 2-5% | Bread & butter | 44% WR (weak) | 51.8% (baseline) | 50.1% (baseline) |
| 5-8% | E3 sweet spot (74% WR, 8.36x R:R) | 43.5% (weak) | 51.4% | 51.8% |
| 8-12% | E3 sweet spot (75% WR, 9.71x R:R) | **56% WR (short sweet spot)** | **45.7% (AVOID)** | **62.3% (bounce sweet spot)** |
| 12%+ | Tops fast (85 min HoD) | 64.7% (small n) | 50.8% | 60.0% |

**Critical asymmetry at 8-12%:**
- Gap-up 8-12%: Continuation long is excellent (E3 = 75% WR). Fade is the worst (45.7%).
- Gap-down 8-12%: Continuation short is strong (56% WR). Bounce is the best contrary trade (62.3%, 76% with filter).

### Pattern 6: Contrary vs Continuation -- When to Fade vs Follow

| Scenario | Best Play | WR | Why |
|---|---|---|---|
| Gap-up + bullish/neutral bar-1 | Long (continuation) | 51% (69% at E3) | The E3 entry is the dataset's best trade |
| Gap-up + bearish bar-1 | Short (fade) if topped at open | 67-71% | Contrary signal is strong; topped confirmation critical |
| Gap-down + bearish/neutral bar-1 | Short (continuation) | 45% (56% at 8%+) | Harder trade; requires patience and late LoD |
| Gap-down + bullish bar-1 | Long (bounce) | 51% (76% at 8%+ bottomed) | +6.4pp edge over forcing the short |

**Gap-down bounces have a +6.4pp edge over gap-down continuation shorts** (51.4% vs 45%). When you see a bullish bar-1 on a gap-down, playing the bounce is significantly better than forcing the short.

---

## SECTION 7: FORWARD RETURNS FROM ENTRY

### Long Continuation

| Timeframe | Return | WR |
|---|---|---|
| 15 min | +0.09% | — |
| 30 min | +0.03% | — |
| 1 hour | +0.07% | — |
| Noon CT | +0.11% | — |
| EOD | +0.43% | 51.0% |

### Gap-Up Fade (Continuation vs Failed)

| Timeframe | Cont Avg | Cont WR | Failed Avg | Failed WR |
|---|---|---|---|---|
| 15 min | +0.49% | 61.2% | -0.50% | 36.1% |
| 30 min | +0.83% | 65.8% | -0.83% | 27.0% |
| 1 hour | +1.32% | 73.2% | -1.18% | 24.4% |
| 2 hours | +1.91% | 81.7% | -1.66% | 18.6% |

### Gap-Down Bounce (Continuation vs Failed)

| Timeframe | Cont Avg | Cont WR | Failed Avg | Failed WR |
|---|---|---|---|---|
| 15 min | +0.55% | 65.2% | -0.50% | 34.7% |
| 30 min | +0.95% | 72.5% | -0.81% | 27.6% |
| 1 hour | +1.49% | 77.7% | -1.02% | 25.9% |
| 2 hours | +1.98% | 84.2% | -1.38% | 21.0% |

**By 30 minutes**, continuation trades are green 66-73% of the time and failed trades are red 73% of the time.

---

## SECTION 8: FT CONFIRMATION TIMING

| Study | Median FT Time | FT in 5 min | FT in 15 min | FT in 30 min | FT after 2 hrs |
|---|---|---|---|---|---|
| Fade | 15 min | 38.9% | 54.1% | 65.8% | 12.0% |
| Bounce | 15 min | 40.3% | 53.4% | 66.2% | 14.0% |

FT typically confirms within the first 15 minutes. About 2/3 confirm within 30 min.

---

## SECTION 9: GAP FILL ANALYSIS

### Gap-Up Fades

| Metric | All FT-confirmed | Continuation | Failed |
|---|---|---|---|
| Close below open (reversal) | 88.3% | 100.0% | 75.9% |
| Full fill (low <= prev close) | 67.6% | 79.9% | 54.7% |

### Gap-Down Bounces

| Metric | All FT-confirmed | Continuation | Failed |
|---|---|---|---|
| Close above open (reversal) | ~86% | 100.0% | 71.3% |
| Full fill (high >= prev close) | 61.4% | 72.2% | 50.0% |

Even failed contrary trades often reverse the open-to-close direction (71-76%). The full gap fill is achieved on continuation days 72-80% of the time.

---

## SECTION 10: DECISION FRAMEWORK -- WHAT TO DO IN EVERY SCENARIO

### At the Open (First 5 Minutes)

| Observation | Action |
|---|---|
| Gap-up + bearish bar-1 | Watch for FADE. 68% chance gap reverses. |
| Gap-down + bullish bar-1 | Watch for BOUNCE. 67% chance gap reverses. |
| Gap-up + bullish/neutral bar-1 | Watch for LONG continuation FT. |
| Gap-down + bearish/neutral bar-1 | Watch for SHORT continuation FT. |

### After FT Confirms

| Scenario | Confidence | Key Stat |
|---|---|---|
| Fade: HoD = open + FT confirmed | HIGH (71%) | Best combo, n=358 |
| Bounce: LoD = open + FT confirmed | HIGH (73%) | Best combo, n=331 |
| Fade: HoD = open (no fast FT) | GOOD (67%) | Topped at open, n=802 |
| Bounce: LoD = open (no fast FT) | GOOD (66%) | Bottomed at open, n=727 |
| Long: FT confirmed, in E3 zone | HIGH (69-75%) | Best entry in long dataset |
| Short continuation: FT confirmed + HoD = open | GOOD (72%) | Strongest short confirmation |

### During the Session

| Signal | Action | Confidence |
|---|---|---|
| Adverse peak being refreshed past 30 min | CUT/TIGHTEN | 83% chance of failure |
| Still making lows/highs after 4 hours | HOLD | 76-83% continuation |
| Pull back < 1% from long entry | HOLD | 67% of all pullbacks this shallow |
| Bounce < 0.6% above short entry | HOLD | Below median adverse |
| 30-min return is positive (your direction) | HOLD | 66-73% continuation |
| 30-min return is negative (against you) | EVALUATE | 73% of these are failed days |

### Kill Signals (EXIT IMMEDIATELY)

| Signal | Continuation Rate |
|---|---|
| Fade: new HoD in last hour | 1% |
| Bounce: new LoD in last hour | 0% |
| Short cont: HoD in last hour | 0% |
| Short cont: LoD in first 30 min + no new lows at 1 hr | 13% (V-bottom) |

### Late Confirmation (TRAIL AND HOLD)

| Signal | WR |
|---|---|
| Fade: LoD in last hour | 91% |
| Bounce: HoD in last hour | 85% |
| Fade: still making lows after 4 hrs | 83% |
| Bounce: still making highs after 4 hrs | 76% |
| Short cont: LoD after 4 hours | 76% |

---

## SECTION 11: INDICATOR STATE ENGINE REFERENCE (v5.1)

The ThinkScript indicator uses a state engine with priority-based label selection. Each contrary candle trade shows exactly one label at all times.

### Fade State Engine (Gap-Up + Bearish Bar-1 = Short)

| State | Code | WR | Label | Color | Action |
|---|---|---|---|---|---|
| DEAD | 10 | 1% | FADE DEAD 1% - EXIT NOW | Red | EXIT immediately |
| LOD_LAST_HR | 9 | 91% | FADE 91% - LOD LAST HR -- TRAIL | Magenta | Trail stop, monster day |
| GRINDING | 8 | 83% | FADE 83% - STILL MAKING LOWS -- HOLD | Magenta | Hold, short is working |
| WEAK | 7 | 17% | FADE WEAK 17% - NEW HIGHS PAST 30M | Red | Cut or tighten aggressively |
| BEST | 6 | 71% | FADE 71% - TOPPED+FT AT OPEN | Pink | Best entry, hold |
| TOPPED | 5 | 67% | FADE 67% - TOPPED AT OPEN -- HOLD | Pink | Hold, HoD is the open |
| CAUTION | -1 | 29% | FADE 29% - NEW HIGHS -- TIGHTEN | Yellow | Tighten, adverse extending |
| E3 | 2 | — | FADE FT HOLD | Gold | E3-equivalent window |
| WORKING | 3 | — | FADE WORKING | Gold | Early session, hold |
| BUILDING | 4 | — | FADE BUILDING | Gold | Mid-session, hold |

### Bounce State Engine (Gap-Down + Bullish Bar-1 = Long)

| State | Code | WR | Label | Color | Action |
|---|---|---|---|---|---|
| DEAD | 10 | 0% | BOUNCE DEAD 0% - EXIT NOW | Red | EXIT immediately |
| HOD_LAST_HR | 9 | 85% | BOUNCE 85% - HOD LAST HR -- TRAIL | Magenta | Trail stop, monster day |
| GRINDING | 8 | 76% | BOUNCE 76% - STILL MAKING HIGHS -- HOLD | Magenta | Hold, long is working |
| WEAK | 7 | 18% | BOUNCE WEAK 18% - NEW LOWS PAST 30M | Red | Cut or tighten aggressively |
| BEST | 6 | 73% | BOUNCE 73% - BOTTOMED+FT AT OPEN | Cyan | Best entry, hold |
| BOTTOMED | 5 | 66% | BOUNCE 66% - BOTTOMED AT OPEN -- HOLD | Cyan | Hold, LoD is the open |
| CAUTION | -1 | 25% | BOUNCE 25% - NEW LOWS -- TIGHTEN | Yellow | Tighten, adverse extending |
| E3 | 2 | — | BOUNCE FT HOLD | Cyan | E3-equivalent window |
| WORKING | 3 | — | BOUNCE WORKING | Cyan | Early session, hold |
| BUILDING | 4 | — | BOUNCE BUILDING | Cyan | Mid-session, hold |

### Priority Chain

States are evaluated top-to-bottom. Higher-priority states always override:
1. DEAD (kill signal overrides everything)
2. LOD_LAST_HR / HOD_LAST_HR (late confirmation = monster)
3. GRINDING (4hr+ still making progress)
4. WEAK (adverse extending past 30 min)
5. BEST (topped/bottomed + fast FT)
6. TOPPED / BOTTOMED (adverse at open but no fast FT)
7. CAUTION (new adverse before 30 min, not at open)
8. E3 (hold window after FT)
9. WORKING / BUILDING (time-based defaults)

### Color Scheme

| Color | Meaning |
|---|---|
| Pink | Fade confirmed/working (short side) |
| Cyan | Bounce confirmed/working (long side) |
| Gold | Pre-confirmation / early session |
| Yellow | Caution / approaching limits |
| Red | Exit / trade dead / weak |
| Magenta | Monster / late confirmation (91%/85%/83%/76%) |
| Green | Long continuation working |

---

## APPENDIX: SOURCE FILES

| File | Contents |
|---|---|
| `studies/gap_execution_blueprint/` | Long continuation study (1,865 events) |
| `studies/gap_down_execution_blueprint/` | Short continuation study (1,861 events) |
| `studies/gap_fade_contrary_candle/` | Contrary candle study (3,821 events) |
| `studies/gap_fade_contrary_candle/outputs/results_analysis.csv` | 3,821 events x 31 columns |
| `studies/gap_fade_contrary_candle/outputs/summary_stats.txt` | Findings 0-7 |
| `studies/gap_fade_contrary_candle/outputs/continuation_deep_dive.txt` | Sections 1-10 |
| `prompts/thinkscript/CUSTOM_INDICATOR_TOS.thinkscript` | v5.1 indicator (915 lines) |
| `prompts/thinkscript/GAP_CONTINUATION_RULES.md` | Detailed rules (Parts 1-4, Rules 1-20) |
| `studies/gap_fade_contrary_candle/README.md` | Contrary candle rules (Parts 1-4, Rules 21-28) |
| `shared/config/watchlist.csv` | 239-ticker universe |
