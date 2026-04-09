"""
QQQ Big-Up-Then-Gap-Down Study
Pattern: QQQ closes +1% or more, then gaps down ≥0.5% the next session.
Question: Does QQQ tend to close higher (open→close) on that gap-down day?
"""

import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')

import pandas as pd
import numpy as np
from shared.data_router import DataRouter

# ── Pull data ──────────────────────────────────────────
df = DataRouter.get_price_data(
    ticker="QQQ",
    start_date="2015-01-01",
    end_date="2026-03-03",
    timeframe="daily",
    source="alpaca",
    fallback=True,
    study_type="returns",
)
df = df.sort_index()

# Daily close-to-close return
df["close_ret"] = df["Close"].pct_change()
# Overnight gap: next open vs prior close
df["gap"] = df["Open"] / df["Close"].shift(1) - 1
# Intraday return on the gap-down day (open→close)
df["intraday"] = df["Close"] / df["Open"] - 1

# ── Identify pattern ──────────────────────────────────
# Day T: close_ret >= +1%
# Day T+1: gap <= -0.5%
df["big_up"] = df["close_ret"] >= 0.01
df["gap_down"] = df["gap"] <= -0.005

# Shift big_up forward so it aligns with the gap-down day
df["prev_big_up"] = df["big_up"].shift(1)
events = df[df["prev_big_up"] & df["gap_down"]].copy()

n = len(events)
wins = (events["intraday"] > 0).sum()
losses = (events["intraday"] < 0).sum()
flat = (events["intraday"] == 0).sum()

print("=" * 60)
print("  QQQ: Big Up (+1%) → Gap Down (-0.5%) Next Day")
print("=" * 60)
print(f"  Period:       2015-01-01 to 2026-03-03")
print(f"  Total events: {n}")
print()
print(f"  Win (close > open):  {wins}  ({wins/n*100:.1f}%)")
print(f"  Loss (close < open): {losses}  ({losses/n*100:.1f}%)")
print(f"  Flat:                {flat}")
print()
print(f"  Avg intraday return (O→C): {events['intraday'].mean()*100:+.2f}%")
print(f"  Median intraday return:    {events['intraday'].median()*100:+.2f}%")
print(f"  Best:                      {events['intraday'].max()*100:+.2f}%")
print(f"  Worst:                     {events['intraday'].min()*100:+.2f}%")
print(f"  Std Dev:                   {events['intraday'].std()*100:.2f}%")
print()

# ── Breakdown by gap severity ─────────────────────────
print("-" * 60)
print("  Breakdown by gap-down size:")
print("-" * 60)
for label, lo, hi in [
    ("-0.5% to -1%", -0.01, -0.005),
    ("-1% to -2%",   -0.02, -0.01),
    ("Worse than -2%", -9.0, -0.02),
]:
    sub = events[(events["gap"] > lo) & (events["gap"] <= hi)]
    if len(sub) == 0:
        continue
    wr = (sub["intraday"] > 0).mean() * 100
    avg = sub["intraday"].mean() * 100
    print(f"  {label:<20}  n={len(sub):>3}  WR={wr:5.1f}%  Avg O→C={avg:+.2f}%")

# ── Breakdown by prior-day up size ────────────────────
print()
print("-" * 60)
print("  Breakdown by prior-day close return size:")
print("-" * 60)
for label, lo, hi in [
    ("+1% to +2%", 0.01, 0.02),
    ("+2% to +3%", 0.02, 0.03),
    ("+3%+",       0.03, 9.0),
]:
    # Need to align with the gap-down day
    sub = events.copy()
    sub["prev_ret"] = df["close_ret"].shift(1).reindex(sub.index)
    sub = sub[(sub["prev_ret"] >= lo) & (sub["prev_ret"] < hi)]
    if len(sub) == 0:
        continue
    wr = (sub["intraday"] > 0).mean() * 100
    avg = sub["intraday"].mean() * 100
    print(f"  {label:<20}  n={len(sub):>3}  WR={wr:5.1f}%  Avg O→C={avg:+.2f}%")

# ── Recent examples ──────────────────────────────────
print()
print("-" * 60)
print("  Last 10 events:")
print("-" * 60)
print(f"  {'Date':<12} {'PrevClose%':>10} {'Gap%':>7} {'O→C%':>7} {'Result':>8}")
for _, r in events.tail(10).iterrows():
    prev_ret = df["close_ret"].shift(1).reindex([r.name]).iloc[0]
    tag = "✅ WIN" if r["intraday"] > 0 else "❌ LOSS"
    print(f"  {r.name.strftime('%Y-%m-%d'):<12} {prev_ret*100:>+9.2f}% {r['gap']*100:>+6.2f}% "
          f"{r['intraday']*100:>+6.2f}% {tag:>8}")

print()
print("=" * 60)
