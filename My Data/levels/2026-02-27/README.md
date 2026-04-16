# Weekly Levels & Volatility Briefing — DELL & RUN

**Date:** February 27, 2026 (Thursday)  
**Week of:** March 2–6, 2026  
**Source:** QuantLab Levels Engine (Alpaca options + SEC EDGAR) + yfinance  
**Generated:** 2026-02-27 ~12:40 CT (RTH session)

---

## DELL — Dell Technologies

### Snapshot

| Metric | Value |
|:-------|------:|
| **Spot** | $147.12 |
| **ATM IV** (Mar 20 monthly) | 49.4% |
| **HV10 / HV20 / HV30 / HV60** | 62.5% / 58.9% / 55.0% / 46.5% |
| **IV − HV20 Premium** | **−9.5%** (IV is CHEAP vs realized) |
| **IV / HV20 Ratio** | 0.84x |
| **IV Percentile Rank** | 59th (vs HV20 history) |
| **HV20 Percentile Rank** | 82nd |
| **Short Interest** | 27.4M shares (9.3% of float) |
| **Days to Cover** | 3.5 |
| **Gamma Regime** | **TRANSITION ZONE** |

### IV Context

- IV at 49.4% is **below realized volatility** (HV20 = 58.9%). Options are underpricing recent moves.
- DELL has averaged **2.9% absolute daily returns** and a **4.7% daily H-L range** over the past 20 sessions.
- 20-day range: $111.20 – $128.06 (15.2% range). Largest single-day move: −9.1%.
- IV rank at 59th percentile suggests vol is **middling historically** — not at extremes.
- Short interest at 9.3% is moderate — not a squeeze candidate but short sellers are present.

### Expected Move (from 49.4% ATM IV)

| Timeframe | ±1σ Move | 1σ Range | 2σ Range (95%) |
|:----------|:---------|:---------|:---------------|
| **1 Day** | ±$4.57 (3.1%) | $142.55 – $151.69 | $138.0 – $156.3 |
| **1 Week** | ±$10.05 (6.8%) | $137.07 – $157.17 | $127.0 – $167.2 |
| **Mar OPEX (21d)** | ±$17.41 (11.8%) | $129.71 – $164.53 | $112.3 – $182.0 |

**ATM Straddle** (Mar 20, $145 strike): $14.28 → straddle-implied EM ≈ ±$12.14

### Gamma Regime

**TRANSITION ZONE** — Spot ($147.12) sits between the $110 put wall and the $150 call wall, but is **close to the $150 call wall boundary**. This means:
- Dealer hedging flows can shift direction quickly around here.
- If $150 breaks and holds, dealers must chase → acceleration higher.
- If rejected at $150, gravity pulls back toward the $140 high-volume zone.
- $140 is the monster monthly strike: **15,000 OI** — acts as the "center of gravity."

### Key Options Levels

#### Call Walls (Resistance)

| Strike | Front OI | Front Vol | Monthly OI | Monthly Vol | Notes |
|-------:|---------:|----------:|-----------:|------------:|:------|
| **$148** | 94 | 2,384 | — | — | Near-spot resistance (front week) |
| **$149** | 2,398 | 1,653 | — | — | Dense call OI cluster |
| **$150** | 790 | 5,695 | 5,416 | 1,799 | **KEY LEVEL — call wall on both lenses** |
| **$155** | 316 | 1,120 | — | — | Secondary front-week wall |
| **$160** | 84 | 451 | 2,165 | 939 | Monthly call wall |
| **$165** | — | — | 2,191 | 1,567 | Monthly call wall |

#### Put Walls (Support)

| Strike | Front OI | Front Vol | Monthly OI | Monthly Vol | Notes |
|-------:|---------:|----------:|-----------:|------------:|:------|
| **$145** | 723 | 10,485 | 3,710 | 3,610 | High volume battle line |
| **$141** | 3,766 | 4,282 | — | — | Front-week step-change |
| **$140** | 1,473 | 6,852 | **15,000** | 3,740 | **MAJOR — highest monthly OI** |
| **$135** | 2,280 | 4,114 | 4,763 | 1,683 | Monthly step-change |
| **$130** | 4,635 | 5,624 | 4,853 | 1,270 | Secondary support cluster |
| **$120** | 1,576 | 717 | 8,754 | 1,182 | Deep monthly put wall |
| **$115** | 2,169 | 159 | 4,489 | 279 | |
| **$110** | 1,356 | 1,300 | **10,815** | 272 | **MAJOR — monthly put wall** |

### SEC Arb / Contractual Levels

**No verified arb structures found** in recent SEC EDGAR filings (last 45 days).

### Strike-to-Strike Paths

- **UPSIDE (front):** $147.12 → $148 → $149 → $150 → $155 → $160
- **UPSIDE (monthly):** $147.12 → $150 → $160 → $165
- **DOWNSIDE (front):** $147.12 → $145 → $141 → $140 → $136 → $135
- **DOWNSIDE (monthly):** $147.12 → $145 → $140 → $135 → $131 → $130

### Verdict

- **Regime:** MIXED
- **Path of least resistance:** UP toward $148
- **Regime flip:** Structure flips if $148 breached (dealer hedging reversal)

### How to Reverse Engineer DELL Price Action

1. **Watch $145–$150** — this is the decision range. 30,529+ contracts on the front-week at $145 (HIGH VOLUME) and $149–$150 (CALL WALLS).
2. **$150 breach = acceleration** — dealers forced to buy, momentum chasers pile in, next stop $155.
3. **$145 rejection = fade to $140** — the $140 strike has 15,000 OI (monthly) and is the gravitational center.
4. **IV is cheap** — if vol expands further, option prices are underpriced. A vol seller's nightmare if DELL keeps moving 3%+ daily.
5. **Earnings context** — DELL reports around this time. If earnings have passed and IV hasn't crushed, there's residual premium. If upcoming, the 49.4% IV includes earnings premium.

---

## RUN — Sunrun Inc.

### Snapshot

| Metric | Value |
|:-------|------:|
| **Spot** | $12.68 |
| **ATM IV** (Mar 20 monthly) | 99.9% |
| **HV10 / HV20 / HV30 / HV60** | 51.3% / 81.3% / 76.4% / 71.6% |
| **IV − HV20 Premium** | **+18.6%** (IV is EXPENSIVE vs realized) |
| **IV / HV20 Ratio** | 1.23x |
| **IV Percentile Rank** | 78th (vs HV20 history) |
| **HV20 Percentile Rank** | 51st |
| **Short Interest** | **58.9M shares (31.8% of float)** ⚠️ |
| **Days to Cover** | **6.8** ⚠️ |
| **Gamma Regime** | **NEUTRAL/POSITIVE GAMMA** |

### IV Context

- IV at 99.9% is **significantly above realized** (HV20 = 81.3%). Options are pricing ~19% more vol than the stock has been delivering.
- Call IV (101%) > Put IV (88.5%) → **call skew** — unusual, suggests demand for upside protection or speculative call buying.
- IV rank at 78th percentile: vol is elevated but not at the maximum.
- **31.8% short interest is EXTREME** — one of the most heavily shorted names. 6.8 days to cover means a short squeeze can take nearly a full week to unwind.
- The combination of **high IV + extreme SI + call skew** = the market is pricing in a potential squeeze or violent move higher.

### Expected Move (from 99.9% ATM IV)

| Timeframe | ±1σ Move | 1σ Range | 2σ Range (95%) |
|:----------|:---------|:---------|:---------------|
| **1 Day** | ±$0.80 (6.3%) | $11.88 – $13.48 | $11.08 – $14.28 |
| **1 Week** | ±$1.75 (13.8%) | $10.93 – $14.43 | $9.18 – $16.18 |
| **Mar OPEX (21d)** | ±$3.04 (24.0%) | $9.64 – $15.72 | $6.60 – $18.76 |

**ATM Straddle** (Mar 20, $13 strike): $2.31 → straddle-implied EM ≈ ±$1.96 → $10.72 – $14.64

### Gamma Regime

**NEUTRAL/POSITIVE GAMMA** — Spot ($12.68) sits between the $3 put wall and the $20 call wall with decent buffer to both. Dealer hedging dampens moves in this zone → **mean-reversion tendency**. However:
- The $15 strike has **14,718 volume** on the monthly — massive activity.
- The $14 strike has **5,432 OI** monthly — step-change where hedging intensity shifts.
- If $14–$15 breaks, we approach the call wall cluster ($18–$20) where dealers get forced.
- The $20 strike is the **major monthly call wall** at **14,551 OI**. This is the squeeze target.

### Key Options Levels

#### Call Walls (Resistance)

| Strike | Front OI | Front Vol | Monthly OI | Monthly Vol | Notes |
|-------:|---------:|----------:|-----------:|------------:|:------|
| **$13.00** | 34 | 1,658 | 2,341 | 1,563 | Step-change just above spot |
| **$13.50** | 4 | 2,822 | — | — | High volume front-week |
| **$14.00** | 1,089 | 2,743 | 5,432 | 1,077 | **Step-change — hedging inflection** |
| **$15.00** | 232 | 1,853 | 2,036 | **14,718** | **KEY — massive monthly volume** |
| **$17.00** | 962 | 689 | 2,381 | 139 | Step-change |
| **$18.00** | — | — | 3,896 | 1,526 | Monthly call wall |
| **$19.00** | 810 | 260 | 5,815 | 5,061 | Monthly call wall |
| **$19.50** | 1,290 | 1,207 | — | — | Front-week step-change |
| **$20.00** | **3,468** | 598 | **14,551** | 2,687 | **MAJOR CALL WALL — squeeze target** |
| **$21.00** | 1,054 | 128 | 3,146 | 2,055 | Above arb level |
| **$24.00** | 859 | 5 | 5,809 | 49 | Deep call wall |
| **$25.00** | 277 | 205 | **8,348** | 236 | Extreme upside wall |

#### Put Walls (Support)

| Strike | Front OI | Front Vol | Monthly OI | Monthly Vol | Notes |
|-------:|---------:|----------:|-----------:|------------:|:------|
| **$12.50** | 7 | 537 | — | — | Near-spot support |
| **$12.00** | 8 | 293 | 1,438 | 1,269 | Monthly step-change |
| **$11.00** | 6 | 60 | 358 | 64 | Monthly put wall |
| **$9.00** | — | — | 512 | 151 | Monthly put wall |
| **$8.00** | — | — | 715 | 40 | Monthly put wall |
| **$5.00** | 6 | 1 | 855 | 12 | Monthly put wall |
| **$3.00** | — | — | **2,819** | 3 | **Deep put wall / floor** |

### SEC Arb / Contractual Levels

| Level | Type | Filing | Date | Notes |
|------:|:-----|:-------|:-----|:------|
| **$21.10** | Cap/Floor | 10-K | 2026-02-26 | Contractual level from annual filing. **Structural participants may defend/press at this level.** |

This is a **verified SEC contractual level** just above the $20 call wall. Combined with the 14,551 OI at $20 and 3,146 OI at $21, the **$20–$21.10 zone is the maximum structural resistance** on RUN.

### Strike-to-Strike Paths

- **UPSIDE (front):** $12.68 → $13.00 → $13.50 → $14.00 → $14.50 → $15.00
- **UPSIDE (monthly):** $12.68 → $13.00 → $14.00 → $15.00 → $16.00 → $17.00
- **DOWNSIDE (front):** $12.68 → $12.50 → $12.00 → $11.00 → $5.00
- **DOWNSIDE (monthly):** $12.68 → $12.00 → $11.00 → $9.00 → $8.00 → $5.00

### Verdict

- **Regime:** MIXED
- **Path of least resistance:** DOWN toward $12.50
- **Regime flip:** Structure flips if $12.50 breached

### How to Reverse Engineer RUN Price Action

1. **$12.50 is the inflection** — put wall support. Below = acceleration lower toward $11.00.
2. **$13–$14 is the battle zone** — 1,658 + 2,822 + 2,743 volume on front-week. Price needs to clear $14 to signal bullish continuation.
3. **$15 monthly volume (14,718) is the tell** — this is where the action is being priced. A move through $15 with conviction activates the call wall chain to $17→$18→$19→$20.
4. **$20 + $21.10 SEC arb = terminus** — 14,551 call wall OI + SEC contractual cap. This is the max pain / squeeze target. Shorts covering 58.9M shares (6.8 days) would mechanically push toward this zone.
5. **IV is expensive** at 99.9% vs 81.3% realized. Option sellers are betting on mean-reversion. If the stock stays calm (<5% daily), premium sellers win. But with 31.8% SI, any catalyst can blow through realized → options become cheap in a hurry.
6. **Call skew is unusual** — Call IV 101% vs Put IV 88.5%. Smart money or spec flow is bidding calls. In a typical name, puts are more expensive. This inversion flags **directional demand for upside**.

---

## Side-by-Side Comparison

| Metric | DELL | RUN |
|:-------|-----:|----:|
| Spot | $147.12 | $12.68 |
| ATM IV | 49.4% | 99.9% |
| HV20 | 58.9% | 81.3% |
| IV − HV20 | −9.5% | +18.6% |
| IV Rank | 59th | 78th |
| Short % Float | 9.3% | **31.8%** ⚠️ |
| Days to Cover | 3.5 | **6.8** ⚠️ |
| Gamma Regime | Transition | Neutral/Positive |
| Daily EM | ±$4.57 (3.1%) | ±$0.80 (6.3%) |
| Weekly EM | ±$10.05 (6.8%) | ±$1.75 (13.8%) |
| Major Support | $140 (15K OI) | $12.00–$12.50 |
| Major Resistance | $150 (call wall) | $20 (14.5K OI) + $21.10 (SEC) |
| SEC Arb Level | None found | $21.10 (10-K) |

## Key Themes for the Coming Week

### DELL
- **IV is cheap** — if the stock keeps moving 3%+ daily, options are underpriced. Advantage: long premium.
- **$150 is THE level.** Break = dealer chase toward $155–$160. Reject = gravity to $140.
- **Moderate SI (9.3%)** — not a squeeze setup, but shorts add fuel if $150 breaks.
- **Earnings proximity** — check if DELL has reported. If pre-earnings, IV includes premium. Post-earnings = crush.

### RUN
- **Short squeeze candidate** — 31.8% SI + 6.8 days to cover + call skew + massive OI at $20.
- **IV is expensive** — selling premium works if the stock doesn't move. But with that SI, any catalyst ignites a squeeze.
- **$14–$15 is the trigger zone.** Through $15 = chain reaction to $17→$18→$19→$20.
- **$21.10 SEC arb = hard cap.** Even in a squeeze, structural sellers likely defend here.
- **Call skew tells you something** — call IV > put IV is rare and suggests directional demand for upside hedging or speculation.

---

*Generated by QuantLab Levels Engine + scratch analysis scripts.*  
*Data sources: Alpaca (options/spot), SEC EDGAR (arb levels), yfinance (SI, historical OHLCV).*  
*Reports: `data/levels/2026-02-27/`*
