"""
Gap-Down Continuation Day Deep Dive
Only analyzing the 845 winning short trades (EOD return > 0)
to find what separates them from V-bottoms.
"""

import sys, os
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')

import pandas as pd
import numpy as np

OUTPUT_DIR = r'C:\QuantLab\Data_Lab\studies\gap_down_execution_blueprint\outputs'
events_path = os.path.join(OUTPUT_DIR, 'gap_down_blueprint_events.csv')

df = pd.read_csv(events_path)
df['gap_abs'] = df['gap_pct'].abs()

all_events = df.copy()
cont = df[df['eod_return'] > 0].copy()       # continuation (short wins)
vbot = df[df['eod_return'] <= 0].copy()       # V-bottoms (short loses)

output_lines = []

def prt(line=""):
    print(line)
    output_lines.append(line)

n_all = len(all_events)
n_cont = len(cont)
n_vbot = len(vbot)

prt("=" * 70)
prt("GAP-DOWN CONTINUATION DAY DEEP DIVE")
prt(f"Total events: {n_all} | Continuation: {n_cont} ({n_cont/n_all*100:.1f}%) | V-Bottom: {n_vbot} ({n_vbot/n_all*100:.1f}%)")
prt("=" * 70)

# ═══════════════════════════════════════════════════════════════
# 1. CANDLE COLOR: DOES IT MATTER FOR CONTINUATION?
# ═══════════════════════════════════════════════════════════════
prt(f"\n{'='*60}")
prt("1. CANDLE COLOR — CONTINUATION vs V-BOTTOM")
prt(f"{'='*60}")

for color in ['BEARISH', 'NEUTRAL']:
    sub_all = all_events[all_events['candle_color'] == color]
    sub_cont = cont[cont['candle_color'] == color]
    if len(sub_all) == 0:
        continue
    cont_rate = len(sub_cont) / len(sub_all) * 100
    avg_ret_cont = sub_cont['eod_return'].mean() * 100 if len(sub_cont) > 0 else 0
    avg_mfe_cont = sub_cont['mfe_pct'].mean() * 100 if len(sub_cont) > 0 else 0
    prt(f"\n  {color} (n={len(sub_all)}):")
    prt(f"    Continuation rate:     {cont_rate:.1f}%")
    prt(f"    Avg return (winners):  {avg_ret_cont:+.2f}%")
    prt(f"    Avg MFE (winners):     +{avg_mfe_cont:.2f}%")

# ═══════════════════════════════════════════════════════════════
# 2. GAP SIZE: WHICH GAPS CONTINUE?
# ═══════════════════════════════════════════════════════════════
prt(f"\n{'='*60}")
prt("2. GAP SIZE — CONTINUATION RATE BY BUCKET")
prt(f"{'='*60}")

gap_buckets = [
    ('2-3%',   0.02, 0.03),
    ('3-5%',   0.03, 0.05),
    ('5-8%',   0.05, 0.08),
    ('8-12%',  0.08, 0.12),
    ('12-20%', 0.12, 0.20),
    ('20%+',   0.20, 1.00),
]

prt(f"\n  {'Gap':<8s} {'All':>5s} {'Cont':>5s} {'Rate':>7s} {'AvgRet':>8s} "
    f"{'MedMFE':>8s} {'MedMAE':>8s} {'MedLoD':>8s}")
prt(f"  {'-'*8} {'-'*5} {'-'*5} {'-'*7} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")

for label, lo, hi in gap_buckets:
    b_all = all_events[(all_events['gap_abs'] >= lo) & (all_events['gap_abs'] < hi)]
    b_cont = cont[(cont['gap_abs'] >= lo) & (cont['gap_abs'] < hi)]
    if len(b_all) < 5:
        continue
    rate = len(b_cont) / len(b_all) * 100
    avg_ret = b_cont['eod_return'].mean() * 100 if len(b_cont) > 0 else 0
    med_mfe = b_cont['mfe_pct'].median() * 100 if len(b_cont) > 0 else 0
    med_mae = b_cont['mae_pct'].median() * 100 if len(b_cont) > 0 else 0
    med_lod = b_cont['lod_minutes_from_open'].median() if len(b_cont) > 0 else 0
    prt(f"  {label:<8s} {len(b_all):>5d} {len(b_cont):>5d} {rate:>6.1f}% "
        f"{avg_ret:>+7.2f}% +{med_mfe:>6.2f}% +{med_mae:>6.2f}% {med_lod:>7.0f}m")

# ═══════════════════════════════════════════════════════════════
# 3. LOD TIMING — CONTINUATION DAYS ONLY
# ═══════════════════════════════════════════════════════════════
prt(f"\n{'='*60}")
prt("3. LOD TIMING — CONTINUATION DAYS ONLY (n={})".format(n_cont))
prt(f"{'='*60}")

lod = cont['lod_minutes_from_open']
prt(f"\n  Median LoD: {lod.median():.0f} min ({int(lod.median())//60}h {int(lod.median())%60}m)")
prt(f"  Mean LoD:   {lod.mean():.0f} min ({int(lod.mean())//60}h {int(lod.mean())%60}m)")
prt(f"  LoD in first 5 min:    {(lod <= 5).mean()*100:.1f}%")
prt(f"  LoD in first 15 min:   {(lod <= 15).mean()*100:.1f}%")
prt(f"  LoD in first 30 min:   {(lod <= 30).mean()*100:.1f}%")
prt(f"  LoD in first 60 min:   {(lod <= 60).mean()*100:.1f}%")
prt(f"  LoD in first 2 hours:  {(lod <= 120).mean()*100:.1f}%")
prt(f"  LoD after 4 hours:     {(lod >= 240).mean()*100:.1f}%")
prt(f"  LoD in last hour:      {(lod >= 330).mean()*100:.1f}%")
prt(f"  LoD in last 30 min:    {(lod >= 360).mean()*100:.1f}%")

# Compare to V-bottoms
lod_v = vbot['lod_minutes_from_open']
prt(f"\n  COMPARISON: Continuation vs V-Bottom LoD")
prt(f"  {'Metric':<25s} {'Continuation':>14s} {'V-Bottom':>14s}")
prt(f"  {'-'*25} {'-'*14} {'-'*14}")
prt(f"  {'Median LoD':<25s} {lod.median():>13.0f}m {lod_v.median():>13.0f}m")
prt(f"  {'LoD < 30 min':<25s} {(lod <= 30).mean()*100:>13.1f}% {(lod_v <= 30).mean()*100:>13.1f}%")
prt(f"  {'LoD > 4 hours':<25s} {(lod >= 240).mean()*100:>13.1f}% {(lod_v >= 240).mean()*100:>13.1f}%")
prt(f"  {'LoD in last hour':<25s} {(lod >= 330).mean()*100:>13.1f}% {(lod_v >= 330).mean()*100:>13.1f}%")

# ═══════════════════════════════════════════════════════════════
# 4. HOD TIMING — WHEN DOES THE BOUNCE PEAK? (CONTINUATION)
# ═══════════════════════════════════════════════════════════════
prt(f"\n{'='*60}")
prt("4. HOD TIMING — CONTINUATION DAYS (when does the bounce peak?)")
prt(f"{'='*60}")

hod = cont['hod_minutes_from_open']
prt(f"\n  Median HoD: {hod.median():.0f} min ({int(hod.median())//60}h {int(hod.median())%60}m)")
prt(f"  HoD in first 5 min:    {(hod <= 5).mean()*100:.1f}%")
prt(f"  HoD in first 15 min:   {(hod <= 15).mean()*100:.1f}%")
prt(f"  HoD in first 30 min:   {(hod <= 30).mean()*100:.1f}%")
prt(f"  HoD in first 60 min:   {(hod <= 60).mean()*100:.1f}%")
prt(f"  HoD in last hour:      {(hod >= 330).mean()*100:.1f}%")

hod_v = vbot['hod_minutes_from_open']
prt(f"\n  COMPARISON: Continuation vs V-Bottom HoD")
prt(f"  {'Metric':<25s} {'Continuation':>14s} {'V-Bottom':>14s}")
prt(f"  {'-'*25} {'-'*14} {'-'*14}")
prt(f"  {'Median HoD':<25s} {hod.median():>13.0f}m {hod_v.median():>13.0f}m")
prt(f"  {'HoD < 5 min':<25s} {(hod <= 5).mean()*100:>13.1f}% {(hod_v <= 5).mean()*100:>13.1f}%")
prt(f"  {'HoD < 30 min':<25s} {(hod <= 30).mean()*100:>13.1f}% {(hod_v <= 30).mean()*100:>13.1f}%")
prt(f"  {'HoD in last hour':<25s} {(hod >= 330).mean()*100:>13.1f}% {(hod_v >= 330).mean()*100:>13.1f}%")

# ═══════════════════════════════════════════════════════════════
# 5. P&L PROFILE — CONTINUATION DAYS ONLY
# ═══════════════════════════════════════════════════════════════
prt(f"\n{'='*60}")
prt("5. P&L PROFILE — CONTINUATION DAYS ONLY")
prt(f"{'='*60}")

mae_c = cont['mae_pct']
mfe_c = cont['mfe_pct']
eod_c = cont['eod_return']

prt(f"\n  EOD Return (short profit):")
prt(f"    Median:       {eod_c.median()*100:+.2f}%")
prt(f"    Mean:         {eod_c.mean()*100:+.2f}%")
prt(f"    25th pctl:    {eod_c.quantile(0.25)*100:+.2f}%")
prt(f"    75th pctl:    {eod_c.quantile(0.75)*100:+.2f}%")
prt(f"    Top 10%:      {eod_c.quantile(0.90)*100:+.2f}%")

prt(f"\n  MAE (worst bounce against short):")
prt(f"    Median:       +{mae_c.median()*100:.2f}%")
prt(f"    Mean:         +{mae_c.mean()*100:.2f}%")
prt(f"    90th pctl:    +{mae_c.quantile(0.90)*100:.2f}%")

prt(f"\n  MFE (best intraday drop):")
prt(f"    Median:       +{mfe_c.median()*100:.2f}%")
prt(f"    Mean:         +{mfe_c.mean()*100:.2f}%")
prt(f"    90th pctl:    +{mfe_c.quantile(0.90)*100:.2f}%")

rr_med = mfe_c.median() / mae_c.median() if mae_c.median() > 0 else 0
prt(f"\n  Median R:R (MFE/MAE):  {rr_med:.2f}x")

# How much MFE is captured at EOD?
mfe_capture = (eod_c / mfe_c).replace([np.inf, -np.inf], np.nan).dropna()
prt(f"  Median MFE captured at EOD: {mfe_capture.median()*100:.1f}%")
prt(f"  Mean MFE captured at EOD:   {mfe_capture.mean()*100:.1f}%")

# ═══════════════════════════════════════════════════════════════
# 6. BOUNCE BEHAVIOR — THE KEY FILTER
# ═══════════════════════════════════════════════════════════════
prt(f"\n{'='*60}")
prt("6. BOUNCE BEHAVIOR — CONTINUATION vs V-BOTTOM")
prt(f"{'='*60}")

prt(f"\n  Did price bounce ABOVE entry before making LoD?")
prt(f"  {'Metric':<35s} {'Continuation':>14s} {'V-Bottom':>14s}")
prt(f"  {'-'*35} {'-'*14} {'-'*14}")

bounce_c = cont['bounce_above_entry_before_lod'].mean() * 100
bounce_v = vbot['bounce_above_entry_before_lod'].mean() * 100
prt(f"  {'Bounce above entry before LoD':<35s} {bounce_c:>13.1f}% {bounce_v:>13.1f}%")

above_c = cont['price_above_entry_after_ft'].mean() * 100
above_v = vbot['price_above_entry_after_ft'].mean() * 100
prt(f"  {'Any price above entry after FT':<35s} {above_c:>13.1f}% {above_v:>13.1f}%")

bd_c = cont['bounce_depth_before_lod']
bd_v = vbot['bounce_depth_before_lod']
prt(f"\n  Bounce DEPTH before LoD (how far price goes against you):")
prt(f"  {'Metric':<35s} {'Continuation':>14s} {'V-Bottom':>14s}")
prt(f"  {'-'*35} {'-'*14} {'-'*14}")
prt(f"  {'Median bounce depth':<35s} +{bd_c.median()*100:>12.2f}% +{bd_v.median()*100:>12.2f}%")
prt(f"  {'Mean bounce depth':<35s} +{bd_c.mean()*100:>12.2f}% +{bd_v.mean()*100:>12.2f}%")
prt(f"  {'90th pctl bounce':<35s} +{bd_c.quantile(0.90)*100:>12.2f}% +{bd_v.quantile(0.90)*100:>12.2f}%")

# Bounce depth buckets
prt(f"\n  Bounce depth distribution — CONTINUATION days:")
depth_c = bd_c * 100
for lo, hi, label in [(0, 0.5, '0-0.5%'), (0.5, 1, '0.5-1%'), (1, 2, '1-2%'),
                       (2, 3, '2-3%'), (3, 5, '3-5%'), (5, 100, '5%+')]:
    pct = ((depth_c >= lo) & (depth_c < hi)).mean() * 100
    prt(f"    {label}: {pct:.1f}%")

prt(f"\n  Bounce depth distribution — V-BOTTOM days:")
depth_v = bd_v * 100
for lo, hi, label in [(0, 0.5, '0-0.5%'), (0.5, 1, '0.5-1%'), (1, 2, '1-2%'),
                       (2, 3, '2-3%'), (3, 5, '3-5%'), (5, 100, '5%+')]:
    pct = ((depth_v >= lo) & (depth_v < hi)).mean() * 100
    prt(f"    {label}: {pct:.1f}%")

# ═══════════════════════════════════════════════════════════════
# 7. FT BAR TIMING — DOES EARLY/LATE FT MATTER?
# ═══════════════════════════════════════════════════════════════
prt(f"\n{'='*60}")
prt("7. FOLLOW-THROUGH TIMING — DOES EARLY FT PREDICT CONTINUATION?")
prt(f"{'='*60}")

ft = all_events['ft_minutes_from_open']
ft_c = cont['ft_minutes_from_open']
ft_v = vbot['ft_minutes_from_open']

prt(f"\n  {'Metric':<25s} {'Continuation':>14s} {'V-Bottom':>14s}")
prt(f"  {'-'*25} {'-'*14} {'-'*14}")
prt(f"  {'Median FT timing':<25s} {ft_c.median():>13.0f}m {ft_v.median():>13.0f}m")
prt(f"  {'Mean FT timing':<25s} {ft_c.mean():>13.0f}m {ft_v.mean():>13.0f}m")

# FT within first bar (0-5 min)
for cutoff, label in [(5, 'FT in first 5 min'), (15, 'FT in first 15 min'),
                       (30, 'FT in first 30 min'), (60, 'FT in first 60 min')]:
    early_all = all_events[all_events['ft_minutes_from_open'] <= cutoff]
    early_cont = early_all[early_all['eod_return'] > 0]
    rate = len(early_cont) / len(early_all) * 100 if len(early_all) > 0 else 0
    prt(f"  {label:<25s}   n={len(early_all):>4d}  cont rate: {rate:.1f}%")

# ═══════════════════════════════════════════════════════════════
# 8. COMBINED SIGNAL: FILTER COMBOS RANKED
# ═══════════════════════════════════════════════════════════════
prt(f"\n{'='*60}")
prt("8. COMBINED FILTERS — HUNTING THE BEST CONTINUATION SETUP")
prt(f"{'='*60}")

# Filter combos
filters = [
    ("No filter (baseline)",
     all_events),
    ("FT in first 5 min (bar 0)",
     all_events[all_events['ft_minutes_from_open'] <= 5]),
    ("FT in first 15 min",
     all_events[all_events['ft_minutes_from_open'] <= 15]),
    ("Bearish candle only",
     all_events[all_events['candle_color'] == 'BEARISH']),
    ("No bounce above entry before LoD",
     all_events[all_events['bounce_above_entry_before_lod'] == False]),
    ("Bounce depth < 1%",
     all_events[all_events['bounce_depth_before_lod'] < 0.01]),
    ("Gap 5-8%",
     all_events[(all_events['gap_abs'] >= 0.05) & (all_events['gap_abs'] < 0.08)]),
    ("Gap 8-12%",
     all_events[(all_events['gap_abs'] >= 0.08) & (all_events['gap_abs'] < 0.12)]),
    ("Gap 12%+",
     all_events[all_events['gap_abs'] >= 0.12]),
    ("FT bar 0 + Bearish candle",
     all_events[(all_events['ft_minutes_from_open'] <= 5) & (all_events['candle_color'] == 'BEARISH')]),
    ("FT bar 0 + Gap 5%+",
     all_events[(all_events['ft_minutes_from_open'] <= 5) & (all_events['gap_abs'] >= 0.05)]),
    ("FT bar 0 + Gap 8%+",
     all_events[(all_events['ft_minutes_from_open'] <= 5) & (all_events['gap_abs'] >= 0.08)]),
    ("FT bar 0 + Gap 5%+ + Bearish",
     all_events[(all_events['ft_minutes_from_open'] <= 5) & (all_events['gap_abs'] >= 0.05) &
                (all_events['candle_color'] == 'BEARISH')]),
    ("Gap 8%+ + Bearish candle",
     all_events[(all_events['gap_abs'] >= 0.08) & (all_events['candle_color'] == 'BEARISH')]),
    ("Gap 8%+ + FT < 15 min",
     all_events[(all_events['gap_abs'] >= 0.08) & (all_events['ft_minutes_from_open'] <= 15)]),
    ("Gap 8%+ + FT < 15 min + Bearish",
     all_events[(all_events['gap_abs'] >= 0.08) & (all_events['ft_minutes_from_open'] <= 15) &
                (all_events['candle_color'] == 'BEARISH')]),
    ("Gap 5-12% + FT bar 0 + Bearish",
     all_events[(all_events['gap_abs'] >= 0.05) & (all_events['gap_abs'] < 0.12) &
                (all_events['ft_minutes_from_open'] <= 5) & (all_events['candle_color'] == 'BEARISH')]),
    ("Gap 12%+ + FT bar 0",
     all_events[(all_events['gap_abs'] >= 0.12) & (all_events['ft_minutes_from_open'] <= 5)]),
    ("Gap 12%+ + FT < 15 min + Bearish",
     all_events[(all_events['gap_abs'] >= 0.12) & (all_events['ft_minutes_from_open'] <= 15) &
                (all_events['candle_color'] == 'BEARISH')]),
]

prt(f"\n  {'Filter':<42s} {'n':>5s} {'WR':>7s} {'AvgRet':>8s} {'MedMFE':>8s} {'MedMAE':>8s} {'R:R':>6s} {'MedLoD':>8s}")
prt(f"  {'-'*42} {'-'*5} {'-'*7} {'-'*8} {'-'*8} {'-'*8} {'-'*6} {'-'*8}")

for label, subset in filters:
    if len(subset) < 10:
        prt(f"  {label:<42s} {len(subset):>5d}   (too few)")
        continue
    wr = (subset['eod_return'] > 0).mean() * 100
    avg_ret = subset['eod_return'].mean() * 100
    med_mfe = subset['mfe_pct'].median() * 100
    med_mae = subset['mae_pct'].median() * 100
    rr = med_mfe / med_mae if med_mae > 0 else 0
    med_lod = subset['lod_minutes_from_open'].median()
    prt(f"  {label:<42s} {len(subset):>5d} {wr:>6.1f}% {avg_ret:>+7.2f}% "
        f"+{med_mfe:>6.2f}% +{med_mae:>6.2f}% {rr:>5.2f}x {med_lod:>7.0f}m")

# ═══════════════════════════════════════════════════════════════
# 9. CONTINUATION DAY RETURN DISTRIBUTION
# ═══════════════════════════════════════════════════════════════
prt(f"\n{'='*60}")
prt("9. CONTINUATION DAY RETURN DISTRIBUTION")
prt(f"{'='*60}")

eod = cont['eod_return'] * 100
prt(f"\n  Return buckets (short profit, continuation days only):")
ret_buckets = [(0, 1, '0-1%'), (1, 2, '1-2%'), (2, 3, '2-3%'),
               (3, 5, '3-5%'), (5, 8, '5-8%'), (8, 100, '8%+')]
for lo, hi, label in ret_buckets:
    pct = ((eod >= lo) & (eod < hi)).mean() * 100
    prt(f"    {label:>6s}: {pct:.1f}%  (n={int(((eod >= lo) & (eod < hi)).sum())})")

# ═══════════════════════════════════════════════════════════════
# 10. TIME FROM ENTRY TO LOD
# ═══════════════════════════════════════════════════════════════
prt(f"\n{'='*60}")
prt("10. MAKING NEW LOWS — CONTINUATION DAYS TIMING")
prt(f"{'='*60}")

ft_c = cont['ft_minutes_from_open']
lod_c = cont['lod_minutes_from_open']

time_ft_to_lod = lod_c - ft_c
prt(f"\n  Time from follow-through entry to LoD:")
prt(f"    Median: {time_ft_to_lod.median():.0f} min")
prt(f"    Mean:   {time_ft_to_lod.mean():.0f} min")
prt(f"    < 30 min: {(time_ft_to_lod <= 30).mean()*100:.1f}%")
prt(f"    < 60 min: {(time_ft_to_lod <= 60).mean()*100:.1f}%")
prt(f"    < 2 hours: {(time_ft_to_lod <= 120).mean()*100:.1f}%")
prt(f"    > 4 hours: {(time_ft_to_lod >= 240).mean()*100:.1f}%")

# ═══════════════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════════════

save_path = os.path.join(OUTPUT_DIR, 'continuation_day_deep_dive.txt')
with open(save_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

cont_csv = os.path.join(OUTPUT_DIR, 'continuation_events_only.csv')
cont.to_csv(cont_csv, index=False)

prt(f"\n{'='*70}")
prt(f"Saved: {save_path}")
prt(f"Saved: {cont_csv}")
prt(f"{'='*70}")
