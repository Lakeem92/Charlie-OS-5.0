# Beat & Sell Probability Study — Narrative Ceiling Fade

> **Study Date:** February 26, 2026
> **Status:** HYPOTHESIS NOT CONFIRMED — composite score does not reliably predict fades
> **Actionable Sub-Findings:** RS Weakness and Range Compression individually show signal

---

## Hypothesis

When mega-cap stocks beat earnings into structural distribution (no new highs, weak relative strength, beat compression, pre-earnings front-running), the probability of a post-earnings **FADE** is significantly elevated — creating a tradeable short setup.

## Methodology

| Parameter | Value |
|-----------|-------|
| Universe | 25 mega-cap stocks |
| Period | 2020-01-01 → 2026-02-26 |
| Earnings Detection | Overnight gap ≥ 2% AND volume ≥ 1.5× 20-day avg |
| Data Source | Alpaca (IEX feed) via `DataRouter` |
| Benchmark | SPY |
| Forward Windows | Day-of (open→close), +1d, +3d, +5d, +10d |

### Structural Conditions Scored (0–5 Composite "Ceiling Score")

| # | Condition | Threshold | Rationale |
|---|-----------|-----------|-----------|
| 1 | Days Since ATH | > 60 trading days | Distribution / no new highs |
| 2 | 60-Day Range Compression | < 15% total range | Stuck in a box |
| 3 | RS vs SPY (trailing 20d) | ≤ 0% | Weak relative strength |
| 4 | Pre-Earnings 5-Day Drift | > +3% | Buy-the-rumor front-running |
| 5 | Consecutive Beat Streak | ≥ 3 quarters | Beat fatigue |

### Regime Classification

- **Score 0** → CLEAN
- **Score 1** → MILD CEILING
- **Score 2** → MODERATE CEILING
- **Score 3** → NARRATIVE CEILING
- **Score 4–5** → EXTREME CEILING

---

## Results: 588 Gap-Up Events Analyzed

### Core Outcome Table

| Regime | n | Day Fade Rate | 5d Mean Return | 5d Expectancy |
|--------|--:|:------------:|:--------------:|:-------------:|
| CLEAN (0) | 28 | **53.6%** | +0.01% | +0.009% |
| MILD CEILING (1) | 175 | 46.9% | +2.02% | +2.018% |
| MODERATE CEILING (2) | 290 | 40.7% | +1.70% | +1.702% |
| NARRATIVE CEILING (3) | 82 | 48.8% | +1.30% | +1.300% |
| EXTREME CEILING (4) | 13 | 38.5% | −0.13% | −0.129% |

### Binary Split

| Group | n | Day Fade Rate | 5d Mean Return |
|-------|--:|:------------:|:--------------:|
| Clean (score 0–1) | 203 | **47.8%** | +1.74% |
| Ceiling (score 2+) | 385 | 42.3% | +1.55% |
| Extreme (score 3+) | 95 | 47.4% | +1.10% |

> **Key Finding:** The composite ceiling score does **NOT** produce a monotonically increasing fade rate. Clean events (score 0–1) actually fade **more often** (47.8%) than ceiling events (42.3%).  
> Fade rate lift = **−5.4 percentage points** — the wrong direction.

---

## Condition Power Analysis

Individual conditions tested in isolation (present vs. absent):

| Condition | n (present) | Fade Rate (present) | Fade Rate (absent) | **Fade Lift** | 5d Mean (present) |
|-----------|:-----------:|:-------------------:|:------------------:|:-------------:|:------------------:|
| Range Compressed (<15% 60d) | 21 | **71.4%** | 43.2% | **+28.2 ppts** | +0.53% |
| RS vs SPY Weak (≤0) | 190 | **54.2%** | 39.4% | **+14.8 ppts** | +1.24% |
| Beat Fatigue (3+ streak) | 88 | 50.0% | 43.2% | +6.8 ppts | +2.05% |
| Days Since ATH > 60 | 373 | 44.2% | 44.2% | +0.0 ppts | +1.15% |
| Pre-Earnings Front-Run (>3% 5d) | 381 | 34.4% | **62.3%** | **−27.9 ppts** | +2.09% |

### Key Takeaways

1. **Range Compression** is the strongest fade predictor (+28.2 ppt lift), but sample is tiny (n=21) — not yet tradeable with confidence.
2. **RS Weakness** is the most robust signal (+14.8 ppt lift, n=190) — weak relative strength into an earnings gap-up reliably predicts same-day fading.
3. **Pre-Earnings Front-Running is COUNTER-INTUITIVE** — stocks that rallied >3% in the 5 days before earnings actually **continued higher** through the gap (fade rate drops to 34.4%). Momentum into earnings = momentum through earnings.
4. **Days Since ATH** has zero predictive power on its own.

---

## NVDA Deep Dive

| Group | n | Day Fade Rate |
|-------|--:|:------------:|
| All Gap-Ups | 38 | ~55% |
| Clean (score 0–1) | 13 | 53.8% |
| Ceiling (score 2+) | 25 | 56.0% |

NVDA fades the majority of its earnings gap-ups **regardless** of ceiling conditions. The +2.2 ppt lift from ceiling score is within noise. Notable ceiling events:

- **2022-01-26** (Score 3): Gapped +4.0%, faded −2.06% day-of, then rallied +8.64% over 5d
- **2025-02-27** (Score 2): Gapped +2.6%, faded −10.93% day-of, continued to −18.10% over 5d
- **2025-05-29** (Score 3): Gapped +5.5%, faded −2.15% day-of, −1.57% over 5d

---

## Ticker Leaderboard — Highest Ceiling Fade Rates

| Ticker | Total Gap-Ups | Ceiling Events | Ceiling Fade Rate | Ceiling 5d Mean |
|--------|:------------:|:--------------:|:-----------------:|:---------------:|
| MSFT | 14 | 10 | **70.0%** | +0.45% |
| UNH | 14 | 12 | **58.3%** | +0.82% |
| META | 28 | 14 | **57.1%** | −0.63% |
| JPM | 15 | 7 | **57.1%** | +3.47% |
| HD | 8 | 7 | **57.1%** | +0.50% |
| NVDA | 38 | 25 | 56.0% | −0.67% |
| CRM | 28 | 20 | 55.0% | −0.58% |

---

## Conclusion

**The "Narrative Ceiling" composite hypothesis is NOT confirmed as a tradeable edge.** The 5-factor score does not reliably separate post-earnings winners from faders.

### What IS Worth Watching

If refining this study further, isolate a **2-factor filter**:

1. **RS Weakness (≤0 vs SPY trailing 20d)** — 54.2% fade rate, +14.8 ppt lift, n=190
2. **Range Compression (<15% 60d range)** — 71.4% fade rate, +28.2 ppt lift, n=21 (needs more data)

These two conditions combined may produce a smaller but more reliable "Narrative Ceiling" subset.

### War Room Recommendation

- **Do NOT** add § 9F BEAT ABSORPTION FILTER based on the composite score as designed
- **Do** flag RS Weakness as a caution modifier on earnings gap-up plays
- Consider a future V2 study with real earnings dates (not gap proxies) and the 2-factor filter

---

## Outputs

| File | Description |
|------|-------------|
| `outputs/all_events.csv` | All 588 gap-up events with scores and forward returns |
| `outputs/condition_power.csv` | Individual condition fade lift analysis |
| `outputs/nvda_deep_dive.csv` | NVDA-specific event history |
| `outputs/summary_stats.txt` | Plain-text summary statistics |
| `outputs/charts/ceiling_score_vs_outcomes.html` | Fade rate & 5d return by score |
| `outputs/charts/condition_power.html` | Condition power grouped bar chart |
| `outputs/charts/nvda_ceiling_timeline.html` | NVDA ceiling score timeline |

## How to Run

```bash
cd C:\QuantLab\Data_Lab
python studies/beat_and_sell_probability/run_beat_and_sell.py
```

Requires: Alpaca API keys loaded via `.env`, Python 3.13 venv with `alpaca-py`, `pandas`, `numpy`, `plotly`.
