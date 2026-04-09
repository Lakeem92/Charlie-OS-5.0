# TLRY Cannabis Rescheduling Price/Volatility Study

## Objective
Test whether U.S. federal cannabis rescheduling/regulatory headlines create a repeatable TLRY edge characterized by:
- Large opening gaps
- Strong intraday upside extension (short-squeeze proxy)
- Weak next-day follow-through / mean reversion

## Study Type
Price / Volatility Study (no indicators, no parameter tuning)

## Methodology

### Data Source
- **Price Data**: Alpaca ONLY (IEX feed)
- **News Data**: Alpaca News API
- **Ticker**: TLRY
- **Timezone**: America/Chicago (CT)
- **Premarket**: INCLUDED (03:00-08:29 CT)

### Date Range
Last 5 years ending at most recent completed trading day

### Event Definition
**Event day** = trading day with ≥1 HIGH-RELEVANCE news item indicating U.S. federal cannabis reform involving:
- DEA, DOJ, White House, President, Attorney General
- Keywords: reschedule/rescheduling, schedule III/3, cannabis/marijuana, 280e
- Excludes: earnings, product launches, routine company news (unless tied to federal reform)

### News → Event Mapping (CT timezone)
For trading day T:
- **Pre-open catalyst window**: Prior trading day 15:00 CT → 08:29 CT
- **Intraday catalyst window**: 08:30 → 15:00 CT
- Flags: `pre_open_flag`, `intraday_flag`

### Metrics Calculated (per event day)

#### Gap Metrics
- `prev_close`: Prior trading day RTH close
- `open_price`: 08:30 CT RTH open
- `open_gap_pct`: (open - prev_close) / prev_close

#### Intraday Extension
- `day_high_rth`: Max price 08:30-15:00 CT
- `open_to_high_pct_rth`: (high - open) / open
- `time_to_high_minutes`: Minutes from 08:30 to RTH high
- `firsthour_open_to_high_pct`: High from 08:30-09:30 vs open

#### Close & Follow-through
- `close_price`: Daily close
- `open_to_close_pct`: (close - open) / open
- `tplus1_return_pct`: (close_{T+1} - close_T) / close_T

#### Volume
- `event_volume`: Daily volume on event day
- `avg_volume_6mo`: Mean daily volume over prior 126 trading days
- `volume_spike_ratio`: event_volume / avg_volume_6mo

## Outputs

### Files Generated
1. **tlry_rescheduling_event_master_table.csv** - Full event table with all metrics
2. **tlry_rescheduling_event_summary.json** - Summary statistics
3. **tlry_open_to_high_hist.png** - Histogram of intraday extensions
4. **tlry_gap_vs_extension_scatter.png** - Gap vs extension scatter with linear fit
5. **tlry_event_timeline.png** - Timeline of events and extensions
6. **run_log.txt** - Execution log with data pulls, counts, assumptions

### Summary Statistics
- N events
- Mean/median: open_gap_pct, open_to_high_pct_rth, open_to_close_pct, tplus1_return_pct
- % events with negative T+1 returns
- Quantiles (10/25/50/75/90) of open_to_high_pct_rth
- Correlations: gap vs extension, volume vs extension

## Running the Study

```bash
cd studies/tlry_rescheduling_events
python tlry_rescheduling_study.py
```

## Requirements
- Python 3.8+
- pandas
- numpy
- matplotlib
- seaborn
- scipy
- pytz
- requests
- Alpaca API credentials configured in environment

## Governance
- Alpaca prices ONLY
- No indicators, no parameter tuning
- Holidays/missing bars handled gracefully with logging
- Prerequisites checked; stops with explanation if missing

## Interpretation Guide

**Hypothesis Confirmation** requires:
1. Mean open_gap_pct > 2%
2. Mean open_to_high_pct_rth > 3%
3. % negative T+1 returns > 50%

Pattern: "Gap + Squeeze + Next-Day Fade"
