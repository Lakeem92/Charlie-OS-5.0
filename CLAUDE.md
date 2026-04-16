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

## War Room Prompt

The analysis framework lives at:
  prompts/WAR_ROOM_v10.0.md

All War Room analyses MUST follow this prompt. Scoring uses §7C
dimensions (5 dimensions, each 0-2, max 10). Verdict tags from §11C.
The One Variable is MANDATORY on every analysis. The formal score
block (§3 format) closes every analysis. No exceptions.

Tunable scoring parameters: prompts/war_room_params.yaml
Session state: prompts/WAR_ROOM_CONTEXT.md (read at session start)

---

## API Stack

All API keys are in .env (gitignored). Clients in shared/config/api_clients.py.
Primary price source: Tiingo (get_daily_prices).
Fallback: FMP (get_historical_prices if Tiingo fails).
News: Benzinga (BENZINGA_API_KEY in .env) — nice-to-have, not yet wired.

---

## Dashboard — Diet Bloomberg Terminal

Runs at localhost:8766 via `python "Diet Bloomberg/serve.py"`.
Data is collected by scripts in data_collectors/ and written to
catalyst_analysis_db/ (the main data store — confusingly named, ignore
the "catalyst" part, it holds all dashboard data).

Collectors:
  data_collectors/macro_collector.py    -- macro regime, COT, rates
  data_collectors/ai_cascade_collector.py -- AI supercycle flows
  data_collectors/etf_collector.py      -- ETF structural + momentum
  data_collectors/focus_list_collector.py -- focus list prices
  data_collectors/news_collector.py     -- news feed

---

## Git / GitHub

Remote: https://github.com/Lakeem92/Charlie-OS-5.0.git (private)
Branch: main
Credential files: NEVER commit shared/config/keys/, live.env, paper.env

---

## Tone

Lakeem is experienced. Skip tutorials unless he asks.
Be direct. Be fast. Get to the answer.
