# Opening Range Violation Survival Study — Executive Summary

Run: run_20260309 | Events: 6,915 | Tickers: 234
Period: 2024-01-23 to 2026-03-06
ATR period: 14 | FT ATR mult: 0.40 | Session: RTH 9:30-16:00 ET

---

## Gap-Up Continuation (Long)
- **n = 2,954** | OR violation rate: **74.6%**
- 0.70 ATR FT (all): 17.7% | 1.00 ATR FT (all): 10.6%
- **No violation (n=749):** 0.70 ATR FT = 49.0% | 1.00 ATR FT = 30.0%
- **With violation (n=2,205):** 0.70 ATR FT = 7.1% | 1.00 ATR FT = 4.0%
- **Violation penalty (0.70 ATR):** 41.9% ↑
- Reverse FT after OR violation: 14.5%
- Median destination time (FT days): 300 min from open
- Median adverse peak: 60 min from open
- Best depth bucket: **no_violation** (49.0% FT, n=749)
- Worst depth bucket: **0.50+ ATR** (1.5% FT, n=848)

## Gap-Down Continuation (Short)
- **n = 1,882** | OR violation rate: **73.9%**
- 0.70 ATR FT (all): 12.5% | 1.00 ATR FT (all): 6.7%
- **No violation (n=492):** 0.70 ATR FT = 11.6% | 1.00 ATR FT = 5.7%
- **With violation (n=1,390):** 0.70 ATR FT = 12.9% | 1.00 ATR FT = 7.1%
- **Violation penalty (0.70 ATR):** 1.3% ↓
- Reverse FT after OR violation: 11.4%
- Median destination time (FT days): 335 min from open
- Median adverse peak: 65 min from open
- Best depth bucket: **0.10-0.25 ATR** (15.5% FT, n=316)
- Worst depth bucket: **0.25-0.50 ATR** (10.3% FT, n=387)

## Gap-Up Fade (Short)
- **n = 1,326** | OR violation rate: **61.1%**
- 0.70 ATR FT (all): 22.7% | 1.00 ATR FT (all): 13.2%
- **No violation (n=516):** 0.70 ATR FT = 43.2% | 1.00 ATR FT = 25.4%
- **With violation (n=810):** 0.70 ATR FT = 9.6% | 1.00 ATR FT = 5.4%
- **Violation penalty (0.70 ATR):** 33.6% ↑
- Reverse FT after OR violation: 44.2%
- Median destination time (FT days): 290 min from open
- Median adverse peak: 25 min from open
- Best depth bucket: **no_violation** (43.2% FT, n=516)
- Worst depth bucket: **0.50+ ATR** (3.0% FT, n=269)

## Gap-Down Bounce (Long)
- **n = 753** | OR violation rate: **78.9%**
- 0.70 ATR FT (all): 15.7% | 1.00 ATR FT (all): 8.6%
- **No violation (n=159):** 0.70 ATR FT = 17.0% | 1.00 ATR FT = 11.3%
- **With violation (n=594):** 0.70 ATR FT = 15.3% | 1.00 ATR FT = 7.9%
- **Violation penalty (0.70 ATR):** 1.7% ↑
- Reverse FT after OR violation: 55.2%
- Median destination time (FT days): 275 min from open
- Median adverse peak: 40 min from open
- Best depth bucket: **0.50+ ATR** (17.1% FT, n=205)
- Worst depth bucket: **0.25-0.50 ATR** (11.5% FT, n=157)

---
## Confidence Flags
- ✅ n ≥ 20  |  ⚠️ LOW CONF n 10-19  |  ❌ INSUFF n < 10

---
## Indicator Update Recommendations (ATR Mooovvvee / Gap Indicator)

### 1. Label Open 5-Minute High / Low
**YES** — always label. This is the structural pivot for stop placement on all 4 paths.

### 2. Display OR Status
**YES** — show "OR HOLDING" vs "OR BREACHED" as a real-time state label.

### 3. Display Breach Depth
**YES** — show "OR BREACHED +X.XX ATR" so the trader can reference depth bucket guidance.

### 4. Include Timing of Breach in State Label
**NO** — timing context is useful but adds visual clutter. Better to track internally and flag only when late violations occur (after 2hr = elevated risk).

### 5. Per-Path Stop Treatment

**Gap-Up Continuation (Long):** `HARD STOP`
- Violation penalty: 41.9%
- Shallow breach (≤0.10 ATR): 15% FT → concerning
- Deep breach (>0.50 ATR): 2% FT → BROKEN

**Gap-Down Continuation (Short):** `SOFT STOP`
- Violation penalty: 1.3%
- Shallow breach (≤0.10 ATR): 13% FT → noise, hold
- Deep breach (>0.50 ATR): 13% FT → recoverable

**Gap-Up Fade (Short):** `HARD STOP`
- Violation penalty: 33.6%
- Shallow breach (≤0.10 ATR): 17% FT → concerning
- Deep breach (>0.50 ATR): 3% FT → BROKEN

**Gap-Down Bounce (Long):** `SOFT STOP`
- Violation penalty: 1.7%
- Shallow breach (≤0.10 ATR): 16% FT → noise, hold
- Deep breach (>0.50 ATR): 17% FT → recoverable
