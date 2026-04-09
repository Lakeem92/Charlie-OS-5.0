# [STUDY NAME]

## Metadata
- **Date Created:** [TODAY'S DATE]
- **Hypothesis:** [ONE SENTENCE — what are we testing?]
- **Direction:** [LONG / SHORT / BOTH]
- **Status:** [IN PROGRESS / COMPLETE / ARCHIVED / INCONCLUSIVE]
- **Result:** [EDGE FOUND / NO EDGE / INCONCLUSIVE — fill when done]

## The Question
[Plain English — what does Lakeem actually want to know?]

## Methodology
- **Data Source:** Alpaca (canonical) / yfinance (indices only)
- **Ticker(s):**
- **Date Range:**
- **Timeframe:** daily / 5min / 1min
- **Minimum Sample Size:** 20 events (flag if under)
- **Study Type:** indicator_honesty / gap_study / event_study / prediction_market / custom

## Results Summary
| Metric | Value |
|---|---|
| Sample Size (n) | |
| Win Rate | |
| Avg Return | |
| Max Drawdown | |
| Edge Classification | STRONG / MODERATE / WEAK / NONE |

## Confidence Level
- [ ] n >= 20 → Standard confidence
- [ ] n < 20 → LOW CONFIDENCE — trade smaller
- [ ] n < 10 → INSUFFICIENT — do not trade

## Key Findings
[3-5 bullet points. Plain English. What did the data say?]

## Actionable Rules (if edge found)
- Entry condition:
- Exit condition:
- Stop parameters:
- Best conditions/regime:
- Avoid when:

## Charts Generated
- [ ] price_chart.html
- [ ] forward_returns.html
- [ ] winrate_heatmap.html
- [ ] gap_distribution.html
- [ ] equity_curve.html
- [ ] pm_overlay.html

## Output Files
- studies/[study_name]/outputs/events.csv
- studies/[study_name]/outputs/summary_stats.txt
- studies/[study_name]/outputs/charts/

## Notes & Observations
[Anything weird about the data, assumptions made, things to revisit]

## Follow-Up Studies Triggered
[What did this make you want to test next?]
