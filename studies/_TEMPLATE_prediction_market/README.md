# [STUDY NAME] — Prediction Market Event Study

## Question
[What specific question does this study answer?]

## Data Sources
- **Prediction Market:** Polymarket / Kalshi (via pm_data_loader.py)
- **Price Data:** Alpaca (via pm_data_loader.py or existing DataRouter)

## Methodology
- **Event Definition:** [What constitutes a trigger event? e.g., "Fed rate cut implied probability drops 10%+ in 7 days"]
- **Market ID(s):** [Specific Polymarket/Kalshi market IDs used]
- **Ticker(s):** [Which stocks/ETFs are being tested]
- **Threshold:** [Minimum odds change to qualify as event]
- **Window:** [Lookback period for odds change detection]
- **Forward Returns:** [1, 2, 3, 5, 10 days post-event]

## Parameters (LOCKED after design — no curve-fitting)
```python
MARKET_ID = ""           # From search_markets()
SOURCE = "kalshi"        # "polymarket" or "kalshi"
TICKER = "QQQ"           # Stock/ETF to analyze
THRESHOLD_ABS = 0.10     # Minimum probability change (10% = 0.10)
WINDOW_DAYS = 7          # Rolling window for change detection
FORWARD_DAYS = [1, 2, 3, 5, 10]
```

## Key Findings
[Filled in after study runs]

| Horizon | N | Win Rate | Mean Return | t-stat | p-value |
|---------|---|----------|-------------|--------|---------|
| 1-day   |   |          |             |        |         |
| 2-day   |   |          |             |        |         |
| 3-day   |   |          |             |        |         |
| 5-day   |   |          |             |        |         |
| 10-day  |   |          |             |        |         |

## Confidence Notes
- **Sample Size:** [N events — is this sufficient?]
- **Data Quality:** [Any gaps or issues in prediction market data?]
- **Look-ahead Bias:** [Confirmed none — event detection uses only prior data]
- **Multiple Testing:** [If testing multiple tickers/markets, apply Bonferroni correction]
- **Caveats:** [Other limitations or considerations]

## Outputs
- `outputs/results.csv` — Raw event-level data
- `outputs/summary_stats.txt` — Statistical summary per horizon
- `outputs/forward_returns.png` — Forward return distribution chart
