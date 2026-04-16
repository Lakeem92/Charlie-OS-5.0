# Stop-Placement Cheat Sheet — Opening Range Violation Survival

Study: run_20260309 | n = 6,915

## How to Read This
- **OR extreme** = the high (shorts) or low (longs) of the first 5-minute candle
- **Violation** = price breaches this level AFTER the first 5-min bar closes
- **Follow-through** = session close is at least 0.70 ATR from the open in setup direction
- **Elite FT** = session close is at least 1.00 ATR from the open in setup direction

---
## Gap-Up Continuation (Long)
*OR extreme watched: Opening 5-min Low (adverse level for LONGs)*

### By Violation Depth

| Depth Bucket | n | 0.70 ATR FT | 1.00 ATR FT | Reverse FT | Conf |
|---|---|---|---|---|---|
| no_violation | 749 | 49.0% | 30.0% | 0.0% | ✅ |
| 0-0.10 ATR | 359 | 15.3% | 7.0% | 0.0% | ✅ |
| 0.10-0.25 ATR | 444 | 11.7% | 6.8% | 0.2% | ✅ |
| 0.25-0.50 ATR | 554 | 6.5% | 4.3% | 12.5% | ✅ |
| 0.50+ ATR | 848 | 1.5% | 1.1% | 29.5% | ✅ |

### By Violation Timing (from open)

| Timing Bucket | n | 0.70 ATR FT | 1.00 ATR FT | Reverse FT | Conf |
|---|---|---|---|---|---|
| no_violation | 749 | 49.0% | 30.0% | 0.0% | ✅ |
| at_open | 765 | 8.4% | 4.6% | 11.6% | ✅ |
| first_30min | 781 | 8.1% | 5.1% | 18.3% | ✅ |
| 30min_to_1hr | 245 | 6.5% | 3.3% | 17.6% | ✅ |
| 1hr_to_2hr | 198 | 4.0% | 1.5% | 13.6% | ✅ |
| 2hr_to_4hr | 143 | 3.5% | 1.4% | 9.1% | ✅ |
| after_4hr | 60 | 0.0% | 0.0% | 8.3% | ✅ |
| last_30min | 13 | 0.0% | 0.0% | 0.0% | ⚠️ LOW CONF |

### Plain-English Stop Guidance

- **HARD STOP recommended.** OR extreme holds → 49% FT rate. Any breach → drops to 7%. The 42% gap is significant.
- Shallow breach (≤0.10 ATR): 15% FT — concerning even when small.
- Deep breach (>0.50 ATR): 2% FT — SETUP BROKEN at this depth.
- Early violation (first 30 min): 8% FT — early breach = trouble.
- Late violation (after 2hr): 2% FT — late breach = GAME OVER.

---
## Gap-Down Continuation (Short)
*OR extreme watched: Opening 5-min High (adverse level for SHORTs)*

### By Violation Depth

| Depth Bucket | n | 0.70 ATR FT | 1.00 ATR FT | Reverse FT | Conf |
|---|---|---|---|---|---|
| no_violation | 492 | 11.6% | 5.7% | 12.6% | ✅ |
| 0-0.10 ATR | 230 | 13.5% | 7.0% | 13.0% | ✅ |
| 0.10-0.25 ATR | 316 | 15.5% | 8.9% | 8.5% | ✅ |
| 0.25-0.50 ATR | 387 | 10.3% | 5.2% | 13.7% | ✅ |
| 0.50+ ATR | 457 | 12.9% | 7.4% | 10.5% | ✅ |

### By Violation Timing (from open)

| Timing Bucket | n | 0.70 ATR FT | 1.00 ATR FT | Reverse FT | Conf |
|---|---|---|---|---|---|
| no_violation | 492 | 11.6% | 5.7% | 12.6% | ✅ |
| at_open | 524 | 14.5% | 8.4% | 13.2% | ✅ |
| first_30min | 479 | 11.9% | 5.4% | 11.9% | ✅ |
| 30min_to_1hr | 129 | 14.0% | 8.5% | 7.8% | ✅ |
| 1hr_to_2hr | 106 | 12.3% | 6.6% | 5.7% | ✅ |
| 2hr_to_4hr | 88 | 9.1% | 4.5% | 13.6% | ✅ |
| after_4hr | 52 | 13.5% | 11.5% | 7.7% | ✅ |
| last_30min | 12 | 0.0% | 0.0% | 0.0% | ⚠️ LOW CONF |

### Plain-English Stop Guidance

- **STOP IS LESS IMPORTANT for this path.** OR holds: 12% FT. Breach: 13% FT. OR extreme is not the dominant signal.
- Shallow breach (≤0.10 ATR): 13% FT — noise, hold through.
- Deep breach (>0.50 ATR): 13% FT — still recoverable.
- Early violation (first 30 min): 13% FT — early breach = trouble.
- Late violation (after 2hr): 10% FT — late breach = GAME OVER.

---
## Gap-Up Fade (Short)
*OR extreme watched: Opening 5-min High (adverse level for SHORTs)*

### By Violation Depth

| Depth Bucket | n | 0.70 ATR FT | 1.00 ATR FT | Reverse FT | Conf |
|---|---|---|---|---|---|
| no_violation | 516 | 43.2% | 25.4% | 92.1% | ✅ |
| 0-0.10 ATR | 131 | 16.8% | 8.4% | 73.3% | ✅ |
| 0.10-0.25 ATR | 198 | 17.2% | 9.6% | 57.1% | ✅ |
| 0.25-0.50 ATR | 212 | 6.6% | 3.8% | 39.6% | ✅ |
| 0.50+ ATR | 269 | 3.0% | 2.2% | 24.2% | ✅ |

### By Violation Timing (from open)

| Timing Bucket | n | 0.70 ATR FT | 1.00 ATR FT | Reverse FT | Conf |
|---|---|---|---|---|---|
| no_violation | 516 | 43.2% | 25.4% | 92.1% | ✅ |
| at_open | 189 | 11.1% | 6.9% | 36.0% | ✅ |
| first_30min | 339 | 12.7% | 7.4% | 39.5% | ✅ |
| 30min_to_1hr | 103 | 7.8% | 5.8% | 42.7% | ✅ |
| 1hr_to_2hr | 70 | 4.3% | 0.0% | 52.9% | ✅ |
| 2hr_to_4hr | 58 | 3.4% | 0.0% | 67.2% | ✅ |
| after_4hr | 43 | 2.3% | 0.0% | 67.4% | ✅ |
| last_30min | 8 | 0.0% | 0.0% | 87.5% | ❌ INSUFF |

### Plain-English Stop Guidance

- **HARD STOP recommended.** OR extreme holds → 43% FT rate. Any breach → drops to 10%. The 34% gap is significant.
- Shallow breach (≤0.10 ATR): 17% FT — concerning even when small.
- Deep breach (>0.50 ATR): 3% FT — SETUP BROKEN at this depth.
- Early violation (first 30 min): 12% FT — early breach = trouble.
- Late violation (after 2hr): 3% FT — late breach = GAME OVER.

---
## Gap-Down Bounce (Long)
*OR extreme watched: Opening 5-min Low (adverse level for LONGs)*

### By Violation Depth

| Depth Bucket | n | 0.70 ATR FT | 1.00 ATR FT | Reverse FT | Conf |
|---|---|---|---|---|---|
| no_violation | 159 | 17.0% | 11.3% | 58.5% | ✅ |
| 0-0.10 ATR | 102 | 15.7% | 7.8% | 55.9% | ✅ |
| 0.10-0.25 ATR | 130 | 16.9% | 9.2% | 53.1% | ✅ |
| 0.25-0.50 ATR | 157 | 11.5% | 5.7% | 54.8% | ✅ |
| 0.50+ ATR | 205 | 17.1% | 8.8% | 56.6% | ✅ |

### By Violation Timing (from open)

| Timing Bucket | n | 0.70 ATR FT | 1.00 ATR FT | Reverse FT | Conf |
|---|---|---|---|---|---|
| no_violation | 159 | 17.0% | 11.3% | 58.5% | ✅ |
| at_open | 245 | 14.3% | 6.1% | 56.7% | ✅ |
| first_30min | 225 | 12.9% | 7.6% | 49.8% | ✅ |
| 30min_to_1hr | 37 | 24.3% | 13.5% | 67.6% | ✅ |
| 1hr_to_2hr | 43 | 20.9% | 14.0% | 60.5% | ✅ |
| 2hr_to_4hr | 18 | 22.2% | 11.1% | 44.4% | ⚠️ LOW CONF |
| after_4hr | 23 | 21.7% | 8.7% | 69.6% | ✅ |
| last_30min | 3 | 0.0% | 0.0% | 66.7% | ❌ INSUFF |

### Plain-English Stop Guidance

- **STOP IS LESS IMPORTANT for this path.** OR holds: 17% FT. Breach: 15% FT. OR extreme is not the dominant signal.
- Shallow breach (≤0.10 ATR): 16% FT — noise, hold through.
- Deep breach (>0.50 ATR): 17% FT — still recoverable.
- Early violation (first 30 min): 14% FT — early breach = trouble.
- Late violation (after 2hr): 20% FT — late reversals exist.
