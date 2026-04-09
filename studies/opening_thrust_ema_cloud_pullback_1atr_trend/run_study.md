# How to Run This Study

## Study
Opening Thrust to EMA Cloud Pullback Study on Strong +/-1.0 ATR Trend Days.

## Prerequisite
Activate the QuantLab venv from repo root:

```powershell
.venv\Scripts\Activate.ps1
```

## Standard Run (End-to-End)

```powershell
python studies\opening_thrust_ema_cloud_pullback_1atr_trend\run_study.py
```

This runs:
1. collect_data.py (cache-first reuse from prior EMA cloud study)
2. analyze.py

## Optional Overrides

```powershell
python studies\opening_thrust_ema_cloud_pullback_1atr_trend\run_study.py --tickers NVDA TSLA --start 2024-01-01 --end 2026-04-03
```

Disable cache reuse:

```powershell
python studies\opening_thrust_ema_cloud_pullback_1atr_trend\run_study.py --disable-reuse
```

Force source run-id for cache copy:

```powershell
python studies\opening_thrust_ema_cloud_pullback_1atr_trend\run_study.py --source-run-id 2026-04-03_0932_ALL_intra
```

Analysis only:

```powershell
python studies\opening_thrust_ema_cloud_pullback_1atr_trend\run_study.py --analysis-only
```

## Versioned Outputs
Each run writes to:

```text
studies/opening_thrust_ema_cloud_pullback_1atr_trend/outputs/runs/<RUN_ID>/
  data/
  tables/
  charts/
  summary/
```

Latest run pointer:

```text
studies/opening_thrust_ema_cloud_pullback_1atr_trend/outputs/LATEST.txt
```
