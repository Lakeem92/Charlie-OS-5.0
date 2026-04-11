"""
Regime Composite Score — Analysis
Builds composite z-score, classifies regimes, computes forward returns,
runs cliff-dive event study, generates charts and summary.
"""

import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime

from shared.chart_builder import ChartBuilder

# ── Paths ─────────────────────────────────────────────────────────
STUDY_DIR = Path(__file__).resolve().parent
DATA_DIR = STUDY_DIR / 'outputs' / 'data'
SUMMARY_DIR = STUDY_DIR / 'outputs' / 'summary'
CHARTS_DIR = STUDY_DIR / 'outputs' / 'charts'

for d in [DATA_DIR, SUMMARY_DIR, CHARTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────
ZSCORE_WINDOW = 252
FORWARD_WINDOWS = [1, 3, 5, 10, 20]
RETURN_TICKERS = ['SPY', 'QQQ', 'IWM']
CLIFF_DIVE_ROC_WINDOW = 20
CLIFF_DIVE_THRESHOLD = -0.10
CLIFF_DIVE_GAP = 20  # min trading days between events

REGIME_BINS = [-np.inf, -2.0, -1.0, 0.0, 1.0, np.inf]
REGIME_LABELS = [
    'EXTREME RISK-OFF / CTA MAX SHORT ZONE',
    'RISK-OFF',
    'MILD RISK-OFF',
    'MILD RISK-ON',
    'RISK-ON',
]

# Colors
C_GREEN = '#26a69a'
C_RED = '#ef5350'
C_BLUE = '#42a5f5'
C_YELLOW = '#ffca28'
C_PURPLE = '#ab47bc'

REGIME_COLORS = {
    'RISK-ON': 'rgba(38,166,154,0.15)',
    'MILD RISK-ON': 'rgba(38,166,154,0.07)',
    'MILD RISK-OFF': 'rgba(239,83,80,0.07)',
    'RISK-OFF': 'rgba(239,83,80,0.15)',
    'EXTREME RISK-OFF / CTA MAX SHORT ZONE': 'rgba(239,83,80,0.30)',
}


def confidence_tag(n: int) -> str:
    if n >= 20:
        return '[RELIABLE]'
    elif n >= 10:
        return '[LOW CONFIDENCE - directional only]'
    else:
        return '[INSUFFICIENT - pattern recognition only]'


# ══════════════════════════════════════════════════════════════════
# STEP 1 — COMPOSITE SCORE
# ══════════════════════════════════════════════════════════════════

def build_composite(df: pd.DataFrame) -> pd.DataFrame:
    """Build composite z-score from 4 signals."""
    print("[STEP 1] Building composite score...")

    # XLY/XLP ratio
    df['xly_xlp_ratio'] = df['XLY'] / df['XLP']

    # Rolling 252-day z-scores
    for col, label in [('vix', 'z_vix'), ('hy_spread', 'z_hy'),
                        ('yield_curve', 'z_t10y2y'), ('xly_xlp_ratio', 'z_xlyxlp')]:
        rolling_mean = df[col].rolling(ZSCORE_WINDOW, min_periods=ZSCORE_WINDOW).mean()
        rolling_std = df[col].rolling(ZSCORE_WINDOW, min_periods=ZSCORE_WINDOW).std()
        df[label] = (df[col] - rolling_mean) / rolling_std

    # Invert VIX and HY (high = bad = risk-off → flip sign)
    df['z_vix_inv'] = -df['z_vix']
    df['z_hy_inv'] = -df['z_hy']

    # Composite = average of 4 z-scores (use nanmean for any gaps)
    z_cols = ['z_vix_inv', 'z_hy_inv', 'z_t10y2y', 'z_xlyxlp']
    df['composite_score'] = df[z_cols].mean(axis=1)

    # Regime labels
    df['regime'] = pd.cut(
        df['composite_score'],
        bins=REGIME_BINS,
        labels=REGIME_LABELS,
        right=True,
    )

    # Drop warmup NaN rows for composite
    valid = df.dropna(subset=['composite_score'])
    print(f"  Composite score computed: {len(valid)} valid rows "
          f"(dropped {len(df) - len(valid)} warmup rows)")
    print(f"  Regime distribution:\n{valid['regime'].value_counts().to_string()}")

    # Save
    save_cols = ['XLY', 'XLP', 'SPY', 'QQQ', 'IWM',
                 'vix', 'hy_spread', 'yield_curve', 'xly_xlp_ratio',
                 'z_vix', 'z_hy', 'z_t10y2y', 'z_xlyxlp',
                 'z_vix_inv', 'z_hy_inv',
                 'composite_score', 'regime']
    save_path = DATA_DIR / 'composite_score_daily.csv'
    df[save_cols].to_csv(save_path)
    print(f"  Saved → {save_path}")

    return df


# ══════════════════════════════════════════════════════════════════
# STEP 2 — FORWARD RETURNS BY REGIME
# ══════════════════════════════════════════════════════════════════

def compute_forward_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Compute forward returns for SPY/QQQ/IWM by regime bucket."""
    print("[STEP 2] Computing forward returns by regime...")

    # Calculate forward returns for each ticker and window
    for ticker in RETURN_TICKERS:
        for n in FORWARD_WINDOWS:
            col = f'{ticker}_fwd_{n}d'
            df[col] = df[ticker].shift(-n) / df[ticker] - 1

    # Filter to rows with valid composite score
    valid = df.dropna(subset=['composite_score']).copy()

    results = []
    for regime in REGIME_LABELS:
        mask = valid['regime'] == regime
        subset = valid[mask]
        for ticker in RETURN_TICKERS:
            for n in FORWARD_WINDOWS:
                col = f'{ticker}_fwd_{n}d'
                series = subset[col].dropna()
                count = len(series)
                if count == 0:
                    continue
                results.append({
                    'regime': regime,
                    'ticker': ticker,
                    'window': f'+{n}d',
                    'n': count,
                    'win_rate': (series > 0).mean(),
                    'avg_return': series.mean(),
                    'median_return': series.median(),
                    'std': series.std(),
                    'confidence': confidence_tag(count),
                })

    results_df = pd.DataFrame(results)
    save_path = DATA_DIR / 'regime_forward_returns.csv'
    results_df.to_csv(save_path, index=False)
    print(f"  {len(results_df)} regime×ticker×window combinations")
    print(f"  Saved → {save_path}")
    return results_df


# ══════════════════════════════════════════════════════════════════
# STEP 3 — CLIFF DIVE EVENT STUDY
# ══════════════════════════════════════════════════════════════════

def cliff_dive_study(df: pd.DataFrame) -> pd.DataFrame:
    """Identify XLY/XLP cliff dive events and compute forward returns."""
    print("[STEP 3] Running cliff dive event study...")

    # 20-day rate of change of XLY/XLP ratio
    df['xlyxlp_roc_20d'] = df['xly_xlp_ratio'] / df['xly_xlp_ratio'].shift(CLIFF_DIVE_ROC_WINDOW) - 1

    # Flag cliff dive days
    cliff_mask = df['xlyxlp_roc_20d'] < CLIFF_DIVE_THRESHOLD
    cliff_dates = df.index[cliff_mask & df['composite_score'].notna()]

    # De-duplicate: keep only first day of each cluster (>= 20 trading day gap)
    deduped = []
    last_date = None
    for dt in cliff_dates:
        if last_date is None:
            deduped.append(dt)
            last_date = dt
        else:
            # Count trading days between
            gap = len(df.loc[last_date:dt]) - 1
            if gap >= CLIFF_DIVE_GAP:
                deduped.append(dt)
                last_date = dt

    print(f"  Raw cliff dive days: {len(cliff_dates)}")
    print(f"  De-duplicated events: {len(deduped)}")

    # Build event table
    events = []
    for dt in deduped:
        row = df.loc[dt]
        event = {
            'date': dt.strftime('%Y-%m-%d'),
            'composite_score': round(row['composite_score'], 3),
            'regime': row['regime'],
            'xly_xlp_ratio': round(row['xly_xlp_ratio'], 4),
            'roc_20d': round(row['xlyxlp_roc_20d'], 4),
        }
        # Forward returns for each ticker
        idx_pos = df.index.get_loc(dt)
        for ticker in RETURN_TICKERS:
            for n in [5, 10, 20]:
                if idx_pos + n < len(df):
                    fwd = df[ticker].iloc[idx_pos + n] / df[ticker].iloc[idx_pos] - 1
                    event[f'{ticker}_fwd_{n}d'] = round(fwd, 5)
                else:
                    event[f'{ticker}_fwd_{n}d'] = np.nan

        # Bounce flag: SPY +20d > 0?
        spy_20 = event.get('SPY_fwd_20d', np.nan)
        if pd.notna(spy_20):
            event['outcome_20d'] = 'BOUNCED' if spy_20 > 0 else 'CONTINUED LOWER'
        else:
            event['outcome_20d'] = 'PENDING'

        events.append(event)

    events_df = pd.DataFrame(events)
    save_path = DATA_DIR / 'cliff_dive_events.csv'
    events_df.to_csv(save_path, index=False)
    print(f"  Saved → {save_path}")

    if len(events_df) > 0:
        print(f"\n  CLIFF DIVE EVENTS:")
        for _, e in events_df.iterrows():
            print(f"    {e['date']}  Score: {e['composite_score']:+.2f}  "
                  f"Regime: {e['regime']}  SPY +20d: "
                  f"{e.get('SPY_fwd_20d', 'N/A')}")

    return events_df


# ══════════════════════════════════════════════════════════════════
# STEP 4 — CURRENT READING
# ══════════════════════════════════════════════════════════════════

def current_reading(df: pd.DataFrame, fwd_returns_df: pd.DataFrame) -> dict:
    """Extract current regime reading and map to historical returns."""
    print("[STEP 4] Current reading...")

    valid = df.dropna(subset=['composite_score'])
    last = valid.iloc[-1]
    last_date = valid.index[-1]

    score = last['composite_score']
    regime = last['regime']
    percentile = (valid['composite_score'] < score).mean() * 100

    # Historical returns for this regime bucket (SPY)
    spy_regime = fwd_returns_df[
        (fwd_returns_df['ticker'] == 'SPY') &
        (fwd_returns_df['regime'] == regime)
    ]
    hist_returns = {}
    for _, row in spy_regime.iterrows():
        hist_returns[row['window']] = row['avg_return']

    reading = {
        'date': last_date.strftime('%Y-%m-%d'),
        'score': score,
        'regime': regime,
        'percentile': percentile,
        'hist_returns': hist_returns,
        'z_vix_inv': last['z_vix_inv'],
        'z_hy_inv': last['z_hy_inv'],
        'z_t10y2y': last['z_t10y2y'],
        'z_xlyxlp': last['z_xlyxlp'],
    }

    print(f"\n  {'='*56}")
    print(f"  CURRENT REGIME SCORE: {score:.2f} — {regime}")
    print(f"  As of: {reading['date']}")
    print(f"  Percentile: {percentile:.1f}th of all readings since 2016")
    hist_str = ', '.join(f"{k} avg {v:+.3%}" for k, v in sorted(hist_returns.items()))
    print(f"  Historical SPY returns: {hist_str}")
    print(f"  {'='*56}\n")

    return reading


# ══════════════════════════════════════════════════════════════════
# STEP 5 — CHARTS
# ══════════════════════════════════════════════════════════════════

def chart_composite_score(df: pd.DataFrame, cliff_events: pd.DataFrame):
    """Chart 1: Composite score time series with regime bands + SPY."""
    print("[CHART 1] Composite score time series...")

    valid = df.dropna(subset=['composite_score']).copy()

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.6, 0.4],
        subplot_titles=['Regime Composite Score (4-signal z-score average)',
                        'SPY Price (context)'],
    )

    # ── Panel 1: Composite score line ──
    fig.add_trace(
        go.Scatter(
            x=valid.index, y=valid['composite_score'],
            mode='lines',
            line=dict(color=C_BLUE, width=1.5),
            name='Composite Score',
        ),
        row=1, col=1,
    )

    # Regime background bands (horizontal rectangles)
    for i, (lo, hi, label) in enumerate(zip(REGIME_BINS[:-1], REGIME_BINS[1:], REGIME_LABELS)):
        color = REGIME_COLORS[label]
        y0 = max(lo, valid['composite_score'].min() - 0.5)
        y1 = min(hi, valid['composite_score'].max() + 0.5)
        fig.add_hrect(
            y0=y0, y1=y1,
            fillcolor=color,
            line_width=0,
            annotation_text=label if abs(y1 - y0) > 0.3 else '',
            annotation_position='top left',
            annotation_font_size=9,
            annotation_font_color='rgba(255,255,255,0.6)',
            row=1, col=1,
        )

    # Zero line
    fig.add_hline(y=0, line_dash='dot', line_color='rgba(255,255,255,0.3)',
                  line_width=1, row=1, col=1)

    # Cliff dive vertical markers
    if len(cliff_events) > 0:
        for _, ev in cliff_events.iterrows():
            fig.add_vline(
                x=ev['date'],
                line_dash='dash',
                line_color=C_YELLOW,
                line_width=1,
                row=1, col=1,
            )
            fig.add_vline(
                x=ev['date'],
                line_dash='dash',
                line_color=C_YELLOW,
                line_width=1,
                row=2, col=1,
            )

    # ── Panel 2: SPY price ──
    fig.add_trace(
        go.Scatter(
            x=valid.index, y=valid['SPY'],
            mode='lines',
            line=dict(color='rgba(255,255,255,0.7)', width=1.2),
            name='SPY',
        ),
        row=2, col=1,
    )

    fig.update_layout(
        template='plotly_dark',
        height=700,
        margin=dict(l=60, r=30, t=50, b=30),
        showlegend=False,
        title_text='Regime Composite Score — "Diet CTA"',
    )
    fig.update_yaxes(title_text='Z-Score', row=1, col=1)
    fig.update_yaxes(title_text='SPY $', row=2, col=1)

    save_path = CHARTS_DIR / 'composite_score_chart.html'
    fig.write_html(str(save_path))
    print(f"  Saved → {save_path}")


def chart_regime_heatmap(fwd_returns_df: pd.DataFrame):
    """Chart 2: Regime returns heatmap (one facet per ticker)."""
    print("[CHART 2] Regime returns heatmap...")

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=RETURN_TICKERS,
        horizontal_spacing=0.08,
    )

    # Order regimes top → bottom: RISK-ON at top
    regime_order = list(reversed(REGIME_LABELS))
    window_order = [f'+{n}d' for n in FORWARD_WINDOWS]

    for col_idx, ticker in enumerate(RETURN_TICKERS, 1):
        subset = fwd_returns_df[fwd_returns_df['ticker'] == ticker].copy()

        # Build matrix
        z_vals = []
        text_vals = []
        for regime in regime_order:
            row_z = []
            row_t = []
            for window in window_order:
                match = subset[(subset['regime'] == regime) & (subset['window'] == window)]
                if len(match) == 0:
                    row_z.append(0)
                    row_t.append('N/A')
                else:
                    avg_ret = match.iloc[0]['avg_return']
                    n = int(match.iloc[0]['n'])
                    conf = confidence_tag(n)
                    row_z.append(avg_ret * 100)  # percent
                    row_t.append(f'{avg_ret:+.2%}<br>n={n} {conf}')
            z_vals.append(row_z)
            text_vals.append(row_t)

        fig.add_trace(
            go.Heatmap(
                z=z_vals,
                x=window_order,
                y=regime_order,
                text=text_vals,
                texttemplate='%{text}',
                textfont=dict(size=9),
                colorscale='RdYlGn',
                zmid=0,
                showscale=(col_idx == 3),
                colorbar=dict(title='Avg Ret %') if col_idx == 3 else None,
            ),
            row=1, col=col_idx,
        )

    fig.update_layout(
        template='plotly_dark',
        height=500,
        width=1200,
        margin=dict(l=220, r=30, t=60, b=40),
        title_text='Forward Returns by Regime Bucket',
    )

    save_path = CHARTS_DIR / 'regime_returns_heatmap.html'
    fig.write_html(str(save_path))
    print(f"  Saved → {save_path}")


def chart_cliff_dive(df: pd.DataFrame, cliff_events: pd.DataFrame):
    """Chart 3: Cliff dive forward return paths for SPY."""
    print("[CHART 3] Cliff dive study chart...")

    if len(cliff_events) == 0:
        print("  No cliff dive events — skipping chart.")
        return

    fig = go.Figure()
    all_paths = []

    for _, ev in cliff_events.iterrows():
        ev_date = pd.Timestamp(ev['date'])
        if ev_date not in df.index:
            continue
        idx_pos = df.index.get_loc(ev_date)

        # Extract 21 trading days of SPY prices (day 0 through day +20)
        end_pos = min(idx_pos + 21, len(df))
        path_prices = df['SPY'].iloc[idx_pos:end_pos]
        if len(path_prices) < 2:
            continue

        base = path_prices.iloc[0]
        cum_returns = (path_prices / base - 1) * 100  # percent
        days = list(range(len(cum_returns)))

        outcome = ev.get('outcome_20d', 'PENDING')
        color = C_GREEN if outcome == 'BOUNCED' else C_RED if outcome == 'CONTINUED LOWER' else 'rgba(255,255,255,0.4)'

        fig.add_trace(go.Scatter(
            x=days, y=cum_returns.values,
            mode='lines',
            line=dict(color=color, width=1.2),
            opacity=0.6,
            name=f"{ev['date']} ({outcome})",
            hovertemplate=f"{ev['date']}<br>Day %{{x}}: %{{y:.2f}}%<extra></extra>",
        ))

        all_paths.append(cum_returns.values)

    # Average path
    if all_paths:
        max_len = max(len(p) for p in all_paths)
        padded = np.full((len(all_paths), max_len), np.nan)
        for i, p in enumerate(all_paths):
            padded[i, :len(p)] = p
        avg_path = np.nanmean(padded, axis=0)

        fig.add_trace(go.Scatter(
            x=list(range(len(avg_path))), y=avg_path,
            mode='lines',
            line=dict(color=C_YELLOW, width=3),
            name=f'Average (n={len(all_paths)})',
        ))

    fig.update_layout(
        template='plotly_dark',
        height=500,
        margin=dict(l=60, r=30, t=50, b=40),
        title_text='XLY/XLP Cliff Dive Events — SPY Forward Return Paths',
        xaxis_title='Trading Days from Event',
        yaxis_title='Cumulative Return (%)',
        legend=dict(font=dict(size=9)),
    )
    fig.add_hline(y=0, line_dash='dot', line_color='rgba(255,255,255,0.3)', line_width=1)

    save_path = CHARTS_DIR / 'cliff_dive_study.html'
    fig.write_html(str(save_path))
    print(f"  Saved → {save_path}")


# ══════════════════════════════════════════════════════════════════
# STEP 6 — SUMMARY
# ══════════════════════════════════════════════════════════════════

def write_summary(reading: dict, fwd_returns_df: pd.DataFrame,
                  cliff_events: pd.DataFrame, df: pd.DataFrame):
    """Generate summary_stats.txt."""
    print("[STEP 6] Writing summary...")

    lines = []

    # ── Section 1: Current Reading ──
    lines.append('=' * 60)
    lines.append('CURRENT REGIME READING')
    lines.append('=' * 60)
    lines.append('')
    lines.append(f"  CURRENT REGIME SCORE: {reading['score']:.2f} — {reading['regime']}")
    lines.append(f"  As of: {reading['date']}")
    lines.append(f"  This maps to the {reading['percentile']:.1f}th percentile of all readings since 2016")
    lines.append('')
    lines.append('  Component Z-Scores:')
    lines.append(f"    VIX (inverted):      {reading['z_vix_inv']:+.2f}")
    lines.append(f"    HY Spread (inverted): {reading['z_hy_inv']:+.2f}")
    lines.append(f"    2s10s Yield Curve:   {reading['z_t10y2y']:+.2f}")
    lines.append(f"    XLY/XLP Ratio:       {reading['z_xlyxlp']:+.2f}")
    lines.append('')
    if reading['hist_returns']:
        lines.append('  Historical forward returns from this regime:')
        for window, ret in sorted(reading['hist_returns'].items()):
            lines.append(f"    SPY {window}: avg {ret:+.3%}")
    lines.append('')

    # ── Section 2: Forward Returns Table ──
    lines.append('=' * 60)
    lines.append('FORWARD RETURNS BY REGIME')
    lines.append('=' * 60)
    lines.append('')

    for ticker in RETURN_TICKERS:
        lines.append(f'  ── {ticker} ──')
        ticker_data = fwd_returns_df[fwd_returns_df['ticker'] == ticker]

        # Header
        header = f"  {'Regime':<42} {'Window':>6} {'n':>6} {'Win%':>7} {'AvgRet':>8} {'MedRet':>8} {'Std':>8}  Confidence"
        lines.append(header)
        lines.append('  ' + '-' * (len(header) - 2))

        for regime in REGIME_LABELS:
            regime_data = ticker_data[ticker_data['regime'] == regime]
            for _, row in regime_data.iterrows():
                lines.append(
                    f"  {regime:<42} {row['window']:>6} {int(row['n']):>6} "
                    f"{row['win_rate']:>6.1%} {row['avg_return']:>+7.3%} "
                    f"{row['median_return']:>+7.3%} {row['std']:>7.3%}  "
                    f"{row['confidence']}"
                )
        lines.append('')

    # ── Section 3: Cliff Dive Events ──
    lines.append('=' * 60)
    lines.append('CLIFF DIVE EVENT STUDY (XLY/XLP 20d ROC < -10%)')
    lines.append('=' * 60)
    lines.append('')

    n_events = len(cliff_events)
    lines.append(f'  Total events identified: {n_events}')

    if n_events > 0:
        lines.append('')
        for _, ev in cliff_events.iterrows():
            lines.append(f"  {ev['date']}  |  Score: {ev['composite_score']:+.3f}  "
                         f"|  Regime: {ev['regime']}  |  ROC: {ev['roc_20d']:+.2%}")
            for ticker in RETURN_TICKERS:
                parts = []
                for n in [5, 10, 20]:
                    val = ev.get(f'{ticker}_fwd_{n}d', np.nan)
                    if pd.notna(val):
                        parts.append(f'+{n}d: {val:+.2%}')
                    else:
                        parts.append(f'+{n}d: N/A')
                lines.append(f"    {ticker}: {' | '.join(parts)}")
            lines.append(f"    Outcome: {ev.get('outcome_20d', 'N/A')}")
            lines.append('')

        # Aggregate stats
        for ticker in RETURN_TICKERS:
            lines.append(f'  ── {ticker} Cliff Dive Aggregate ──')
            for n in [5, 10, 20]:
                col = f'{ticker}_fwd_{n}d'
                if col in cliff_events.columns:
                    vals = cliff_events[col].dropna()
                    if len(vals) > 0:
                        lines.append(
                            f"    +{n}d:  avg {vals.mean():+.2%}  |  "
                            f"median {vals.median():+.2%}  |  "
                            f"win rate {(vals > 0).mean():.0%}  |  n={len(vals)}"
                        )
            lines.append('')

        # Bounce rate
        if 'outcome_20d' in cliff_events.columns:
            resolved = cliff_events[cliff_events['outcome_20d'].isin(['BOUNCED', 'CONTINUED LOWER'])]
            if len(resolved) > 0:
                bounce_rate = (resolved['outcome_20d'] == 'BOUNCED').mean()
                lines.append(f'  20-day resolution: {bounce_rate:.0%} bounced, '
                             f'{1-bounce_rate:.0%} continued lower (n={len(resolved)})')
                lines.append('')

    # ── Section 4: Sample Size Context ──
    lines.append('=' * 60)
    lines.append('SAMPLE SIZE CONTEXT')
    lines.append('=' * 60)
    lines.append('')
    lines.append(f'  Total cliff dive events found: n={n_events}')
    lines.append(f'  Confidence classification: {confidence_tag(n_events)}')
    lines.append('')
    lines.append('  Doctrine:')
    lines.append('    n >= 20: [RELIABLE]')
    lines.append('    n 10-19: [LOW CONFIDENCE - directional only]')
    lines.append('    n < 10:  [INSUFFICIENT - pattern recognition only]')
    lines.append('')

    if n_events > 0 and 'outcome_20d' in cliff_events.columns:
        resolved = cliff_events[cliff_events['outcome_20d'].isin(['BOUNCED', 'CONTINUED LOWER'])]
        if len(resolved) > 0:
            bounce_rate = (resolved['outcome_20d'] == 'BOUNCED').mean()
            lines.append(
                f'  Small n does not kill this thesis. {n_events} events with '
                f'{bounce_rate:.0%} resolution rate + specific technical '
                f'fingerprint = actionable with reduced sizing and tight technicals.'
            )
        else:
            lines.append(
                f'  Small n does not kill this thesis. {n_events} events with '
                f'pending resolution + specific technical fingerprint = '
                f'actionable with reduced sizing and tight technicals.'
            )
    else:
        lines.append(
            f'  Small n does not kill this thesis. {n_events} events with '
            f'specific technical fingerprint = actionable with reduced sizing '
            f'and tight technicals.'
        )
    lines.append('')

    # ── Section 5: Regime Forward Returns — Sample Sizes ──
    lines.append('=' * 60)
    lines.append('REGIME BUCKET SAMPLE SIZES')
    lines.append('=' * 60)
    lines.append('')

    for regime in REGIME_LABELS:
        regime_data = fwd_returns_df[(fwd_returns_df['regime'] == regime) &
                                     (fwd_returns_df['ticker'] == 'SPY') &
                                     (fwd_returns_df['window'] == '+5d')]
        if len(regime_data) > 0:
            n = int(regime_data.iloc[0]['n'])
            lines.append(f"  {regime:<42}  n={n:<6}  {confidence_tag(n)}")
        else:
            lines.append(f"  {regime:<42}  n=0     [NO DATA]")
    lines.append('')

    # ── Section 6: Plain-English Interpretation ──
    lines.append('=' * 60)
    lines.append('INTERPRETATION')
    lines.append('=' * 60)
    lines.append('')
    lines.append(f"  Current composite score ({reading['score']:.2f}) places the macro regime in")
    lines.append(f"  {reading['regime']} territory, at the {reading['percentile']:.1f}th percentile")
    lines.append(f"  of all readings since January 2016.")
    lines.append('')

    # Interpret component signals
    components = [
        ('VIX (inverted)', reading['z_vix_inv']),
        ('HY Spread (inverted)', reading['z_hy_inv']),
        ('2s10s Yield Curve', reading['z_t10y2y']),
        ('XLY/XLP Ratio', reading['z_xlyxlp']),
    ]
    most_bullish = max(components, key=lambda x: x[1])
    most_bearish = min(components, key=lambda x: x[1])
    lines.append(f"  Most bullish signal: {most_bullish[0]} at {most_bullish[1]:+.2f}")
    lines.append(f"  Most bearish signal: {most_bearish[0]} at {most_bearish[1]:+.2f}")
    lines.append('')

    if reading['hist_returns']:
        ret_5d = reading['hist_returns'].get('+5d', None)
        ret_20d = reading['hist_returns'].get('+20d', None)
        if ret_5d is not None and ret_20d is not None:
            lines.append(f"  Historical precedent for this regime: SPY +5d avg {ret_5d:+.3%}, "
                         f"+20d avg {ret_20d:+.3%}.")
    lines.append('')
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Write
    save_path = SUMMARY_DIR / 'summary_stats.txt'
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"  Saved → {save_path}")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print('=' * 60)
    print('REGIME COMPOSITE SCORE — ANALYSIS')
    print('=' * 60)
    print()

    # Load raw merged data
    raw_path = DATA_DIR / 'raw_merged.csv'
    if not raw_path.exists():
        raise FileNotFoundError(f"Run collect_data.py first. Missing: {raw_path}")

    df = pd.read_csv(raw_path, index_col=0, parse_dates=True)
    print(f"Loaded {len(df)} rows from {raw_path.name}")
    print()

    # Step 1: Build composite score
    df = build_composite(df)
    print()

    # Step 2: Forward returns by regime
    fwd_returns_df = compute_forward_returns(df)
    print()

    # Step 3: Cliff dive event study
    cliff_events = cliff_dive_study(df)
    print()

    # Step 4: Current reading
    reading = current_reading(df, fwd_returns_df)

    # Step 5: Charts
    print()
    chart_composite_score(df, cliff_events)
    chart_regime_heatmap(fwd_returns_df)
    chart_cliff_dive(df, cliff_events)
    print()

    # Step 6: Summary
    write_summary(reading, fwd_returns_df, cliff_events, df)

    print()
    print('ANALYSIS COMPLETE')
    print(f"  Charts → {CHARTS_DIR}")
    print(f"  Data   → {DATA_DIR}")
    print(f"  Summary → {SUMMARY_DIR}")


if __name__ == '__main__':
    main()
