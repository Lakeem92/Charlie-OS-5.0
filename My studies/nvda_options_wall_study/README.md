# NVDA Post-Earnings Options Wall Study

## Hypothesis
When NVDA's post-earnings overnight move **clears** the nearest major call strike above the pre-earnings closing price (by >1%), the gap is more likely to **hold and continue**. When it fails to clear, the gap is more likely to **fade**.

## Methodology
1. Identify the last 12 NVDA earnings dates (after-market-close reports)
2. For each event:
   - Record the closing price the day before earnings (pre-earnings level)
   - Record the next trading day's open, high, low, close (captures overnight reaction)
   - Find the nearest major call strike above the pre-earnings close ($5 or $10 increments)
   - Determine if the move "cleared" the strike: next-day close > strike × 1.01
3. Split events into CLEARED vs NOT CLEARED buckets
4. Compare average returns, median returns, and win rates across buckets

## Data Source
- **Primary:** Alpaca (daily OHLCV via DataRouter)
- **Fallback:** yfinance

## Outputs
- `outputs/nvda_earnings_events.csv` — Full event table with all metrics
- `outputs/bucket_statistics.csv` — Aggregated stats per bucket
- `outputs/study_summary.txt` — Human-readable summary with interpretation
- `outputs/charts/forward_returns_comparison.html` — Grouped bar chart
- `outputs/charts/winrate_comparison.html` — Win rate comparison
- `outputs/charts/return_distributions.html` — Box+strip plot distributions
- `outputs/charts/event_timeline.html` — Timeline scatter of all events

## How to Run
```bash
cd C:\QuantLab\Data_Lab\studies\nvda_options_wall_study
python run_nvda_options_wall.py
```

## Key Definitions
- **Pre-earnings close:** Closing price on the day NVDA reports (after close)
- **Call wall strike:** Nearest $5/$10 strike above pre-earnings close
- **Cleared:** Next-day close > strike × 1.01 (1% above the wall)
- **Next-day return:** Open→Close on the post-earnings trading day
- **3-day forward return:** Post-earnings open → close 3 trading days later
