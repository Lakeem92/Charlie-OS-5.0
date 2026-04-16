"""
Opening Range Violation Survival Study — Analysis & Output Generation
=====================================================================
Loads enriched event dataset from collect_or_data.py, runs all cross-tabs,
generates executive summary, stop-placement cheatsheet, timing tables,
charts, and JSON summary.
"""

import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# ─── Configuration ───────────────────────────────────────────────
STUDY_DIR = Path(r'C:\QuantLab\Data_Lab\studies\opening_range_violation_survival_study')
RUN_ID = 'run_20260309'
OUTPUT_DIR = STUDY_DIR / 'outputs' / RUN_ID
CHART_DIR = OUTPUT_DIR / 'charts'
CACHE_FILE = OUTPUT_DIR / 'or_master_events.csv'

PATH_ORDER = [
    'gapup_continuation_long',
    'gapdown_continuation_short',
    'gapup_fade_short',
    'gapdown_bounce_long',
]
PATH_LABELS = {
    'gapup_continuation_long': 'Gap-Up Continuation (Long)',
    'gapdown_continuation_short': 'Gap-Down Continuation (Short)',
    'gapup_fade_short': 'Gap-Up Fade (Short)',
    'gapdown_bounce_long': 'Gap-Down Bounce (Long)',
}
DEPTH_ORDER = ['no_violation', '0-0.10 ATR', '0.10-0.25 ATR', '0.25-0.50 ATR', '0.50+ ATR']
GAP_BUCKET_ORDER = ['2-5%', '5-8%', '8-12%', '12%+']
TIMING_ABS_ORDER = [
    'no_violation', 'at_open', 'first_30min', '30min_to_1hr',
    '1hr_to_2hr', '2hr_to_4hr', 'after_4hr', 'last_30min'
]

GREEN = '#26a69a'
RED = '#ef5350'
BLUE = '#42a5f5'
AMBER = '#ffa726'
GREY = '#78909c'


def confidence_flag(n):
    if n >= 20:
        return '✅'
    if n >= 10:
        return '⚠️ LOW CONF'
    return '❌ INSUFF'


# ─── Load Data ───────────────────────────────────────────────────

def load_data():
    print("Loading enriched events from cache...")
    df = pd.read_csv(CACHE_FILE)
    df['or_violated'] = df['or_violated'].astype(bool)
    df['achieved_0p70_atr'] = df['achieved_0p70_atr'].astype(bool)
    df['achieved_1p00_atr'] = df['achieved_1p00_atr'].astype(bool)
    df['path_ft_fired'] = df['path_ft_fired'].astype(bool)
    df['path_reverse_ft_fired'] = df['path_reverse_ft_fired'].astype(bool)
    print(f"  Loaded {len(df):,} events across {df['ticker'].nunique()} tickers")
    return df


# ─── Section 1: Core Statistics by Path ──────────────────────────

def compute_path_stats(df):
    """Compute core metrics for each path."""
    rows = []
    for path in PATH_ORDER:
        sub = df[df['path_type'] == path]
        n = len(sub)
        if n == 0:
            continue

        viol = sub['or_violated']
        ft70 = sub['achieved_0p70_atr']
        ft100 = sub['achieved_1p00_atr']
        pft = sub['path_ft_fired']
        prev_ft = sub['path_reverse_ft_fired']

        # No violation subsets
        no_v = sub[~viol]
        yes_v = sub[viol]

        rows.append({
            'path': PATH_LABELS[path],
            'n': n,
            'or_violation_rate': viol.mean(),
            'ft_0p70_all': ft70.mean(),
            'ft_1p00_all': ft100.mean(),
            'ft_0p70_no_violation': ft70[~viol].mean() if len(no_v) > 0 else np.nan,
            'ft_0p70_with_violation': ft70[viol].mean() if len(yes_v) > 0 else np.nan,
            'ft_1p00_no_violation': ft100[~viol].mean() if len(no_v) > 0 else np.nan,
            'ft_1p00_with_violation': ft100[viol].mean() if len(yes_v) > 0 else np.nan,
            'n_no_violation': len(no_v),
            'n_with_violation': len(yes_v),
            'path_ft_rate': pft.mean(),
            'reverse_ft_after_violation': prev_ft[viol].mean() if len(yes_v) > 0 else np.nan,
            'median_close_from_open_atr': sub['close_from_open_atr'].median(),
            'median_violation_depth_atr': yes_v['max_violation_depth_atr'].median() if len(yes_v) > 0 else 0,
            'median_destination_min': sub[ft70]['destination_minutes'].median() if ft70.sum() > 0 else np.nan,
            'median_adverse_min': sub['adverse_peak_minutes'].median(),
        })

    return pd.DataFrame(rows)


# ─── Section 2: Depth Bucket Analysis ────────────────────────────

def compute_depth_analysis(df):
    """Follow-through rates by path × violation depth bucket."""
    rows = []
    for path in PATH_ORDER:
        sub = df[df['path_type'] == path]
        for bucket in DEPTH_ORDER:
            if bucket == 'no_violation':
                grp = sub[~sub['or_violated']]
            else:
                grp = sub[sub['violation_depth_bucket'] == bucket]
            n = len(grp)
            if n == 0:
                continue
            rows.append({
                'path': PATH_LABELS[path],
                'depth_bucket': bucket,
                'n': n,
                'ft_0p70_rate': grp['achieved_0p70_atr'].mean(),
                'ft_1p00_rate': grp['achieved_1p00_atr'].mean(),
                'path_ft_rate': grp['path_ft_fired'].mean(),
                'reverse_ft_rate': grp['path_reverse_ft_fired'].mean(),
                'median_close_atr': grp['close_from_open_atr'].median(),
                'conf': confidence_flag(n),
            })
    return pd.DataFrame(rows)


# ─── Section 3: Timing Bucket Analysis ───────────────────────────

def compute_timing_analysis(df):
    """Follow-through rates by path × violation timing bucket (absolute)."""
    rows = []
    for path in PATH_ORDER:
        sub = df[df['path_type'] == path]
        for bucket in TIMING_ABS_ORDER:
            if bucket == 'no_violation':
                grp = sub[~sub['or_violated']]
            else:
                grp = sub[sub['violation_timing_abs_bucket'] == bucket]
            n = len(grp)
            if n == 0:
                continue
            rows.append({
                'path': PATH_LABELS[path],
                'timing_bucket': bucket,
                'n': n,
                'ft_0p70_rate': grp['achieved_0p70_atr'].mean(),
                'ft_1p00_rate': grp['achieved_1p00_atr'].mean(),
                'reverse_ft_rate': grp['path_reverse_ft_fired'].mean(),
                'conf': confidence_flag(n),
            })
    return pd.DataFrame(rows)


# ─── Section 4: Gap Bucket Analysis ──────────────────────────────

def compute_gap_bucket_analysis(df):
    """OR violation rate and survival by path × gap bucket."""
    rows = []
    for path in PATH_ORDER:
        sub = df[df['path_type'] == path]
        for gb in GAP_BUCKET_ORDER:
            grp = sub[sub['gap_bucket'] == gb]
            n = len(grp)
            if n == 0:
                continue
            no_v = grp[~grp['or_violated']]
            yes_v = grp[grp['or_violated']]
            rows.append({
                'path': PATH_LABELS[path],
                'gap_bucket': gb,
                'n': n,
                'violation_rate': grp['or_violated'].mean(),
                'ft_0p70_no_viol': no_v['achieved_0p70_atr'].mean() if len(no_v) > 0 else np.nan,
                'ft_0p70_with_viol': yes_v['achieved_0p70_atr'].mean() if len(yes_v) > 0 else np.nan,
                'ft_1p00_no_viol': no_v['achieved_1p00_atr'].mean() if len(no_v) > 0 else np.nan,
                'ft_1p00_with_viol': yes_v['achieved_1p00_atr'].mean() if len(yes_v) > 0 else np.nan,
                'conf': confidence_flag(n),
            })
    return pd.DataFrame(rows)


# ─── Section 5: HoD/LoD Timing Tables ────────────────────────────

def compute_hodlod_timing(df):
    """Timing profiles for true follow-through days only."""
    rows = []
    for path in PATH_ORDER:
        sub = df[df['path_type'] == path]
        for tier_name, tier_col in [('0.70 ATR+', 'achieved_0p70_atr'), ('1.00 ATR+', 'achieved_1p00_atr')]:
            ft_days = sub[sub[tier_col]]
            n = len(ft_days)
            if n < 5:
                continue
            dest = ft_days['destination_minutes']
            adv = ft_days['adverse_peak_minutes']
            rows.append({
                'path': PATH_LABELS[path],
                'tier': tier_name,
                'n': n,
                'median_destination_min': dest.median(),
                'pct_dest_first_30min': (dest <= 30).mean(),
                'pct_dest_after_4hr': (dest > 240).mean(),
                'pct_dest_last_30min': (dest > 360).mean(),
                'median_adverse_min': adv.median(),
                'pct_adverse_first_5min': (adv <= 5).mean(),
                'pct_adverse_first_30min': (adv <= 30).mean(),
                'pct_adverse_after_30min': (adv > 30).mean(),
                'conf': confidence_flag(n),
            })
    return pd.DataFrame(rows)


# ─── Chart Generation ────────────────────────────────────────────

def make_heatmap(matrix_df, title, xlabel, ylabel, save_name, zmin=0, zmax=1, fmt='.0%'):
    """Generic annotated heatmap → HTML."""
    z = matrix_df.values
    x_labels = list(matrix_df.columns)
    y_labels = list(matrix_df.index)

    annotations = []
    for i, row in enumerate(y_labels):
        for j, col in enumerate(x_labels):
            val = z[i][j]
            if np.isnan(val):
                text = '—'
            elif fmt == '.0%':
                text = f'{val:.0%}'
            elif fmt == 'd':
                text = f'{int(val)}'
            else:
                text = f'{val:.2f}'
            annotations.append(dict(
                x=col, y=row, text=text,
                showarrow=False, font=dict(size=11, color='white' if val > 0.5 else 'black')
            ))

    fig = go.Figure(data=go.Heatmap(
        z=z, x=x_labels, y=y_labels,
        colorscale='RdYlGn', zmin=zmin, zmax=zmax,
        hovertemplate='%{y}<br>%{x}<br>Value: %{z:.2%}<extra></extra>'
    ))
    fig.update_layout(
        title=title, xaxis_title=xlabel, yaxis_title=ylabel,
        annotations=annotations,
        template='plotly_dark', width=900, height=500, margin=dict(l=200)
    )
    path = CHART_DIR / save_name
    fig.write_html(str(path))
    print(f"  Chart saved: {path.name}")


def generate_charts(df, depth_df, timing_df, gap_df):
    """Generate all required charts."""
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    print("\nGenerating charts...")

    # ── Chart 1: Follow-through heatmap by path × depth bucket
    pivot = depth_df.pivot_table(index='path', columns='depth_bucket', values='ft_0p70_rate')
    pivot = pivot.reindex(columns=DEPTH_ORDER, index=[PATH_LABELS[p] for p in PATH_ORDER])
    make_heatmap(pivot, '0.70 ATR Follow-Through Rate by Path × OR Depth Bucket',
                 'Violation Depth', 'Path', 'ft_heatmap_path_x_depth.html')

    # ── Chart 2: Follow-through heatmap by path × timing bucket
    pivot2 = timing_df.pivot_table(index='path', columns='timing_bucket', values='ft_0p70_rate')
    cols = [c for c in TIMING_ABS_ORDER if c in pivot2.columns]
    pivot2 = pivot2.reindex(columns=cols, index=[PATH_LABELS[p] for p in PATH_ORDER])
    make_heatmap(pivot2, '0.70 ATR Follow-Through Rate by Path × OR Timing Bucket',
                 'Violation Timing', 'Path', 'ft_heatmap_path_x_timing.html')

    # ── Chart 3: Gap bucket × violation survival heatmap
    pivot3 = gap_df.pivot_table(index='path', columns='gap_bucket', values='ft_0p70_with_viol')
    pivot3 = pivot3.reindex(columns=GAP_BUCKET_ORDER, index=[PATH_LABELS[p] for p in PATH_ORDER])
    make_heatmap(pivot3, '0.70 ATR FT Rate AFTER OR Violation, by Path × Gap Bucket',
                 'Gap Bucket', 'Path', 'gap_bucket_survival.html')

    # ── Chart 4: Distribution of violation depth by path
    violated = df[df['or_violated']].copy()
    if len(violated) > 0:
        fig4 = px.histogram(
            violated, x='max_violation_depth_atr', color='path_type',
            nbins=50, barmode='overlay', opacity=0.7,
            labels={'max_violation_depth_atr': 'Max Violation Depth (ATR)',
                    'path_type': 'Path'},
            title='Distribution of OR Violation Depth (ATR) by Path',
            color_discrete_sequence=[GREEN, RED, AMBER, BLUE],
        )
        fig4.update_layout(template='plotly_dark', width=900, height=500)
        fig4.write_html(str(CHART_DIR / 'violation_depth_dist.html'))
        print("  Chart saved: violation_depth_dist.html")

    # ── Chart 5: Destination timing distribution for FT days
    ft_days = df[df['achieved_0p70_atr']].copy()
    if len(ft_days) > 0:
        fig5 = px.histogram(
            ft_days, x='destination_minutes', color='path_type',
            nbins=40, barmode='overlay', opacity=0.7,
            labels={'destination_minutes': 'Destination Minutes from Open',
                    'path_type': 'Path'},
            title='Destination Timing Distribution (0.70 ATR+ FT Days)',
            color_discrete_sequence=[GREEN, RED, AMBER, BLUE],
        )
        fig5.update_layout(template='plotly_dark', width=900, height=500)
        fig5.write_html(str(CHART_DIR / 'destination_timing_dist.html'))
        print("  Chart saved: destination_timing_dist.html")

    # ── Chart 6: Adverse peak timing distribution
    fig6 = px.histogram(
        df, x='adverse_peak_minutes', color='path_type',
        nbins=40, barmode='overlay', opacity=0.7,
        labels={'adverse_peak_minutes': 'Adverse Peak Minutes from Open',
                'path_type': 'Path'},
        title='Adverse Peak Timing Distribution (All Events)',
        color_discrete_sequence=[GREEN, RED, AMBER, BLUE],
    )
    fig6.update_layout(template='plotly_dark', width=900, height=500)
    fig6.write_html(str(CHART_DIR / 'adverse_timing_dist.html'))
    print("  Chart saved: adverse_timing_dist.html")

    # ── Chart 7: Survival odds comparison (no-violation vs violation)
    survival_data = []
    for path in PATH_ORDER:
        sub = df[df['path_type'] == path]
        no_v = sub[~sub['or_violated']]
        yes_v = sub[sub['or_violated']]
        for label, grp in [('No Violation', no_v), ('Violated', yes_v)]:
            if len(grp) > 0:
                survival_data.append({
                    'path': PATH_LABELS[path], 'status': label,
                    'ft_0p70': grp['achieved_0p70_atr'].mean(),
                    'ft_1p00': grp['achieved_1p00_atr'].mean(),
                    'n': len(grp),
                })

    surv_df = pd.DataFrame(survival_data)
    if len(surv_df) > 0:
        fig7 = go.Figure()
        for status, color in [('No Violation', GREEN), ('Violated', RED)]:
            s = surv_df[surv_df['status'] == status]
            fig7.add_trace(go.Bar(
                x=s['path'], y=s['ft_0p70'], name=f'{status} (0.70 ATR)',
                marker_color=color, opacity=0.8,
                text=[f"n={n}" for n in s['n']], textposition='outside',
            ))
        fig7.update_layout(
            title='0.70 ATR Follow-Through: No Violation vs Violated',
            yaxis_title='Follow-Through Rate',
            yaxis_tickformat='.0%', barmode='group',
            template='plotly_dark', width=900, height=500,
        )
        fig7.write_html(str(CHART_DIR / 'survival_odds_comparison.html'))
        print("  Chart saved: survival_odds_comparison.html")


# ─── Executive Summary ───────────────────────────────────────────

def generate_executive_summary(df, path_stats, depth_df, timing_df, gap_df, hodlod_df):
    """Write the executive summary markdown."""
    lines = []
    lines.append("# Opening Range Violation Survival Study — Executive Summary")
    lines.append(f"\nRun: {RUN_ID} | Events: {len(df):,} | Tickers: {df['ticker'].nunique()}")
    lines.append(f"Period: {df['date'].min()[:10]} to {df['date'].max()[:10]}")
    lines.append(f"ATR period: 14 | FT ATR mult: 0.40 | Session: RTH 9:30-16:00 ET")
    lines.append("\n---\n")

    for _, row in path_stats.iterrows():
        p = row['path']
        lines.append(f"## {p}")
        lines.append(f"- **n = {int(row['n']):,}** | OR violation rate: **{row['or_violation_rate']:.1%}**")
        lines.append(f"- 0.70 ATR FT (all): {row['ft_0p70_all']:.1%} | 1.00 ATR FT (all): {row['ft_1p00_all']:.1%}")
        lines.append(f"- **No violation (n={int(row['n_no_violation']):,}):** "
                      f"0.70 ATR FT = {row['ft_0p70_no_violation']:.1%}" +
                      (f" | 1.00 ATR FT = {row['ft_1p00_no_violation']:.1%}" if not pd.isna(row['ft_1p00_no_violation']) else ""))
        lines.append(f"- **With violation (n={int(row['n_with_violation']):,}):** "
                      f"0.70 ATR FT = {row['ft_0p70_with_violation']:.1%}" +
                      (f" | 1.00 ATR FT = {row['ft_1p00_with_violation']:.1%}" if not pd.isna(row['ft_1p00_with_violation']) else ""))

        # Delta
        if not pd.isna(row['ft_0p70_no_violation']) and not pd.isna(row['ft_0p70_with_violation']):
            delta = row['ft_0p70_no_violation'] - row['ft_0p70_with_violation']
            direction = '↑' if delta > 0 else '↓'
            lines.append(f"- **Violation penalty (0.70 ATR):** {abs(delta):.1%} {direction}")

        if not pd.isna(row['reverse_ft_after_violation']):
            lines.append(f"- Reverse FT after OR violation: {row['reverse_ft_after_violation']:.1%}")

        if not pd.isna(row['median_destination_min']):
            lines.append(f"- Median destination time (FT days): {row['median_destination_min']:.0f} min from open")
        lines.append(f"- Median adverse peak: {row['median_adverse_min']:.0f} min from open")

        # Best/worst depth buckets for this path
        path_depths = depth_df[depth_df['path'] == p]
        if len(path_depths) > 1:
            valid = path_depths[path_depths['n'] >= 10]
            if len(valid) > 0:
                best = valid.loc[valid['ft_0p70_rate'].idxmax()]
                worst = valid.loc[valid['ft_0p70_rate'].idxmin()]
                lines.append(f"- Best depth bucket: **{best['depth_bucket']}** "
                             f"({best['ft_0p70_rate']:.1%} FT, n={int(best['n'])})")
                lines.append(f"- Worst depth bucket: **{worst['depth_bucket']}** "
                             f"({worst['ft_0p70_rate']:.1%} FT, n={int(worst['n'])})")

        lines.append("")

    # ── Confidence flags
    lines.append("---\n## Confidence Flags")
    lines.append("- ✅ n ≥ 20  |  ⚠️ LOW CONF n 10-19  |  ❌ INSUFF n < 10\n")

    path = OUTPUT_DIR / 'executive_summary.md'
    path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"\n  Executive summary saved: {path.name}")
    return '\n'.join(lines)


# ─── Stop-Placement Cheatsheet ───────────────────────────────────

def generate_stop_cheatsheet(df, depth_df, timing_df):
    """Generate the trader-facing stop-placement cheatsheet."""
    lines = []
    lines.append("# Stop-Placement Cheat Sheet — Opening Range Violation Survival")
    lines.append(f"\nStudy: {RUN_ID} | n = {len(df):,}\n")
    lines.append("## How to Read This")
    lines.append("- **OR extreme** = the high (shorts) or low (longs) of the first 5-minute candle")
    lines.append("- **Violation** = price breaches this level AFTER the first 5-min bar closes")
    lines.append("- **Follow-through** = session close is at least 0.70 ATR from the open in setup direction")
    lines.append("- **Elite FT** = session close is at least 1.00 ATR from the open in setup direction")
    lines.append("")

    for path_key in PATH_ORDER:
        label = PATH_LABELS[path_key]
        setup_dir = 'LONG' if 'long' in path_key else 'SHORT'
        or_type = 'Low' if setup_dir == 'LONG' else 'High'

        lines.append(f"---\n## {label}")
        lines.append(f"*OR extreme watched: Opening 5-min {or_type} (adverse level for {setup_dir}s)*\n")

        # Depth table
        path_depths = depth_df[depth_df['path'] == label].copy()
        if len(path_depths) > 0:
            lines.append("### By Violation Depth\n")
            lines.append("| Depth Bucket | n | 0.70 ATR FT | 1.00 ATR FT | Reverse FT | Conf |")
            lines.append("|---|---|---|---|---|---|")
            for _, r in path_depths.iterrows():
                lines.append(
                    f"| {r['depth_bucket']} | {int(r['n'])} | "
                    f"{r['ft_0p70_rate']:.1%} | {r['ft_1p00_rate']:.1%} | "
                    f"{r['reverse_ft_rate']:.1%} | {r['conf']} |"
                )
            lines.append("")

        # Timing table
        path_timings = timing_df[timing_df['path'] == label].copy()
        if len(path_timings) > 0:
            lines.append("### By Violation Timing (from open)\n")
            lines.append("| Timing Bucket | n | 0.70 ATR FT | 1.00 ATR FT | Reverse FT | Conf |")
            lines.append("|---|---|---|---|---|---|")
            for _, r in path_timings.iterrows():
                lines.append(
                    f"| {r['timing_bucket']} | {int(r['n'])} | "
                    f"{r['ft_0p70_rate']:.1%} | {r['ft_1p00_rate']:.1%} | "
                    f"{r['reverse_ft_rate']:.1%} | {r['conf']} |"
                )
            lines.append("")

        # Plain-English interpretation
        sub = df[df['path_type'] == path_key]
        no_v = sub[~sub['or_violated']]
        yes_v = sub[sub['or_violated']]

        lines.append("### Plain-English Stop Guidance\n")

        if len(no_v) > 0 and len(yes_v) > 0:
            no_v_ft = no_v['achieved_0p70_atr'].mean()
            yes_v_ft = yes_v['achieved_0p70_atr'].mean()
            delta = no_v_ft - yes_v_ft

            if delta > 0.15:
                lines.append(f"- **HARD STOP recommended.** OR extreme holds → {no_v_ft:.0%} FT rate. "
                             f"Any breach → drops to {yes_v_ft:.0%}. "
                             f"The {abs(delta):.0%} gap is significant.")
            elif delta > 0.05:
                lines.append(f"- **SOFT STOP with depth awareness.** OR holds: {no_v_ft:.0%} FT. "
                             f"Breach: {yes_v_ft:.0%} FT. Penalty exists but moderate.")
            else:
                lines.append(f"- **STOP IS LESS IMPORTANT for this path.** OR holds: {no_v_ft:.0%} FT. "
                             f"Breach: {yes_v_ft:.0%} FT. OR extreme is not the dominant signal.")

        # Depth-specific guidance — compare to path baseline, not absolute thresholds
        no_viol_row = path_depths[path_depths['depth_bucket'] == 'no_violation']
        baseline_ft = no_viol_row.iloc[0]['ft_0p70_rate'] if len(no_viol_row) > 0 else 0.5

        shallow = path_depths[path_depths['depth_bucket'] == '0-0.10 ATR']
        deep = path_depths[path_depths['depth_bucket'] == '0.50+ ATR']
        if len(shallow) > 0 and shallow.iloc[0]['n'] >= 10:
            sr = shallow.iloc[0]
            pct_of_baseline = sr['ft_0p70_rate'] / baseline_ft if baseline_ft > 0 else 0
            lines.append(f"- Shallow breach (≤0.10 ATR): {sr['ft_0p70_rate']:.0%} FT — "
                         f"{'noise, hold through' if pct_of_baseline > 0.80 else 'concerning even when small' if pct_of_baseline < 0.50 else 'moderate degradation'}.")
        if len(deep) > 0 and deep.iloc[0]['n'] >= 10:
            dr = deep.iloc[0]
            pct_of_baseline = dr['ft_0p70_rate'] / baseline_ft if baseline_ft > 0 else 0
            lines.append(f"- Deep breach (>0.50 ATR): {dr['ft_0p70_rate']:.0%} FT — "
                         f"{'still recoverable' if pct_of_baseline > 0.70 else 'SETUP BROKEN at this depth' if pct_of_baseline < 0.30 else 'meaningful degradation'}.")

        # Timing-specific guidance
        early = path_timings[path_timings['timing_bucket'].isin(['at_open', 'first_30min'])]
        late = path_timings[path_timings['timing_bucket'].isin(['2hr_to_4hr', 'after_4hr', 'last_30min'])]
        if len(early) > 0:
            early_n = early['n'].sum()
            early_ft = (early['n'] * early['ft_0p70_rate']).sum() / early_n if early_n > 0 else np.nan
            if not pd.isna(early_ft):
                lines.append(f"- Early violation (first 30 min): {early_ft:.0%} FT — "
                             f"{'normal opening noise' if early_ft > 0.35 else 'early breach = trouble'}.")
        if len(late) > 0:
            late_n = late['n'].sum()
            late_ft = (late['n'] * late['ft_0p70_rate']).sum() / late_n if late_n > 0 else np.nan
            if not pd.isna(late_ft):
                lines.append(f"- Late violation (after 2hr): {late_ft:.0%} FT — "
                             f"{'late reversals exist' if late_ft > 0.20 else 'late breach = GAME OVER'}.")

        lines.append("")

    path = OUTPUT_DIR / 'stop_placement_cheatsheet.md'
    path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"  Cheatsheet saved: {path.name}")


# ─── HoD/LoD Timing Tables ──────────────────────────────────────

def generate_hodlod_tables(hodlod_df):
    """Write HoD/LoD timing comparison tables."""
    lines = []
    lines.append("# HoD / LoD Timing Profiles — True Follow-Through Days\n")

    if len(hodlod_df) == 0:
        lines.append("Insufficient data for timing breakdown.")
    else:
        lines.append("| Path | Tier | n | Med Dest (min) | Dest ≤30m | Dest >4h | Dest Last 30m | "
                      "Med Adverse (min) | Adv ≤5m | Adv ≤30m | Adv >30m | Conf |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for _, r in hodlod_df.iterrows():
            lines.append(
                f"| {r['path']} | {r['tier']} | {int(r['n'])} | "
                f"{r['median_destination_min']:.0f} | {r['pct_dest_first_30min']:.0%} | "
                f"{r['pct_dest_after_4hr']:.0%} | {r['pct_dest_last_30min']:.0%} | "
                f"{r['median_adverse_min']:.0f} | {r['pct_adverse_first_5min']:.0%} | "
                f"{r['pct_adverse_first_30min']:.0%} | {r['pct_adverse_after_30min']:.0%} | "
                f"{r['conf']} |"
            )

    lines.append("\n## 0.70 ATR vs 1.00 ATR Comparison\n")
    for path_key in PATH_ORDER:
        label = PATH_LABELS[path_key]
        sub = hodlod_df[hodlod_df['path'] == label]
        if len(sub) >= 2:
            t1 = sub[sub['tier'] == '0.70 ATR+'].iloc[0] if len(sub[sub['tier'] == '0.70 ATR+']) > 0 else None
            t2 = sub[sub['tier'] == '1.00 ATR+'].iloc[0] if len(sub[sub['tier'] == '1.00 ATR+']) > 0 else None
            if t1 is not None and t2 is not None:
                lines.append(f"**{label}:**")
                lines.append(f"- 0.70+ dest median: {t1['median_destination_min']:.0f}min | "
                             f"1.00+ dest median: {t2['median_destination_min']:.0f}min")
                lines.append(f"- 0.70+ adverse ≤5min: {t1['pct_adverse_first_5min']:.0%} | "
                             f"1.00+ adverse ≤5min: {t2['pct_adverse_first_5min']:.0%}")
                lines.append("")

    path = OUTPUT_DIR / 'hod_lod_timing.md'
    path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"  HoD/LoD tables saved: {path.name}")


# ─── JSON Summary ────────────────────────────────────────────────

def generate_json_summary(df, path_stats, depth_df):
    """Machine-readable JSON summary for indicator integration."""
    summary = {
        'study': 'opening_range_violation_survival',
        'run_id': RUN_ID,
        'generated': datetime.now().isoformat(),
        'total_events': len(df),
        'tickers': df['ticker'].nunique(),
        'atr_period': 14,
        'ft_atr_mult': 0.40,
        'ft_tiers': {'tier1': 0.70, 'tier2': 1.00},
        'paths': {},
    }

    for _, row in path_stats.iterrows():
        pkey = [k for k, v in PATH_LABELS.items() if v == row['path']][0]
        summary['paths'][pkey] = {
            'n': int(row['n']),
            'or_violation_rate': round(row['or_violation_rate'], 4),
            'ft_0p70_all': round(row['ft_0p70_all'], 4),
            'ft_1p00_all': round(row['ft_1p00_all'], 4),
            'ft_0p70_no_violation': round(row['ft_0p70_no_violation'], 4) if not pd.isna(row['ft_0p70_no_violation']) else None,
            'ft_0p70_with_violation': round(row['ft_0p70_with_violation'], 4) if not pd.isna(row['ft_0p70_with_violation']) else None,
            'ft_1p00_no_violation': round(row['ft_1p00_no_violation'], 4) if not pd.isna(row['ft_1p00_no_violation']) else None,
            'ft_1p00_with_violation': round(row['ft_1p00_with_violation'], 4) if not pd.isna(row['ft_1p00_with_violation']) else None,
            'violation_penalty_0p70': round(
                row['ft_0p70_no_violation'] - row['ft_0p70_with_violation'], 4
            ) if not pd.isna(row['ft_0p70_no_violation']) and not pd.isna(row['ft_0p70_with_violation']) else None,
            'depth_buckets': {},
        }

        # Add depth bucket data
        path_depths = depth_df[depth_df['path'] == row['path']]
        for _, d in path_depths.iterrows():
            summary['paths'][pkey]['depth_buckets'][d['depth_bucket']] = {
                'n': int(d['n']),
                'ft_0p70_rate': round(d['ft_0p70_rate'], 4),
                'ft_1p00_rate': round(d['ft_1p00_rate'], 4),
            }

    # Indicator recommendations
    summary['indicator_recommendations'] = {
        'label_open_5m_high_low': True,
        'display_or_status': True,
        'show_breach_depth_atr': True,
        'include_timing_in_label': False,
        'notes': 'See stop_placement_cheatsheet.md for per-path stop guidance',
    }

    path = OUTPUT_DIR / 'study_summary.json'
    path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(f"  JSON summary saved: {path.name}")
    return summary


# ─── Indicator Update Recommendations ────────────────────────────

def generate_indicator_recommendations(df, path_stats, depth_df):
    """Append indicator-update recommendations to executive summary."""
    lines = []
    lines.append("\n---\n## Indicator Update Recommendations (ATR Mooovvvee / Gap Indicator)\n")

    lines.append("### 1. Label Open 5-Minute High / Low")
    lines.append("**YES** — always label. This is the structural pivot for stop placement on all 4 paths.\n")

    lines.append("### 2. Display OR Status")
    lines.append('**YES** — show "OR HOLDING" vs "OR BREACHED" as a real-time state label.\n')

    lines.append("### 3. Display Breach Depth")
    lines.append('**YES** — show "OR BREACHED +X.XX ATR" so the trader can reference depth bucket guidance.\n')

    lines.append("### 4. Include Timing of Breach in State Label")
    lines.append("**NO** — timing context is useful but adds visual clutter. Better to track internally "
                 "and flag only when late violations occur (after 2hr = elevated risk).\n")

    lines.append("### 5. Per-Path Stop Treatment\n")

    for path_key in PATH_ORDER:
        label = PATH_LABELS[path_key]
        row = path_stats[path_stats['path'] == label]
        if len(row) == 0:
            continue
        row = row.iloc[0]

        path_depths = depth_df[depth_df['path'] == label]
        shallow = path_depths[path_depths['depth_bucket'] == '0-0.10 ATR']
        deep = path_depths[path_depths['depth_bucket'] == '0.50+ ATR']

        penalty = None
        if not pd.isna(row['ft_0p70_no_violation']) and not pd.isna(row['ft_0p70_with_violation']):
            penalty = row['ft_0p70_no_violation'] - row['ft_0p70_with_violation']

        if penalty is not None and penalty > 0.15:
            stop_type = "HARD STOP"
        elif penalty is not None and penalty > 0.05:
            stop_type = "TIMING-CONDITIONED STOP"
        else:
            stop_type = "SOFT STOP"

        lines.append(f"**{label}:** `{stop_type}`")
        if penalty is not None:
            lines.append(f"- Violation penalty: {abs(penalty):.1%}")
        if len(shallow) > 0 and shallow.iloc[0]['n'] >= 10:
            baseline = row['ft_0p70_no_violation'] if not pd.isna(row['ft_0p70_no_violation']) else 0.5
            shallow_pct = shallow.iloc[0]['ft_0p70_rate'] / baseline if baseline > 0 else 0
            lines.append(f"- Shallow breach (≤0.10 ATR): {shallow.iloc[0]['ft_0p70_rate']:.0%} FT → "
                         f"{'noise, hold' if shallow_pct > 0.80 else 'concerning' if shallow_pct < 0.50 else 'moderate drop'}")
        if len(deep) > 0 and deep.iloc[0]['n'] >= 10:
            baseline = row['ft_0p70_no_violation'] if not pd.isna(row['ft_0p70_no_violation']) else 0.5
            deep_pct = deep.iloc[0]['ft_0p70_rate'] / baseline if baseline > 0 else 0
            lines.append(f"- Deep breach (>0.50 ATR): {deep.iloc[0]['ft_0p70_rate']:.0%} FT → "
                         f"{'recoverable' if deep_pct > 0.70 else 'BROKEN' if deep_pct < 0.30 else 'degraded'}")
        lines.append("")

    # Append to executive summary
    exec_path = OUTPUT_DIR / 'executive_summary.md'
    with open(exec_path, 'a', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print("  Indicator recommendations appended to executive_summary.md")


# ─── Main Analysis Pipeline ─────────────────────────────────────

def run_analysis():
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data()

    print("\nComputing statistics...")
    path_stats = compute_path_stats(df)
    depth_df = compute_depth_analysis(df)
    timing_df = compute_timing_analysis(df)
    gap_df = compute_gap_bucket_analysis(df)
    hodlod_df = compute_hodlod_timing(df)

    # Save analysis tables
    depth_df.to_csv(OUTPUT_DIR / 'depth_analysis.csv', index=False)
    timing_df.to_csv(OUTPUT_DIR / 'timing_analysis.csv', index=False)
    gap_df.to_csv(OUTPUT_DIR / 'gap_bucket_analysis.csv', index=False)
    hodlod_df.to_csv(OUTPUT_DIR / 'hodlod_timing.csv', index=False)
    path_stats.to_csv(OUTPUT_DIR / 'path_stats.csv', index=False)
    print("  Analysis tables saved.")

    # Generate outputs
    summary_text = generate_executive_summary(df, path_stats, depth_df, timing_df, gap_df, hodlod_df)
    generate_stop_cheatsheet(df, depth_df, timing_df)
    generate_hodlod_tables(hodlod_df)
    generate_charts(df, depth_df, timing_df, gap_df)
    generate_json_summary(df, path_stats, depth_df)
    generate_indicator_recommendations(df, path_stats, depth_df)

    # Print key findings to console
    print("\n" + "=" * 70)
    print("KEY FINDINGS")
    print("=" * 70)
    for _, row in path_stats.iterrows():
        p = row['path']
        print(f"\n{p} (n={int(row['n']):,}):")
        print(f"  OR violation rate: {row['or_violation_rate']:.1%}")
        print(f"  No violation → 0.70 ATR FT: {row['ft_0p70_no_violation']:.1%}")
        print(f"  With violation → 0.70 ATR FT: {row['ft_0p70_with_violation']:.1%}")
        if not pd.isna(row['ft_0p70_no_violation']) and not pd.isna(row['ft_0p70_with_violation']):
            delta = row['ft_0p70_no_violation'] - row['ft_0p70_with_violation']
            print(f"  Penalty: {abs(delta):.1%}")

    print("\n  ALL OUTPUTS SAVED TO:", OUTPUT_DIR)
    return df, path_stats


if __name__ == '__main__':
    run_analysis()
