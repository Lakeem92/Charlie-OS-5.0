# -*- coding: utf-8 -*-
"""
Contrary Candle Study - Continuation Day Deep Dive
===================================================
Splits FT-confirmed fade/bounce events into:
  - Continuation days (trade worked: eod_return > 0)
  - Failed days (trade lost: eod_return <= 0)

Then computes the same timing/MAE/MFE analysis that the
gap-down execution blueprint did for continuation vs V-bottom.
"""
import os
import sys
import pandas as pd
import numpy as np

# ---------------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'outputs')
CSV_PATH = os.path.join(OUTPUT_DIR, 'results_analysis.csv')

if not os.path.exists(CSV_PATH):
    print(f"ERROR: {CSV_PATH} not found. Run the main study first.")
    sys.exit(1)

df = pd.read_csv(CSV_PATH)
ft = df[df['has_ft'] == True].copy()

fade_all = ft[ft['direction'] == 'GAP_UP'].copy()
bounce_all = ft[ft['direction'] == 'GAP_DN'].copy()

# Split into continuation (won) and failed (lost)
fade_cont = fade_all[fade_all['eod_return'] > 0].copy()
fade_fail = fade_all[fade_all['eod_return'] <= 0].copy()
bounce_cont = bounce_all[bounce_all['eod_return'] > 0].copy()
bounce_fail = bounce_all[bounce_all['eod_return'] <= 0].copy()

output_lines = []


def prt(line=""):
    print(line)
    output_lines.append(line)


# ---------------------------------------------------------------
# HELPER: timing distribution
# ---------------------------------------------------------------
def timing_stats(series, label):
    """Print timing distribution for a series of minutes-from-open."""
    s = series.dropna()
    if len(s) == 0:
        prt(f"    {label}: no data")
        return
    prt(f"    Median: {s.median():.0f} min ({int(s.median())//60}h {int(s.median())%60}m)")
    prt(f"    In first 5 min:   {(s<=5).mean()*100:.1f}%")
    prt(f"    In first 30 min:  {(s<=30).mean()*100:.1f}%")
    prt(f"    In first 60 min:  {(s<=60).mean()*100:.1f}%")
    prt(f"    In first 2 hrs:   {(s<=120).mean()*100:.1f}%")
    prt(f"    After 4 hours:    {(s>=240).mean()*100:.1f}%")
    prt(f"    In last hour:     {(s>=330).mean()*100:.1f}%")
    prt(f"    In last 30 min:   {(s>=360).mean()*100:.1f}%")


def pnl_stats(sub, label):
    """Print P&L profile."""
    eod = sub['eod_return'].dropna()
    if len(eod) == 0:
        prt(f"  {label}: no data")
        return
    prt(f"  {label} (n={len(eod)})")
    prt(f"    Median EOD Return: {eod.median()*100:+.2f}%")
    prt(f"    Mean EOD Return:   {eod.mean()*100:+.2f}%")
    if 'mae_pct' in sub.columns:
        mae = sub['mae_pct'].dropna()
        prt(f"    MAE Median:        {mae.median()*100:+.2f}%")
        prt(f"    MAE Mean:          {mae.mean()*100:+.2f}%")
        prt(f"    MAE 90th:          {mae.quantile(0.90)*100:+.2f}%")
    if 'mfe_pct' in sub.columns:
        mfe = sub['mfe_pct'].dropna()
        prt(f"    MFE Median:        {mfe.median()*100:+.2f}%")
        prt(f"    MFE Mean:          {mfe.mean()*100:+.2f}%")
        prt(f"    MFE 90th:          {mfe.quantile(0.90)*100:+.2f}%")
    if 'mae_pct' in sub.columns and 'mfe_pct' in sub.columns:
        mae = sub['mae_pct'].dropna()
        mfe = sub['mfe_pct'].dropna()
        if mae.median() > 0:
            prt(f"    R:R (MFE/MAE med):  {mfe.median()/mae.median():.2f}x")


# ===============================================================
prt("=" * 70)
prt("CONTRARY CANDLE STUDY - CONTINUATION DAY DEEP DIVE")
prt("=" * 70)
prt(f"Source: results_analysis.csv ({len(ft)} FT-confirmed events)")
prt(f"Date range: {ft['date'].min()} to {ft['date'].max()}")
prt("")


# ===============================================================
# SECTION 1: POPULATION SPLIT
# ===============================================================
prt("=" * 70)
prt("SECTION 1: CONTINUATION vs FAILED SPLIT")
prt("=" * 70)

prt(f"\n  GAP-UP FADES (short from FT):")
prt(f"    Total FT-confirmed:       {len(fade_all)}")
prt(f"    Continuation (short won):  {len(fade_cont)} ({len(fade_cont)/len(fade_all)*100:.1f}%)")
prt(f"    Failed (short lost):       {len(fade_fail)} ({len(fade_fail)/len(fade_all)*100:.1f}%)")

prt(f"\n  GAP-DN BOUNCES (long from FT):")
prt(f"    Total FT-confirmed:       {len(bounce_all)}")
prt(f"    Continuation (long won):   {len(bounce_cont)} ({len(bounce_cont)/len(bounce_all)*100:.1f}%)")
prt(f"    Failed (long lost):        {len(bounce_fail)} ({len(bounce_fail)/len(bounce_all)*100:.1f}%)")


# ===============================================================
# SECTION 2: CONTINUATION vs FAILED BY GAP BUCKET
# ===============================================================
prt(f"\n{'='*70}")
prt("SECTION 2: CONTINUATION RATE BY GAP BUCKET")
prt("=" * 70)

buckets = ['2-5%', '5-8%', '8-12%', '12%+']

for type_label, all_sub, cont_sub in [
    ("GAP-UP FADE (short)", fade_all, fade_cont),
    ("GAP-DN BOUNCE (long)", bounce_all, bounce_cont),
]:
    prt(f"\n  -- {type_label} --")
    prt(f"  {'Bucket':<8s} {'Total':>6s} {'Cont':>6s} {'Rate':>7s} {'AvgRet':>9s} {'MedMFE':>9s} {'MedMAE':>9s}")
    prt(f"  {'-'*8} {'-'*6} {'-'*6} {'-'*7} {'-'*9} {'-'*9} {'-'*9}")

    for b in buckets:
        total = all_sub[all_sub['gap_bucket'] == b]
        cont = cont_sub[cont_sub['gap_bucket'] == b]
        if len(total) < 3:
            prt(f"  {b:<8s} {len(total):>6d}   (too few)")
            continue
        rate = len(cont) / len(total) * 100
        avg_ret = cont['eod_return'].mean() * 100 if len(cont) > 0 else 0
        med_mfe = cont['mfe_pct'].median() * 100 if len(cont) > 0 else 0
        med_mae = cont['mae_pct'].median() * 100 if len(cont) > 0 else 0
        prt(f"  {b:<8s} {len(total):>6d} {len(cont):>6d} {rate:>6.1f}% {avg_ret:>+8.2f}% {med_mfe:>+8.2f}% {med_mae:>+8.2f}%")


# ===============================================================
# SECTION 3: LOD/HOD TIMING - THE KEY DIFFERENTIATOR
# ===============================================================
prt(f"\n{'='*70}")
prt("SECTION 3: DESTINATION TIMING (Continuation vs Failed)")
prt("  Fade destination = LoD (short wants price to go lower)")
prt("  Bounce destination = HoD (long wants price to go higher)")
prt("=" * 70)

# --- GAP-UP FADES ---
prt(f"\n  -- GAP-UP FADE: LoD Timing (destination for short) --")
prt(f"\n  Continuation (n={len(fade_cont)}):")
timing_stats(fade_cont['lod_minutes_from_open'], 'LoD')
prt(f"\n  Failed (n={len(fade_fail)}):")
timing_stats(fade_fail['lod_minutes_from_open'], 'LoD')

prt(f"\n  -- GAP-UP FADE: HoD Timing (adverse for short) --")
prt(f"\n  Continuation (n={len(fade_cont)}):")
timing_stats(fade_cont['hod_minutes_from_open'], 'HoD')
prt(f"\n  Failed (n={len(fade_fail)}):")
timing_stats(fade_fail['hod_minutes_from_open'], 'HoD')

# --- GAP-DN BOUNCES ---
prt(f"\n  -- GAP-DN BOUNCE: HoD Timing (destination for long) --")
prt(f"\n  Continuation (n={len(bounce_cont)}):")
timing_stats(bounce_cont['hod_minutes_from_open'], 'HoD')
prt(f"\n  Failed (n={len(bounce_fail)}):")
timing_stats(bounce_fail['hod_minutes_from_open'], 'HoD')

prt(f"\n  -- GAP-DN BOUNCE: LoD Timing (adverse for long) --")
prt(f"\n  Continuation (n={len(bounce_cont)}):")
timing_stats(bounce_cont['lod_minutes_from_open'], 'LoD')
prt(f"\n  Failed (n={len(bounce_fail)}):")
timing_stats(bounce_fail['lod_minutes_from_open'], 'LoD')


# ===============================================================
# SECTION 4: P&L PROFILES - CONTINUATION vs FAILED
# ===============================================================
prt(f"\n{'='*70}")
prt("SECTION 4: P&L PROFILE (Continuation vs Failed)")
prt("=" * 70)

prt(f"\n  -- GAP-UP FADES --")
pnl_stats(fade_cont, "Continuation (short won)")
pnl_stats(fade_fail, "Failed (short lost)")

prt(f"\n  -- GAP-DN BOUNCES --")
pnl_stats(bounce_cont, "Continuation (long won)")
pnl_stats(bounce_fail, "Failed (long lost)")


# ===============================================================
# SECTION 5: EARLY WARNING FILTERS
# ===============================================================
prt(f"\n{'='*70}")
prt("SECTION 5: EARLY WARNING FILTERS")
prt("  Can we identify continuation vs failed EARLY in the session?")
prt("=" * 70)

# --- FADE: LoD < 30 min ---
prt(f"\n  -- GAP-UP FADE FILTERS --")

# Filter 1: LoD in first 30 min
fade_lod_early = fade_all[fade_all['lod_minutes_from_open'] <= 30]
fade_lod_late = fade_all[fade_all['lod_minutes_from_open'] > 30]
if len(fade_lod_early) > 0:
    early_cont = (fade_lod_early['eod_return'] > 0).mean() * 100
    prt(f"  LoD in first 30 min (n={len(fade_lod_early)}): {early_cont:.1f}% continuation rate")
    prt(f"    (Interpretation: if LoD is set early, the fade may already be done)")
if len(fade_lod_late) > 0:
    late_cont = (fade_lod_late['eod_return'] > 0).mean() * 100
    prt(f"  LoD after 30 min (n={len(fade_lod_late)}): {late_cont:.1f}% continuation rate")

# Filter 2: HoD in first 5 min (adverse peak at open = strong fade signal)
fade_hod_open = fade_all[fade_all['hod_minutes_from_open'] <= 5]
fade_hod_later = fade_all[fade_all['hod_minutes_from_open'] > 5]
if len(fade_hod_open) > 0:
    hod_open_cont = (fade_hod_open['eod_return'] > 0).mean() * 100
    prt(f"  HoD in first 5 min (n={len(fade_hod_open)}): {hod_open_cont:.1f}% continuation rate")
    prt(f"    (Interpretation: gap-up topped at/near open = fade is real)")
if len(fade_hod_later) > 0:
    hod_later_cont = (fade_hod_later['eod_return'] > 0).mean() * 100
    prt(f"  HoD after 5 min (n={len(fade_hod_later)}): {hod_later_cont:.1f}% continuation rate")

# Filter 3: HoD in first 30 min
fade_hod_30 = fade_all[fade_all['hod_minutes_from_open'] <= 30]
fade_hod_after30 = fade_all[fade_all['hod_minutes_from_open'] > 30]
if len(fade_hod_30) > 0:
    prt(f"  HoD in first 30 min (n={len(fade_hod_30)}): {(fade_hod_30['eod_return']>0).mean()*100:.1f}% continuation rate")
if len(fade_hod_after30) > 0:
    prt(f"  HoD after 30 min (n={len(fade_hod_after30)}): {(fade_hod_after30['eod_return']>0).mean()*100:.1f}% continuation rate")

# Filter 4: LoD after 4 hours
fade_lod_4hr = fade_all[fade_all['lod_minutes_from_open'] >= 240]
if len(fade_lod_4hr) > 0:
    prt(f"  LoD after 4 hours (n={len(fade_lod_4hr)}): {(fade_lod_4hr['eod_return']>0).mean()*100:.1f}% continuation rate")
    prt(f"    Avg return: {fade_lod_4hr['eod_return'].mean()*100:+.2f}%")

# Filter 5: LoD in last hour
fade_lod_last = fade_all[fade_all['lod_minutes_from_open'] >= 330]
if len(fade_lod_last) > 0:
    prt(f"  LoD in last hour (n={len(fade_lod_last)}): {(fade_lod_last['eod_return']>0).mean()*100:.1f}% continuation rate")
    prt(f"    Avg return: {fade_lod_last['eod_return'].mean()*100:+.2f}%")

# Filter 6: FT in first 5 min (fast FT = strong signal?)
fade_ft_fast = fade_all[fade_all['ft_minutes_from_open'] <= 5]
fade_ft_slow = fade_all[fade_all['ft_minutes_from_open'] > 15]
if len(fade_ft_fast) > 0:
    prt(f"  FT in first 5 min (n={len(fade_ft_fast)}): {(fade_ft_fast['eod_return']>0).mean()*100:.1f}% continuation rate")
if len(fade_ft_slow) > 0:
    prt(f"  FT after 15 min (n={len(fade_ft_slow)}): {(fade_ft_slow['eod_return']>0).mean()*100:.1f}% continuation rate")

# Filter 7: HoD in last hour (on a fade = gap is NOT fading)
fade_hod_last = fade_all[fade_all['hod_minutes_from_open'] >= 330]
if len(fade_hod_last) > 0:
    prt(f"  HoD in last hour (n={len(fade_hod_last)}): {(fade_hod_last['eod_return']>0).mean()*100:.1f}% continuation rate")
    prt(f"    (If gap-up is making new highs late, your fade is dead)")

# --- BOUNCE FILTERS ---
prt(f"\n  -- GAP-DN BOUNCE FILTERS --")

# Filter 1: HoD in first 30 min
bounce_hod_early = bounce_all[bounce_all['hod_minutes_from_open'] <= 30]
bounce_hod_late = bounce_all[bounce_all['hod_minutes_from_open'] > 30]
if len(bounce_hod_early) > 0:
    prt(f"  HoD in first 30 min (n={len(bounce_hod_early)}): {(bounce_hod_early['eod_return']>0).mean()*100:.1f}% continuation rate")
    prt(f"    (Interpretation: if bounce peaks early, it may reverse)")
if len(bounce_hod_late) > 0:
    prt(f"  HoD after 30 min (n={len(bounce_hod_late)}): {(bounce_hod_late['eod_return']>0).mean()*100:.1f}% continuation rate")

# Filter 2: LoD in first 5 min (adverse low at open = strong bounce)
bounce_lod_open = bounce_all[bounce_all['lod_minutes_from_open'] <= 5]
bounce_lod_later = bounce_all[bounce_all['lod_minutes_from_open'] > 5]
if len(bounce_lod_open) > 0:
    prt(f"  LoD in first 5 min (n={len(bounce_lod_open)}): {(bounce_lod_open['eod_return']>0).mean()*100:.1f}% continuation rate")
    prt(f"    (Gap-down bottomed at open = bounce is real)")
if len(bounce_lod_later) > 0:
    prt(f"  LoD after 5 min (n={len(bounce_lod_later)}): {(bounce_lod_later['eod_return']>0).mean()*100:.1f}% continuation rate")

# Filter 3: LoD in first 30 min
bounce_lod_30 = bounce_all[bounce_all['lod_minutes_from_open'] <= 30]
bounce_lod_after30 = bounce_all[bounce_all['lod_minutes_from_open'] > 30]
if len(bounce_lod_30) > 0:
    prt(f"  LoD in first 30 min (n={len(bounce_lod_30)}): {(bounce_lod_30['eod_return']>0).mean()*100:.1f}% continuation rate")
if len(bounce_lod_after30) > 0:
    prt(f"  LoD after 30 min (n={len(bounce_lod_after30)}): {(bounce_lod_after30['eod_return']>0).mean()*100:.1f}% continuation rate")

# Filter 4: HoD after 4 hours
bounce_hod_4hr = bounce_all[bounce_all['hod_minutes_from_open'] >= 240]
if len(bounce_hod_4hr) > 0:
    prt(f"  HoD after 4 hours (n={len(bounce_hod_4hr)}): {(bounce_hod_4hr['eod_return']>0).mean()*100:.1f}% continuation rate")
    prt(f"    Avg return: {bounce_hod_4hr['eod_return'].mean()*100:+.2f}%")

# Filter 5: HoD in last hour
bounce_hod_last = bounce_all[bounce_all['hod_minutes_from_open'] >= 330]
if len(bounce_hod_last) > 0:
    prt(f"  HoD in last hour (n={len(bounce_hod_last)}): {(bounce_hod_last['eod_return']>0).mean()*100:.1f}% continuation rate")
    prt(f"    Avg return: {bounce_hod_last['eod_return'].mean()*100:+.2f}%")

# Filter 6: FT speed
bounce_ft_fast = bounce_all[bounce_all['ft_minutes_from_open'] <= 5]
bounce_ft_slow = bounce_all[bounce_all['ft_minutes_from_open'] > 15]
if len(bounce_ft_fast) > 0:
    prt(f"  FT in first 5 min (n={len(bounce_ft_fast)}): {(bounce_ft_fast['eod_return']>0).mean()*100:.1f}% continuation rate")
if len(bounce_ft_slow) > 0:
    prt(f"  FT after 15 min (n={len(bounce_ft_slow)}): {(bounce_ft_slow['eod_return']>0).mean()*100:.1f}% continuation rate")

# Filter 7: LoD in last hour on a bounce = bounce is dead
bounce_lod_last = bounce_all[bounce_all['lod_minutes_from_open'] >= 330]
if len(bounce_lod_last) > 0:
    prt(f"  LoD in last hour (n={len(bounce_lod_last)}): {(bounce_lod_last['eod_return']>0).mean()*100:.1f}% continuation rate")
    prt(f"    (If gap-down is making new lows late, your bounce is dead)")


# ===============================================================
# SECTION 6: COMBINED FILTER STACKS (best edge combos)
# ===============================================================
prt(f"\n{'='*70}")
prt("SECTION 6: COMBINED FILTER STACKS")
prt("=" * 70)

prt(f"\n  -- GAP-UP FADE: Best Setups --")
filters_fade = [
    ("No filter (baseline)", fade_all),
    ("HoD <= 5 min (topped at open)", fade_all[fade_all['hod_minutes_from_open'] <= 5]),
    ("HoD <= 5 min + gap 2-5%", fade_all[(fade_all['hod_minutes_from_open'] <= 5) & (fade_all['gap_bucket'] == '2-5%')]),
    ("HoD <= 5 min + gap 5%+", fade_all[(fade_all['hod_minutes_from_open'] <= 5) & (fade_all['abs_gap_pct'] >= 0.05)]),
    ("HoD <= 5 min + FT <= 5 min", fade_all[(fade_all['hod_minutes_from_open'] <= 5) & (fade_all['ft_minutes_from_open'] <= 5)]),
    ("LoD >= 240 min", fade_all[fade_all['lod_minutes_from_open'] >= 240]),
    ("Gap 2-5% only", fade_all[fade_all['gap_bucket'] == '2-5%']),
    ("Gap 5-8% only", fade_all[fade_all['gap_bucket'] == '5-8%']),
    ("Gap 8-12% only", fade_all[fade_all['gap_bucket'] == '8-12%']),
]

prt(f"  {'Filter':<35s} {'n':>5s} {'WR':>7s} {'AvgRet':>9s} {'MedMFE':>9s} {'MedMAE':>9s}")
prt(f"  {'-'*35} {'-'*5} {'-'*7} {'-'*9} {'-'*9} {'-'*9}")
for label, sub in filters_fade:
    if len(sub) < 5:
        continue
    eod = sub['eod_return'].dropna()
    wr = (eod > 0).mean() * 100
    avg = eod.mean() * 100
    mfe = sub['mfe_pct'].median() * 100
    mae = sub['mae_pct'].median() * 100
    prt(f"  {label:<35s} {len(sub):>5d} {wr:>6.1f}% {avg:>+8.2f}% {mfe:>+8.2f}% {mae:>+8.2f}%")

prt(f"\n  -- GAP-DN BOUNCE: Best Setups --")
filters_bounce = [
    ("No filter (baseline)", bounce_all),
    ("LoD <= 5 min (bottomed at open)", bounce_all[bounce_all['lod_minutes_from_open'] <= 5]),
    ("LoD <= 5 min + gap 2-5%", bounce_all[(bounce_all['lod_minutes_from_open'] <= 5) & (bounce_all['gap_bucket'] == '2-5%')]),
    ("LoD <= 5 min + gap 8%+", bounce_all[(bounce_all['lod_minutes_from_open'] <= 5) & (bounce_all['abs_gap_pct'] >= 0.08)]),
    ("LoD <= 5 min + FT <= 5 min", bounce_all[(bounce_all['lod_minutes_from_open'] <= 5) & (bounce_all['ft_minutes_from_open'] <= 5)]),
    ("LoD <= 30 min", bounce_all[bounce_all['lod_minutes_from_open'] <= 30]),
    ("HoD >= 240 min", bounce_all[bounce_all['hod_minutes_from_open'] >= 240]),
    ("Gap 2-5% only", bounce_all[bounce_all['gap_bucket'] == '2-5%']),
    ("Gap 5-8% only", bounce_all[bounce_all['gap_bucket'] == '5-8%']),
    ("Gap 8-12% only", bounce_all[bounce_all['gap_bucket'] == '8-12%']),
    ("Gap 12%+ only", bounce_all[bounce_all['gap_bucket'] == '12%+']),
    ("Gap 8%+ + LoD <= 5 min", bounce_all[(bounce_all['abs_gap_pct'] >= 0.08) & (bounce_all['lod_minutes_from_open'] <= 5)]),
]

prt(f"  {'Filter':<35s} {'n':>5s} {'WR':>7s} {'AvgRet':>9s} {'MedMFE':>9s} {'MedMAE':>9s}")
prt(f"  {'-'*35} {'-'*5} {'-'*7} {'-'*9} {'-'*9} {'-'*9}")
for label, sub in filters_bounce:
    if len(sub) < 5:
        continue
    eod = sub['eod_return'].dropna()
    wr = (eod > 0).mean() * 100
    avg = eod.mean() * 100
    mfe = sub['mfe_pct'].median() * 100
    mae = sub['mae_pct'].median() * 100
    prt(f"  {label:<35s} {len(sub):>5d} {wr:>6.1f}% {avg:>+8.2f}% {mfe:>+8.2f}% {mae:>+8.2f}%")


# ===============================================================
# SECTION 7: ADVERSE EXCURSION COMPARISON
# ===============================================================
prt(f"\n{'='*70}")
prt("SECTION 7: ADVERSE EXCURSION - CONTINUATION vs FAILED")
prt("  bounce_depth_before_dest = worst adverse move before destination")
prt("=" * 70)

for type_label, cont, fail in [
    ("GAP-UP FADE", fade_cont, fade_fail),
    ("GAP-DN BOUNCE", bounce_cont, bounce_fail),
]:
    prt(f"\n  -- {type_label} --")
    for sub_label, sub in [("Continuation", cont), ("Failed", fail)]:
        if 'bounce_depth_before_dest' not in sub.columns or len(sub) == 0:
            continue
        bd = sub['bounce_depth_before_dest'].dropna()
        prt(f"  {sub_label} (n={len(sub)}):")
        prt(f"    Median adverse before dest: {bd.median()*100:+.2f}%")
        prt(f"    Mean:                       {bd.mean()*100:+.2f}%")
        prt(f"    90th pctl:                  {bd.quantile(0.90)*100:+.2f}%")

    # Adverse percentile distribution
    prt(f"  Adverse distribution (bounce_depth_before_dest):")
    for sub_label, sub in [("Continuation", cont), ("Failed", fail)]:
        bd = sub['bounce_depth_before_dest'].dropna() * 100
        if len(bd) == 0:
            continue
        bins = [0, 0.5, 1.0, 2.0, 3.0, 5.0, 100]
        labels_b = ['0-0.5%', '0.5-1%', '1-2%', '2-3%', '3-5%', '5%+']
        dist = pd.cut(bd, bins=bins, labels=labels_b, right=False)
        prt(f"    {sub_label}:")
        for lb in labels_b:
            cnt = (dist == lb).sum()
            prt(f"      {lb:<8s}: {cnt:>4d} ({cnt/len(bd)*100:.1f}%)")


# ===============================================================
# SECTION 8: FT TIMING COMPARISON
# ===============================================================
prt(f"\n{'='*70}")
prt("SECTION 8: FT TIMING - CONTINUATION vs FAILED")
prt("=" * 70)

for type_label, cont, fail in [
    ("GAP-UP FADE", fade_cont, fade_fail),
    ("GAP-DN BOUNCE", bounce_cont, bounce_fail),
]:
    prt(f"\n  -- {type_label} --")
    for sub_label, sub in [("Continuation", cont), ("Failed", fail)]:
        ft_t = sub['ft_minutes_from_open'].dropna()
        if len(ft_t) == 0:
            continue
        prt(f"  {sub_label} (n={len(sub)}):")
        prt(f"    Median FT time: {ft_t.median():.0f} min")
        prt(f"    FT in first 5 min:  {(ft_t<=5).mean()*100:.1f}%")
        prt(f"    FT in first 15 min: {(ft_t<=15).mean()*100:.1f}%")
        prt(f"    FT in first 30 min: {(ft_t<=30).mean()*100:.1f}%")
        prt(f"    FT after 60 min:    {(ft_t>=60).mean()*100:.1f}%")


# ===============================================================
# SECTION 9: GAP FILL RATE - CONTINUATION vs FAILED
# ===============================================================
prt(f"\n{'='*70}")
prt("SECTION 9: GAP FILL - CONTINUATION vs FAILED")
prt("=" * 70)

prt(f"\n  -- GAP-UP FADE --")
for sub_label, sub in [("Continuation", fade_cont), ("Failed", fade_fail)]:
    if len(sub) == 0:
        continue
    close_below = (sub['close_above_open'] == False).mean() * 100
    full_fill = 0
    if 'prev_close' in sub.columns and 'session_low' in sub.columns:
        full_fill = (sub['session_low'] <= sub['prev_close']).mean() * 100
    prt(f"  {sub_label} (n={len(sub)}):")
    prt(f"    Close below open (reversal): {close_below:.1f}%")
    prt(f"    Full gap fill (low <= prev close): {full_fill:.1f}%")

prt(f"\n  -- GAP-DN BOUNCE --")
for sub_label, sub in [("Continuation", bounce_cont), ("Failed", bounce_fail)]:
    if len(sub) == 0:
        continue
    close_above = sub['close_above_open'].mean() * 100
    full_fill = 0
    if 'prev_close' in sub.columns and 'session_high' in sub.columns:
        full_fill = (sub['session_high'] >= sub['prev_close']).mean() * 100
    prt(f"  {sub_label} (n={len(sub)}):")
    prt(f"    Close above open (reversal): {close_above:.1f}%")
    prt(f"    Full gap fill (high >= prev close): {full_fill:.1f}%")


# ===============================================================
# SECTION 10: FORWARD RETURNS COMPARISON
# ===============================================================
prt(f"\n{'='*70}")
prt("SECTION 10: FORWARD RETURNS FROM ENTRY - CONT vs FAILED")
prt("=" * 70)

for type_label, cont, fail in [
    ("GAP-UP FADE", fade_cont, fade_fail),
    ("GAP-DN BOUNCE", bounce_cont, bounce_fail),
]:
    prt(f"\n  -- {type_label} --")
    prt(f"  {'Timeframe':<12s} {'Cont Avg':>10s} {'Cont WR':>8s} {'Fail Avg':>10s} {'Fail WR':>8s}")
    prt(f"  {'-'*12} {'-'*10} {'-'*8} {'-'*10} {'-'*8}")
    for col, lbl in [('fwd_15min', '15 min'), ('fwd_30min', '30 min'),
                      ('fwd_1hr', '1 hour'), ('fwd_2hr', '2 hours')]:
        c_vals = cont[col].dropna()
        f_vals = fail[col].dropna()
        if len(c_vals) == 0 or len(f_vals) == 0:
            continue
        prt(f"  {lbl:<12s} {c_vals.mean()*100:>+9.2f}% {(c_vals>0).mean()*100:>7.1f}% "
            f"{f_vals.mean()*100:>+9.2f}% {(f_vals>0).mean()*100:>7.1f}%")


# ===============================================================
# SAVE
# ===============================================================
summary_path = os.path.join(OUTPUT_DIR, 'continuation_deep_dive.txt')
with open(summary_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))
prt(f"\nSaved: {summary_path}")

prt(f"\n{'='*70}")
prt("CONTINUATION DEEP DIVE COMPLETE")
prt(f"{'='*70}")
