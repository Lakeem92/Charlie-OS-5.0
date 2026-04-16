# Opening Range Violation Survival Study

## Question
For each gap path, how much can price violate the opening 5-minute extreme after it closes — and when can that happen — before the setup is statistically broken?

## Paths Analyzed
| Path | Direction | OR Extreme Watched | n |
|---|---|---|---|
| Gap-Up Continuation | Long | Bar-1 Low | 2,954 |
| Gap-Down Continuation | Short | Bar-1 High | 1,882 |
| Gap-Up Fade | Short | Bar-1 High | 1,326 |
| Gap-Down Bounce | Long | Bar-1 Low | 753 |

## Headline Finding
OR violation penalty is **path-asymmetric**:
- **Gap-UP paths (Continuation Long + Fade Short): HARD STOP.** Violation destroys FT — 42% and 34% penalties respectively.
- **Gap-DOWN paths (Continuation Short + Bounce Long): SOFT STOP.** Violation is noise — 1-2% penalty, depth doesn't matter.

## Key Numbers

| Path | No-Violation FT | With-Violation FT | Penalty | Stop Type |
|---|---|---|---|---|
| Gap-Up Continuation Long | 49.0% | 7.1% | **-41.9%** | HARD |
| Gap-Down Continuation Short | 11.6% | 12.9% | **+1.3%** | SOFT |
| Gap-Up Fade Short | 43.2% | 9.6% | **-33.6%** | HARD |
| Gap-Down Bounce Long | 17.0% | 15.3% | **-1.7%** | SOFT |

## Data
- **Source:** `all_events_with_cs.csv` from opening_candle_strength study (11,733 events)
- **Intraday:** Alpaca IEX 5-min bars via DataRouter
- **Period:** 2024-01-23 to 2026-03-06
- **Enriched:** 6,915 events (4,818 skipped — no intraday data for those dates)
- **Tickers:** 234 from watchlist

## Definitions
- **OR extreme:** High or Low of the first 5-minute candle (9:30-9:35 ET)
- **Violation:** Price breaches the adverse OR extreme after bar-1 closes
- **Follow-through (FT):** Session close ≥ 0.70 ATR from the open in setup direction
- **Elite FT:** Session close ≥ 1.00 ATR from the open in setup direction
- **Depth buckets:** 0-0.10, 0.10-0.25, 0.25-0.50, 0.50+ ATR beyond OR extreme
- **Timing buckets:** at_open, first_30min, 30min-1hr, 1hr-2hr, 2hr-4hr, after_4hr, last_30min

## Scripts
- `collect_or_data.py` — Data collection. Loads event universe, pulls 5-min intraday, computes OR metrics. ~22 min runtime.
- `analyze_or_study.py` — Analysis. Generates all outputs from cached `or_master_events.csv`. ~5 sec runtime.

## Outputs (`outputs/run_20260309/`)
| File | Description |
|---|---|
| `or_master_events.csv` | Master event dataset (6,915 rows, 4 MB) |
| `executive_summary.md` | Full summary with indicator recommendations |
| `stop_placement_cheatsheet.md` | Per-path depth/timing tables + plain-English guidance |
| `hod_lod_timing.md` | When HoD/LoD occur by path |
| `study_summary.json` | Machine-readable summary |
| `path_stats.csv` | Path-level statistics |
| `depth_analysis.csv` | Depth bucket cross-tab |
| `timing_analysis.csv` | Timing bucket cross-tab |
| `gap_bucket_analysis.csv` | Gap-size bucket cross-tab |
| `hodlod_timing.csv` | HoD/LoD timing distribution |
| `charts/` | 7 interactive Plotly .html charts |

## Indicator Recommendation
Label the Bar-1 High/Low on the indicator. Display "OR HOLDING" vs "OR BREACHED +X.XX ATR" as real-time state.
- Gap-UP paths: **HARD STOP** at OR extreme. Any breach = dramatically degraded odds.
- Gap-DOWN paths: **SOFT STOP.** OR extreme is not the dominant signal — use other confluence.
