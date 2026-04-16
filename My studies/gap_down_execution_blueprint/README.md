# Gap-Down Execution Blueprint — Short Side Study

## The Question
> "When a stock gaps DOWN 2%+ and the first candle is neutral or bearish with downside follow-through, what does the SHORT trade look like — and when should you enter, hold, and cover?"

Mirror study of the Gap Day Execution Blueprint (long side) applied to gap-downs.

### Entry Definition (applies to all metrics in this study)

**"Entry" in this study = the close price of the first 5-minute bar that confirms downside follow-through (FT).**

Here is the exact mechanic, step by step:
1. Compute the stock's **14-period ATR** on daily bars (true range averaged over 14 days).
2. On the gap-down day, calculate the **FT level**: `Day's Open − (ATR₁₄ × 0.40)`.
3. Scan each 5-minute bar from the open. The **first bar whose Close ≤ the FT level** is the follow-through bar.
4. **Entry price = that bar's Close.** All returns, MAE, MFE, and win rates are measured from this price.

> **Example:** Stock opens at $100. ATR₁₄ = $5. FT level = $100 − ($5 × 0.40) = **$98.00**. The second 5-min bar closes at $97.80 → that $97.80 close is the entry price (short side).

## Status
**Phase 1: Base study** — running. Results pending.

## Run
```bash
cd C:\QuantLab\Data_Lab
.venv\Scripts\python.exe studies\gap_down_execution_blueprint\run_gap_down_blueprint.py
```
