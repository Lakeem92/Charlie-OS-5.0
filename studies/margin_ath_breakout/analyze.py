"""
╔══════════════════════════════════════════════════════════════════════╗
║  MARGIN ATH BREAKOUT — Phase 3: Analysis & Visualization           ║
║                                                                    ║
║  1. Computes forward returns at 1/2/3/4/6/8/12 weeks              ║
║     for all signal groups and 3 control groups                     ║
║                                                                    ║
║  2. Statistical analysis:                                          ║
║     • Mean/median return, win rate, IQR per group per window       ║
║     • Mann-Whitney U test vs Control A for each group              ║
║     • Margin type ranking by predictive power                      ║
║     • Stacking effect: single → double → all-three margins         ║
║                                                                    ║
║  3. Visualizations (all saved as interactive .html):               ║
║     Chart 1 — Forward return curves (mean, all groups)            ║
║     Chart 2 — Win rate heatmap (margin type × time horizon)       ║
║     Chart 3 — Return distributions at 4wk & 12wk (box plots)     ║
║     Chart 4 — Stacking effect (single vs double vs triple)        ║
║                                                                    ║
║  Usage: python analyze.py                                          ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from scipy import stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ══════════════════════════════════════════════════════════════════════
# PATHS & CONSTANTS
# ══════════════════════════════════════════════════════════════════════

STUDY_DIR    = Path(r'C:\QuantLab\Data_Lab\studies\margin_ath_breakout')
DATA_DIR     = STUDY_DIR / 'data'
PRICES_DIR   = DATA_DIR / 'prices'
SIGNALS_PATH = DATA_DIR / 'signals_final.parquet'
CHARTS_DIR   = STUDY_DIR / 'outputs' / 'charts'
TABLES_DIR   = STUDY_DIR / 'outputs' / 'tables'
TODAY_STR    = datetime.now().strftime('%Y%m%d')

for d in [CHARTS_DIR, TABLES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Forward return windows: label → trading days
FWD_WINDOWS = {
    '1wk':  5,
    '2wk':  10,
    '3wk':  15,
    '4wk':  20,
    '6wk':  30,
    '8wk':  40,
    '12wk': 60,
}
WEEK_LABELS  = list(FWD_WINDOWS.keys())
WEEK_DAYS    = list(FWD_WINDOWS.values())

# Sample confidence thresholds
N_RELIABLE         = 20
N_LOW_CONFIDENCE   = 10

# ── Color palette (QuantLab standard) ───────────────────────────────
COLORS = {
    'GROSS_ONLY':       '#26a69a',   # teal — gross margin
    'OPERATING_ONLY':   '#42a5f5',   # blue — operating margin
    'EBITDA_ONLY':      '#ab47bc',   # purple — ebitda margin
    'GROSS+OPERATING':  '#66bb6a',   # green
    'GROSS+EBITDA':     '#26c6da',   # cyan
    'OPERATING+EBITDA': '#7986cb',   # indigo
    'ALL_THREE':        '#ffd54f',   # gold — all three firing
    'CONTROL_A':        '#ef5350',   # red — baseline ATH only
    'CONTROL_B':        '#ff7043',   # orange — margin without ATH
    'CONTROL_C':        '#78909c',   # grey — random
    'SINGLE':           '#42a5f5',
    'DOUBLE':           '#66bb6a',
    'TRIPLE':           '#ffd54f',
}

# Ordered groups for display (signal groups first, then controls)
SIGNAL_GROUPS = [
    'GROSS_ONLY', 'OPERATING_ONLY', 'EBITDA_ONLY',
    'GROSS+OPERATING', 'GROSS+EBITDA', 'OPERATING+EBITDA', 'ALL_THREE',
]
ALL_GROUPS = SIGNAL_GROUPS + ['CONTROL_A', 'CONTROL_B', 'CONTROL_C']

# Primary signal groups to include in the main forward-return chart
CHART1_GROUPS = ['GROSS_ONLY', 'OPERATING_ONLY', 'EBITDA_ONLY', 'ALL_THREE', 'CONTROL_A']

# ══════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════

print('=' * 70)
print('MARGIN ATH BREAKOUT — ANALYSIS')
print(f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
print('=' * 70)

if not SIGNALS_PATH.exists():
    print(f'ERROR: {SIGNALS_PATH} not found. Run build_signals.py first.')
    sys.exit(1)

events = pd.read_parquet(SIGNALS_PATH)
events['signal_date'] = pd.to_datetime(events['signal_date'])
print(f'\nLoaded {len(events)} events across {events["group"].value_counts().to_dict()}')

# ══════════════════════════════════════════════════════════════════════
# LOAD PRICE CACHE
# ══════════════════════════════════════════════════════════════════════

print('\nLoading price data...')
price_dict = {}
for ticker in events['ticker'].dropna().unique():
    pth = PRICES_DIR / f'{ticker}.parquet'
    if pth.exists():
        df = pd.read_parquet(pth, columns=['close'])
        idx = pd.to_datetime(df.index)
        if idx.tz is not None:
            idx = idx.tz_convert('UTC').tz_localize(None)
        df.index = idx.normalize()
        df = df.sort_index()
        price_dict[ticker] = df['close']   # store as pd.Series for fast iloc access

print(f'  Price series loaded for {len(price_dict)} tickers')

# ══════════════════════════════════════════════════════════════════════
# FORWARD RETURN COMPUTATION
# ══════════════════════════════════════════════════════════════════════

def compute_forward_return(ticker: str, signal_date, n_days: int) -> float:
    """
    Return % gain from the close on signal_date to the close n_days later.
    Returns np.nan if price data is unavailable or insufficient.
    """
    if ticker not in price_dict:
        return np.nan

    prices = price_dict[ticker]
    sig_ts = pd.Timestamp(signal_date).normalize()

    # Find the logical array index for signal_date using searchsorted
    idx = prices.index.searchsorted(sig_ts)
    if idx >= len(prices):
        return np.nan

    # Snap forward to nearest available trading day (handles non-trading days)
    # signals should already land on trading days, but be defensive
    fwd_idx = idx + n_days
    if fwd_idx >= len(prices):
        return np.nan

    p0 = prices.iloc[idx]
    p1 = prices.iloc[fwd_idx]

    if p0 <= 0 or pd.isna(p0) or pd.isna(p1):
        return np.nan

    return (p1 / p0 - 1) * 100.0


print('\nComputing forward returns for all events...')
for lbl, td in FWD_WINDOWS.items():
    events[f'ret_{lbl}'] = events.apply(
        lambda r: compute_forward_return(r['ticker'], r['signal_date'], td), axis=1)
    valid = events[f'ret_{lbl}'].notna().sum()
    print(f'  {lbl} ({td:2d}d): {valid} valid observations')

# ══════════════════════════════════════════════════════════════════════
# COMPUTE GROUP STATISTICS
# ══════════════════════════════════════════════════════════════════════

def confidence_tag(n: int) -> str:
    if n >= N_RELIABLE:        return 'HIGH'
    if n >= N_LOW_CONFIDENCE:  return '⚠️ LOW'
    return '❌ INSUFFICIENT'


def group_stats(df_grp, ret_col: str) -> dict:
    vals = df_grp[ret_col].dropna()
    n    = len(vals)
    if n == 0:
        return dict(n=0, mean=np.nan, median=np.nan, win_rate=np.nan,
                    pct25=np.nan, pct75=np.nan)
    return dict(
        n        = n,
        mean     = vals.mean(),
        median   = vals.median(),
        win_rate = (vals > 0).mean() * 100.0,
        pct25    = vals.quantile(0.25),
        pct75    = vals.quantile(0.75),
    )


print('\n' + '-' * 60)
print('Computing group statistics per forward window...\n')

# Pre-group for efficiency
groups_map = {g: events[events['group'] == g] for g in events['group'].unique()}
# Also build stacking-tier groups (signal events only)
sig_only = events[events['group'] == 'SIGNAL'] if 'SIGNAL' in events['group'].values \
           else events[events['group'].str.startswith('GROSS') |
                        events['group'].str.startswith('OPERAT') |
                        events['group'].str.startswith('EBITDA') |
                        (events['group'] == 'ALL_THREE')]

# Remap: use margin_combo as the fine-grained group key for signal events
events_detailed = events.copy()
events_detailed.loc[events_detailed['group'] == 'SIGNAL', 'group'] = \
    events_detailed.loc[events_detailed['group'] == 'SIGNAL', 'margin_combo']

groups_map = {g: events_detailed[events_detailed['group'] == g]
              for g in (SIGNAL_GROUPS + ['CONTROL_A', 'CONTROL_B', 'CONTROL_C'])}

# Build stats table: rows = group, cols = window metrics
stats_rows = []
for grp in ALL_GROUPS:
    df_g = groups_map.get(grp, pd.DataFrame())
    row  = {'group': grp}
    for lbl in WEEK_LABELS:
        s = group_stats(df_g, f'ret_{lbl}')
        for k, v in s.items():
            row[f'{lbl}_{k}'] = v
    stats_rows.append(row)

stats_df = pd.DataFrame(stats_rows)
stats_df.to_csv(TABLES_DIR / f'stats_by_group_{TODAY_STR}.csv', index=False)

# ══════════════════════════════════════════════════════════════════════
# MANN-WHITNEY U TESTS vs CONTROL A
# ══════════════════════════════════════════════════════════════════════

print('Running Mann-Whitney U tests (each group vs Control A)...\n')

ctrl_a_events = groups_map.get('CONTROL_A', pd.DataFrame())
mw_rows = []

for grp in SIGNAL_GROUPS:
    df_g = groups_map.get(grp, pd.DataFrame())
    row  = {'group': grp}
    for lbl in WEEK_LABELS:
        sig_vals = df_g[f'ret_{lbl}'].dropna()
        ctl_vals = ctrl_a_events[f'ret_{lbl}'].dropna()
        if len(sig_vals) >= N_LOW_CONFIDENCE and len(ctl_vals) >= N_LOW_CONFIDENCE:
            u_stat, p_val = stats.mannwhitneyu(sig_vals, ctl_vals, alternative='two-sided')
            row[f'{lbl}_U']       = u_stat
            row[f'{lbl}_p']       = p_val
            row[f'{lbl}_sig']     = '*' if p_val < 0.05 else ('~' if p_val < 0.10 else '')
            row[f'{lbl}_n_grp']   = len(sig_vals)
            row[f'{lbl}_n_ctrl']  = len(ctl_vals)
        else:
            row[f'{lbl}_U']       = np.nan
            row[f'{lbl}_p']       = np.nan
            row[f'{lbl}_sig']     = '❌'
            row[f'{lbl}_n_grp']   = len(sig_vals)
            row[f'{lbl}_n_ctrl']  = len(ctl_vals)
    mw_rows.append(row)

mw_df = pd.DataFrame(mw_rows)
mw_df.to_csv(TABLES_DIR / f'mann_whitney_vs_control_a_{TODAY_STR}.csv', index=False)

# ══════════════════════════════════════════════════════════════════════
# STACKING ANALYSIS
# ══════════════════════════════════════════════════════════════════════

stack_events = events_detailed[events_detailed['stacking_tier'].notna() &
                                events_detailed['stacking_tier'].isin(['SINGLE','DOUBLE','TRIPLE'])]

stack_rows = []
for tier in ['SINGLE', 'DOUBLE', 'TRIPLE']:
    df_t = stack_events[stack_events['stacking_tier'] == tier]
    row  = {'stacking_tier': tier}
    for lbl in WEEK_LABELS:
        s = group_stats(df_t, f'ret_{lbl}')
        for k, v in s.items():
            row[f'{lbl}_{k}'] = v
    stack_rows.append(row)

stack_df = pd.DataFrame(stack_rows)
stack_df.to_csv(TABLES_DIR / f'stacking_effect_{TODAY_STR}.csv', index=False)

# ══════════════════════════════════════════════════════════════════════
# TEXT SUMMARY — KEY FINDINGS
# ══════════════════════════════════════════════════════════════════════

print()
print('█' * 70)
print('  MARGIN ATH BREAKOUT — KEY FINDINGS')
print('█' * 70)
print()

# Rank the three primary single-margin groups by 4wk and 12wk mean return
ranking_rows = []
for grp in ['GROSS_ONLY', 'OPERATING_ONLY', 'EBITDA_ONLY']:
    df_g = groups_map.get(grp, pd.DataFrame())
    n4   = df_g['ret_4wk'].dropna().__len__()
    n12  = df_g['ret_12wk'].dropna().__len__()
    m4   = df_g['ret_4wk'].mean()
    m12  = df_g['ret_12wk'].mean()
    w4   = (df_g['ret_4wk'] > 0).mean() * 100 if n4 > 0 else np.nan
    w12  = (df_g['ret_12wk'] > 0).mean() * 100 if n12 > 0 else np.nan
    # p-value vs Control A at 4wk
    ctrl_4 = ctrl_a_events['ret_4wk'].dropna()
    sig_4  = df_g['ret_4wk'].dropna()
    p4     = stats.mannwhitneyu(sig_4, ctrl_4, alternative='two-sided')[1] \
             if len(sig_4) >= N_LOW_CONFIDENCE and len(ctrl_4) >= N_LOW_CONFIDENCE else np.nan
    ranking_rows.append({
        'group': grp, 'n_4wk': n4, 'mean_4wk': m4, 'winrate_4wk': w4,
        'n_12wk': n12, 'mean_12wk': m12, 'winrate_12wk': w12, 'p_4wk': p4,
    })

ranking_df = pd.DataFrame(ranking_rows).sort_values('mean_4wk', ascending=False)
ranking_df.to_csv(TABLES_DIR / f'margin_type_ranking_{TODAY_STR}.csv', index=False)

ctrl_a_4wk_mean  = ctrl_a_events['ret_4wk'].mean()
ctrl_a_12wk_mean = ctrl_a_events['ret_12wk'].mean()
ctrl_a_n = ctrl_a_events['ret_4wk'].dropna().__len__()
signal_total = sum(len(groups_map.get(g, [])) for g in SIGNAL_GROUPS)

print(f'Signal events total:    {signal_total}')
print(f'Control A (ATH only):   {ctrl_a_n}')
print(f'Date range covered:     {events_detailed["signal_date"].min().date()} → '
      f'{events_detailed["signal_date"].max().date()}')
print()

print('─' * 60)
print('PRIMARY MARGIN TYPE RANKING (by 4-week mean return)')
print('─' * 60)
for _, r in ranking_df.iterrows():
    conf = confidence_tag(r['n_4wk'])
    lift = r['mean_4wk'] - ctrl_a_4wk_mean if pd.notna(ctrl_a_4wk_mean) else np.nan
    p_flag = ''
    if pd.notna(r['p_4wk']):
        p_flag = f'  p={r["p_4wk"]:.3f}' + (' *' if r['p_4wk'] < 0.05 else '')
    print(f'  {r["group"]:<20}  '
          f'4wk mean={r["mean_4wk"]:+.2f}%  '
          f'win={r["winrate_4wk"]:.1f}%  '
          f'lift vs ATH baseline={lift:+.2f}%  '
          f'n={r["n_4wk"]}  [{conf}]{p_flag}')

print()
print('─' * 60)
print('CONTROL GROUP BASELINES')
print('─' * 60)
for grp, label in [('CONTROL_A','ATH only (no margin milestone)'),
                   ('CONTROL_B','Margin high, no ATH follow-through'),
                   ('CONTROL_C','Random days')]:
    df = groups_map.get(grp, pd.DataFrame())
    n4 = df['ret_4wk'].dropna().__len__()
    m4 = df['ret_4wk'].mean()
    w4 = (df['ret_4wk'] > 0).mean() * 100 if n4 > 0 else np.nan
    print(f'  {grp:<12}  {label:<40}  4wk mean={m4:+.2f}%  win={w4:.1f}%  n={n4}')

print()
print('─' * 60)
print('STACKING EFFECT (does hitting multiple margin highs simultaneously amplify returns?)')
print('─' * 60)
for _, r in stack_df.iterrows():
    print(f'  {r["stacking_tier"]:<7}  '
          f'4wk mean={r["4wk_mean"]:+.2f}%  '
          f'12wk mean={r["12wk_mean"]:+.2f}%  '
          f'n={r["4wk_n"]}')

print()
print('─' * 60)
print('BEST SIGNAL WINDOW (12-week perspective, top 3 groups)')
print('─' * 60)
top3_12 = stats_df[stats_df['group'].isin(SIGNAL_GROUPS)].nlargest(3, '12wk_mean')
for _, r in top3_12.iterrows():
    conf = confidence_tag(r['12wk_n'])
    ctrl12 = ctrl_a_12wk_mean if pd.notna(ctrl_a_12wk_mean) else 0
    lift12 = r['12wk_mean'] - ctrl12
    print(f'  {r["group"]:<20}  '
          f'12wk mean={r["12wk_mean"]:+.2f}%  '
          f'win={r["12wk_win_rate"]:.1f}%  '
          f'lift={lift12:+.2f}%  '
          f'n={r["12wk_n"]}  [{conf}]')

print()
print('█' * 70)

# ══════════════════════════════════════════════════════════════════════
# CHART 1 — FORWARD RETURN CURVES
# ══════════════════════════════════════════════════════════════════════

print('\nBuilding Chart 1: Forward return curves...')

fig1 = go.Figure()

week_nums = [1, 2, 3, 4, 6, 8, 12]

for grp in CHART1_GROUPS:
    df_g = groups_map.get(grp, pd.DataFrame())
    means = []
    errors = []
    for lbl in WEEK_LABELS:
        vals = df_g[f'ret_{lbl}'].dropna()
        if len(vals) > 0:
            means.append(vals.mean())
            errors.append(vals.std() / np.sqrt(len(vals)) * 1.96)  # 95% CI
        else:
            means.append(np.nan)
            errors.append(0)

    is_ctrl = grp.startswith('CONTROL')
    line    = dict(color=COLORS.get(grp, '#999999'),
                   width=1.5 if is_ctrl else 2.5,
                   dash='dot' if is_ctrl else 'solid')

    n_4wk = groups_map.get(grp, pd.DataFrame())['ret_4wk'].dropna().__len__()
    label = f'{grp} (n={n_4wk})'

    fig1.add_trace(go.Scatter(
        x=week_nums,
        y=means,
        name=label,
        mode='lines+markers',
        line=line,
        marker=dict(size=7),
        error_y=dict(
            type='data', array=errors,
            visible=not is_ctrl,
            color=COLORS.get(grp, '#999999'),
            thickness=1.0, width=4,
        ),
    ))

fig1.add_hline(y=0, line_color='rgba(255,255,255,0.3)', line_width=1)
fig1.update_layout(
    template='plotly_dark',
    title=dict(
        text='Margin ATH Breakout — Forward Return Curves<br>'
             '<sup>Mean cumulative return (%) from signal date • '
             'Error bars = 95% CI • Solid = signal groups • Dotted = baseline</sup>',
        font=dict(size=16)
    ),
    xaxis=dict(
        title='Weeks forward from signal date',
        tickvals=week_nums,
        ticktext=[f'{w}wk' for w in week_nums],
    ),
    yaxis=dict(title='Mean Return (%)'),
    hovermode='x unified',
    legend=dict(orientation='v', x=1.01, y=1),
    width=1100, height=600,
)

chart1_path = CHARTS_DIR / f'margin_ath_fwd_returns_{TODAY_STR}.html'
fig1.write_html(str(chart1_path))
print(f'  Saved: {chart1_path.name}')

# ══════════════════════════════════════════════════════════════════════
# CHART 2 — WIN RATE HEATMAP
# ══════════════════════════════════════════════════════════════════════

print('Building Chart 2: Win rate heatmap...')

heatmap_groups = ALL_GROUPS
heatmap_data   = []
heatmap_text   = []

for grp in heatmap_groups:
    df_g = groups_map.get(grp, pd.DataFrame())
    row_vals = []
    row_text = []
    for lbl in WEEK_LABELS:
        vals = df_g[f'ret_{lbl}'].dropna()
        n    = len(vals)
        wr   = (vals > 0).mean() * 100.0 if n > 0 else np.nan
        row_vals.append(wr)
        row_text.append(f'{wr:.1f}%<br>n={n}' if n > 0 else 'n/a')
    heatmap_data.append(row_vals)
    heatmap_text.append(row_text)

fig2 = go.Figure(data=go.Heatmap(
    z=heatmap_data,
    x=WEEK_LABELS,
    y=heatmap_groups,
    text=heatmap_text,
    texttemplate='%{text}',
    colorscale=[
        [0.0,  '#ef5350'],   # red  — low win rate
        [0.5,  '#37474f'],   # dark — 50%
        [1.0,  '#26a69a'],   # teal — high win rate
    ],
    zmid=50.0,
    zmin=30.0, zmax=70.0,
    colorbar=dict(title='Win Rate %'),
    hoverongaps=False,
))
fig2.update_layout(
    template='plotly_dark',
    title=dict(
        text='Margin ATH Breakout — Win Rate Heatmap<br>'
             '<sup>% of signal events with positive forward returns, by group and time horizon</sup>',
        font=dict(size=16)
    ),
    xaxis_title='Forward Window',
    yaxis_title='Group',
    width=900, height=550,
)

chart2_path = CHARTS_DIR / f'margin_ath_winrate_heatmap_{TODAY_STR}.html'
fig2.write_html(str(chart2_path))
print(f'  Saved: {chart2_path.name}')

# ══════════════════════════════════════════════════════════════════════
# CHART 3 — BOX PLOTS AT 4WK AND 12WK
# ══════════════════════════════════════════════════════════════════════

print('Building Chart 3: Return distribution box plots...')

fig3 = make_subplots(
    rows=1, cols=2,
    subplot_titles=['Return Distribution — 4 Week', 'Return Distribution — 12 Week'],
    shared_yaxes=False,
)

box_groups = SIGNAL_GROUPS + ['CONTROL_A']

for col_idx, (window_lbl, pane_title) in enumerate([('4wk', '4wk'), ('12wk', '12wk')], 1):
    for grp in box_groups:
        df_g = groups_map.get(grp, pd.DataFrame())
        vals = df_g[f'ret_{window_lbl}'].dropna()
        if len(vals) == 0:
            continue

        is_ctrl = grp.startswith('CONTROL')
        fig3.add_trace(
            go.Box(
                y=vals,
                name=grp,
                marker_color=COLORS.get(grp, '#999999'),
                boxpoints='outliers',
                jitter=0.3,
                line_width=1.5 if not is_ctrl else 1,
                showlegend=(col_idx == 1),
            ),
            row=1, col=col_idx,
        )

for col_idx in [1, 2]:
    fig3.add_hline(y=0, line_color='rgba(255,255,255,0.3)',
                   line_width=1, row=1, col=col_idx)

fig3.update_layout(
    template='plotly_dark',
    title=dict(
        text='Margin ATH Breakout — Return Distributions (4wk & 12wk)<br>'
             '<sup>Each box: IQR | Whiskers: 1.5×IQR | Dots: outliers</sup>',
        font=dict(size=15)
    ),
    boxmode='group',
    hovermode='x',
    legend=dict(orientation='v', x=1.01, y=1),
    width=1200, height=580,
)
fig3.update_yaxes(title_text='Return (%)', row=1, col=1)
fig3.update_yaxes(title_text='Return (%)', row=1, col=2)

chart3_path = CHARTS_DIR / f'margin_ath_distributions_{TODAY_STR}.html'
fig3.write_html(str(chart3_path))
print(f'  Saved: {chart3_path.name}')

# ══════════════════════════════════════════════════════════════════════
# CHART 4 — STACKING EFFECT
# ══════════════════════════════════════════════════════════════════════

print('Building Chart 4: Stacking effect (single vs double vs triple)...')

fig4 = make_subplots(
    rows=1, cols=2,
    subplot_titles=['Stacking Effect — Mean Return', 'Stacking Effect — Win Rate'],
    shared_xaxes=False,
)

tiers = ['SINGLE', 'DOUBLE', 'TRIPLE']

for tier in tiers:
    df_t   = stack_events[stack_events['stacking_tier'] == tier]
    means  = [df_t[f'ret_{lbl}'].mean() for lbl in WEEK_LABELS]
    wrates = [(df_t[f'ret_{lbl}'] > 0).mean() * 100 for lbl in WEEK_LABELS]
    n_4wk  = df_t['ret_4wk'].dropna().__len__()
    color  = COLORS.get(tier, '#999')

    fig4.add_trace(go.Bar(
        x=WEEK_LABELS, y=means,
        name=f'{tier} (n≈{n_4wk})',
        marker_color=color,
        text=[f'{v:+.1f}%' for v in means],
        textposition='outside',
    ), row=1, col=1)

    fig4.add_trace(go.Bar(
        x=WEEK_LABELS, y=wrates,
        name=f'{tier}',
        marker_color=color,
        showlegend=False,
        text=[f'{v:.1f}%' for v in wrates],
        textposition='outside',
    ), row=1, col=2)

fig4.add_hline(y=0, line_color='rgba(255,255,255,0.3)', row=1, col=1)
fig4.add_hline(y=50, line_color='rgba(255,255,255,0.3)',
               line_dash='dot', row=1, col=2)

fig4.update_layout(
    template='plotly_dark',
    title=dict(
        text='Margin ATH Breakout — Stacking Effect<br>'
             '<sup>Does hitting 1, 2, or all 3 margin highs simultaneously amplify returns?</sup>',
        font=dict(size=15)
    ),
    barmode='group',
    legend=dict(orientation='h', y=-0.15),
    width=1200, height=560,
)
fig4.update_yaxes(title_text='Mean Return (%)', row=1, col=1)
fig4.update_yaxes(title_text='Win Rate (%)', row=1, col=2)

chart4_path = CHARTS_DIR / f'margin_ath_stacking_{TODAY_STR}.html'
fig4.write_html(str(chart4_path))
print(f'  Saved: {chart4_path.name}')

# ══════════════════════════════════════════════════════════════════════
# SAVE FULL EVENTS TABLE
# ══════════════════════════════════════════════════════════════════════

ret_cols = [f'ret_{lbl}' for lbl in WEEK_LABELS]
export_cols = ['ticker', 'signal_date', 'group', 'margin_combo', 'stacking_tier',
               'n_margins_3yr', 'gross_margin', 'operating_margin', 'ebitda_margin',
               'days_to_ath'] + ret_cols
export = events_detailed[[c for c in export_cols if c in events_detailed.columns]].copy()
export.to_csv(TABLES_DIR / f'all_events_with_returns_{TODAY_STR}.csv', index=False)

# ══════════════════════════════════════════════════════════════════════
# PRINT CHART LOCATIONS
# ══════════════════════════════════════════════════════════════════════

print()
print('=' * 70)
print('ANALYSIS COMPLETE')
print('=' * 70)
print(f'\nCharts saved to: {CHARTS_DIR}')
print(f'  {chart1_path.name}  — forward return curves (primary finding)')
print(f'  {chart2_path.name}  — win rate heatmap')
print(f'  {chart3_path.name}  — return distributions')
print(f'  {chart4_path.name}  — stacking effect')
print(f'\nTables saved to: {TABLES_DIR}')
print(f'  stats_by_group_{TODAY_STR}.csv')
print(f'  mann_whitney_vs_control_a_{TODAY_STR}.csv')
print(f'  stacking_effect_{TODAY_STR}.csv')
print(f'  margin_type_ranking_{TODAY_STR}.csv')
print(f'  all_events_with_returns_{TODAY_STR}.csv')
print()
print('See README.md for interpretation guide.')
print('=' * 70)
