# How to Use the Lab

## The Promise

**Ask questions in normal language. The agent maps to a study and runs it.**

No study IDs required. No code. Just ask your research question, and the system handles the rest.

---

## What You Can Ask

The lab is designed for research questions about price action, indicators, and patterns. Examples:

- **"Is my Trend Strength indicator lying to me on TSLA?"**  
  Tests if MAX_CONVICTION_BULL signals actually produce better returns than random days.

- **"When does HOD usually happen on gap-up days?"**  
  Analyzes timing distributions (before 10am, 10am-noon, after noon CT).

- **"Do squeezes into the open actually continue?"**  
  Measures follow-through after TTM Squeeze releases near market open.

- **"Test if NR7 compression predicts expansion on NVDA"**  
  Evaluates if narrow range compression leads to increased volatility.

- **"Does high trend agreement lead to better forward returns?"**  
  Checks if agreement ≥ 0.67 produces asymmetric outcomes.

If your question fits a defined study, the agent runs it. If not, the agent tells you and suggests defining a new study.

---

## What the Agent Will Do (Every Time)

The workflow is consistent and governed by protocol:

1. **Interpret your intent**  
   Maps your question to the most appropriate canonical study

2. **Choose the study**  
   Selects from [STUDY_PROMPT_LIBRARY.md](STUDY_PROMPT_LIBRARY.md) (currently: indicator honesty tests, with more coming)

3. **Confirm any missing inputs**  
   Asks for ticker, date range, or timeframe if not specified (uses defaults where possible)

4. **Run the study**  
   Fetches data from Alpaca, applies indicators (if study requires them), calculates metrics

5. **Save outputs**  
   Event table, aggregated stats, metadata → all saved to `studies/<study_name>/`

6. **Summarize results**  
   Plain-English summary of findings with required caveats (sample size, limitations)

You get structured data files + a readable summary. No guessing, no manual spreadsheet work.

---

## What the Agent Will NEVER Do (Without Permission)

The lab has strict guardrails to prevent "loose springs":

- ❌ **Change indicator definitions**  
  Indicators are defined in [INDICATOR_SPECS.md](INDICATOR_SPECS.md) and cannot be modified mid-study

- ❌ **Tune parameters**  
  Default parameters are canonical. No optimization or curve-fitting during execution.

- ❌ **Switch data sources away from Alpaca for price/returns/volatility**  
  Alpaca is the single canonical source for US equity studies (per [API_MAP.md](API_MAP.md))

- ❌ **Silently exclude premarket**  
  Intraday studies include premarket + RTH (3:00 AM - 3:00 PM CT) by default

- ❌ **Invent a study if none exists**  
  If your question doesn't match a defined study, the agent tells you explicitly and suggests creating one

These rules keep results reproducible and prevent agents from improvising logic that you can't verify.

---

## When the Agent Needs Clarification

Some questions require additional inputs. The agent will ask for:

### Required (if not provided):
- **Symbols:** Which ticker(s)? (e.g., TSLA, NVDA, AMD)
- **Date range:** How far back? (default: 1-2 years)
- **Timeframe:** Daily bars or intraday (5m, 15m)?

### Optional (defaults exist):
- **Session window:** Premarket + RTH, RTH only, or custom?
- **Trigger conditions:** Specific indicator thresholds? (defaults in study definition)
- **Comparison groups:** Random days, moderate signals, or custom?

**Example interaction:**
```
You: "Is my indicator lying to me?"
Agent: "Which ticker? (default: TSLA)"
You: "NVDA"
Agent: "Date range? (default: last 2 years)"
You: "Last 1 year"
Agent: "Running STUDY 001 — Indicator Honesty Test on NVDA (2024-12-14 to 2023-12-14)..."
```

---

## Copy/Paste Examples (Ready to Use)

These requests map directly to **STUDY 001 — Indicator Honesty Test (Trend Strength)**:

### Example 1: Simple Question
```
Is my Trend Strength indicator lying to me on TSLA?
```

### Example 2: Explicit Parameters
```
Test if MAX_CONVICTION_BULL days (consensusClamped ≥ 70) produce better forward returns than random days on NVDA over the last 2 years.
```

### Example 3: Multi-Ticker
```
Run an indicator honesty test on TSLA, NVDA, and AMD. I want to see if the highest conviction trend signals actually outperform.
```

---

## Where to Find Results

After execution, check:

```
studies/<study_name>/
├── event_table.csv          # One row per signal day
├── aggregated_stats.txt     # Win rates, returns, sample size
├── drawdown_distribution.csv # MFE/MAE per occurrence
├── metadata.txt             # Study ID, date range, data source
└── summary.txt              # Plain-English findings
```

All timestamps in Central Time. All returns calculated from Alpaca price data.

---

## Quick Reference

| I Want To... | Just Ask... |
|-------------|-------------|
| Test an indicator | "Is my [indicator name] lying to me on [ticker]?" |
| Analyze timing | "When does HOD usually happen on [condition] days?" |
| Measure follow-through | "Do [trigger] setups actually continue?" |
| Check multiple tickers | "Test [hypothesis] on TSLA, NVDA, AMD" |
| Use a specific timeframe | "Run [study] using 5-minute bars" |

---

**Remember:** The lab is research infrastructure, not a trading bot. Studies evaluate patterns and indicators. You decide what to trade.

---

**Document Status:** ✅ Active  
**Last Updated:** December 14, 2025  
**Related Files:**
- [docs/STUDY_PROMPT_LIBRARY.md](STUDY_PROMPT_LIBRARY.md) - Available studies
- [docs/STUDY_EXECUTION_PROTOCOL.md](STUDY_EXECUTION_PROTOCOL.md) - How studies run
- [docs/INDICATOR_SPECS.md](INDICATOR_SPECS.md) - Indicator definitions
