# Study Execution Protocol

## Purpose

This document defines the mandatory procedure an AI agent must follow when executing any study from [STUDY_PROMPT_LIBRARY.md](STUDY_PROMPT_LIBRARY.md).

## Scope

This protocol applies to ALL studies unless explicitly overridden in a study definition.

## Constraints

- The agent must not reinterpret study definitions
- The agent must not modify trigger logic, metrics, or timeframes
- The agent must not introduce new indicators or data sources

---

## 1. Execution Preconditions

Before executing any study, the agent must verify:

1. **Study exists** in [STUDY_PROMPT_LIBRARY.md](STUDY_PROMPT_LIBRARY.md)
2. **Required indicators exist** in `shared/indicators/` and match specifications
3. **Required data source is available** (Alpaca for US equities per [docs/API_MAP.md](API_MAP.md))
4. **Timeframe is defined** (daily or intraday resolution)
5. **Timezone is confirmed** (Central Time per [prompts/STRUCTURAL_TRIGGER_MASTER.md](../prompts/STRUCTURAL_TRIGGER_MASTER.md))

If any precondition fails, halt execution and report the missing dependency.

---

## 2. Natural Language Query Interpretation

### Purpose

Users may express research questions in natural language without referencing study IDs or technical terminology. The agent must interpret intent and map to canonical studies.

### Interpretation Rules

**Rule 1: Natural Language is Acceptable**

User queries may be expressed in natural language and do not need to reference study IDs or titles.

**Valid queries:**
- "Is my Trend Strength indicator lying to me on TSLA?"
- "Does the squeeze release actually work?"
- "Test if MAX_CONVICTION_BULL days are profitable"

**Not required:**
- "Run STUDY 001 on TSLA" (formal references are optional)

---

**Rule 2: Agent Must Map to Canonical Studies**

The agent must interpret the user's intent and map it to the most appropriate study in [STUDY_PROMPT_LIBRARY.md](STUDY_PROMPT_LIBRARY.md).

**Mapping process:**
1. Parse user question for key concepts (indicator names, timeframes, tickers, hypothesis)
2. Search [STUDY_PROMPT_LIBRARY.md](STUDY_PROMPT_LIBRARY.md) for matching study purpose and trigger definitions
3. Select the canonical study that best matches user intent

---

**Rule 3: Handle Multiple Candidates**

If multiple studies could apply, the agent must:
1. List the candidate studies with brief descriptions
2. Ask the user which one to run before execution
3. Do NOT execute speculatively or guess user intent

**Example:**
```
User: "Test if TSLA gaps are predictive"

Agent: "Multiple studies could apply:
- STUDY 001: Indicator Honesty Test (if you want to test an indicator's gap filter)
- STUDY 015: Gap Continuation Study (if testing raw gap behavior)

Which study should I run?"
```

---

**Rule 4: Handle Missing Studies**

If no existing study matches the user's question, the agent must:
1. Say so explicitly
2. Suggest creating a new canonical study
3. **NOT invent a study or partially run analysis**

**Example:**
```
User: "Analyze TSLA options IV crush after earnings"

Agent: "No canonical study in STUDY_PROMPT_LIBRARY.md matches options analysis.

Available studies focus on equity price action and indicators.

To analyze options IV:
1. Define a new canonical study in STUDY_PROMPT_LIBRARY.md
2. Specify data requirements (options chain, IV data source)
3. Define metrics and interpretation rules

Would you like to define a new study?"
```

---

**Rule 5: Study IDs Are Internal References**

Study IDs (e.g., STUDY 001) are for internal reference only and must not be required in user-facing interaction.

- Users may say "Run STUDY 001" if they know the ID
- Users may say "Is my indicator lying to me?" without knowing the ID
- Agent must accept both forms

---

### Query Mapping Examples

**Example 1: Indicator Evaluation**

```
User Query:
"Is my Trend Strength indicator lying to me on TSLA?"

Agent Interpretation:
- Key concepts: Trend Strength indicator, validation/honesty, TSLA ticker
- Search STUDY_PROMPT_LIBRARY.md
- Match found: STUDY 001 — Indicator Honesty Test (Trend Strength)

Agent Response:
"Mapping to STUDY 001 — Indicator Honesty Test (Trend Strength)
Symbol: TSLA
Classification: Indicator Evaluation Study
Proceeding with execution..."
```

**Example 2: Ambiguous Query**

```
User Query:
"Test NVDA gaps"

Agent Interpretation:
- Key concepts: NVDA, gaps
- Ambiguous: Could be raw gap analysis or indicator-filtered gaps
- No unique match

Agent Response:
"Multiple interpretations possible:
- Price/Volatility Study: Analyze raw NVDA gap behavior (size, follow-through)
- Structural Filter Study: Analyze NVDA gaps filtered by Trend Strength or TTM Squeeze

Currently available: STUDY 001 (Indicator Honesty Test)

Please clarify:
- Do you want to test if Trend Strength MAX_CONVICTION days produce better gap continuation?
- Or analyze raw gap behavior without indicators?

Note: Raw gap study is not yet defined in STUDY_PROMPT_LIBRARY.md."
```

**Example 3: No Match Found**

```
User Query:
"Backtest a 50-bar breakout strategy on SPY"

Agent Interpretation:
- Key concepts: Breakout strategy, 50-bar, SPY
- This is a strategy backtest, not a study
- No match in STUDY_PROMPT_LIBRARY.md

Agent Response:
"No canonical study matches strategy backtesting.

QuantLab Data_Lab studies evaluate:
- Price/volatility patterns (gap studies, TTP analysis)
- Indicator validity (honesty tests)
- Structural filters (squeeze release + trend alignment)

Studies do NOT backtest complete entry/exit strategies.

Available studies: STUDY 001 (Indicator Honesty Test - Trend Strength)

Would you like to define a new study or run an existing one?"
```

---

## 3. Data Handling Rules

### Price Data Source

- **All volatility, TTP, and return calculations must use Alpaca price data** unless explicitly overridden per [prompts/VOLATILITY_LAB_MASTER.md](../prompts/VOLATILITY_LAB_MASTER.md)
- Fallback sources (Tiingo, yfinance) may only be used if documented limitations in [docs/API_MAP.md](API_MAP.md) prevent Alpaca usage
- Any fallback must be explicitly noted in study outputs

### Session Windows

- **Intraday studies:** Include premarket + RTH (3:00 AM - 3:00 PM CT) unless study definition specifies otherwise
- **Daily studies:** Use official session close (3:00 PM CT / 4:00 PM ET)
- **Session defaults:** Per [prompts/STRUCTURAL_TRIGGER_MASTER.md](../prompts/STRUCTURAL_TRIGGER_MASTER.md)

### Timezone Conversion

- All timestamps returned from data sources (typically ET) must be converted to Central Time (CT) before analysis
- All time-of-day statistics (HOD timing, trigger time, etc.) must be reported in Central Time
- "Noon" means 12:00 PM CT, not ET

### Data Validation

- Verify no gaps in required price data
- Verify sufficient lookback period exists
- Report any missing data explicitly

---

## 3. Indicator Usage Rules

### Indicator Source

- Only indicators defined in indicator specification files may be used
- Indicators must be imported from `shared/indicators/`
- No ad-hoc indicator implementations

### Parameter Constraints

- Indicator parameters must match their canonical definitions
- No parameter tuning or optimization during execution
- If a study requires non-default parameters, they must be explicitly stated in the study definition

### Calculation Order

1. Fetch price data (Alpaca)
2. Apply indicator calculations
3. Identify trigger occurrences
4. Measure forward outcomes
5. Aggregate statistics

Do not reverse or skip steps.

---

## 4. Session & Time Handling Rules

### 1. Timezone Standard

**Central Time (CT) is the single authoritative timezone for all intraday studies.**

- All timestamps returned from data sources (typically Eastern Time) must be converted to Central Time before analysis
- All time-of-day statistics (HOD timing, trigger time, session windows) must be reported in Central Time
- "Noon" means 12:00 PM CT, not ET

### 2. Market Sessions (US Equities)

| Session | Time Range (CT) | Description |
|---------|----------------|-------------|
| **Premarket** | 3:00 AM – 8:29 AM | Pre-open trading session |
| **RTH (Regular Trading Hours)** | 8:30 AM – 3:00 PM | Official market hours |
| **After Hours** | 3:00 PM – 7:00 PM | Post-close trading (used only if explicitly requested) |

**Default Session:** Premarket + RTH (3:00 AM – 3:00 PM CT) per [prompts/STRUCTURAL_TRIGGER_MASTER.md](../prompts/STRUCTURAL_TRIGGER_MASTER.md)

### 3. Market Open Definition

**"Market open" is defined as 8:30 AM CT (9:30 AM ET).**

Any reference to:
- "Open"
- "Opening range"
- "First X minutes"
- "Market open"

Uses 8:30 AM CT as the reference time.

**Example:** "First 15 minutes" means 8:30 AM – 8:45 AM CT.

### 4. Premarket Handling

**Premarket data must be included in intraday studies unless explicitly excluded.**

**Premarket Metrics:**
- **Premarket High (PMH):** Highest price between 3:00 AM – 8:29 AM CT
- **Premarket Low (PML):** Lowest price between 3:00 AM – 8:29 AM CT
- **Premarket Range (PMR):** PMH - PML

**Tracking Rules:**
- Premarket highs and lows must be tracked separately from RTH highs/lows
- Studies may reference PMH/PML as breakout levels or comparison points
- If a study mentions "premarket gap," it refers to the difference between previous day's close and the premarket open (first bar at 3:00 AM CT)

### 5. High of Day (HOD) / Low of Day (LOD)

**HOD and LOD are calculated using RTH only unless otherwise specified.**

**Definition:**
- **HOD (High of Day):** Highest price during RTH (8:30 AM – 3:00 PM CT)
- **LOD (Low of Day):** Lowest price during RTH (8:30 AM – 3:00 PM CT)

**Timestamp Recording:**
- The timestamp of HOD/LOD must be recorded in Central Time
- If HOD/LOD occurs on multiple bars, use the first occurrence

**HOD Timing Buckets:**
Studies may categorize HOD timing as:
- **Early:** Before 10:00 AM CT
- **Mid:** 10:00 AM – 12:00 PM CT
- **Late:** After 12:00 PM CT

**Example:** "HOD before noon" means HOD occurred before 12:00 PM CT.

### 6. Time-Based Metrics

**Time-to-Peak (TTP):**
- **Intraday studies:** Measured from 8:30 AM CT (market open) to HOD
- **Daily studies:** Measured from signal bar close to subsequent HOD
- Reported in minutes for intraday, days for daily studies

**Time-to-Trough (TTT):**
- Follows the same logic as TTP
- Measured from reference time to LOD

**Time Interval Measurements:**
- "Next 15 minutes" = 15 minutes forward from trigger time
- "Next 1 hour" = 60 minutes forward from trigger time
- "EOD" = End of RTH session (3:00 PM CT)

### 7. Default Assumptions

**If a study references time without specifying a session, assume:**
- **Timezone:** Central Time (CT)
- **Session Context:** RTH (8:30 AM – 3:00 PM CT)
- **Reference Point:** Market open (8:30 AM CT) for intraday, bar close for daily

**Example Interpretations:**
- "Gap up at open" → Price at 8:30 AM CT vs previous close
- "First 30 minutes" → 8:30 AM – 9:00 AM CT
- "HOD timing" → Time of RTH high in CT
- "Premarket high" → Highest price 3:00 AM – 8:29 AM CT

---

## 5. Output Requirements

### Required Files

All studies must produce the following files in the study folder:

1. **Raw event table** (CSV format)
   - One row per trigger occurrence
   - Columns: date, time (CT), symbol, trigger conditions, forward returns, MFE, MAE, volatility metrics

2. **Aggregated statistics** (TXT or CSV format)
   - Win rates by horizon
   - Mean/median/percentile MFE/MAE
   - Sample size
   - Comparison group statistics (if applicable)

3. **Metadata file** (TXT format)
   - Study ID and version
   - Date range analyzed
   - Symbols analyzed
   - Data source used
   - Execution timestamp

### Output Separation

- **Data tables:** No commentary, only numbers
- **Narrative summary:** Separate file describing results in plain English
- Do not mix data and interpretation in the same file

### File Naming

- Use study folder structure: `studies/<study_name>/outputs/`
- Use descriptive filenames: `event_table.csv`, `aggregated_stats.txt`, `metadata.txt`

---

## 5. Result Interpretation Boundaries

### What the Agent May Do

- Describe statistical results objectively
- Compare groups (e.g., "Group A had 60% win rate vs Group B at 48%")
- Report sample sizes and statistical significance
- Highlight limitations (e.g., "Sample size N=15 is below threshold")

### What the Agent Must NOT Do

- Prescribe specific trades or entries
- Make forward-looking claims (e.g., "This signal will work next time")
- Recommend position sizing without user request
- Claim causation from correlation

### Required Caveats

The agent must include the following in any narrative summary:

- Sample size and whether it meets minimum threshold (typically N ≥ 20)
- Date range analyzed (results may not hold in different market regimes)
- Data source used (Alpaca, with fallback noted if applicable)
- Study limitations per the study definition's "Interpretation Rules"

---

## 6. Reproducibility Rules

### Logging Requirements

Every study execution must log:

1. **Study Identification**
   - Study ID (e.g., "STUDY 001")
   - Study name (e.g., "Indicator Honesty Test - Trend Strength")

2. **Execution Parameters**
   - Date range: start and end dates
   - Symbols: list of tickers analyzed
   - Timeframe: daily or intraday resolution
   - Session window: premarket+RTH, RTH only, etc.

3. **Data Source**
   - Primary source used (Alpaca)
   - Fallback source if used (with reason)
   - Number of bars retrieved per symbol

4. **Indicator Configuration**
   - Indicator names and versions
   - Parameters used (if non-default)

5. **Execution Metadata**
   - Execution timestamp (UTC)
   - Python environment version
   - Agent session ID (if available)

### Storage Location

All logs must be saved to `studies/<study_name>/metadata.txt` or equivalent.

---

## 7. Study Classification

Studies fall into one of three categories. The agent must correctly identify the study type before execution.

### 1. Price / Volatility Studies

**Definition:**  
Studies that analyze price action, volatility, and timing using OHLCV data only.

**Characteristics:**
- Use OHLCV, ATR, session times, and returns only
- Do NOT require any indicators
- Focus on raw market behavior

**Examples:**
- Gap studies (overnight gap measurement and follow-through)
- Time-to-Peak (TTP) analysis (when HOD/LOD occurs)
- HOD timing distributions (percentage before noon CT)
- Volatility expansion (ATR after specific events)
- Forward return calculations (Day 1, 3, 5, 10 returns)

**Execution Rule:**  
No indicators may be applied unless explicitly stated in the study definition.

---

### 2. Structural Filter Studies

**Definition:**  
Studies that use indicators as filters or conditions to isolate specific market states, then measure price behavior.

**Characteristics:**
- Use indicators only as filters or conditions
- Indicators must be defined in [docs/INDICATOR_SPECS.md](INDICATOR_SPECS.md)
- Price and volatility remain the primary measurements
- Indicators define "when" to measure, not "what" to measure

**Examples:**
- "Gaps when Trend Strength consensusClamped ≥ 70"
- "TTM Squeeze release + momentum positive"
- "NR7 compression days with MAX_CONVICTION_BULL"

**Execution Rule:**  
Only indicators explicitly named in the study definition may be used. No additional indicators may be inferred or applied.

---

### 3. Indicator Evaluation Studies

**Definition:**  
Studies that evaluate whether an indicator produces statistically asymmetric outcomes.

**Characteristics:**
- Indicators are the subject of evaluation
- Price action determines indicator validity
- Compares indicator signals to control groups (random days, moderate signals)

**Examples:**
- "Do MAX_CONVICTION_BULL days (consensusClamped ≥ 70) produce higher forward returns than random days?"
- "Does TTM Squeeze release predict volatility expansion?"
- "Is NR7 + Trend Strength agreement ≥ 0.67 predictive?"

**Execution Rule:**  
The indicator's predictive power is being tested. Price outcomes validate or invalidate the indicator's utility.

---

### Classification Rule

**If a study does not explicitly reference an indicator, the agent must not apply or infer any indicator logic.**

- Study mentions "gaps" only → Price/Volatility Study (no indicators)
- Study mentions "gaps when consensusClamped ≥ 70" → Structural Filter Study (use Trend Strength)
- Study asks "Do MAX_CONVICTION_BULL days outperform?" → Indicator Evaluation Study (test Trend Strength)

The agent must classify the study correctly and execute accordingly. Misclassification leads to invalid results.

---

## Execution Checklist

Before marking a study complete, verify:

- [ ] All preconditions met
- [ ] Data fetched from correct source (Alpaca)
- [ ] Timestamps converted to Central Time
- [ ] Indicators applied per canonical definitions
- [ ] Raw event table saved
- [ ] Aggregated statistics saved
- [ ] Metadata logged
- [ ] Interpretation includes required caveats
- [ ] No trades prescribed
- [ ] Reproducibility information complete

---

**Document Status:** ✅ Active  
**Last Updated:** December 14, 2025  
**Related Files:**
- [docs/STUDY_PROMPT_LIBRARY.md](STUDY_PROMPT_LIBRARY.md) - Study definitions
- [docs/API_MAP.md](API_MAP.md) - Data source routing
- [prompts/VOLATILITY_LAB_MASTER.md](../prompts/VOLATILITY_LAB_MASTER.md) - Volatility calculation rules
- [prompts/STRUCTURAL_TRIGGER_MASTER.md](../prompts/STRUCTURAL_TRIGGER_MASTER.md) - Session and timezone defaults
