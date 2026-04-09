# IWM 1% Move Followup Analysis

This study analyzes how IWM (Russell 2000 ETF) performs the day after experiencing a 1% or greater move (up or down).

## Methodology

- Data source: Alpaca (via DataRouter, study_type='returns')
- Period: 2010-01-01 to present
- Identifies days where |daily return| >= 1%
- Measures the next trading day's performance
- Calculates win rate, average move, and other statistics

## Results

*Results will be populated after running the analysis*

## Files

- `run_iwm_1pct_followup.py`: Main analysis script
- `outputs/iwm_1pct_followup_details.csv`: Detailed day-by-day results
- `outputs/iwm_1pct_followup_summary.txt`: Summary statistics

## Usage

```bash
cd studies/iwm_1pct_followup
python run_iwm_1pct_followup.py
```