# Study Prompt Library

## Purpose

This document is the canonical library of reusable research study prompts for QuantLab Data_Lab.

Each study definition specifies WHAT to analyze, not HOW to execute it. Execution logic resides in Python code, not here.

## Usage Instructions

When an AI agent is asked to run a study:

1. The user references a study by name from the "Canonical Studies" section below
2. The agent reads the complete study definition
3. The agent applies the study using:
   - Data source rules from [docs/API_MAP.md](API_MAP.md)
   - Session/timezone defaults from [prompts/STRUCTURAL_TRIGGER_MASTER.md](../prompts/STRUCTURAL_TRIGGER_MASTER.md)
   - Volatility rules from [prompts/VOLATILITY_LAB_MASTER.md](../prompts/VOLATILITY_LAB_MASTER.md)
   - Indicator implementations from `shared/indicators/`
4. The agent outputs results to the appropriate study folder per workspace structure

Do NOT modify study definitions unless explicitly updating the canonical specification.

## Rules

- This file is blueprint-only (no execution)
- Do NOT write Python code here
- Do NOT fetch data here
- Do NOT compute results here
- Do NOT invent indicators
- Only reference existing indicators, data rules, and specifications already in the lab

---

## Canonical Studies

### STUDY 001 — Indicator Honesty Test (Trend Strength)

**Purpose:**  
Determine whether the Trend Strength indicator's highest conviction state produces statistically asymmetric returns or merely looks convincing visually.

**Trigger Definition:**
- Signal Type: Daily bar close
- Data Source: Alpaca (required)
- Symbols: Flexible (default: TSLA, NVDA, AMD)
- A signal day occurs when:
  - Trend Strength `consensusClamped ≥ 70`

**Comparison Groups:**
- Random trading days (same symbols, same date range)
- Moderate conviction days where:
  - `consensusClamped` between 30 and 50

**Measurements:**
- Forward returns at:
  - +1 day
  - +3 days
  - +5 days
  - +10 days
- Maximum drawdown after signal (in % and ATR terms)
- Percentage of green closes following signal
- Volatility behavior post-signal:
  - ATR expansion vs compression

**Required Outputs:**
- Event table (one row per signal)
- Aggregated performance table by group
- Drawdown distribution comparison
- Volatility regime summary

**Interpretation Rules:**
- This study evaluates signal honesty, not trade timing.
- Results determine when the indicator deserves increased size.
- Conclusions are only valid at the daily timeframe.

**Notes:**
- This study must not be modified without explicit user approval.
- Execution details belong in execution protocol, not here.

---

**Document Status:** ✅ Active  
**Last Updated:** December 14, 2025
