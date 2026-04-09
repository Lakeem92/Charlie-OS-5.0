# QuantLab Data Hygiene Rules

## Storage Traffic Light

### GREEN — Pull freely
- Daily OHLCV any ticker any window → tiny
- HTML chart files → ~500KB each, negligible
- CSV study outputs → negligible

### YELLOW — Be intentional  
- 5min intraday over 6+ months → getting large
- Same study across 20+ tickers → multiplies fast
- Old scratch notebooks → clutter

### RED — Always justify first
- 1min intraday over long windows → gigabytes fast
- Bulk historical pulls across many tickers at once
- Duplicate studies with slightly different parameters

## Study Lifecycle
1. Fill README.md BEFORE running the study
2. Update Status when study completes
3. Add a row to STUDY_INDEX.md for every new study
4. Outputs from ARCHIVED studies older than 90 days can be deleted
   (charts regenerate from scripts)
5. Never duplicate a study — extend the existing one

## Naming Convention
studies/[ticker]_[what_youre_testing]/

CORRECT:
  nvda_indicator_honesty/
  tsla_gap_down_8pct/
  fed_odds_xlf_reaction/

WRONG:
  study1/
  test_new/
  lakeem_idea_march/

## Intraday Data Rules
- 1min data: max 90 day windows unless justified
- 5min data: max 6 month windows unless justified  
- Daily data: no restriction, pull freely

## Scratch Folder Rules
- scratch/ is for testing ONLY — never real studies
- test_visualization.ipynb lives here permanently
- Everything else in scratch/ is temporary
- Clean scratch/ every 30 days

## The One Question Before Every Pull
"Is this the minimum data needed to answer the question?"
Yes → pull it. No → scope it down first.
