# Opening Candle Strength × Gap Regime Study
**Generated:** 2026-03-09 12:55
**Purpose:** Final data layer for ATR_MOOOVVVEE_INDICATOR rewrite

## Study Design

### Questions Answered
1. Does a MAX BULLISH (TrendStrength cs≥70) bar-1 on gap-downs produce better outcomes than regular bullish/neutral/bearish?
2. Which gap regimes (2-5%, 5-8%, 8-12%, 12%+) benefit most from max bullish opens?
3. When bar-1 is bearish but price still hits reverse FT (0.4×ATR), what are the HOD/LOD and win rates?
4. Full HOD/LOD profile for all 5 candle tiers — raw % AND ATR-normalized
5. Ultimate regime summary for direct indicator integration

### Methodology
- **Universe:** 235 tickers, 1034 unique dates
- **Total events:** 11733 (5216 gap-downs, 6517 gap-ups)
- **Period:** 2024-01-22 to 2026-03-06 05:00:00+00:00
- **Gap threshold:** ≥2% absolute
- **Bar-1:** First 5-min candle of session (9:30-9:35 ET)
- **Candle tiers:** 5-tier classification using body ratio (>40%) + TrendStrength cs score
- **Win:** Close > Open for gap-downs (rally), Close < Open for gap-ups (fade)
- **FT threshold:** 0.40 × ATR14
- **HOD/LOD:** Both raw % from open AND ATR-normalized

### Candle Tier Definitions
| Tier | Criteria |
|------|----------|
| MAX_BULLISH | cs ≥ 70, body > 40%, close > open |
| BULLISH | cs < 70, body > 40%, close > open |
| NEUTRAL | body ≤ 40% of range (any cs) |
| BEARISH | cs > -70, body > 40%, close < open |
| MAX_BEARISH | cs ≤ -70, body > 40%, close < open |

---

## Table 1: Gap-Down × Opening Candle Tier

**Question:** Does MAX_BULLISH bar-1 on gap-downs predict better bounce outcomes?

| Candle Tier | n | Win Rate | Avg EOD Ret | Avg HOD% | Avg LOD% | HOD (ATR) | LOD (ATR) | Med HOD Min | Med LOD Min | FT Fire% |
|-------------|---|----------|-------------|----------|----------|-----------|-----------|-------------|-------------|----------|
| MAX_BULLISH | 78 | 66.7% | +1.866% | 5.606% | 2.261% | 0.656 | 0.246 | 85 | 35 | 59.0% |
| BULLISH | 1547 | 67.6% | +1.541% | 4.488% | 1.726% | 0.682 | 0.241 | 80 | 20 | 64.1% |
| NEUTRAL | 2013 | 53.2% | +0.265% | 2.932% | 2.573% | 0.473 | 0.405 | 85 | 50 | 0.0% |
| BEARISH | 795 | 36.7% | -1.311% | 2.018% | 4.106% | 0.324 | 0.605 | 45 | 45 | 59.2% |
| MAX_BEARISH | 783 | 36.5% | -1.325% | 2.112% | 4.510% | 0.317 | 0.686 | 50 | 45 | 63.9% |

**Key Insight:** MAX_BULLISH win rate = 66.7% vs BULLISH = 67.6% (-0.9 pp)

---

## Table 2: Gap-Up × Opening Candle Tier

**Question:** Does MAX_BEARISH bar-1 on gap-ups predict better fade outcomes?

| Candle Tier | n | Win Rate | Avg EOD Ret | Avg HOD% | Avg LOD% | HOD (ATR) | LOD (ATR) | Med HOD Min | Med LOD Min | FT Fire% |
|-------------|---|----------|-------------|----------|----------|-----------|-----------|-------------|-------------|----------|
| MAX_BEARISH | 131 | 66.4% | +2.263% | 2.462% | 5.913% | 0.320 | 0.868 | 20 | 70 | 69.5% |
| BEARISH | 2030 | 67.3% | +1.461% | 2.068% | 4.455% | 0.302 | 0.721 | 25 | 65 | 64.2% |
| NEUTRAL | 2569 | 50.6% | -0.002% | 3.212% | 2.960% | 0.511 | 0.505 | 55 | 70 | 0.0% |
| BULLISH | 943 | 35.0% | -2.333% | 5.773% | 1.977% | 0.857 | 0.311 | 65 | 30 | 69.4% |
| MAX_BULLISH | 844 | 33.3% | -2.486% | 6.047% | 1.866% | 0.871 | 0.294 | 60 | 30 | 71.6% |

**Key Insight:** MAX_BEARISH win rate = 66.4% vs BEARISH = 67.3% (-0.9 pp)

---

## Table 3: Gap-Down — Regime × Candle Cross-Tab

**Question:** In which gap regimes does MAX_BULLISH perform best?

### Gap-Down 2-5%
| Candle Tier | n | Win Rate | Avg EOD Ret | HOD (ATR) | LOD (ATR) | FT Fire% |
|-------------|---|----------|-------------|-----------|-----------|----------|
| MAX_BULLISH | 68 | 64.7% | +1.597% | 0.654 | 0.258 | 58.8% |
| BULLISH | 1209 | 67.7% | +1.324% | 0.654 | 0.234 | 62.9% |
| NEUTRAL | 1617 | 53.4% | +0.318% | 0.458 | 0.386 | 0.0% |
| BEARISH | 679 | 36.7% | -1.157% | 0.308 | 0.583 | 58.0% |
| MAX_BEARISH | 597 | 38.5% | -0.810% | 0.312 | 0.633 | 61.5% |

### Gap-Down 5-8%
| Candle Tier | n | Win Rate | Avg EOD Ret | HOD (ATR) | LOD (ATR) | FT Fire% |
|-------------|---|----------|-------------|-----------|-----------|----------|
| MAX_BULLISH ❌INSUFF | 8 | 100.0% | +5.290% | 0.796 | 0.084 | 75.0% |
| BULLISH | 202 | 70.3% | +2.441% | 0.752 | 0.236 | 67.8% |
| NEUTRAL | 250 | 50.8% | +0.088% | 0.492 | 0.442 | 0.0% |
| BEARISH | 83 | 38.6% | -1.215% | 0.397 | 0.646 | 61.4% |
| MAX_BEARISH | 112 | 34.8% | -1.740% | 0.364 | 0.766 | 68.8% |

### Gap-Down 8-12%
| Candle Tier | n | Win Rate | Avg EOD Ret | HOD (ATR) | LOD (ATR) | FT Fire% |
|-------------|---|----------|-------------|-----------|-----------|----------|
| MAX_BULLISH ❌INSUFF | 1 | 0.0% | -2.637% | 0.232 | 0.540 | 0.0% |
| BULLISH | 69 | 56.5% | +1.759% | 0.813 | 0.314 | 69.6% |
| NEUTRAL | 92 | 56.5% | +0.132% | 0.604 | 0.497 | 0.0% |
| BEARISH | 20 | 15.0% | -4.229% | 0.275 | 0.964 | 80.0% |
| MAX_BEARISH | 40 | 25.0% | -3.588% | 0.307 | 0.925 | 70.0% |

### Gap-Down 12%+
| Candle Tier | n | Win Rate | Avg EOD Ret | HOD (ATR) | LOD (ATR) | FT Fire% |
|-------------|---|----------|-------------|-----------|-----------|----------|
| MAX_BULLISH ❌INSUFF | 1 | 0.0% | -2.764% | 0.130 | 0.471 | 0.0% |
| BULLISH | 67 | 67.2% | +2.513% | 0.858 | 0.315 | 68.7% |
| NEUTRAL | 54 | 51.9% | -0.295% | 0.581 | 0.643 | 0.0% |
| BEARISH ⚠️LOW | 13 | 61.5% | -5.476% | 0.740 | 0.968 | 76.9% |
| MAX_BEARISH | 34 | 20.6% | -6.334% | 0.258 | 1.064 | 82.4% |

---

## Table 4: Gap-Up — Regime × Candle Cross-Tab

**Question:** In which gap regimes does MAX_BEARISH perform best?

### Gap-Up 2-5%
| Candle Tier | n | Win Rate | Avg EOD Ret | HOD (ATR) | LOD (ATR) | FT Fire% |
|-------------|---|----------|-------------|-----------|-----------|----------|
| MAX_BEARISH | 109 | 67.9% | +2.422% | 0.282 | 0.866 | 72.5% |
| BEARISH | 1560 | 65.6% | +1.153% | 0.291 | 0.655 | 61.2% |
| NEUTRAL | 1991 | 50.3% | +0.039% | 0.471 | 0.464 | 0.0% |
| BULLISH | 771 | 35.5% | -1.822% | 0.783 | 0.305 | 67.4% |
| MAX_BULLISH | 615 | 33.7% | -1.963% | 0.784 | 0.277 | 69.6% |

### Gap-Up 5-8%
| Candle Tier | n | Win Rate | Avg EOD Ret | HOD (ATR) | LOD (ATR) | FT Fire% |
|-------------|---|----------|-------------|-----------|-----------|----------|
| MAX_BEARISH ⚠️LOW | 15 | 53.3% | +0.737% | 0.414 | 0.721 | 40.0% |
| BEARISH | 301 | 72.8% | +2.065% | 0.299 | 0.805 | 70.4% |
| NEUTRAL | 374 | 56.7% | +0.318% | 0.489 | 0.581 | 0.0% |
| BULLISH | 121 | 34.7% | -3.029% | 1.045 | 0.345 | 75.2% |
| MAX_BULLISH | 137 | 30.7% | -3.179% | 0.938 | 0.248 | 71.5% |

### Gap-Up 8-12%
| Candle Tier | n | Win Rate | Avg EOD Ret | HOD (ATR) | LOD (ATR) | FT Fire% |
|-------------|---|----------|-------------|-----------|-----------|----------|
| MAX_BEARISH ❌INSUFF | 6 | 66.7% | -0.201% | 0.782 | 1.122 | 83.3% |
| BEARISH | 102 | 71.6% | +2.473% | 0.319 | 0.924 | 73.5% |
| NEUTRAL | 116 | 44.0% | -0.568% | 0.765 | 0.658 | 0.0% |
| BULLISH | 38 | 31.6% | -4.943% | 1.270 | 0.337 | 78.9% |
| MAX_BULLISH | 49 | 38.8% | -3.888% | 1.027 | 0.444 | 79.6% |

### Gap-Up 12%+
| Candle Tier | n | Win Rate | Avg EOD Ret | HOD (ATR) | LOD (ATR) | FT Fire% |
|-------------|---|----------|-------------|-----------|-----------|----------|
| MAX_BEARISH ❌INSUFF | 1 | 100.0% | +22.559% | 0.258 | 1.665 | 100.0% |
| BEARISH | 67 | 76.1% | +4.374% | 0.555 | 1.577 | 94.0% |
| NEUTRAL | 88 | 39.8% | -1.568% | 1.168 | 0.899 | 0.0% |
| BULLISH ⚠️LOW | 13 | 15.4% | -18.530% | 2.248 | 0.244 | 100.0% |
| MAX_BULLISH | 43 | 30.2% | -6.167% | 1.731 | 0.513 | 90.7% |

---

## Table 5: Bearish/Bullish Bar-1 Reverse FT Analysis

**Question:** When bar-1 is bearish but price still hits the OPPOSITE FT level (0.4×ATR), what happens?

### Gap-Down
| Group | n | Win Rate | Avg EOD Ret | Avg HOD% | Avg LOD% | HOD (ATR) | LOD (ATR) | Med FT Min |
|-------|---|----------|-------------|----------|----------|-----------|-----------|------------|
| BEARISH_REVERSED | 428 | 84.6% | +2.649% | 5.013% | 2.339% | 0.831 | 0.412 | 90 |
| BEARISH_NOT_REVERSED | 1150 | 18.8% | -2.794% | 0.967% | 5.038% | 0.130 | 0.732 | — |
| BULLISH_REVERSED | 321 | 10.9% | -3.180% | 2.427% | 5.153% | 0.345 | 0.727 | 110 |
| BULLISH_NOT_REVERSED | 1304 | 81.4% | +2.722% | 5.063% | 0.915% | 0.764 | 0.122 | — |

### Gap-Up
| Group | n | Win Rate | Avg EOD Ret | Avg HOD% | Avg LOD% | HOD (ATR) | LOD (ATR) | Med FT Min |
|-------|---|----------|-------------|----------|----------|-----------|-----------|------------|
| BEARISH_REVERSED | 525 | 15.6% | -3.341% | 6.053% | 2.847% | 0.857 | 0.429 | 105 |
| BEARISH_NOT_REVERSED | 1636 | 83.9% | +3.066% | 0.820% | 5.088% | 0.125 | 0.827 | — |
| BULLISH_REVERSED | 471 | 83.7% | +2.663% | 3.035% | 4.901% | 0.500 | 0.810 | 85 |
| BULLISH_NOT_REVERSED | 1316 | 16.5% | -4.219% | 6.929% | 0.859% | 0.994 | 0.122 | — |

### Table 5B: TS Slope Filter on Reverse FT (Supplement)

**Question:** The raw reverse FT numbers don't account for TrendStrength line direction. If the TS line is sloping DOWN at the time the reverse FT fires, you can't take the long. What happens when we filter by TS slope?

**Methodology:** For each reverse FT event, we captured the `cs` value at the exact 5-min bar where the FT level was hit, plus the `cs` 5 bars (25 min) earlier. Slope = cs_at_FT − cs_prior. RISING = Δ > +10, FLAT = −10 to +10, FALLING = Δ < −10.

#### Gap-Down Bearish Bar-1 Reversed — by TS Slope at FT Trigger
| TS Slope | n | Win Rate | Avg EOD Ret | Avg cs @ FT |
|----------|---|----------|-------------|-------------|
| TS_RISING | 181 | 85.6% | +2.846% | +31.1 |
| TS_FLAT | 98 | 91.8% | +2.867% | +23.6 |
| TS_FALLING | 15 ⚠️LOW | 80.0% | +0.990% | -30.0 |
| UNKNOWN | 74 | 73.0% | +2.536% | -45.8 |

#### Gap-Down Bearish Bar-1 Reversed — by TS Level at FT Trigger
| TS Level | n | Win Rate | Avg cs @ FT |
|----------|---|----------|-------------|
| BULLISH (cs ≥ 40) | 150 | 90.7% | +87.3 |
| NEUTRAL (−15 to 40) | 70 | 90.0% | +12.1 |
| BEARISH (cs ≤ −15) | 146 | 76.0% | -66.7 |

#### Gap-Up Bullish Bar-1 Reversed — by TS Slope at FT Trigger
| TS Slope | n | Win Rate | Avg EOD Ret | Avg cs @ FT |
|----------|---|----------|-------------|-------------|
| TS_FALLING | 240 | 82.9% | +2.916% | -28.9 |
| TS_FLAT | 78 | 85.9% | +2.318% | -9.6 |
| TS_RISING | 7 ❌INSUFF | 71.4% | +0.706% | +37.9 |
| UNKNOWN | 84 | 79.8% | +2.471% | +24.9 |

#### Gap-Up Bullish Bar-1 Reversed — by TS Level at FT Trigger
| TS Level | n | Win Rate | Avg cs @ FT |
|----------|---|----------|-------------|
| BEARISH (cs ≤ −15) | 208 | 87.0% | -69.8 |
| NEUTRAL (−15 to 40) | 94 | 79.8% | +12.0 |
| BULLISH (cs ≥ 40) | 104 | 76.0% | +76.9 |

#### Tradeable Filter: TS Rising/Flat + FT Bar Bullish/Neutral
| Direction | Filter | n | Win Rate | Avg EOD Ret |
|-----------|--------|---|----------|-------------|
| Gap-Down (long) | TRADEABLE | 260 | 87.3% | +2.862% |
| Gap-Down (long) | NOT TRADEABLE | 108 | 77.8% | +2.356% |
| Gap-Up (short) | TRADEABLE | 305 | 83.3% | +2.750% |
| Gap-Up (short) | NOT TRADEABLE | 104 | 80.8% | +2.446% |

**Key Insight:** Your instinct is correct — filtering for TS rising/flat at FT trigger lifts gap-down reversal WR from 84.6% → **87.3%** (n=260) and drops the untradeable set to 77.8%. But the bigger filter is TS LEVEL: when the TS line is in bullish territory (cs ≥ 40) at the reversal moment, WR = **90.7%** (n=150). When TS is bearish territory at FT trigger, WR drops to 76.0% — still positive but a 14.7 pp penalty. The TS line turning is the confirmation. TS still pointing hard bearish (cs < -15) when FT fires = lower conviction, smaller size.

---

## Table 6: HOD/LOD Timing Profile by Candle Tier

**Question:** When does the session high/low get set, by candle type?

### Gap-Down — HOD Timing (% of events)
| Candle Tier | n | At Open | First 30min | First Hour | First 2Hr | Mid-Session | Last Hour |
|-------------|---|---------|-------------|------------|-----------|-------------|-----------|
| MAX_BULLISH | 78 | 20.5% | 10.3% | 14.1% | 10.3% | 24.4% | 20.5% |
| BULLISH | 1547 | 19.3% | 14.5% | 9.2% | 15.1% | 22.6% | 19.4% |
| NEUTRAL | 2013 | 22.7% | 12.9% | 8.6% | 11.6% | 24.0% | 20.2% |
| BEARISH | 795 | 36.1% | 9.6% | 8.1% | 10.4% | 17.2% | 18.6% |
| MAX_BEARISH | 783 | 38.6% | 8.2% | 5.6% | 12.0% | 17.8% | 17.9% |

### Gap-Down — LOD Timing (% of events)
| Candle Tier | n | At Open | First 30min | First Hour | First 2Hr | Mid-Session | Last Hour |
|-------------|---|---------|-------------|------------|-----------|-------------|-----------|
| MAX_BULLISH | 78 | 38.5% | 10.3% | 10.3% | 5.1% | 16.7% | 19.2% |
| BULLISH | 1547 | 44.9% | 10.2% | 6.5% | 6.5% | 14.6% | 17.3% |
| NEUTRAL | 2013 | 30.2% | 14.2% | 8.8% | 9.7% | 18.6% | 18.5% |
| BEARISH | 795 | 24.8% | 19.9% | 9.6% | 8.7% | 17.2% | 19.9% |
| MAX_BEARISH | 783 | 25.5% | 19.2% | 8.8% | 11.9% | 18.5% | 16.1% |

### Gap-Up — HOD Timing (% of events)
| Candle Tier | n | At Open | First 30min | First Hour | First 2Hr | Mid-Session | Last Hour |
|-------------|---|---------|-------------|------------|-----------|-------------|-----------|
| MAX_BULLISH | 844 | 21.4% | 19.5% | 10.2% | 10.3% | 18.1% | 20.4% |
| BULLISH | 943 | 23.3% | 16.0% | 9.1% | 11.3% | 19.9% | 20.3% |
| NEUTRAL | 2569 | 30.1% | 13.8% | 7.9% | 10.2% | 20.0% | 17.9% |
| BEARISH | 2030 | 41.7% | 11.1% | 6.5% | 7.2% | 16.5% | 17.0% |
| MAX_BEARISH | 131 | 48.1% | 6.1% | 4.6% | 6.9% | 18.3% | 16.0% |

### Gap-Up — LOD Timing (% of events)
| Candle Tier | n | At Open | First 30min | First Hour | First 2Hr | Mid-Session | Last Hour |
|-------------|---|---------|-------------|------------|-----------|-------------|-----------|
| MAX_BULLISH | 844 | 41.6% | 9.0% | 5.1% | 11.0% | 17.3% | 16.0% |
| BULLISH | 943 | 38.0% | 12.8% | 7.5% | 11.2% | 15.2% | 15.3% |
| NEUTRAL | 2569 | 24.6% | 13.8% | 9.8% | 12.5% | 19.4% | 19.8% |
| BEARISH | 2030 | 21.0% | 18.5% | 10.4% | 12.2% | 18.2% | 19.7% |
| MAX_BEARISH | 131 | 29.8% | 11.5% | 4.6% | 16.0% | 21.4% | 16.8% |

---

## Table 7: Ultimate Regime Summary (Indicator Lookup Table)

**This is the final cross-tab for ATR_MOOOVVVEE_INDICATOR integration.**

### Gap-Down
| Gap Bucket | Candle Tier | n | Win Rate | Avg EOD Ret | HOD (ATR) | LOD (ATR) | Med HOD Min | Med LOD Min | FT% | Rev FT% |
|------------|-------------|---|----------|-------------|-----------|-----------|-------------|-------------|-----|---------|
| 2-5% | MAX_BULLISH | 68 | 64.7% | +1.597% | 0.654 | 0.258 | 98 | 35 | 58.8% | 20.6% |
| 2-5% | BULLISH | 1209 | 67.7% | +1.324% | 0.654 | 0.234 | 80 | 20 | 62.9% | 19.5% |
| 2-5% | NEUTRAL | 1617 | 53.4% | +0.318% | 0.458 | 0.386 | 85 | 50 | 0.0% | 0.0% |
| 2-5% | BEARISH | 679 | 36.7% | -1.157% | 0.308 | 0.583 | 50 | 45 | 58.0% | 26.4% |
| 2-5% | MAX_BEARISH | 597 | 38.5% | -0.810% | 0.312 | 0.633 | 65 | 40 | 61.5% | 28.0% |
| 5-8% | MAX_BULLISH ❌INSUFF | 8 | 100.0% | +5.290% | 0.796 | 0.084 | 80 | 5 | 75.0% | 0.0% |
| 5-8% | BULLISH | 202 | 70.3% | +2.441% | 0.752 | 0.236 | 105 | 8 | 67.8% | 15.8% |
| 5-8% | NEUTRAL | 250 | 50.8% | +0.088% | 0.492 | 0.442 | 72 | 55 | 0.0% | 0.0% |
| 5-8% | BEARISH | 83 | 38.6% | -1.215% | 0.397 | 0.646 | 45 | 40 | 61.4% | 33.7% |
| 5-8% | MAX_BEARISH | 112 | 34.8% | -1.740% | 0.364 | 0.766 | 35 | 40 | 68.8% | 27.7% |
| 8-12% | MAX_BULLISH ❌INSUFF | 1 | 0.0% | -2.637% | 0.232 | 0.540 | 0 | 25 | 0.0% | 100.0% |
| 8-12% | BULLISH | 69 | 56.5% | +1.759% | 0.813 | 0.314 | 65 | 25 | 69.6% | 29.0% |
| 8-12% | NEUTRAL | 92 | 56.5% | +0.132% | 0.604 | 0.497 | 80 | 28 | 0.0% | 0.0% |
| 8-12% | BEARISH | 20 | 15.0% | -4.229% | 0.275 | 0.964 | 8 | 158 | 80.0% | 15.0% |
| 8-12% | MAX_BEARISH | 40 | 25.0% | -3.588% | 0.307 | 0.925 | 0 | 92 | 70.0% | 17.5% |
| 12%+ | MAX_BULLISH ❌INSUFF | 1 | 0.0% | -2.764% | 0.130 | 0.471 | 0 | 305 | 0.0% | 100.0% |
| 12%+ | BULLISH | 67 | 67.2% | +2.513% | 0.858 | 0.315 | 75 | 40 | 68.7% | 25.4% |
| 12%+ | NEUTRAL | 54 | 51.9% | -0.295% | 0.581 | 0.643 | 65 | 52 | 0.0% | 0.0% |
| 12%+ | BEARISH ⚠️LOW | 13 | 61.5% | -5.476% | 0.740 | 0.968 | 200 | 90 | 76.9% | 46.2% |
| 12%+ | MAX_BEARISH | 34 | 20.6% | -6.334% | 0.258 | 1.064 | 2 | 125 | 82.4% | 20.6% |

### Gap-Up
| Gap Bucket | Candle Tier | n | Win Rate | Avg EOD Ret | HOD (ATR) | LOD (ATR) | Med HOD Min | Med LOD Min | FT% | Rev FT% |
|------------|-------------|---|----------|-------------|-----------|-----------|-------------|-------------|-----|---------|
| 2-5% | MAX_BULLISH | 615 | 33.7% | -1.963% | 0.784 | 0.277 | 60 | 30 | 69.6% | 25.4% |
| 2-5% | BULLISH | 771 | 35.5% | -1.822% | 0.783 | 0.305 | 65 | 35 | 67.4% | 27.1% |
| 2-5% | NEUTRAL | 1991 | 50.3% | +0.039% | 0.471 | 0.464 | 55 | 75 | 0.0% | 0.0% |
| 2-5% | BEARISH | 1560 | 65.6% | +1.153% | 0.291 | 0.655 | 30 | 60 | 61.2% | 24.6% |
| 2-5% | MAX_BEARISH | 109 | 67.9% | +2.422% | 0.282 | 0.866 | 5 | 90 | 72.5% | 21.1% |
| 5-8% | MAX_BULLISH | 137 | 30.7% | -3.179% | 0.938 | 0.248 | 65 | 20 | 71.5% | 19.0% |
| 5-8% | BULLISH | 121 | 34.7% | -3.029% | 1.045 | 0.345 | 60 | 25 | 75.2% | 28.1% |
| 5-8% | NEUTRAL | 374 | 56.7% | +0.318% | 0.489 | 0.581 | 35 | 72 | 0.0% | 0.0% |
| 5-8% | BEARISH | 301 | 72.8% | +2.065% | 0.299 | 0.805 | 15 | 80 | 70.4% | 21.6% |
| 5-8% | MAX_BEARISH ⚠️LOW | 15 | 53.3% | +0.737% | 0.414 | 0.721 | 100 | 30 | 40.0% | 26.7% |
| 8-12% | MAX_BULLISH | 49 | 38.8% | -3.888% | 1.027 | 0.444 | 35 | 75 | 79.6% | 32.7% |
| 8-12% | BULLISH | 38 | 31.6% | -4.943% | 1.270 | 0.337 | 68 | 25 | 78.9% | 31.6% |
| 8-12% | NEUTRAL | 116 | 44.0% | -0.568% | 0.765 | 0.658 | 88 | 55 | 0.0% | 0.0% |
| 8-12% | BEARISH | 102 | 71.6% | +2.473% | 0.319 | 0.924 | 5 | 65 | 73.5% | 25.5% |
| 8-12% | MAX_BEARISH ❌INSUFF | 6 | 66.7% | -0.201% | 0.782 | 1.122 | 10 | 12 | 83.3% | 50.0% |
| 12%+ | MAX_BULLISH | 43 | 30.2% | -6.167% | 1.731 | 0.513 | 40 | 10 | 90.7% | 34.9% |
| 12%+ | BULLISH ⚠️LOW | 13 | 15.4% | -18.530% | 2.248 | 0.244 | 140 | 5 | 100.0% | 23.1% |
| 12%+ | NEUTRAL | 88 | 39.8% | -1.568% | 1.168 | 0.899 | 62 | 35 | 0.0% | 0.0% |
| 12%+ | BEARISH | 67 | 76.1% | +4.374% | 0.555 | 1.577 | 0 | 45 | 94.0% | 31.3% |
| 12%+ | MAX_BEARISH ❌INSUFF | 1 | 100.0% | +22.559% | 0.258 | 1.665 | 25 | 380 | 100.0% | 0.0% |

---

## Key Findings Summary

### Gap-Down Bounce — Candle Tier Impact
- **MAX_BULLISH** (n=78): 66.7% WR, avg EOD +1.866%, HOD 0.66×ATR at ~85min, LOD 0.25×ATR at ~35min, FT fire 59%
- **BULLISH** (n=1547): 67.6% WR, avg EOD +1.541%, HOD 0.68×ATR at ~80min, LOD 0.24×ATR at ~20min, FT fire 64%
- **NEUTRAL** (n=2013): 53.2% WR, avg EOD +0.265%, HOD 0.47×ATR at ~85min, LOD 0.41×ATR at ~50min, FT fire 0%
- **BEARISH** (n=795): 36.7% WR, avg EOD -1.311%, HOD 0.32×ATR at ~45min, LOD 0.60×ATR at ~45min, FT fire 59%
- **MAX_BEARISH** (n=783): 36.5% WR, avg EOD -1.325%, HOD 0.32×ATR at ~50min, LOD 0.69×ATR at ~45min, FT fire 64%

### Gap-Up Fade — Candle Tier Impact
- **MAX_BEARISH** (n=131): 66.4% WR, avg EOD +2.263%, HOD 0.32×ATR at ~20min, LOD 0.87×ATR at ~70min, FT fire 70%
- **BEARISH** (n=2030): 67.3% WR, avg EOD +1.461%, HOD 0.30×ATR at ~25min, LOD 0.72×ATR at ~65min, FT fire 64%
- **NEUTRAL** (n=2569): 50.6% WR, avg EOD -0.002%, HOD 0.51×ATR at ~55min, LOD 0.51×ATR at ~70min, FT fire 0%
- **BULLISH** (n=943): 35.0% WR, avg EOD -2.333%, HOD 0.86×ATR at ~65min, LOD 0.31×ATR at ~30min, FT fire 69%
- **MAX_BULLISH** (n=844): 33.3% WR, avg EOD -2.486%, HOD 0.87×ATR at ~60min, LOD 0.29×ATR at ~30min, FT fire 72%

### Best Gap-Down Regimes for MAX_BULLISH Opens
- **5-8%** (n=8 ❌INSUFF): 100.0% WR, HOD 0.80×ATR
- **2-5%** (n=68): 64.7% WR, HOD 0.65×ATR
- **8-12%** (n=1 ❌INSUFF): 0.0% WR, HOD 0.23×ATR
- **12%+** (n=1 ❌INSUFF): 0.0% WR, HOD 0.13×ATR

### Best Gap-Up Regimes for MAX_BEARISH Opens
- **12%+** (n=1 ❌INSUFF): 100.0% WR, LOD 1.67×ATR
- **2-5%** (n=109): 67.9% WR, LOD 0.87×ATR
- **8-12%** (n=6 ❌INSUFF): 66.7% WR, LOD 1.12×ATR
- **5-8%** (n=15 ⚠️LOW): 53.3% WR, LOD 0.72×ATR

### Bearish Bar-1 Reverse FT — The Reversal Pattern (with TS Slope Filter)
- **Gap-Down RAW** (n=428): 84.6% WR — but this doesn't account for TS line direction
- **Gap-Down FILTERED** (TS rising/flat + FT bar bullish/neutral, n=260): **87.3% WR**, avg EOD +2.862%
- **Gap-Down NOT TRADEABLE** (TS falling or FT bar still bearish, n=108): 77.8% WR — still positive but 9.5 pp penalty
- **Gap-Down by TS Level:** Bullish territory (cs≥40) at FT trigger = **90.7% WR** (n=150). Bearish territory (cs≤-15) = 76.0% (n=146)
- **Gap-Up Bullish Reversed FILTERED** (TS falling/flat + FT bar bearish/neutral, n=305): **83.3% WR**, avg EOD +2.750%
- **Gap-Up by TS Level:** Bearish territory at FT trigger = **87.0% WR** (n=208). Bullish territory = 76.0% (n=104)
- ⚠️ **TS FALLING at Gap-Down FT trigger** (n=15): 80.0% WR but ❌INSUFFICIENT sample — treat as untradeable per the user's rule

---

## Implications for ATR_MOOOVVVEE_INDICATOR Rewrite

### What This Study Proves/Disproves
1. **MAX_BULLISH vs BULLISH**: Check Table 1 for whether cs≥70 opens deliver a statistically meaningful edge over regular bullish opens on gap-downs
2. **Regime-Specific Labels**: Table 7 provides the exact lookup values for win rate, HOD/LOD expectations, and FT fire rates — by direction × gap bucket × candle tier
3. **Reverse FT Pattern**: Table 5 answers whether bearish bar-1 reversals are tradeable and at what HOD/LOD profile
4. **Timing Rules**: Table 6 tells the indicator WHEN to expect the session extreme — critical for state engine transitions

### Direct Integration Points
- **Candle tier label**: Replace 3-tier (BULL/NEUTRAL/BEAR) with 5-tier classification on the indicator
- **Win rate labels**: Use Table 7 values instead of single-number labels — splice by gap bucket + candle tier
- **HOD/LOD expectations**: Use ATR-normalized values from Table 7 for pullback zone calibration
- **Reverse FT trigger**: If bearish bar-1 hits reverse FT, check TS line direction FIRST. Only upgrade the state engine label if TS is rising/flat (Table 5B). If TS is still falling → do NOT take the long. Best case: TS in bullish territory (cs≥40) at FT fire = 90.7% WR
- **Timing bucket rules**: Table 6 values feed the 'when to expect topped/bottomed' state transitions

### Sample Size Notes
- Cells with n < 20 are flagged ⚠️LOW CONFIDENCE
- Cells with n < 10 are flagged ❌INSUFFICIENT — do not use for indicator rules
- All unflagged cells have n ≥ 20 and are considered reliable