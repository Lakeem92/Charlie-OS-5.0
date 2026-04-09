# How to Run This Study

## Study
Intraday EMA Cloud Pullback and 21 EMA Structural Failure Study.

EMA logic is fixed to EMA10/EMA21 only.

## Prerequisite
Activate the QuantLab venv from repo root:

```powershell
.venv\Scripts\Activate.ps1
```

## Standard Run (End-to-End)
From repo root:

```powershell
python studies\ema_cloud_pullback_21ema_failure\run_study.py
```

This runs:
1. collect_data.py
2. analyze.py

## Optional Overrides

```powershell
python studies\ema_cloud_pullback_21ema_failure\run_study.py --tickers NVDA TSLA --start 2024-01-01 --end 2026-04-03
```

Skip collection and run analysis on already-collected data in the active run folder:

```powershell
python studies\ema_cloud_pullback_21ema_failure\run_study.py --analysis-only
```

## Versioned Outputs
Each run writes to:

```text
studies/ema_cloud_pullback_21ema_failure/outputs/runs/<RUN_ID>/
  data/
  tables/
  charts/
  summary/
```

Latest run pointer:

```text
studies/ema_cloud_pullback_21ema_failure/outputs/LATEST.txt
```

## Core Output Files
- data/events_detailed.csv
- tables/overall_sample_summary.csv
- tables/cloud_pullback_stats.csv
- tables/ema21_close_through_stats.csv
- tables/post_break_recovery_failure_stats.csv
- tables/time_of_day_break_outcomes.csv
- tables/early_expansion_bucket_stats.csv
- summary/analysis_summary.txt
- summary/analysis_manifest.csv

## Troubleshooting
- If collection returns many missing symbols, verify watchlist symbols are valid on Alpaca IEX feed.
- If sample size is too small, keep start date at 2024-01-01 and expand ticker universe.
- If run is interrupted, rerun the same command; a new run folder is created with a unique suffix when needed.
- Cache results: Save to CSV and reuse
- Switch to fallback source (see [docs/API_MAP.md](../../docs/API_MAP.md))

---

## Clean Up

To remove outputs and start fresh:

```powershell
# Remove all output files
Remove-Item outputs/*.csv, outputs/*.txt

# Keep directory structure
```

---

## Where Outputs Go

```
studies/[study_name]/
├── collect_data.py              # Step 1 script
├── analyze_[ticker]_[event].py  # Step 2 script
├── study_notes.md               # Research notes
├── run_study.md                 # This file
├── README.md                    # Final analysis (create after run)
└── outputs/                     # All generated files
    ├── [study]_analysis.csv
    ├── [study]_analysis.txt
    └── charts/ (optional)
        ├── forward_returns.png
        └── gap_distribution.png
```

---

## Next Steps After Completion

1. **Archive Study**
   - Zip entire folder: `studies/[study_name]/`
   - Move to archive if pattern no longer works

2. **Share Results**
   - README.md is self-contained
   - Can share just that file + CSV for review

3. **Apply to Live Trading**
   - Use Alpaca paper trading to test strategy
   - See `shared/config/api_clients.py` → `AlpacaClient`

4. **Extend Study**
   - Add more events (extend date range)
   - Test on related tickers
   - Add additional filters (VIX, sector strength, etc.)

---

**Template Version:** 1.0  
**Last Updated:** December 14, 2025
