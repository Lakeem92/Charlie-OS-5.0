# Study: Earnings Gap + Round Number Break + Candle Color

## Research Question

**Does momentum confirmation (TrendStrength candle color) matter when a structural level breaks on a catalyst gap day — or is the structural break itself the signal?**

This study directly addresses Lakeem's identified hesitation pattern: delaying entries on round-number / call-wall breaks when TrendStrength shows gray (neutral) candles, even when catalyst and options structure both support the move.

---

## Hypotheses

| Hypothesis | Interpretation | Action |
|---|---|---|
| GRAY ≈ CYAN forward returns | Candle color is noise on gap days | Treat round-number break as entry regardless of color |
| CYAN >> GRAY | Momentum confirmation has edge | Size smaller on gray; full size on cyan |
| ORB Low holds >75% on 5%+ gaps | ORB structure is reliable on gap days | Use ORB low as stop, don't cut intra-ORB weakness |

---

## Methodology

### Gap Day Identification (Daily Data)
- Universe: full watchlist (~240 tickers)
- Date range: 2024-01-01 → 2026-03-06
- Gap threshold: ≥ 5% open vs. prior close

### Intraday Analysis (5-min Bars)
For each gap day:
1. Pull 5-min bars (event day + 7-day warmup for indicator z-scores)
2. Compute TrendStrength consensus score on every bar
3. Identify the nearest **$5 round number above the open** (call wall proxy)
4. Find the **first bar closing above that level** — the "break bar"
5. Record candle color at break (CYAN/GREEN/GRAY/RED)
6. Measure forward returns: 15min, 30min, 1hr, 2hr, EOD (from break bar close)
7. Record max adverse excursion (MAE) and max favorable excursion (MFE)

### TrendStrength Color Thresholds
| Color | Consensus Score |
|---|---|
| CYAN | ≥ 70 (max bull) |
| GREEN | 30–70 (moderate bull) |
| GRAY | −30–30 (neutral) |
| RED | < −30 (bearish) |

### ORB Analysis (Secondary)
- Opening Range = first 5-min candle of the session
- Measures: does the ORB low hold through the session?
- Stratified by: candle color of opening bar, gap size bucket

---

## Run

```powershell
cd C:\QuantLab\Data_Lab
python studies/gap_round_number_break/run_gap_round_number_break.py
```

---

## Outputs

| File | Description |
|---|---|
| `gap_events_raw.csv` | All 5%+ gap-up days identified |
| `round_number_break_events.csv` | Per-event: break details, colors, forward returns, MAE/MFE |
| `orb_integrity_events.csv` | Per-gap-day: ORB high/low, color, held/broken, EOD return |
| `candle_color_vs_returns.csv` | Aggregated avg return + win rate by color × window |

---

## Configuration

All parameters are in the `CONFIGURATION` block at the top of the run script:

- `GAP_THRESHOLD` — minimum gap size (default 5%)
- `ROUND_NUMBER_INCREMENT` — round number step size (default $5)
- `CYAN/GREEN/GRAY_THRESHOLD` — consensus score color cutoffs
- `FORWARD_WINDOWS` — return measurement horizons

---

## Related Studies
- `studies/tsla_indicator_honesty/` — indicator honesty test on single ticker
- `studies/indicator_honesty_tsla/` — forward returns on signal days vs. random days
- `studies/gap_tsl_rs_confluence/` — gap + relative strength confluence
