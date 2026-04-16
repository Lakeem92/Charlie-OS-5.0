# Magenta vs Normal Bearish Gap-Up Study

## Study Question
When a stock gaps up and opens with a bearish first 5-minute candle, does a `max bearish magenta` open have a stronger downside edge than a `weak/normal bearish` open?

This study compares:
- Group A (`magenta_max_bear`): `consensusClamped (cs) <= -70` and `NOT NR7`
- Group B (`bearish_non_magenta`): bearish bar-1 with `cs > -70`

## Scope
- Universe: QuantLab watchlist (same ecosystem as existing gap studies)
- Date range: Jan 2024 to Mar 2026
- Market session: Regular trading hours (`09:30` to `16:00` ET)
- Gap filter: `gap-up >= 2%`
- Candle filter: bar-1 must be bearish (same body/range logic used in gap studies)

## Core Definitions
- Gap %: `(today_open - prev_close) / prev_close`
- FT-down: first 5-minute close at or below `open - (ATR14 * 0.40)`
- Win from open: `eod_return_from_open > 0` (short-side convention in this context)
- Win from FT entry: `eod_return > 0` on the FT-confirmed subset
- HoD/LoD timing: minutes from `09:30 ET` to session high/low

## Data and Logic Reuse
This study is intentionally fast and reuses prior outputs:
- Base event population comes from:
  - `studies/gap_fade_contrary_candle/outputs/results_analysis.csv`
- Opening-bar indicator tagging (`cs`, `is_nr7`) is added by pulling only required intraday data per event date.
- Tagged opening-bar values are cached to avoid repeated full API pulls:
  - `studies/magenta_vs_normal_bearish_gapup/outputs/opening_bar_metrics.csv`

## Implementation
Runner script:
- `studies/magenta_vs_normal_bearish_gapup/run_study.py`

Required path bootstrap in script:
- `C:\QuantLab\Data_Lab`
- `C:\QuantLab\Data_Lab\shared`
- `C:\QuantLab\Data_Lab\shared\config`
- `C:\QuantLab\Data_Lab\tools`

## How to Run
From workspace root:

```powershell
C:/QuantLab/Data_Lab/.venv/Scripts/python.exe studies/magenta_vs_normal_bearish_gapup/run_study.py
```

Expected behavior:
- First run: slower (builds opening-bar cache for all required events)
- Subsequent runs: fast (`Opening-bar cache hit: no API pull needed.`)

## Outputs
- Event-level usable dataset:
  - `studies/magenta_vs_normal_bearish_gapup/outputs/magenta_vs_normal_events.csv`
- Event-level full dataset (includes excluded/missing rows):
  - `studies/magenta_vs_normal_bearish_gapup/outputs/magenta_vs_normal_events_all.csv`
- Group summary table:
  - `studies/magenta_vs_normal_bearish_gapup/outputs/summary_by_group.csv`
- Text summary with tests:
  - `studies/magenta_vs_normal_bearish_gapup/outputs/summary.txt`

## Headline Results (Current Run)
From `summary_by_group.csv` and `summary.txt`:

- `bearish_non_magenta`:
  - `n=1316`
  - Win rate from open: `67.02%`
  - FT rate: `63.53%`
  - FT-entry win rate (`n=836`): `50.48%`
  - Avg HoD: `114.4 min`
  - Avg LoD: `133.2 min`

- `magenta_max_bear`:
  - `n=85`
  - Win rate from open: `74.12%`
  - FT rate: `75.29%`
  - FT-entry win rate (`n=64`): `60.94%`
  - Avg HoD: `89.5 min`
  - Avg LoD: `145.9 min`

Pairwise deltas (`A - B`):
- Win rate from open: `+7.10 pp` (two-proportion p=`0.175959`)
- FT rate: `+11.77 pp` (two-proportion p=`0.028238`)
- HoD mean diff: `-24.93 min` (95% CI `[-51.94, 3.55]`)
- LoD mean diff: `+12.76 min` (95% CI `[-17.66, 44.36]`)

Coverage snapshot from all bearish gap-up events (`n=2076`):
- `bearish_non_magenta`: `1316`
- `magenta_max_bear`: `85`
- `excluded_or_missing`: `675`

## Confidence Policy
Applied in script output:
- `n >= 20`: `HIGH`
- `10 <= n < 20`: `LOW`
- `n < 10`: `INSUFFICIENT`

## Notes
- Equity data routing is handled through `shared/data_router.py` per lab governance.
- This study is gap-up specific and compares bearish-open subtypes only.
- For deeper drill-down, next extension is by gap bucket (`2-5`, `5-8`, `8-12`, `12+`).
