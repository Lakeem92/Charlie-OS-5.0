# Charlie OS 5.0 -- Claude Agent Instructions
# War Room v10.0 | Data Lab

This file tells Claude (and any VSCode agent session) how to operate
in this repository. Read this before taking any action.

---

## Who You Are Working With

Lakeem is a full-time prop trader. He runs a pre-market War Room
6:30-8:25 AM CT using the War Room v10.0 prompt at:
  prompts/WAR_ROOM_v10.0.md

He is long AND short, momentum and trend-following. He does not want
execution advice. He wants clean data, clean analysis, clean answers.

---

## Catalyst Tracker -- AUTO-LOG PROTOCOL

After EVERY War Room analysis (any time Lakeem asks for a score or
catalyst analysis on a ticker), you MUST:

1. Extract the structured data from the analysis output:
   - ticker, analysis_date (today), sector, lifecycle_stage
   - catalyst_type (1-14), catalyst_engine (F/M/N/combo)
   - score_realness, score_freshness, score_thesis_impact,
     score_magnitude, score_stacking (each 0-2)
   - score_modifier (if any penalty applied), modifier_reason
   - score_total (final 0-10)
   - conviction_tag (HIGH/DEVELOPING/WEAK)
   - macro_context (TAILWIND/HEADWIND/NEUTRAL)
   - the_one_variable (from the verdict block)
   - thesis_summary (1-2 sentence synthesis)
   - catalyst_direction (LONG/SHORT -- direction of the catalyst)
   - is_earnings (true/false)
   - If Lakeem mentions the stock price, log it via log_outcome.py
     as price_at_analysis

2. Run this command immediately after delivering the analysis:
   python scripts/tracker/log_catalyst.py --json '<JSON_DATA>'

3. Confirm the log with a single short line, e.g.:
   "[Logged to tracker: ID #X]"

This is non-negotiable. Every analysis gets logged. No exceptions.

---

## Forward Returns -- FETCH PROTOCOL

When Lakeem asks ANYTHING about forward returns, outcomes, or
how a catalyst played out, in any natural phrasing such as:

  "What are the forward returns for NVDA after earnings?"
  "How did my TSLA catalyst play out?"
  "Show me my 5-day returns from last week"
  "What happened to [ticker] after I logged it?"
  "Pull up the outcomes for Q1 earnings"
  "Update my returns"
  "What's the follow-through on [ticker]?"

You MUST do the following IN THIS ORDER:

  STEP 1 -- Run the fetcher to get latest prices from Tiingo:
    For a specific ticker:
      python scripts/tracker/fetch_returns.py --ticker NVDA
    For everything pending:
      python scripts/tracker/fetch_returns.py --all
    For a specific ID:
      python scripts/tracker/fetch_returns.py --id <N>

  STEP 2 -- Query the database and report back:
    python scripts/tracker/query_patterns.py --report ticker --ticker NVDA
    (or whichever report fits the question)

  STEP 3 -- Interpret the results for Lakeem in plain English.
    Don't just dump numbers. Connect the return to the catalyst.
    "Your TYPE 1 NVDA call scored 8.5, 5-day return was +6.2% in the
    catalyst direction. The fundamental engine held up."

Never report stale data without running the fetcher first.
Never run the fetcher without being asked.

---

## Database Location

  data/catalyst_tracker.db   (local only, gitignored)

Scripts:
  scripts/tracker/init_db.py        -- one-time setup
  scripts/tracker/log_catalyst.py   -- log a new analysis
  scripts/tracker/log_outcome.py    -- manual outcome entry
  scripts/tracker/fetch_returns.py  -- auto-fetch prices from Tiingo
  scripts/tracker/query_patterns.py -- pattern reports

Notebook:
  notebooks/catalyst_review.ipynb   -- visual review, run any time

---

## API Stack

All API keys are in .env (gitignored). Clients in shared/config/api_clients.py.
Primary price source for return fetching: Tiingo (get_daily_prices).
Fallback: FMP (get_historical_prices if Tiingo fails).

---

## Git / GitHub

Remote: https://github.com/Lakeem92/Charlie-OS-5.0.git (private)
Branch: main
Credential files: NEVER commit shared/config/keys/, live.env, paper.env

---

## Tone

Lakeem is experienced. Skip tutorials unless he asks.
Be direct. Be fast. Get to the answer.
