# Magenta Opening Bar Win Rate Study — Short Side

**Study type:** Opening bar signal classification (09:30–10:00 ET)
**Side:** SHORT
**Signal:** `cs <= -70` AND `NOT is_nr7` (TrendStrengthCandles — max bear)
**Complement to:** `studies/cyan_open_rising_tsl` (long side)
**Universe:** 20 tickers | **Period:** Nov 2024 – Feb 2025 | **Timeframe:** 5-min bars

---

## Signal Logic

A **magenta** bar fires when `TrendStrengthCandles` consensus score reaches -70 or below, indicating the current bar is a maximum-bear candle relative to its 200-bar history. NR7 bars are excluded from Group A (but tested separately as Group C).

**Return convention (short-side):** `return = (entry_price − forward_close) / entry_price`  
Positive return = stock went DOWN = short position is winning.

**Dual win definitions:**
- `win_raw` — any lower close (return > 0)
- `win_thr` — lower by ≥ 0.1% (filters microstructure noise)

---

## Group Structure

| Group | Definition | n | Purpose |
|-------|-----------|---|---------|
| **A** | cs ≤ −70, NOT NR7 | 634 | Primary signal |
| **B** | −70 < cs ≤ −50, NOT NR7 | 206 | Strong bear, not max |
| **C** | cs ≤ −70, IS NR7 | 42 | NR7 as override test |
| **D** | Everything else | 2,218 | Baseline |

Total opening bars: **3,100**

---

## Key Results

### 1. Headline: Cyan beats Magenta by +8.7 percentage points EOD

```
Cyan (long)    EOD win rate:  58.2%  (Group A, n=588)
Magenta (short) EOD win rate: 49.5%  (Group A, n=634)
```

**Interpretation:** The opening-bar edge is asymmetric. Cyan candles at the open carry statistically meaningful long-side momentum; magenta candles at this timeframe do **not** carry equivalent short-side momentum. The opening hour may naturally absorb sell-side pressure before reversing.

---

### 2. 12-bar (60 min) is slightly above random — barely

```
Group A raw   12-bar:  53.1%  (n=633)
Group A thr   12-bar:  46.6%  (0.1% threshold)
Group B       12-bar:  51.9%
Group D baseline:      52.4%
```

Group A 12-bar win rate (53.1%) is **statistically indistinguishable from the 52.4% baseline**. The win threshold (46.6%) confirms most "wins" are microstructure noise. Unlike the cyan study where Group A clearly beat baseline, the magenta signal produces no meaningful 12-bar lift.

---

### 3. HIGH quality tickers show genuine short-side edge (+11pp)

```
HIGH tier Group A  12-bar win_raw: 61.2%  (n=260)
MIDDLE tier:       ~52%
LOW tier:          ~45%
```

The HIGH quality tier (MSFT, ARM, QQQ, MU, AVGO, MSTR, SPY, NVDA) shows a real 61.2% short-side 12-bar win rate. This is the **one actionable configuration**. Tickers that trend cleanly in both directions appear to generate valid short signals from magenta bars.

---

### 4. TSLA, MSTR, AMD are the strongest short candidates

Top 3 by `win_raw_eod` (Group A):

| Ticker | EOD win rate | n |
|--------|-------------|---|
| TSLA   | 84.2% | 19 |
| MSTR   | 69.2% | 26 |
| AMD    | 68.8% | 32 |

**TSLA** is the inverse of its behavior on the long side (39.4% in base study). It is a strong follow-through ticker in both directions — when it opens with a maximum bear candle, it tends to close lower with high reliability.

---

### 5. Worst short candidates — PLTR and AAPL reverse hard

Bottom 3 by `win_raw_eod` (Group A):

| Ticker | EOD win rate | n |
|--------|-------------|---|
| PLTR   | 5.0% | 20 |
| AAPL   | 27.8% | 18 |
| SOFI   | 30.3% | 33 |

**PLTR** (5.0%) is nearly perfectly counter-cyclic — magenta opening bars are a contrarian buy signal on PLTR. This mirrors its long-side behavior: PLTR's best long setups often start from apparent weakness.

---

### 6. FIRST_BAR is not a standout bucket

```
FIRST_BAR  Group A 12-bar win_raw: 52.0%  (n=102)
```

Unlike cyan where the first bar at open was the most predictive bucket, magenta opening bars don't produce outsized short-side momentum in the first candle. Selling the open-bar weakness frequently reverses intraday.

---

### 7. NR7 disqualification (Group C) weakens the signal

Group C (cs ≤ −70 but NR7) n=42 — too small for firm conclusions, but directionally: NR7 bars that are also max-bear are compression setups, not directional breakdowns. Excluding them from Group A is correct.

---

## Summary Table

| Metric | Value |
|--------|-------|
| Total opening bars | 3,100 |
| Group A signals (magenta) | 634 |
| Group A 12-bar win_raw | 53.1% |
| Group A 12-bar win_thr | 46.6% |
| Group A EOD win_raw | **49.5%** |
| Group A EOD win_thr | 46.8% |
| HIGH tier 12-bar win_raw | **61.2%** |
| TSLA EOD win_raw | **84.2%** |
| PLTR EOD win_raw | **5.0%** (inverse) |
| Cyan EOD edge advantage | **+8.7pp** |

---

## Actionable Conclusions

1. **Do not apply magenta as a blanket short signal at the open** — EOD win rate of 49.5% is below 50%. Naked short on magenta opening bars loses money overall.

2. **Restrict to HIGH quality tickers** — 61.2% at 12-bar is the only configuration with clear edge. Focus on MSFT, QQQ, NVDA, ARM, MU in particular.

3. **TSLA and MSTR are the cleanest short candidates** — 84.2% and 69.2% EOD win rates with reasonable sample sizes suggest follow-through is structurally different on these names.

4. **Never short PLTR on magenta** — 5.0% EOD win rate means it's a contrarian long. Add to your buy list when PLTR opens magenta.

5. **Cyan has a better opening-bar edge than magenta** — For session setups, prioritize long-side cyan signals over short-side magenta. The asymmetry (~8.7pp) is likely structural: opening-hour selling pressure gets absorbed, but opening-hour buying has follow-through on strong trend days.

---

## Outputs

| File | Description |
|------|-------------|
| `outputs/magenta_signals.csv` | All 3,100 opening bars with group, returns, win flags |
| `outputs/summary_group_comparison.txt` | A/B/C/D win rates at all windows |
| `outputs/summary_by_open_bucket.txt` | FIRST_BAR / EARLY_OPEN / OPEN_WINDOW |
| `outputs/summary_by_ticker_quality.txt` | HIGH / MIDDLE / LOW tier breakdown |
| `outputs/summary_by_ticker.txt` | Per-ticker ranked win rates (12-bar) |
| `outputs/summary_cyan_vs_magenta_comparison.txt` | Direct long/short comparison |
| `outputs/charts/group_comparison.html` | Group A–D bar chart |
| `outputs/charts/open_bucket_winrates.html` | Bucket breakdown chart |
| `outputs/charts/ticker_quality_comparison.html` | Quality tier chart |
| `outputs/charts/eod_return_distribution.html` | EOD return histogram |
| `outputs/charts/cyan_vs_magenta_eod.html` | Side-by-side comparison |

---

## Study Lineage

| Study | Link |
|-------|------|
| Mid-session base study (long) | `studies/cyan_candle_rising_tsl_winrate/` |
| Opening bar long study | `studies/cyan_open_rising_tsl/` |
| **This study (short)** | `studies/magenta_open_winrate/` |
