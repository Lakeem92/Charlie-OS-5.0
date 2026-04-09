# Gap Studies README
### QuantLab Canonical Gap Research Stack
### Last Full Refresh: 2026-03-09
### Refresh Cadence: Annual, or sooner if market structure materially changes

---

## Purpose

This document is the master operating guide for all QuantLab gap studies.

It answers four questions:

1. Which studies are part of the canonical gap research stack?
2. What does each study measure?
3. Which statistics are current source-of-truth?
4. How should the full gap suite be rerun and refreshed each year?

This is the human-facing control document.

For machine-facing statistics and trading summaries, use:
- `prompts/GAP_STUDIES_MASTER_REFERENCE.md`
- `prompts/WAR_ROOM_CONTEXT.md`

---

## Canonical Gap Study Stack

### Tier 1 -- Core studies used directly in live gap thinking

| Study | Path | Purpose | Current Role |
|---|---|---|---|
| Gap-Up Continuation Blueprint | `studies/gap_execution_blueprint` | Long-side gap continuation behavior, FT timing, E1/E3 structure, HoD timing, pullback depth | Core live execution framework |
| Gap-Down Continuation Blueprint | `studies/gap_down_execution_blueprint` | Short-side gap continuation behavior, cover timing, LoD timing, bounce depth | Core live execution framework |
| Gap Fade / Contrary Candle | `studies/gap_fade_contrary_candle` | Gap-up bearish bar-1 fades and gap-down bullish bar-1 bounces | Core contrary-signal framework |
| Opening Candle Strength | `studies/opening_candle_strength` | 5-tier opening candle regime model, reverse FT analysis, timing profile, regime lookup tables | Core indicator data layer |

### Tier 2 -- Supporting / adjacent gap studies

| Study | Path | Purpose | Current Role |
|---|---|---|---|
| Beat and Sell Probability | `studies/beat_and_sell_probability` | Earnings gap-up fade / narrative ceiling behavior | Supporting earnings-gap context |
| Gap Round Number Break | `studies/gap_round_number_break` | Gap behavior around round-number levels | Supporting structure study |
| Trend Chop Gap Quality | `studies/trend_chop_gap_quality` | Trend regime / chop regime interaction with gaps | Supporting regime context |
| Gap TSL + RS Confluence | `studies/gap_tsl_rs_confluence` | Gap-down reversal behavior when TSL slope and RS align | Supporting confluence study |

### Tier 3 -- Legacy / precursor studies

These are still useful historically, but are not the primary live framework anymore:

| Study | Path | Notes |
|---|---|---|
| magenta_open_winrate | `studies/magenta_open_winrate` | Older opening-bar framing |
| magenta_vs_normal_bearish_gapup | `studies/magenta_vs_normal_bearish_gapup` | Pre-v6 opening-candle work |
| cyan_open_rising_tsl | `studies/cyan_open_rising_tsl` | Older bullish-open framework |
| cyan_candle_rising_tsl_winrate | `studies/cyan_candle_rising_tsl_winrate` | Older slope-filtered bullish-open work |

---

## Source-of-Truth Hierarchy

When multiple docs mention the same stat, use this order:

1. Raw output tables in the study folder
2. Study-specific README in that folder
3. `prompts/GAP_STUDIES_MASTER_REFERENCE.md`
4. `prompts/WAR_ROOM_CONTEXT.md`

`WAR_ROOM_CONTEXT` is the trading summary layer.
`GAP_STUDIES_MASTER_REFERENCE` is the cross-study stats layer.
Study READMEs are the detailed methodology layer.

---

## Current Core Findings To Preserve

| Finding | Result | n | Source |
|---|---|---:|---|
| Contrary candle raw signal on gap-up | 68.4% fade rate | 2,076 | `gap_fade_contrary_candle` |
| Contrary candle raw signal on gap-down | 66.8% bounce rate | 1,745 | `gap_fade_contrary_candle` |
| E3 entry on 8-12% gap-up continuation | 74.7% WR, 9.71x R:R | 79 | `gap_execution_blueprint` |
| Gap-down bearish reversed to long | 84.6% WR | 428 | `opening_candle_strength` |
| Gap-up bullish reversed to short | 83.7% WR | 471 | `opening_candle_strength` |
| Reverse FT with bullish TS level on gap-down long reversal | 90.7% WR | 150 | `opening_candle_strength` supplement |
| RS weakness into earnings gap-up | 54.2% fade rate vs 39.4% baseline | 190 | `beat_and_sell_probability` |

---

## Annual Refresh Protocol

### Trigger

Run the full refresh:
- once per year
- after a clear market regime shift
- after major data-routing changes
- after changing any canonical gap definition

### Standard refresh window

Use the full rolling history available, extending the end date to the current run date.

### Run order

Run in this order because later studies depend on earlier framing:

1. Gap-up continuation blueprint
2. Gap-down continuation blueprint
3. Gap fade / contrary candle study
4. Opening candle strength main study
5. Opening candle strength supplement
6. Supporting gap studies
7. Update cross-study docs
8. Update war-room summary edges

---

## Exact Rerun Commands

From the repo root:

```powershell
C:\QuantLab\Data_Lab\.venv\Scripts\python.exe studies\gap_execution_blueprint\run_gap_execution_blueprint.py
C:\QuantLab\Data_Lab\.venv\Scripts\python.exe studies\gap_execution_blueprint\run_extended_analysis.py

C:\QuantLab\Data_Lab\.venv\Scripts\python.exe studies\gap_down_execution_blueprint\run_gap_down_blueprint.py

C:\QuantLab\Data_Lab\.venv\Scripts\python.exe studies\gap_fade_contrary_candle\run_gap_fade_study.py
C:\QuantLab\Data_Lab\.venv\Scripts\python.exe studies\gap_fade_contrary_candle\run_continuation_deep_dive.py

C:\QuantLab\Data_Lab\.venv\Scripts\python.exe studies\opening_candle_strength\run_study.py
C:\QuantLab\Data_Lab\.venv\Scripts\python.exe studies\opening_candle_strength\supplement_ts_slope.py

C:\QuantLab\Data_Lab\.venv\Scripts\python.exe studies\beat_and_sell_probability\run_beat_and_sell.py
C:\QuantLab\Data_Lab\.venv\Scripts\python.exe studies\gap_round_number_break\run_gap_round_number_break.py
```

Optional supporting reruns, if still considered active:
- `studies/trend_chop_gap_quality/run_study.py`
- Full script chain in `studies/gap_tsl_rs_confluence/README.md`

---

## Post-Refresh Update Checklist

After rerunning the studies, update these files in order:

1. Update each study README with new sample size, date range, headline stats, and refresh date.
2. Update `prompts/GAP_STUDIES_MASTER_REFERENCE.md` with changed stats and retained edges.
3. Update `docs/STUDY_INDEX.md` with refreshed dates and current status.
4. Update `prompts/WAR_ROOM_CONTEXT.md` with still-valid confirmed edges.
5. Update indicator-facing docs if opening-candle or reverse-FT stats changed.

---

## Validation Rules Before Accepting a Refresh

Do not accept a refresh blindly. Check:

- sample sizes still meet confidence thresholds
- definitions did not drift
- FT logic is unchanged unless intentionally revised
- opening-candle tier logic is unchanged unless intentionally revised
- raw outputs and README headline stats match
- changed edges are reflected in both the master reference and war-room context

If a core edge flips materially, flag it explicitly rather than silently replacing it.

---

## Canonical Agent Prompt For Yearly Refresh

Use this exact request in VS Code when it is time:

> Run the annual gap study refresh. Re-run the full canonical gap stack: gap_execution_blueprint, gap_down_execution_blueprint, gap_fade_contrary_candle, opening_candle_strength, and the opening_candle_strength TS supplement. Then update the gap study READMEs, prompts/GAP_STUDIES_MASTER_REFERENCE.md, docs/STUDY_INDEX.md, prompts/WAR_ROOM_CONTEXT.md, and any indicator documentation impacted by changed stats. End by summarizing what changed versus the prior refresh.

---

## Minimum Required Outputs After Refresh

A refresh is not complete unless it leaves behind:

- updated study outputs in each study folder
- updated per-study README files
- updated master gap reference
- updated study index
- updated war-room confirmed edges
- a short summary of what changed, what stayed stable, and what weakened or strengthened

---

## Maintenance Notes

This lab should treat gap studies as a maintained research stack, not a one-off experiment.

The goal is not only to rerun them. The goal is to preserve:
- definitions
- methodology
- source-of-truth stats
- live trading relevance

That is what keeps the research layer trustworthy year after year.