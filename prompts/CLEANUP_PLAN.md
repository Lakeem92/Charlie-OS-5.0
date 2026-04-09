# Data_Lab Workspace Cleanup Plan

**Date:** December 14, 2025  
**Status:** Planning Phase - NO FILES MOVED YET

---

## Current Workspace Inventory

### 📂 Root Directory Files (25 items)

#### **Prompt/Protocol Documents**
*Documentation for AI assistants and project context*
- `AGENT_CONTEXT.md` - User trading profile and methodology
- `ENVIRONMENT.md` - Complete environment and API documentation
- `README.md` - BABA/NBS study comprehensive analysis
- `README_CANNABIS.md` - Cannabis rally study comprehensive analysis
- `CLEANUP_PLAN.md` - This file (workspace reorganization plan)

#### **Study 1: BABA/NBS Conference Analysis**
*Study Code:*
- `get_nbs_dates.py` - Web scraper for China NBS conference dates
- `analyze_baba_nbs.py` - BABA price action analysis on NBS dates

*Study Output:*
- `nbs_conference_dates.txt` - 20 conference dates (April 2023 - Nov 2024)
- `baba_nbs_analysis.csv` - Structured data table with gaps/returns
- `baba_nbs_analysis.txt` - Detailed text analysis report

#### **Study 2: Cannabis Rally Comparison**
*Study Code:*
- `cannabis_rally_analysis.py` - TLRY/CGC/MSOS quantitative comparison
- `forward_returns_analysis.py` - 1-day, 3-day, 5-day forward returns
- `check_float_data.py` - Float and volume comparison TLRY vs CGC

*Study Output:*
- `cannabis_rally_comparison.csv` - Main metrics table (returns, volatility, volume)
- `cannabis_rally_analysis.txt` - Detailed text report
- `cannabis_forward_returns.csv` - Forward returns from rally endpoints
- `cannabis_forward_returns.txt` - Forward returns text report

#### **Shared Utilities**
*Reusable across studies*
- None currently isolated as utilities
  - Note: `api_clients.py` and `api_config.py` in config/ are shared utilities

#### **Config/Environment**
- `.env` - API credentials (Alpaca, Tiingo, FMP, etc.)
- `.gitignore` - Git exclusions
- `requirements.txt` - Python dependencies
- `.venv/` - Virtual environment directory

#### **Scratch/Test Files**
*One-off tests, not part of studies*
- `test_apis.py` - Original API testing script
- `test_alpaca_connection.py` - Alpaca connection test
- `test_alpaca_full.py` - Alpaca full functionality test
- `test_alpaca_sdk.py` - Alpaca SDK test (working version)
- `alpaca_examples.py` - Alpaca API usage examples

---

### 📂 Subdirectories

#### `config/`
*Shared API configuration and client classes*
- `__init__.py` - Package initialization
- `api_config.py` - Centralized API credential management
- `api_clients.py` - Ready-to-use API client classes (Tiingo, Alpaca, etc.)
- `__pycache__/` - Python bytecode cache

#### `docs/`
*API documentation*
- `API_DOCUMENTATION.md` - Comprehensive API documentation for all 8 APIs

---

## Study Identification

### Study 1: BABA x China NBS Conference Analysis
**Research Question:** Does BABA exhibit predictable price action on China NBS conference dates?

**Key Finding:** -2.56% avg 3-day return, 100% fade rate on >2.5% gap ups

**Files (5):**
1. `get_nbs_dates.py` - Data collection (web scraper)
2. `analyze_baba_nbs.py` - Analysis engine
3. `nbs_conference_dates.txt` - Raw input data (20 dates)
4. `baba_nbs_analysis.csv` - Structured results
5. `baba_nbs_analysis.txt` - Detailed report

**Documentation:** `README.md`

---

### Study 2: Cannabis Rally Comparison (2018 vs 2021)
**Research Question:** Which cannabis rally (TLRY/CGC 2018 vs MSOS 2021) had better risk-adjusted momentum characteristics?

**Key Finding:** MSOS (2021) had superior risk-adjusted returns (2.60 ratio, -32% drawdown vs TLRY's -69%)

**Files (8):**
1. `cannabis_rally_analysis.py` - Main comparison analysis
2. `forward_returns_analysis.py` - Post-rally forward returns
3. `check_float_data.py` - Float/volume comparison (TLRY vs CGC)
4. `cannabis_rally_comparison.csv` - Main metrics table
5. `cannabis_rally_analysis.txt` - Detailed comparison report
6. `cannabis_forward_returns.csv` - Forward returns data
7. `cannabis_forward_returns.txt` - Forward returns report

**Documentation:** `README_CANNABIS.md`

---

## Proposed Folder Structure

### Option A: Study-Centric (Recommended)
*Groups all study-related files together*

```
Data_Lab/
├── .env
├── .gitignore
├── .venv/
├── requirements.txt
├── AGENT_CONTEXT.md
├── ENVIRONMENT.md
│
├── config/                          # Shared utilities
│   ├── __init__.py
│   ├── api_config.py
│   ├── api_clients.py
│   └── __pycache__/
│
├── docs/                            # Documentation
│   └── API_DOCUMENTATION.md
│
├── studies/                         # All research studies
│   │
│   ├── baba_nbs/                    # Study 1: BABA x NBS
│   │   ├── README.md                # Study documentation (current root README.md)
│   │   ├── get_nbs_dates.py         # Data collection script
│   │   ├── analyze_baba_nbs.py      # Analysis script
│   │   ├── nbs_conference_dates.txt # Input data
│   │   ├── baba_nbs_analysis.csv    # Output data
│   │   └── baba_nbs_analysis.txt    # Output report
│   │
│   └── cannabis_rallies/            # Study 2: Cannabis
│       ├── README.md                # Study documentation (current README_CANNABIS.md)
│       ├── cannabis_rally_analysis.py           # Main analysis
│       ├── forward_returns_analysis.py          # Forward returns
│       ├── check_float_data.py                  # Float comparison
│       ├── cannabis_rally_comparison.csv        # Output: main metrics
│       ├── cannabis_rally_analysis.txt          # Output: main report
│       ├── cannabis_forward_returns.csv         # Output: forward returns data
│       └── cannabis_forward_returns.txt         # Output: forward returns report
│
└── archive/                         # Old/test files
    ├── test_apis.py
    ├── test_alpaca_connection.py
    ├── test_alpaca_full.py
    ├── test_alpaca_sdk.py
    └── alpaca_examples.py
```

**Benefits:**
- Each study is self-contained
- Easy to archive completed studies
- Clear separation of concerns
- Future studies follow same pattern

---

### Option B: Type-Centric (Alternative)
*Groups by file type (code vs data vs docs)*

```
Data_Lab/
├── .env
├── .gitignore
├── .venv/
├── requirements.txt
├── AGENT_CONTEXT.md
├── ENVIRONMENT.md
│
├── config/                          # Shared utilities
│   ├── __init__.py
│   ├── api_config.py
│   └── api_clients.py
│
├── scripts/                         # All analysis code
│   ├── baba/
│   │   ├── get_nbs_dates.py
│   │   └── analyze_baba_nbs.py
│   └── cannabis/
│       ├── cannabis_rally_analysis.py
│       ├── forward_returns_analysis.py
│       └── check_float_data.py
│
├── data/                            # All data files
│   ├── baba/
│   │   ├── nbs_conference_dates.txt
│   │   ├── baba_nbs_analysis.csv
│   │   └── baba_nbs_analysis.txt
│   └── cannabis/
│       ├── cannabis_rally_comparison.csv
│       ├── cannabis_rally_analysis.txt
│       ├── cannabis_forward_returns.csv
│       └── cannabis_forward_returns.txt
│
├── docs/                            # All documentation
│   ├── API_DOCUMENTATION.md
│   ├── BABA_NBS_STUDY.md            # Current README.md
│   └── CANNABIS_RALLY_STUDY.md      # Current README_CANNABIS.md
│
└── archive/                         # Test files
    └── [test files]
```

**Benefits:**
- Easy to find all scripts or all data
- Clearer for code development
- Better for data management

**Drawbacks:**
- Studies are split across multiple folders
- Harder to archive completed work

---

## Recommendation: Option A (Study-Centric)

### Why Study-Centric Wins:

1. **Self-Contained Units:** Each study is a complete research package
2. **Easy Archiving:** Move entire `studies/baba_nbs/` to archive when done
3. **Portable:** Can zip and share individual studies
4. **Scalable:** Add new studies without reorganizing existing ones
5. **Clear Context:** README.md lives with the study it documents

### Migration Complexity:
- **Low Risk:** No code changes needed (all paths are relative or current directory)
- **File Count:** 13 files to move (5 BABA + 8 Cannabis)
- **Impact:** Zero - scripts use relative paths or cwd

---

## File Movement Plan (NOT EXECUTED YET)

### Phase 1: Create Directories
```
studies/
studies/baba_nbs/
studies/cannabis_rallies/
archive/
```

### Phase 2: Move BABA Study (5 files)
```
README.md → studies/baba_nbs/README.md
get_nbs_dates.py → studies/baba_nbs/get_nbs_dates.py
analyze_baba_nbs.py → studies/baba_nbs/analyze_baba_nbs.py
nbs_conference_dates.txt → studies/baba_nbs/nbs_conference_dates.txt
baba_nbs_analysis.csv → studies/baba_nbs/baba_nbs_analysis.csv
baba_nbs_analysis.txt → studies/baba_nbs/baba_nbs_analysis.txt
```

### Phase 3: Move Cannabis Study (8 files)
```
README_CANNABIS.md → studies/cannabis_rallies/README.md
cannabis_rally_analysis.py → studies/cannabis_rallies/cannabis_rally_analysis.py
forward_returns_analysis.py → studies/cannabis_rallies/forward_returns_analysis.py
check_float_data.py → studies/cannabis_rallies/check_float_data.py
cannabis_rally_comparison.csv → studies/cannabis_rallies/cannabis_rally_comparison.csv
cannabis_rally_analysis.txt → studies/cannabis_rallies/cannabis_rally_analysis.txt
cannabis_forward_returns.csv → studies/cannabis_rallies/cannabis_forward_returns.csv
cannabis_forward_returns.txt → studies/cannabis_rallies/cannabis_forward_returns.txt
```

### Phase 4: Archive Test Files (5 files)
```
test_apis.py → archive/test_apis.py
test_alpaca_connection.py → archive/test_alpaca_connection.py
test_alpaca_full.py → archive/test_alpaca_full.py
test_alpaca_sdk.py → archive/test_alpaca_sdk.py
alpaca_examples.py → archive/alpaca_examples.py
```

### Phase 5: Verify Root Cleanliness
**Remaining in root (9 items):**
- `.env`
- `.gitignore`
- `.venv/`
- `requirements.txt`
- `AGENT_CONTEXT.md`
- `ENVIRONMENT.md`
- `CLEANUP_PLAN.md`
- `config/` (directory)
- `docs/` (directory)
- `studies/` (directory - NEW)
- `archive/` (directory - NEW)

---

## Code Impact Assessment

### Files That Reference Other Files:

#### `analyze_baba_nbs.py`
**Current:**
```python
with open('nbs_conference_dates.txt', 'r') as f:
```
**After Move:** Still works (same directory)

**Current:**
```python
df.to_csv('baba_nbs_analysis.csv', index=False)
with open('baba_nbs_analysis.txt', 'w') as f:
```
**After Move:** Still works (same directory, outputs written to cwd)

#### `get_nbs_dates.py`
**Current:**
```python
with open('nbs_conference_dates.txt', 'w') as f:
```
**After Move:** Still works (same directory)

#### Cannabis Scripts
All use relative paths or cwd, no imports between them.
**After Move:** Still works (same directory)

### ✅ **ZERO CODE CHANGES REQUIRED**
All scripts write outputs to current working directory. Moving them together preserves functionality.

---

## Benefits of Proposed Structure

### Current State (Root Clutter):
```
25 files in root directory
5 BABA files scattered
8 Cannabis files scattered
5 test files mixed in
```

### After Cleanup:
```
9 essential root files
2 organized study folders (self-contained)
1 archive folder (out of sight)
```

### Improvements:
1. **70% fewer root files** (25 → 9)
2. **Studies self-contained** (easy to share/archive)
3. **Test files archived** (not deleted, but out of the way)
4. **Future-proof** (new studies slot into studies/ folder)
5. **No code changes** (all paths remain valid)

---

## Next Steps

### To Execute This Plan:
```powershell
# Phase 1: Create directories
New-Item -ItemType Directory -Path "studies/baba_nbs"
New-Item -ItemType Directory -Path "studies/cannabis_rallies"
New-Item -ItemType Directory -Path "archive"

# Phase 2-4: Move files using Move-Item
# (Commands will be provided when user approves plan)
```

### Alternative: Stay As-Is
If the current flat structure is preferred:
- Keep all files in root
- Use naming prefixes consistently (baba_*, cannabis_*, test_*)
- Accept the 25-file root directory

---

## Questions for User

1. **Approve Option A (Study-Centric)?** Or prefer Option B (Type-Centric)?
2. **Archive test files?** Or delete them permanently?
3. **Create top-level README.md?** To explain workspace structure (since current README.md moves to baba_nbs/)?
4. **Keep CLEANUP_PLAN.md in root?** Or move to docs/ after execution?

---

## File Classification Summary

| Category | Count | Files |
|----------|-------|-------|
| **Prompt/Protocol** | 4 | AGENT_CONTEXT.md, ENVIRONMENT.md, README.md, README_CANNABIS.md |
| **Study 1 Code** | 2 | get_nbs_dates.py, analyze_baba_nbs.py |
| **Study 1 Output** | 3 | nbs_conference_dates.txt, baba_nbs_analysis.csv, baba_nbs_analysis.txt |
| **Study 2 Code** | 3 | cannabis_rally_analysis.py, forward_returns_analysis.py, check_float_data.py |
| **Study 2 Output** | 4 | cannabis_rally_comparison.csv, cannabis_rally_analysis.txt, cannabis_forward_returns.csv, cannabis_forward_returns.txt |
| **Shared Utilities** | 3 | config/api_config.py, config/api_clients.py, config/__init__.py |
| **Config/Env** | 4 | .env, .gitignore, requirements.txt, .venv/ |
| **Documentation** | 1 | docs/API_DOCUMENTATION.md |
| **Scratch/Test** | 5 | test_apis.py, test_alpaca_*.py, alpaca_examples.py |
| **TOTAL** | 29 | (25 root files + 4 in subdirs) |

---

**Status:** PLAN COMPLETE - Awaiting user approval before moving any files.
