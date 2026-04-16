# Intraday EMA Cloud Pullback and 21 EMA Structural Failure Study

## Scope
This study tests whether a 5-minute close through EMA21 behaves as a real kill switch or a recoverable shakeout on strong intraday trend days.

### Directional scope
- Long trend days and short trend days are analyzed with mirrored logic.
- Results are reported as long, short, and combined.

### Date window
- Default start date: 2024-01-01
- End date: today (runtime resolved)

### Data routing
- US equity OHLCV is pulled via Alpaca through QuantLab DataRouter (fallbacks handled by router).

## Definitions (Canonical)
- Session open: first RTH 5-minute bar open at 08:30 CT.
- Session close: last RTH 5-minute bar close at 15:00 CT.
- RTH window: 08:30-15:00 CT only.
- ATR14 source: daily bars; true range rolling mean(14).
- ATR timing convention: prior-day ATR14 (atr14_prev) for same-session classification (no lookahead).
- Strong long trend day: session close >= session open + 1.0 * atr14_prev.
- Strong short trend day: session close <= session open - 1.0 * atr14_prev.

## EMA Cloud Logic (Locked)
- Fast EMA: 10
- Slow EMA: 21
- Source: 5-minute close
- Cloud zone: area between EMA10 and EMA21

Important: this study uses EMA10/EMA21 only. No EMA8 logic is used.

## Event Sequencing
Each qualifying +/-1.0 ATR close-from-open day is processed in strict order:
1. Classify day as long or short trend day.
2. Compute first-30-minute directional expansion from session open (6 bars) and normalize by atr14_prev.
3. Bucket early expansion:
	- 0.50-0.60
	- 0.60-0.70
	- 0.70-0.80
	- 0.80-1.00
	- 1.00+
4. Confirm trend-side positioning after first-30-minute expansion peak:
	- Long: close above cloud
	- Short: close below cloud
5. Detect cloud pullback after trend-side positioning:
	- Pullback = first bar whose high/low range intersects cloud zone.
6. Detect EMA21 close-through only after pullback starts:
	- Long break: 5-minute close below EMA21
	- Short break: 5-minute close above EMA21
	- Wick-only crossings do not count.
7. For break events only, compute post-break outcomes from later bars only:
	- New session extreme after break (new HoD/new LoD)
	- Structural failure (no new extreme)
	- Close still >= +/-1.0 ATR from open
	- Favorable close quartile (upper quartile for longs, lower quartile for shorts)
	- Forward return from break to session extreme and to session close
	- Minutes from break to new extreme and to session close
8. Assign break time-of-day bucket:
	- Morning: 08:30-10:00 CT
	- Midday: 10:00-12:30 CT
	- Afternoon: 12:30-15:00 CT

## Output Artifacts
Each run is versioned under outputs/runs/<RUN_ID>/ with:

LATEST run pointer is written to outputs/LATEST.txt.

## Latest Run Summary

Run ID: 2026-04-03_0932_ALL_intra

Scope of this run:
- Universe executed: full QuantLab master watchlist (239 requested tickers)
- Date range: 2024-01-01 to 2026-04-03
- EMA logic: EMA10/EMA21 only

Headline result:
- Among 8,685 strong +/-1.0 ATR close-from-open sessions, cloud pullbacks occurred in 88.2% of cases.
- Among cloud pullbacks, EMA21 close-through occurred in 92.1% of cases.
- Among EMA21 close-through events, 70.8% still made a new session extreme later (shakeout), while 28.7% were structural failures.

Long trend days (full universe):
- Sample size: n=4,359 (pullbacks=3,856, break events=3,589)
- Cloud pullback rate: 88.5%
- EMA21 close-through rate among pullbacks: 93.1%
- New session extreme after break: 70.2%
- Structural failure after break: 29.4%
- Close still >= +1.0 ATR from open after break: 100.0%
- Favorable close quartile after break: 88.4%
- Confidence: RELIABLE

Short trend days (full universe):
- Sample size: n=4,326 (pullbacks=3,807, break events=3,466)
- Cloud pullback rate: 88.0%
- EMA21 close-through rate among pullbacks: 91.0%
- New session extreme after break: 71.5%
- Structural failure after break: 27.9%
- Close still >= +1.0 ATR from open (short-direction normalized) after break: 99.9%
- Favorable close quartile after break: 90.5%
- Confidence: RELIABLE

Combined results (full universe):
- Sample size: n=8,685 (pullbacks=7,663, break events=7,055)
- Cloud pullback rate: 88.2%
- EMA21 close-through rate among pullbacks: 92.1%
- New session extreme after break: 70.8%
- Structural failure after break: 28.7%
- Close still >= +/-1.0 ATR from open after break: 100.0%
- Favorable close quartile after break: 89.4%
- Confidence: RELIABLE

Time-of-day read (combined):
- Morning breaks (n=2,339): 93.7% recovered to a new extreme; 6.3% failed structurally.
- Midday breaks (n=3,029): 70.8% recovered; 29.2% failed structurally.
- Afternoon breaks (n=1,687): 39.2% recovered; 59.7% failed structurally.
- Practical takeaway: afternoon EMA21 close-through events are materially more terminal than morning/midday in this run.

Early expansion bucket read (combined):
- All primary buckets were well populated and RELIABLE:
	- 0.50-0.60: n=891 | break rate=81.1% | new-extreme-given-break=69.7%
	- 0.60-0.70: n=797 | break rate=81.8% | new-extreme-given-break=70.2%
	- 0.70-0.80: n=725 | break rate=87.2% | new-extreme-given-break=71.4%
	- 0.80-1.00: n=976 | break rate=85.2% | new-extreme-given-break=60.8%
	- 1.00+: n=1,349 | break rate=87.5% | new-extreme-given-break=49.5%
- 70% ATR is not a clean cliff in this full run; post-break recovery degrades more meaningfully as early expansion rises into 0.80-1.00 and 1.00+ buckets.

Interpretation for trading use:
- Pullback-to-cloud is normal on these strong trend days.
- EMA21 close-through is common enough (92.1% of pullbacks) that it is not a rare stop event by itself.
- EMA21 close-through is not a universal kill switch, but terminal risk is much higher for afternoon breaks.
- Practical use: treat EMA21 close-through as context-dependent (especially time-of-day and early-expansion regime), not binary.

Confidence note:
- Long subgroup: RELIABLE (n=4,359)
- Short subgroup: RELIABLE (n=4,326)
- Combined: RELIABLE (n=8,685)

Definition/Count Audit (Corrected)
- 1. True cloud pullback rate:
	- Long: 3,856 / 4,359 = 88.5%
	- Short: 3,807 / 4,326 = 88.0%
	- Combined: 7,663 / 8,685 = 88.2%
- 2. Pullback-rate denominator:
	- Denominator is all qualified strong trend days (n_base), not only pullback days.
- 3. Break-rate denominator:
	- Reported break rate is among pullback days only: n_break / n_pullback.
	- Combined: 7,055 / 7,663 = 92.1%.
- 4. Gating logic that narrows pullback subset:
	- Yes. Pullback detection is gated by sequence rules after early expansion.
	- Specifically, pullback must occur after first-30-minute expansion peak and after trend-side positioning is confirmed (close above cloud for longs, below cloud for shorts).
	- Days that qualify as strong trend days but fail these post-expansion sequence gates are included in n_base but excluded from n_pullback.

## Confidence Policy
- n >= 20: RELIABLE
- n < 20: LOW
- n < 10: INSUFFICIENT

## Sanity Guards
- No lookahead ATR alignment (prior-day ATR only)
- Pullback must occur after early expansion peak
- EMA21 break must occur after pullback
- Recovery checks use bars after break timestamp only
- RTH-only handling in Central Time
