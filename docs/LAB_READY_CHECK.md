# Lab Ready Check

## Purpose

This document defines the mandatory pre-flight validation the agent must perform before executing any study or answering any research question.

---

## 1. Pre-Execution Checklist (Must Pass All)

Before executing any study, the agent must verify the following items exist and are readable:

### Required Documentation
- [ ] [docs/STUDY_PROMPT_LIBRARY.md](STUDY_PROMPT_LIBRARY.md) exists and contains at least one canonical study
- [ ] [docs/STUDY_EXECUTION_PROTOCOL.md](STUDY_EXECUTION_PROTOCOL.md) exists and is readable
- [ ] [docs/INDICATOR_SPECS.md](INDICATOR_SPECS.md) exists
- [ ] [docs/HOW_TO_USE_THE_LAB.md](HOW_TO_USE_THE_LAB.md) exists

### Data Infrastructure
- [ ] Alpaca API is configured (API keys present in `.env` via `APIConfig`)
- [ ] Alpaca API is reachable (basic connectivity test passes)
- [ ] `shared/config/api_clients.py` contains `AlpacaClient` class

### Session and Timezone Rules
- [ ] Central Time (CT) conversion is available (timezone library loaded)
- [ ] Premarket + RTH session rules are loaded from [prompts/STRUCTURAL_TRIGGER_MASTER.md](../prompts/STRUCTURAL_TRIGGER_MASTER.md)
  - Premarket: 3:00 AM – 8:29 AM CT
  - RTH: 8:30 AM – 3:00 PM CT

### Optional but Recommended
- [ ] [prompts/VOLATILITY_LAB_MASTER.md](../prompts/VOLATILITY_LAB_MASTER.md) exists (Alpaca-first volatility rule)
- [ ] [docs/API_MAP.md](API_MAP.md) exists (data source routing)
- [ ] At least one indicator exists in `shared/indicators/` (if study requires indicators)

---

## 2. Execution Gate Rule

**Before running any study, the agent must silently verify all checklist items.**

### If All Items Pass:
- Proceed to study execution
- Apply natural language query interpretation per [STUDY_EXECUTION_PROTOCOL.md](STUDY_EXECUTION_PROTOCOL.md)

### If ANY Item Fails:
1. **Do not run analysis**
2. **Report the failing item clearly:**
   - "LAB NOT READY — [specific item] missing or inaccessible"
   - List what failed and why
3. **Ask the user whether to fix or stop:**
   - "Would you like me to create the missing file/configuration?"
   - "Or shall I halt execution until this is resolved?"

**No partial execution.** Do not proceed with incomplete infrastructure.

---

## 3. Natural Language Flow Confirmation

### User Input Requirements

**User does NOT need to:**
- Reference study IDs (e.g., "STUDY 001")
- Use technical terminology
- Specify all parameters upfront

**User may ask:**
- "Is my indicator lying to me on TSLA?"
- "Test squeeze releases on NVDA"
- "When does HOD usually happen?"

### Agent Responsibilities

1. **Map intent → study**
   - Parse user question for key concepts (indicator, ticker, hypothesis)
   - Search [STUDY_PROMPT_LIBRARY.md](STUDY_PROMPT_LIBRARY.md) for matching study
   - Select best match or list candidates if multiple apply

2. **Generate execution plan**
   - Identify required data (ticker, date range, timeframe)
   - Identify required indicators (if any)
   - Determine study classification (price-only, structural filter, indicator evaluation)

3. **Confirm missing inputs only**
   - If ticker missing: Ask "Which ticker?"
   - If date range missing: Use default (1-2 years)
   - If timeframe missing: Use default from study definition (daily or 5m)
   - Do NOT ask for inputs that have sensible defaults

4. **Proceed to execution**
   - Fetch data from Alpaca
   - Apply study logic per canonical definition
   - Save outputs to study folder
   - Generate summary

---

## 4. Success Declaration

### If All Checks Pass

**Agent may proceed directly to execution without further confirmation.**

Declaration:
```
LAB READY — EXECUTING
Study: [Study Name]
Symbol(s): [Ticker list]
Date Range: [Start] to [End]
Classification: [Price/Volatility | Structural Filter | Indicator Evaluation]
```

### After Execution

**Agent must:**

1. **Save outputs** to `studies/<study_name>/`
   - `event_table.csv` (raw data)
   - `aggregated_stats.txt` (summary statistics)
   - `metadata.txt` (study ID, date range, data source, execution timestamp)

2. **Summarize findings** in plain English
   - Win rates, forward returns, sample size
   - Comparison to control groups (if applicable)
   - Required caveats (sample size, limitations, date range)

3. **Reference canonical study used**
   - "Results based on [STUDY_PROMPT_LIBRARY.md](STUDY_PROMPT_LIBRARY.md) definition: [Study Name]"
   - "Execution followed [STUDY_EXECUTION_PROTOCOL.md](STUDY_EXECUTION_PROTOCOL.md)"

4. **Confirm data source**
   - "Price data: Alpaca (US equities)"
   - "Timezone: Central Time (CT)"
   - "Session: Premarket + RTH (3:00 AM - 3:00 PM CT)" (if intraday)

---

## 5. Final Verdict Language

**Use exactly one of these declarations:**

### Success Path
```
LAB READY — EXECUTING
```

**Meaning:** All checklist items passed. Study execution proceeding.

---

### Failure Path
```
LAB NOT READY — ACTION REQUIRED
```

**Meaning:** At least one checklist item failed. Execution halted until resolved.

**Required follow-up:**
- List failing items explicitly
- Suggest remediation steps
- Ask user whether to fix or stop

---

## Execution Flow Summary

```
1. User asks research question (natural language)
   ↓
2. Agent runs LAB_READY_CHECK
   ↓
3. If NOT READY → report failures, halt
   ↓
4. If READY → map intent to canonical study
   ↓
5. Confirm missing inputs (ticker, date range)
   ↓
6. Execute study per STUDY_EXECUTION_PROTOCOL
   ↓
7. Save outputs to study folder
   ↓
8. Summarize findings with caveats
```

---

## Checklist Validation (Agent Internal Use)

Before any study execution, agent must verify:

```python
# Pseudocode validation logic
def validate_lab_readiness():
    checks = {
        'STUDY_PROMPT_LIBRARY': file_exists('docs/STUDY_PROMPT_LIBRARY.md') and has_studies(),
        'STUDY_EXECUTION_PROTOCOL': file_exists('docs/STUDY_EXECUTION_PROTOCOL.md'),
        'INDICATOR_SPECS': file_exists('docs/INDICATOR_SPECS.md'),
        'HOW_TO_USE_LAB': file_exists('docs/HOW_TO_USE_THE_LAB.md'),
        'ALPACA_CONFIG': alpaca_client_exists() and api_keys_present(),
        'ALPACA_REACHABLE': test_alpaca_connection(),
        'TIMEZONE_SUPPORT': timezone_conversion_available(),
        'SESSION_RULES': session_rules_loaded(),
    }
    
    failed = [k for k, v in checks.items() if not v]
    
    if failed:
        return False, failed
    else:
        return True, []

ready, failures = validate_lab_readiness()

if not ready:
    print("LAB NOT READY — ACTION REQUIRED")
    print(f"Failed: {', '.join(failures)}")
    # Halt execution
else:
    print("LAB READY — EXECUTING")
    # Proceed with study
```

---

**Document Status:** ✅ Active  
**Last Updated:** December 14, 2025  
**Related Files:**
- [docs/STUDY_PROMPT_LIBRARY.md](STUDY_PROMPT_LIBRARY.md) - Canonical studies
- [docs/STUDY_EXECUTION_PROTOCOL.md](STUDY_EXECUTION_PROTOCOL.md) - Execution rules
- [docs/INDICATOR_SPECS.md](INDICATOR_SPECS.md) - Indicator definitions
- [docs/HOW_TO_USE_THE_LAB.md](HOW_TO_USE_THE_LAB.md) - User guide
