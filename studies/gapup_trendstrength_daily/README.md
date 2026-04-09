# Gap-Up ≥5% — TrendStrength Candle Forward Returns (1-20 Days)

## Metadata
- **Date Created:** 2026-03-20
- **Hypothesis:** TrendStrength candle colour on 5%+ gap-up days predicts forward return trajectory over 1-20 trading days — bullish candles (gap WITH trend) outperform bearish candles (gap AGAINST trend).
- **Direction:** LONG (measuring forward returns from gap-day close)
- **Status:** COMPLETE
- **Result:** EDGE FOUND — Counter-intuitive: bearish-trend gaps OUTPERFORM bullish-trend gaps over 1-20 days

## The Question
When a stock gaps up 5%+, does the TrendStrength candle tier on that day tell us anything about the next 1-20 days? Specifically: do bullish-trend gap-ups (cyan/green candles) continue better than bearish-trend gap-ups (red/magenta candles)?

## Methodology
- **Data Source:** Alpaca (primary) via DataRouter, with fallback
- **Ticker(s):** Full watchlist (~237 tickers)
- **Date Range:** 2020-01-01 to present (6 years)
- **Timeframe:** Daily
- **Gap Definition:** (Open[t] − Close[t−1]) / Close[t−1] ≥ 5%
- **Entry:** Gap-day close price
- **Forward Returns:** T+1 through T+20 (close-to-close from gap day)
- **TrendStrength Warmup:** First 250 bars skipped per ticker for z-score stability
- **Minimum Sample Size:** 20 events per tier (flag if under)
- **Study Type:** gap_study / indicator interaction

### TrendStrength Tier Definitions (cs = consensus score)
| Tier | cs Range | Candle Color |
|------|----------|-------------|
| STRONG_BULL | ≥ 70 | Cyan |
| BULL | 40–69 | Green |
| WEAK_BULL | 15–39 | Light Green |
| NEUTRAL | -14 to 14 | Yellow |
| WEAK_BEAR | -15 to -39 | Salmon |
| BEAR | -40 to -69 | Red |
| STRONG_BEAR | ≤ -70 | Magenta |

### Binary Rollup
- **BULLISH:** cs ≥ 15 (STRONG_BULL + BULL + WEAK_BULL)
- **NEUTRAL:** -15 < cs < 15
- **BEARISH:** cs ≤ -15 (WEAK_BEAR + BEAR + STRONG_BEAR)

## Results Summary
| Metric | Value |
|---|---|
| Sample Size (n) | 4,852 events |
| Unique Tickers | 215 |
| Date Range | 2021-07 to 2026-03 |
| Avg Gap Size | 10.8% (median 6.8%) |
| Edge Classification | MODERATE — Bearish candles outperform on 10-20 day hold |

## Confidence Level
- [x] n >= 20 → Standard confidence (ALL 7 tiers ✅ RELIABLE)

## Key Findings
1. **STRONG_BEAR gaps are the best 20-day holds:** +15.75% avg return, 53.9% WR (n=957). Stocks gapping 5%+ against a bearish trend show the strongest mean reversion / continuation.
2. **NEUTRAL gaps are the WORST:** 41.9% WR at T+5, -1.57% avg return (n=485). Gap-ups with no directional trend are most likely to fade.
3. **Binary rollup — BEARISH > BULLISH > NEUTRAL:** Bearish candle gaps deliver +11.37% avg at T+20 (52.2% WR, PF 2.53) vs Bullish at +7.29% (48.5% WR, PF 1.86).
4. **Win rates are near-50% for T+1 across all tiers** — the first day after a 5%+ gap is essentially a coin flip. The edge DIVERGES at T+5 and beyond.
5. **BEARISH candles have HIGHER win rates by T+15-T+20** (52-54%) while BULLISH candles stay sub-50% on WR despite positive avg returns — bullish avg returns are driven by fat right tails, not consistency.
6. **STRONG_BULL (cyan) gaps: positive avg returns (+9.74% at T+20) but sub-50% WR** — a small number of massive winners pull the average up. Median return is negative. Skewed distribution.
7. **Profit factors tell the story:** BEARISH PF grows from 1.40 (T+1) → 2.53 (T+20). BULLISH PF stays flat ~1.73-1.88. NEUTRAL PF < 1.0 at all horizons (negative edge).

## Actionable Rules
- **Best setup: Gap-up ≥5% on BEARISH candle (cs ≤ -15), hold 10-20 days from close**
  - T+20: 52.2% WR, +11.37% avg return, PF 2.53 (n=1,716)
  - STRONG_BEAR tier (cs ≤ -70) is the sweet spot: 53.9% WR, +15.75% avg at T+20 (n=957)
- **Avoid: Gap-up on NEUTRAL candle (cs -15 to +15)** — negative edge at all horizons T+3 to T+15
- **BULLISH gap-ups are playable but inconsistent** — positive avg returns driven by outliers, not consistency
- **T+1 is noise for ALL tiers** — no reliable edge on day-1 from any candle colour alone
- **Best conditions:** Stock gapping against prevailing trend (bearish → surprise reversal catalyst)
- **Avoid when:** NEUTRAL trend + 5% gap = highest fade probability

## Charts Generated
- [x] winrate_heatmap.html — 7-tier × 20-day win rate heatmap
- [x] forward_returns_binary.html — Bullish vs Bearish vs Neutral grouped bars
- [x] forward_returns_7tier.html — All 7 tiers at key horizons
- [x] winrate_curve.html — Multi-line win rate progression 1-20 days
- [x] avg_return_curve.html — Multi-line avg return progression 1-20 days
- [x] gap_distribution.html — Gap size histogram

## Output Files
- studies/gapup_trendstrength_daily/outputs/events.csv
- studies/gapup_trendstrength_daily/outputs/summary_stats.csv
- studies/gapup_trendstrength_daily/outputs/charts/
