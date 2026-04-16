# Regime Composite Score — "Diet CTA"

## Hypothesis
A composite z-score of 4 macro signals (VIX, HY credit spread, 2s10s yield curve, XLY/XLP consumer discretionary-to-staples ratio) provides statistically meaningful forward return signal for SPY, QQQ, and IWM across regime buckets.

Secondary hypothesis: XLY/XLP "cliff dive" events (20d ROC < -10%) are high-signal macro stress events with predictable forward return patterns.

## Signals
| # | Signal | Source | Inversion | Rationale |
|---|--------|--------|-----------|-----------|
| 1 | VIX (VIXCLS) | FRED | YES (high = bad) | Fear gauge — elevated = risk-off |
| 2 | HY Credit Spread (BAMLH0A0HYM2) | FRED | YES (high = bad) | Credit stress — widening = risk-off |
| 3 | 2s10s Yield Curve (T10Y2Y) | FRED | NO (high = good) | Steepening = growth expectations |
| 4 | XLY/XLP Ratio | Alpaca | NO (high = good) | Consumer risk appetite proxy |

## Regime Buckets
| Composite Z-Score | Label |
|---|---|
| > 1.0 | RISK-ON |
| 0 to 1.0 | MILD RISK-ON |
| -1.0 to 0 | MILD RISK-OFF |
| -2.0 to -1.0 | RISK-OFF |
| < -2.0 | EXTREME RISK-OFF / CTA MAX SHORT ZONE |

## Results

| Regime | Ticker | +1d Avg | +5d Avg | +10d Avg | +20d Avg | n= | Confidence |
|--------|--------|---------|---------|----------|----------|----|------------|
| _TBD_ | | | | | | | |

## Cliff Dive Events

| Date | Composite Score | SPY +5d | SPY +10d | SPY +20d | Outcome |
|------|----------------|---------|----------|----------|---------|
| _TBD_ | | | | | |

## Timeframe
2016-01-01 through present (~10 years, ~2,500 trading days)

## Key Findings
_Populated after study execution._

## Actionable Rules
_Populated after study execution._

## Outputs
- `outputs/data/raw_merged.csv` — merged equity + FRED raw data
- `outputs/data/composite_score_daily.csv` — daily composite score + regime
- `outputs/data/regime_forward_returns.csv` — forward returns by regime
- `outputs/data/cliff_dive_events.csv` — cliff dive events + outcomes
- `outputs/summary/summary_stats.txt` — full summary with current reading
- `outputs/charts/composite_score_chart.html` — score time series + SPY
- `outputs/charts/regime_returns_heatmap.html` — regime × holding period heatmap
- `outputs/charts/cliff_dive_study.html` — cliff dive forward return paths
