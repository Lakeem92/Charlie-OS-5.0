# Gap Continuation Trade Rules — Data-Backed Field Guide
### ATR Relative Movement Indicator Alignment Document
#### Source: Gap Execution Blueprint (Long) + Gap-Down Execution Blueprint (Short)
#### Date Range: Jan 2024 – Mar 2026 | Long: 1,865 events | Short: 1,861 events (844 continuation)
#### Last Updated: March 7, 2026

---

## ⚠️ CRITICAL CLARIFICATION: The "93.9% Retrace" Stat

The studies show two numbers that sound alarming out of context:

- **LONG SIDE: 94.8%** of gap-up events see price dip BELOW entry after FT confirmation
- **SHORT SIDE: 93.9%** of gap-down events see price bounce ABOVE entry after FT confirmation

### What This ACTUALLY Means

These stats measure a very specific thing: "At any point between your FT entry and end of day, did price touch the other side of your entry price?"

**This is NOT saying 94% of trades retrace the move.** It's saying almost every gap-day trade will go against you at some point — even by a single penny — before working.

Here's why this is normal, not alarming:

| Context (Long Side) | Stat | Source |
|---|---|---|
| Price dips below entry after FT | 94.8% | Extended Study Bug Fix |
| Median depth of that dip | −0.51% | Section A2 |
| 66.8% of dips stay within | 1.0% | A2 Distribution |
| Price recovers and exceeds FT high | 89.5% | Section A4 |
| Deepest dip happens within 30 min | 81.3% | Section A3 |

**Translation:** Yes, almost every long trade will tick red briefly. But two-thirds of the time it's less than 1%, and 89.5% recover. The dip IS the pattern — it's not a failure, it's the E3 entry forming.

| Context (Short Side) | Stat | Source |
|---|---|---|
| Price bounces above entry after FT | 93.9% | Finding 4 |
| Bounce above entry BEFORE making LoD | 85.6% | Finding 4 |
| Median bounce depth before LoD | +0.59% | Finding 4 |
| 90th pctl bounce before LoD | +2.75% | Finding 4 |
| Median MAE (worst bounce against short) | +2.15% | Finding 4 |

**Translation:** 86% of shorts bounce above your entry BEFORE making their low of day. The median bounce is tiny (0.59%). This means: if you short at follow-through and it goes green, that's what's SUPPOSED to happen. Don't cover. The continuation comes later.

### Why This Doesn't Contradict Continuation

Think about it mechanically:
1. Stock gaps up 5%
2. Follow-through confirms at Open + 40% ATR (your entry)
3. Price immediately pulls back 0.3% below entry (you're "red")
4. This is the E3 pullback forming
5. Price then grinds to session high

Step 3 makes you part of the 94.8%. Step 5 makes you a winner. They're not contradictions — they're sequential phases of the same move. **The retrace after the ATR momentum shift IS the continuation setup forming, not the continuation failing.**

If anything, the absence of a retrace is the anomaly (only 5.2% of longs never dip below entry). The continuation happens THROUGH the brief adverse excursion.

---

## PART 1: LONG CONTINUATION RULES (Gap-Up ≥ 2%)

### Study Population
| Filter | Count |
|---|---|
| Total gap-up events scanned | 12,341 |
| Bearish first candles excluded | 2,053 |
| No follow-through excluded | 1,695 |
| No intraday data | 6,423 |
| **Final dataset** | **1,865** |
| Unique tickers | 211 |
| Date range | Jan 2024 – Mar 2026 |

### Qualification Criteria (MUST have all three):
1. Gap ≥ +2% (today's open vs yesterday's close)
2. First 5-min candle is NOT bearish (close < open AND body > 40% of range)
3. Follow-through: a 5-min bar closes at or above Open + (ATR₁₄ × 0.40)

---

### RULE 1: Pullbacks Are Normal — Don't Panic at Red

| Stat | Value | Source |
|---|---|---|
| Events that pull back below entry | 77.9% | Section A1 |
| Price dips below entry at some point | 94.8% | Bug Fix |
| Median pullback depth from entry | −0.51% | Section A2 |
| 66.8% of pullbacks stay within | 1.0% | A2 Distribution |
| Only 2.9% pull back more than | 5.0% | A2 Distribution |
| Recovery rate (price exceeds FT high) | 89.5% | Section A4 |

**THE RULE:** After FT confirmation, a pullback below entry of less than 1% is NORMAL. Do NOT cut. 66.8% of all events stay within this band. If you're less than 30 minutes in and the pullback is under 1%, you are in the majority of events that work.

---

### RULE 2: The Pullback Is Fast — Survive 30 Minutes

| Stat | Value | Source |
|---|---|---|
| Median time of deepest pullback | 5 min after entry | Section A3 |
| Deepest pullback within 30 min | 81.3% | Section A3 |
| Deepest pullback 30-60 min | 10.6% | Section A3 |
| Deepest pullback after 60 min | 8.2% | Section A3 |

**THE RULE:** If you're 30 minutes past entry and haven't been stopped out, the worst is almost certainly over. 81.3% of maximum pain happens in the first half hour. This is the E3 formation window. Don't cut during it.

---

### RULE 3: Low of Day Is Set Early, High of Day Comes Late

**LoD (floor sets fast):**
| Stat (All Events) | Value | Source |
|---|---|---|
| Median LoD | 5 min from open | Finding 2 |
| LoD in first 30 min | 67.3% | Finding 2 |
| LoD in first 60 min | 73.4% | Finding 2 |

**HoD (ceiling sets slow):**
| Stat (All Events) | Value | Source |
|---|---|---|
| Median HoD | 170 min = 11:20 CT | Section B3 |
| HoD after 11:30 CT | 48.9% | Section B3 |
| HoD in final hour (2-3 PM CT) | 27.5% | Section B3 |

**THE RULE:** The gap sets its floor in the first 5 minutes and its ceiling around lunch or later. If you sell before noon, you are selling in the first half of the move more often than not.

---

### RULE 4: HoD Timing Depends on Gap Size — Scale Your Patience

| Gap Bucket | n | Median HoD | Translation (CT) | Source |
|---|---|---|---|---|
| 2-5% | 1,391 | 170 min | ~11:20 CT | Section D3 |
| **5-8%** | **261** | **210 min** | **~12:00 CT** | **D3** |
| 8-12% | 104 | 145 min | ~10:55 CT | D3 |
| 12%+ | 108 | 85 min | ~9:55 CT | D3 |

**THE RULE:**
- **2-5% gaps:** Hold to 11:30 CT minimum. Median HoD = 11:20 CT.
- **5-8% gaps:** Hold to at LEAST noon CT. These grind the longest. Median HoD = 12:00 CT. This is the sweet spot — don't leave early.
- **8-12% gaps:** Monitor starting at 11:00 CT. These are volatile.
- **12%+ gaps:** These top by 10:00 CT median. Be ready to trail early. The opening spike IS the move.

---

### RULE 5: Don't Exit Before Noon — You're Leaving 73-93% of the Return on the Table

| Exit Time (CT) | Avg Return | % of Total Return Left on Table | Source |
|---|---|---|---|
| 9:30 CT (10:30 ET) | +0.09% | 79.8% | Section D2 |
| 10:00 CT (11:00 ET) | +0.03% | 93.3% | D2 |
| 10:30 CT (11:30 ET) | +0.07% | 84.0% | D2 |
| 11:00 CT (12:00 ET) | +0.11% | 73.1% | D2 |
| 11:30 CT (12:30 ET) | +0.21% | 50.6% | D2 |
| 12:00 CT (1:00 ET) | +0.26% | 39.6% | D2 |
| **EOD** | **+0.43%** | **baseline** | D2 |

MFE capture for winners only:
| Exit Time (CT) | % of Max Move Captured | Source |
|---|---|---|
| 9:30 CT | 10.3% | Section D1 |
| 10:00 CT | 10.9% | D1 |
| 11:00 CT | 19.1% | D1 |
| 12:00 CT | 27.0% | D1 |
| **EOD** | **62.6%** | D1 |

**THE RULE:** Even holding to EOD, you only capture 63% of the max move (the rest is given back from HoD). Exiting at 10 AM CT captures 11%. The money is made between noon and close.

---

### RULE 6: Not All Pullbacks Are the Same — Know Your Depth Zones

**Pullback from ENTRY (post-FT):**
| Depth | Meaning | % of Events | Action |
|---|---|---|---|
| 0-0.51% | Below median | ~50% | HOLD — Normal noise |
| 0.51-1.18% | Median to 75th pctl | ~17% | HOLD — Still in majority |
| 1.18-2.83% | 75th to 90th pctl | ~16% | MONITOR — Deeper than normal |
| 2.83%+ | Past 90th pctl | ~9% | EVALUATE — Only 9% get here |

**Drawdown from SESSION HIGH (HoD to close):**
| Depth | Meaning | % of Events | Action |
|---|---|---|---|
| 0-1.18% | Above 75th pctl (shallowest quarter) | 21.3% | HOLD — Tight fade is normal |
| 1.18-2.87% | 75th pctl to median | 30.0% | HOLD — Half of all events fade this much |
| 2.87-5.71% | Median to 25th pctl | 30.0% | TIGHTEN — In the deeper half |
| 5.71-9.65% | 25th pctl to 90th pctl | 11.3% | TRAIL STOP — Significant giveback |
| 9.65%+ | Past 90th pctl | 7.4% | EXIT — Only 10% of events get here |

**Source:** Section B1 distribution

---

### RULE 7: Trailing Stops Must Scale to Gap Size

A fixed trail stop is wrong. Here's why:

| Gap | 3.5% trail as % of gap | What happens |
|---|---|---|
| 3% gap | 117% of gap | Trail fires AFTER gap is completely erased — too late |
| 5% gap | 70% of gap | Trail fires when most of gap is gone — too late |
| 8% gap | 44% of gap | Reasonable |
| 12% gap | 29% of gap | Normal pullback — too tight, stops you out of winners |

**Data-justified trail stops (from HoD):**
| Gap Bucket | Trail Stop | Rationale | Source |
|---|---|---|---|
| 2-5% | 3.5% | Tighter moves, median HoD drawdown applies | B1 |
| 5-8% | 5.0% | Sweet spot, needs room for E3. Median MAE at E1 = -2.85% | Section E (5-8%) |
| 8-12% | 6.5% | Wide ATR. Median MAE at E1 = -4.09% | Section E (8-12%) |
| 12%+ | 5.0% | Tops fast (85min), but pullbacks are large. Median MAE at E1 = -5.44% | Section E (12%+), D3 |

---

### RULE 8: The E3 Entry Is the Best Trade in the Dataset

| Metric | E1 (Breakout) | E2 (First PB) | E3 (Deep PB) | Source |
|---|---|---|---|---|
| Win Rate | 51.0% | 50.1% | **69.2%** | Section E |
| Avg Return | +0.43% | +0.32% | **+2.22%** | E |
| Median MAE | -2.29% | -1.67% | **-0.49%** | E |
| Median MFE | +1.88% | +1.66% | **+3.19%** | E |
| **Median R:R** | **0.82x** | **1.00x** | **6.47x** | E |

**By gap bucket — E3 only:**
| Gap Bucket | n | Win Rate | Avg Return | R:R | Source |
|---|---|---|---|---|---|
| 2-5% | 1,109 | 68.1% | +1.65% | 6.36x | Section E |
| **5-8%** | **211** | **73.9%** | **+3.65%** | **8.36x** | **E** |
| **8-12%** | **79** | **74.7%** | **+3.59%** | **9.71x** | **E** |
| 12%+ | 88 | 65.9% | +3.29% | 4.09x | E |

**THE RULE:** E3 (buying the deepest pullback between FT and session high) is a 69% win rate with 6.47x R:R. In the 5-8% gap bucket, it's 74% / 8.36x. In the 8-12% bucket, 75% / 9.71x. This IS the trade. The pullback after FT isn't the end — it's the entry.

---

### RULE 9: Once HoD Is Set, It's Usually Done

| Stat | Value | Source |
|---|---|---|
| Multiple HoD attempts (touch, retreat >1%, return) | 9.9% | Section B2 |

**THE RULE:** Only 1 in 10 events makes a second run at the session high. If price pulls back from HoD by more than 1%, the odds are 90% that the high is in. This is NOT a pullback-to-buy. This is a signal to manage the trade.

---

### RULE 10: MFE Capture at EOD = 62.6% — The Fade Is Real

| Stat | Value | Source |
|---|---|---|
| Median MFE captured at EOD (winners) | 62.6% | Section D1 |

Even winning trades give back ~37% of their max move by close. A trailing stop based on HoD drawdown percentiles is superior to a time-based exit.

---

---

## PART 2: SHORT CONTINUATION RULES (Gap-Down ≥ 2%)

### Study Population
| Filter | Count |
|---|---|
| Total gap-down events (qualified) | 1,861 |
| Continuation days (close below entry) | 844 (45.4%) |
| V-bottom days (close above entry) | 1,017 (54.6%) |
| Unique tickers | 228 |

### Qualification Criteria (MUST have all three):
1. Gap ≤ −2% (today's open vs yesterday's close)
2. First 5-min candle is NOT bullish (close > open AND body > 40% of range)
3. Follow-through: a 5-min bar closes at or below Open − (ATR₁₄ × 0.40)

---

### RULE 11: Shorts Are Harder — 45.4% Win Rate, 0.97 R:R (All Events)

| Metric (All Events) | Value | Source |
|---|---|---|
| EOD Win Rate (short) | 45.4% | Finding 1 |
| Avg EOD Return | −0.28% (profit) | Finding 1 |
| Avg Winner | +2.58% | Finding 4 |
| Avg Loser | −2.65% | Finding 4 |
| R:R | 0.97:1 | Finding 4 |

**But on continuation days only:**
| Metric (Continuation Only, n=844) | Value | Source |
|---|---|---|
| Median EOD Return (profit) | +1.58% | Deep Dive §5 |
| Mean EOD Return (profit) | +2.58% | §5 |
| Median R:R (MFE/MAE) | 2.37x | §5 |
| Median MFE | +2.88% | §5 |
| Median MAE | +1.22% | §5 |

**THE RULE:** The all-events win rate is 45.4%, but that includes V-bottoms. Your job is to identify whether you're on a continuation day early enough to benefit from the 2.37x R:R.

---

### RULE 12: LoD Timing Is the #1 Differentiator Between Continuation and V-Bottom

| Metric | Continuation (n=844) | V-Bottom (n=1,017) | Source |
|---|---|---|---|
| Median LoD | **315 min (5h 15m)** | 65 min | Deep Dive §3 |
| LoD < 30 min | 2.5% | 33.9% | §3 |
| LoD > 4 hours | **68.4%** | 18.1% | §3 |
| LoD in last hour | **46.3%** | 8.7% | §3 |
| LoD in last 30 min | **35.4%** | — | §3 |

**THE RULE:**
- If LoD is set in the **first 30 min**: only 2.5% of continuation days do this. You're almost certainly on a V-bottom. EXIT.
- If LoD is **still being refreshed after 2 hours**: you're likely on a continuation day (68.4% make their LoD after 4 hours).
- If it's 2 PM CT and the stock is still making new lows: **46.3% of continuation days make their LoD in the final hour.** HOLD.

---

### RULE 13: HoD Timing Tells You If the Short Is Real

| Metric | Continuation (n=844) | V-Bottom (n=1,017) | Source |
|---|---|---|---|
| Median HoD | **0 min (the open)** | 35 min | Deep Dive §4 |
| HoD in first 5 min | **71.9%** | 37.4% | §4 |
| HoD in first 30 min | **87.7%** | 49.1% | §4 |
| HoD in last hour | **0.0%** | 16.7% | §4 |

**THE RULE:**
- If HoD is the open (first 5 min): 71.9% of continuation days show this. The stock never bounces meaningfully. **This is the strongest confirmation signal.**
- If HoD forms after 30 min: only 12.3% of continuation days do this. You're increasingly likely on a V-bottom.
- If HoD is in the last hour: **0.0% of continuation days show this.** If price is making new highs in the afternoon, your short is dead. EXIT.

---

### RULE 14: Bounces Are Normal — Even on Continuation Days

**All events:**
| Stat | Value | Source |
|---|---|---|
| Price bounces above entry after FT | 93.9% | Finding 4 |
| Bounce above entry BEFORE making LoD | 85.6% | Finding 4 |
| Median bounce depth before LoD | +0.59% | Finding 4 |
| Mean bounce depth before LoD | +1.07% | Finding 4 |
| 90th pctl bounce before LoD | +2.75% | Finding 4 |

**Continuation days only:**
| Stat | Value | Source |
|---|---|---|
| Bounce above entry before LoD | 84.7% | Deep Dive §6 |
| Median bounce depth | +0.66% | §6 |
| Mean bounce depth | +1.16% | §6 |
| 90th pctl bounce | +2.97% | §6 |

**Bounce depth distribution (continuation days):**
| Depth | % of Events | Source |
|---|---|---|
| 0-0.5% | 30.8% | §6 |
| 0.5-1.0% | 19.4% | §6 |
| 1.0-2.0% | 19.2% | §6 |
| 2.0-3.0% | 8.4% | §6 |
| 3.0-5.0% | 6.5% | §6 |
| 5.0%+ | 3.2% | §6 |

**THE RULE:** On continuation days, 84.7% bounce above entry before making LoD. HALF of those bounces are under 0.5%. Another 19% are under 1%. A 1% bounce above entry is NOT a failed short — it's what 50% of continuation days look like. Don't cover at the first green tick.

---

### RULE 15: Short Bounce Thresholds — Know Your Zones

**All events (for the indicator — since you don't know if it's continuation yet):**
| Depth | What It Means | % Context | Action |
|---|---|---|---|
| < 0.59% | Below median pre-LoD bounce | ~50% of continuation days | HOLD — Short is working |
| 0.59-2.15% | Median pre-LoD to median MAE | Normal range | HOLD — 86% bounce before LoD |
| 2.15-3.12% | Median to mean MAE | Above average bounce | MONITOR LoD freshness |
| 3.12-cover% | Mean MAE to bucket threshold | Elevated | TIGHTEN |
| > cover% | Past bucket threshold | Top 10-20% of bounces | THESIS IN QUESTION |

**Cover stops by gap size:**
| Gap Bucket | Cover Stop | Median MAE (all events) | Source |
|---|---|---|---|
| 2-3% | 4.0% | +1.69% | Finding 5 |
| 3-5% | 4.5% | +2.18% | Finding 5 |
| 5-8% | 5.5% | +2.76% | Finding 5 |
| 8-12% | 7.0% | +3.44% | Finding 5 |
| 12-20% | 7.5% | +4.72% | Finding 5 |
| 20%+ | 5.5% | +6.87% | Finding 5 |

**THE RULE:** A 3.5% bounce on a 2-3% gap is a 117% retrace — the thesis is likely dead. A 3.5% bounce on an 8-12% gap is a 29-44% retrace — completely normal noise.

---

### RULE 16: V-Bottom Detection — Early Warning Signs

| Signal | Stat | Implication | Source |
|---|---|---|---|
| LoD set in first 30 min | 86.9% of these are V-bottoms | EXIT if LoD < 30 min and bouncing | Finding 6 |
| Price above open within 30 min | V-bottom forming | EXIT immediately | Finding 6 |
| HoD NOT in first 5 min | Drops continuation odds from 71.9% to baseline | Lower confidence | §4 |
| No new lows after 60 min, LoD < 30 min | 87% V-bottom | EXIT | §3 comparison |

**THE RULE:** If LoD was set in the first 30 minutes and you're now 60+ minutes in with no new lows, you are on a V-bottom day 87% of the time. Get out.

---

### RULE 17: Late LoD = Short Is Working

| Stat | Value | Source |
|---|---|---|
| When LoD > 4 hours from open | 75.8% short win rate | Finding 6 |
| Continuation days with LoD after 4 hours | 68.4% | Deep Dive §3 |
| Continuation days with LoD in last hour | 46.3% | §3 |
| Continuation days with LoD in last 30 min | 35.4% | §3 |

**THE RULE:** If the stock is still making new lows at 12:30 PM CT (2 hours in), you're probably on a continuation day. If still making new lows at 2:00 PM CT, the win rate jumps to 75.8%. HOLD. Be patient.

---

### RULE 18: How Long to Hold a Short

Continuation day LoD timing:
| Time Horizon | % of Continuation LoDs Captured | Source |
|---|---|---|
| First 30 min | 2.5% (almost none — too early to trail) | §3 |
| First 60 min | 6.0% | §3 |
| First 2 hours | 16.2% | §3 |
| After 4 hours | 68.4% | §3 |
| Last hour (2-3 PM CT) | 46.3% | §3 |

Time from FT entry to LoD (continuation days):
| Metric | Value | Source |
|---|---|---|
| Median time FT → LoD | 200 min (3h 20m) | §10 |
| < 30 min after FT | 8.5% | §10 |
| < 2 hours after FT | 31.9% | §10 |
| > 4 hours after FT | 41.8% | §10 |

**THE RULE:**
- **Too early to cut:** Before 2 hours after FT. Only 31.9% of continuation LoDs have been made by then.
- **Hold zone:** 2-4 hours after FT. The move is building.
- **Sweet spot:** If still making lows at 4+ hours, you have a 75.8% WR trade.
- **MFE capture:** Continuation days capture 66.7% of MFE at EOD (median). The fade from LoD is smaller than longs (median EOD capture = 66.7% vs 62.6% for longs).

---

### RULE 19: Gap Size Matters for Shorts Too

| Gap Bucket | n | WR | Avg Return | Med MAE | Med MFE | Med LoD | Source |
|---|---|---|---|---|---|---|---|
| 2-3% | 820 | 44.0% | −0.41% | +1.69% | +1.11% | 180m | Finding 5 |
| 3-5% | 630 | 44.8% | −0.36% | +2.18% | +1.47% | 170m | Finding 5 |
| 5-8% | 248 | 43.5% | −0.47% | +2.76% | +1.98% | 135m | Finding 5 |
| **8-12%** | **91** | **56.0%** | **+0.99%** | +3.44% | +3.97% | 230m | **Finding 5** |
| **12-20%** | **51** | **64.7%** | **+1.60%** | +4.72% | +4.07% | 205m | **Finding 5** |
| 20%+ | 21 | 42.9% | −0.42% | +6.87% | +3.80% | 90m | Finding 5 |

**Continuation days only:**
| Gap Bucket | n | Rate | Avg Return | Med MFE | Med MAE | Med LoD | Source |
|---|---|---|---|---|---|---|---|
| 2-3% | 361 | 44.0% | +1.80% | +2.38% | +0.97% | 315m | Deep Dive §2 |
| 3-5% | 282 | 44.8% | +2.43% | +2.57% | +1.12% | 322m | §2 |
| 5-8% | 108 | 43.5% | +3.22% | +3.92% | +1.45% | 325m | §2 |
| **8-12%** | **51** | **56.0%** | **+4.40%** | +5.05% | +2.61% | 295m | **§2** |
| 12-20% | 33 | 64.7% | +6.00% | +5.01% | +4.02% | 270m | §2 |
| 20%+ | 9 | 42.9% | +7.78% | +6.06% | +2.15% | 205m | §2 |

**THE RULE:**
- **2-5% gaps:** 44% WR, modest return. These are the bread-and-butter but require patience (LoD at 315-322 min on continuation days).
- **5-8% gaps:** Similar WR but larger MFE (+3.92% on continuation). Higher MAE (+1.45%) means wider stops needed.
- **8-12% gaps:** **56% WR = the short sweet spot.** +4.40% avg return on continuation. But MAE is +2.61% — you MUST give room.
- **12-20% gaps:** Highest WR (64.7%) but small sample (n=33 continuation). Huge MAE (+4.02%).
- **20%+ gaps:** Tiny sample. Behave erratically. 42.9% WR despite massive gap.

---

### RULE 20: Combined Filter Stack — Highest-Edge Short Setups

From the deep dive's filter analysis (all events):
| Filter | n | WR | Avg Return | R:R | Source |
|---|---|---|---|---|---|
| No filter (baseline) | 1,861 | 45.4% | −0.28% | 0.69x | §8 |
| Gap 8%+ + Bearish candle | 88 | **56.8%** | **+1.24%** | 0.81x | §8 |
| Gap 8%+ + FT < 15 min | 89 | **56.2%** | **+1.43%** | 0.76x | §8 |
| Gap 12%+ + FT < 15 min + Bearish | 33 | **60.6%** | **+2.11%** | 0.51x | §8 |
| No bounce above entry before LoD | 268 | 48.1% | +0.22% | **1.41x** | §8 |

**THE RULE:** The highest-probability short setup is: gap ≥ 8% + bearish first candle + FT in first 15 min. This gives 56-61% WR. The best R:R filter is "no bounce above entry before LoD" at 1.41x — but you can't know this in real-time. Use HoD timing as a proxy (HoD in first 5 min = 71.9% of continuation days).

---

## PART 3: INDICATOR ALIGNMENT CHECKLIST

### Labels That Should Fire (and When)

| Condition | Label | Color | Rationale |
|---|---|---|---|
| No gap ≥ 2% | "NO QUALIFYING GAP — DATA DOES NOT APPLY" | Gray | Stats come from ≥2% gaps only |
| Contrary first candle | "CONTRARY CANDLE — EXCLUDED FROM STUDY" | Gray | Bearish on gap-up / bullish on gap-down excluded |
| Pre-FT | "AWAITING FT at [level]" | Yellow | No study labels until FT confirmed |
| FT confirmed + qualified | "QUALIFIED [LONG/SHORT] \| Gap X% \| [BUCKET]" | Green | All study labels now active |

### Long Pullback Zones (post-FT)

| Zone | From Entry | From HoD | Label Color | Action |
|---|---|---|---|---|
| Normal | < 0.51% | < 1.18% | Green | HOLD |
| Median | 0.51-1.18% | 1.18-2.87% | Green | HOLD — E3 forming zone |
| Elevated | — | 2.87-trail% | Yellow/Orange | MONITOR HoD freshness |
| Trail | — | > trail% (gap-adaptive) | Red | EXIT |

### Short Bounce Zones (post-FT)

| Zone | Bounce Against | Label Color | Action |
|---|---|---|---|
| Normal | < 0.59% | Green | HOLD — Short working |
| Expected | 0.59-2.15% | Light Green | HOLD — 86% bounce before LoD |
| Median MAE | 2.15-3.12% | Yellow | MONITOR — At median |
| Elevated | 3.12-cover% | Orange | TIGHTEN |
| Failed | > cover% (gap-adaptive) | Red | THESIS IN QUESTION |

---

## PART 4: WHEN IT'S TOO EARLY TO CUT

### LONGS — Don't Exit If:
| Situation | Why | Data |
|---|---|---|
| < 30 min after FT, pullback < 2.83% | 81.3% of deepest pullbacks form in first 30 min. This IS E3. | A3 |
| Pullback < 1% at any time | 66.8% of all pullbacks stay within 1%. | A2 |
| Before noon CT with 5-8% gap | Median HoD = 12:00 CT for this bucket. | D3 |
| HoD just set and pullback < 2.87% | Median drawdown from HoD = 2.87%. You're in the normal half. | B1 |
| Before 11:30 CT for any gap | 48.9% of HoDs happen after 11:30 CT. | B3 |

### SHORTS — Don't Cover If:
| Situation | Why | Data |
|---|---|---|
| < 60 min after FT, bounce < 2.15% | Median MAE = 2.15%. Most shorts bounce this much. | Finding 4 |
| Bounce < 0.59% at any time | Below median pre-LoD bounce. Short is working. | Finding 4 |
| Still making new lows at 2+ hours | 68.4% of continuation LoDs are after 4 hours. | §3 |
| HoD was in first 5 min | 71.9% of continuation days: HoD = the open. | §4 |
| Before 4 hours on 8-12% gap | Median continuation LoD = 295 min for this bucket. | §2 |

### LONGS — CUT If:
| Situation | Why | Data |
|---|---|---|
| Drawdown from HoD > gap-adaptive trail | Past 75th pctl of drawdown for that gap bucket | B1 |
| HoD set > 90 min ago + mature zone | Only 9.9% make second run at HoD | B2 |
| Pullback > 2.83% from entry | Past 90th pctl pullback from entry | A2 |
| 12%+ gap and HoD set at 85+ min | Median HoD for 12%+ = 85 min. It's done. | D3 |

### SHORTS — COVER If:
| Situation | Why | Data |
|---|---|---|
| LoD set in first 30 min + no new lows at 60 min | 86.9% V-bottom rate | Finding 6 |
| Price above open in first 30 min | V-bottom forming | Finding 6 |
| Bounce > gap-adaptive cover stop | Past 80th+ pctl MAE for that bucket | Finding 5 |
| HoD NOT in first 5 min + LoD < 30 min | Both continuation signals missing | §3, §4 |
| No new lows after 2+ hours + LoD was < 30 min | 87% V-bottom | §3 |

---

## Appendix: Source File Reference

| File | What It Contains |
|---|---|
| `studies/gap_execution_blueprint/outputs/extended_summary_stats.txt` | Sections A-E: pullback, HoD, entry timing, hold time |
| `studies/gap_execution_blueprint/outputs/rr_comparison_table.csv` | E1/E2/E3 by gap bucket |
| `studies/gap_execution_blueprint/README.md` | Full long-side findings narrative |
| `studies/gap_down_execution_blueprint/outputs/base_study_summary.txt` | Findings 1-6: all events |
| `studies/gap_down_execution_blueprint/outputs/continuation_day_deep_dive.txt` | §1-10: continuation vs V-bottom split |
| `studies/gap_down_execution_blueprint/outputs/continuation_events_only.csv` | Raw continuation day event data |
