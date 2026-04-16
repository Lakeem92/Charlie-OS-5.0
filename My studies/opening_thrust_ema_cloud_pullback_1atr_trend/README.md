# Opening Thrust to EMA Cloud Pullback Study on Strong +/-1.0 ATR Trend Days

## Scope
This study measures next-hour EMA10/EMA21 cloud pullback behavior after an early opening thrust (0.70+ ATR in bars 1-3) on strong trend days.

## Canonical Definitions
- Session open: first RTH 5-minute bar open at 08:30 CT
- Session close: last RTH 5-minute bar close at 15:00 CT
- RTH window: 08:30-15:00 CT only
- ATR14 source: daily true range rolling mean(14)
- ATR timing: prior-day ATR14 only (atr14_prev)
- Strong long trend day: close >= open + 1.0 * atr14_prev
- Strong short trend day: close <= open - 1.0 * atr14_prev

## EMA Cloud Logic (ThinkScript-Mirrored)
- Fast EMA: 10
- Slow EMA: 21
- Source: 5-minute close
- Cloud: area between EMA10 and EMA21
- Bullish cloud when EMA10 > EMA21
- Bearish cloud when EMA10 < EMA21

Important: no EMA8 logic is used in this study.

## Event Sequence
1. Identify strong trend day (long/short)
2. Detect first 0.70+ ATR thrust in bars 1-3 from session open
3. Anchor event at trigger bar
4. Evaluate next-hour window (12 bars after trigger)
5. Measure cloud depth:
   - touch EMA10
   - enter cloud zone
   - touch EMA21
6. Measure directional breach after cloud contact starts:
   - long: close below EMA21
   - short: close above EMA10
7. Measure optional cloud flip:
   - long: EMA10 cross below EMA21
   - short: EMA10 cross above EMA21
8. Measure later-day recovery from breach/flip to new session extreme

## Denominators
- Base sample denominator: all strong trend days
- Trigger and cloud-depth denominators: triggered events only
- Recovery denominators: breach-only or flip-only subsets

## Output Artifacts
Each run is versioned under outputs/runs/<RUN_ID>/ with:
- data/events_opening_thrust_detailed.csv
- tables/overall_sample_summary.csv
- tables/trigger_timing_exact_bar.csv
- tables/trigger_timing_cumulative.csv
- tables/trigger_magnitude_buckets.csv
- tables/cloud_touch_depth_rates.csv
- tables/directional_breach_rates_and_recovery.csv
- tables/cloud_flip_rates_and_recovery.csv
- tables/post_trigger_30m_split.csv
- tables/session_context_breach_tod.csv
- summary/analysis_summary.txt
- summary/analysis_manifest.csv

LATEST pointer is written to outputs/LATEST.txt.

## Latest Run Summary
Run ID: 2026-04-03_1207_ALL_intra

Universe and period:
- Requested watchlist: 239 names
- Strong trend base sample (combined): n=8529
- Date window: 2024-01-01 to 2026-04-03

Trigger incidence (denominator = strong trend base):
- Combined: 1626/8529 = 19.1%
- Long: 869/4286 = 20.3%
- Short: 757/4243 = 17.8%

Next-hour cloud pullback depth (denominator = triggered only):
- Cloud touch-any (combined): 1298/1626 = 79.8%
- Cloud entry (combined): 1294/1626 = 79.6%
- Touch EMA21 (combined): 959/1626 = 59.0%

Directional structure break after contact starts (denominator = triggered only):
- Combined directional breach: 815/1626 = 50.1%
- Long breach: 369/869 = 42.5%
- Short breach: 446/757 = 58.9%

Cloud flip (denominator = triggered only):
- Combined cloud flip: 391/1626 = 24.0%
- Long cloud flip: 214/869 = 24.6%
- Short cloud flip: 177/757 = 23.4%

Event timing and thrust profile:
- Trigger timing (combined pattern): most triggers appear on bar 2, then bar 1, then bar 3
- Trigger magnitude buckets are concentrated in 0.70-1.00 ATR (both directions)
- Breaches and flips are mostly first-30-minute events after trigger (combined: 71.2% of breaches, 83.9% of flips)

Recovery context after structural failure:
- Post-breach new extreme rate (combined): 87.7% of breach events
- Post-flip new extreme rate (combined): 90.3% of flip events
- Median minutes to new extreme: 50.0 min after breach, 45.0 min after flip

Confidence:
- Combined, long, and short cohorts are all marked RELIABLE (all key denominators n >= 20)

Denominator audit:
- Trigger rate uses strong trend base days.
- Cloud depth, breach, and flip rates use triggered events only.
- Recovery rates use breach-only or flip-only subsets.
