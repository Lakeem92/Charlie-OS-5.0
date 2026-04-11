"""
QuantLab Morning Dashboard
Generates a single interactive HTML file (scratch/dashboard/index.html)
serving as a visual war room dashboard viewable in VS Code Simple Browser.
"""

import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

from dotenv import load_dotenv
load_dotenv(r'C:\QuantLab\Data_Lab\.env', override=True)

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from shared.data_router import DataRouter
from shared.watchlist import get_watchlist
from shared.config.api_clients import FREDClient

# ── Constants ──────────────────────────────────────────────────
GREEN = "#26a69a"
RED = "#ef5350"
BLUE = "#42a5f5"
BG_COLOR = "#111111"
CARD_BG = "#1e1e1e"
TEXT_COLOR = "#e0e0e0"
MUTED_TEXT = "#888888"

OUTPUT_DIR = Path(r"C:\QuantLab\Data_Lab\scratch\dashboard")
OUTPUT_FILE = OUTPUT_DIR / "index.html"


# ══════════════════════════════════════════════════════════════
#  PHASE 1 — DATA FETCHING
# ══════════════════════════════════════════════════════════════

def fetch_macro_indices(lookback_days: int = 90) -> dict:
    """Pull ^VIX, ^SPX, ^NDX, ^RUT via yfinance (last 90 days)."""
    start = (datetime.now() - timedelta(days=lookback_days + 10)).strftime("%Y-%m-%d")
    tickers = {"VIX": "^VIX", "S&P 500": "^SPX", "NASDAQ": "^NDX", "Russell 2000": "^RUT"}
    results = {}
    for label, sym in tickers.items():
        try:
            df = DataRouter.get_price_data(sym, start, source="yfinance")
            df = df.tail(lookback_days)
            results[label] = df
        except Exception as e:
            print(f"  ⚠ Failed to fetch {label} ({sym}): {e}")
    return results


def fetch_fred_series(lookback_days: int = 90) -> dict:
    """Pull HY spread and yield curve directly from FRED via FREDClient."""
    start = (datetime.now() - timedelta(days=lookback_days + 30)).strftime("%Y-%m-%d")
    series = {
        "HY Spread": "BAMLH0A0HYM2",
        "Yield Curve (10Y-2Y)": "T10Y2Y",
    }
    fred = FREDClient()
    results = {}
    for label, sid in series.items():
        try:
            s = fred.get_series(sid, start_date=start)
            df = s.dropna().tail(lookback_days).to_frame(name="value")
            results[label] = df
        except Exception as e:
            print(f"  ⚠ FRED failed for {label} ({sid}): {e}")
    return results


def fetch_xly_xlp(lookback_days: int = 370) -> pd.DataFrame:
    """Pull XLY/XLP, compute ratio + 20-day MA (last 252 trading days)."""
    start = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    xly = DataRouter.get_price_data("XLY", start)
    xlp = DataRouter.get_price_data("XLP", start)
    # Align dates
    ratio_df = pd.DataFrame(index=xly.index)
    ratio_df["XLY"] = xly["Close"]
    ratio_df["XLP"] = xlp["Close"].reindex(xly.index, method="ffill")
    ratio_df["ratio"] = ratio_df["XLY"] / ratio_df["XLP"]
    ratio_df["ma20"] = ratio_df["ratio"].rolling(20).mean()
    ratio_df = ratio_df.dropna().tail(252)
    # Strip timezone so Plotly renders the traces correctly
    dt_index = pd.DatetimeIndex(ratio_df.index)
    if dt_index.tz is not None:
        ratio_df.index = dt_index.tz_localize(None)
    return ratio_df


def fetch_risk_spread(lookback_days: int = 370) -> pd.DataFrame:
    """Compute risk-on vs defensive basket spread over 252 trading days.
    Risk-On: XLY + XLK + XLF | Defensive: XLP + XLU + XLV
    """
    start = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    risk_on_tickers = ["XLY", "XLK", "XLF"]
    defensive_tickers = ["XLP", "XLU", "XLV"]

    all_close = {}
    for t in risk_on_tickers + defensive_tickers:
        try:
            df = DataRouter.get_price_data(t, start)
            all_close[t] = df["Close"]
        except Exception as e:
            print(f"  ⚠ Failed to fetch {t}: {e}")

    close_df = pd.DataFrame(all_close).dropna()
    if close_df.empty or len(close_df) < 30:
        return pd.DataFrame()

    # Normalize to 100 at start
    norm_df = (close_df / close_df.iloc[0]) * 100

    risk_on_cols = [c for c in risk_on_tickers if c in norm_df.columns]
    defensive_cols = [c for c in defensive_tickers if c in norm_df.columns]
    if not risk_on_cols or not defensive_cols:
        return pd.DataFrame()

    result = pd.DataFrame(index=norm_df.index)
    result["risk_on"] = norm_df[risk_on_cols].mean(axis=1)
    result["defensive"] = norm_df[defensive_cols].mean(axis=1)
    result["spread"] = result["risk_on"] - result["defensive"]
    result["spread_ma"] = result["spread"].rolling(20).mean()

    # Slope: 5-day change of 20d MA
    result["slope"] = result["spread_ma"].diff(5)

    # Adaptive regime classification
    slope_std = result["slope"].std()
    threshold = slope_std * 0.3 if slope_std > 0 else 0.1
    result["regime"] = "FLAT"
    result.loc[result["slope"] > threshold, "regime"] = "WIDENING"
    result.loc[result["slope"] < -threshold, "regime"] = "NARROWING"

    result = result.dropna().tail(252)

    dt_index = pd.DatetimeIndex(result.index)
    if dt_index.tz is not None:
        result.index = dt_index.tz_localize(None)
    return result


def fetch_watchlist_movers() -> pd.DataFrame:
    """Get today's % change for watchlist tickers via batch yfinance download."""
    import yfinance as yf

    tickers = get_watchlist()
    # Filter to likely-valid equity tickers (skip indices/special symbols)
    equity_tickers = [t for t in tickers if not t.startswith("^") and "." not in t]

    start = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

    # Batch download — much faster than one-by-one
    raw = yf.download(equity_tickers, start=start, progress=False, auto_adjust=True, threads=True)
    if raw is None or raw.empty:
        return pd.DataFrame(columns=["ticker", "pct_change"])

    records = []
    for t in equity_tickers:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                close = raw["Close"][t].dropna()
            else:
                close = raw["Close"].dropna()
            if len(close) >= 2:
                prev_close = close.iloc[-2]
                last_close = close.iloc[-1]
                pct = ((last_close - prev_close) / prev_close) * 100
                records.append({"ticker": t, "pct_change": round(float(pct), 2)})
        except Exception:
            pass
    if not records:
        return pd.DataFrame(columns=["ticker", "pct_change"])
    return pd.DataFrame(records).sort_values("pct_change", ascending=False)


# ══════════════════════════════════════════════════════════════
#  PHASE 2 — PANEL BUILDERS
# ══════════════════════════════════════════════════════════════

def _sparkline_color(label: str, change: float) -> str:
    """Return green or red depending on risk-on/risk-off direction."""
    # UP = bad (risk-off) → red: VIX and HY Spread (wider spread = stress)
    # Everything else: UP = good (risk-on) → green
    risk_off_up = {"VIX", "HY Spread"}
    if label in risk_off_up:
        return RED if change > 0 else GREEN
    return GREEN if change > 0 else RED


def build_macro_scorecard(macro_data: dict, fred_data: dict) -> go.Figure:
    """Build a 2×3 sparkline scorecard grid."""
    # Ordered grid: row1=[VIX, SPX, NDX], row2=[RUT, HY Spread, Yield Curve]
    grid_items = [
        ("VIX", macro_data.get("VIX")),
        ("S&P 500", macro_data.get("S&P 500")),
        ("NASDAQ", macro_data.get("NASDAQ")),
        ("Russell 2000", macro_data.get("Russell 2000")),
        ("HY Spread", fred_data.get("HY Spread")),
        ("Yield Curve (10Y-2Y)", fred_data.get("Yield Curve (10Y-2Y)")),
    ]

    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=[g[0] for g in grid_items],
        vertical_spacing=0.18,
        horizontal_spacing=0.08,
    )

    for idx, (label, df) in enumerate(grid_items):
        row = idx // 3 + 1
        col = idx % 3 + 1

        if df is None or df.empty:
            fig.add_annotation(
                text="No Data", row=row, col=col,
                font=dict(color=RED, size=14), showarrow=False,
            )
            continue

        # Extract series
        if "Close" in df.columns:
            vals = df["Close"]
        elif "value" in df.columns:
            vals = df["value"]
        else:
            continue

        vals = vals.dropna()
        if len(vals) < 2:
            continue

        current = vals.iloc[-1]
        # 5-day change
        lookback_5 = min(5, len(vals) - 1)
        change_5d = current - vals.iloc[-(lookback_5 + 1)]
        pct_5d = (change_5d / abs(vals.iloc[-(lookback_5 + 1)])) * 100 if vals.iloc[-(lookback_5 + 1)] != 0 else 0

        # Last 30 days for sparkline
        spark_vals = vals.tail(30)
        color = _sparkline_color(label, change_5d)

        # Sparkline trace
        fig.add_trace(
            go.Scatter(
                x=spark_vals.index, y=spark_vals.values,
                mode="lines", line=dict(color=color, width=2),
                fill="tozeroy", fillcolor=f"rgba({','.join(str(int(color.lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.1)",
                showlegend=False, hovertemplate="%{y:.2f}<extra></extra>",
            ),
            row=row, col=col,
        )

        # Current value annotation
        fig.add_annotation(
            x=0.5, y=0.95, xref=f"x{idx+1} domain" if idx > 0 else "x domain",
            yref=f"y{idx+1} domain" if idx > 0 else "y domain",
            text=f"<b>{current:,.2f}</b>",
            showarrow=False, font=dict(size=22, color=TEXT_COLOR),
        )

        # 5-day change annotation
        arrow = "▲" if change_5d > 0 else "▼"
        fig.add_annotation(
            x=0.5, y=0.75, xref=f"x{idx+1} domain" if idx > 0 else "x domain",
            yref=f"y{idx+1} domain" if idx > 0 else "y domain",
            text=f"{arrow} {pct_5d:+.2f}% (5d)",
            showarrow=False, font=dict(size=12, color=color),
        )

    fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR,
        height=420, margin=dict(l=30, r=30, t=50, b=20),
        title=dict(text="Macro Regime Scorecard", font=dict(size=16, color=TEXT_COLOR)),
    )
    # Remove axis labels/ticks for clean sparklines
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False)
    fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)

    return fig


def build_vix_gauge(macro_data: dict) -> go.Figure:
    """Build a VIX regime gauge."""
    vix_df = macro_data.get("VIX")
    current_vix = 20.0  # fallback
    if vix_df is not None and not vix_df.empty and "Close" in vix_df.columns:
        current_vix = float(vix_df["Close"].dropna().iloc[-1])

    # Determine regime label
    if current_vix < 15:
        regime = "Low Vol / Trend Mode"
    elif current_vix < 20:
        regime = "Normal"
    elif current_vix < 25:
        regime = "Elevated"
    elif current_vix < 35:
        regime = "High Vol / Fade Mode"
    else:
        regime = "Panic / Crisis"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=current_vix,
        number=dict(font=dict(size=48, color=TEXT_COLOR), suffix=""),
        title=dict(text=f"VIX Regime: {regime}", font=dict(size=14, color=TEXT_COLOR)),
        gauge=dict(
            axis=dict(range=[0, 50], tickwidth=1, tickcolor=MUTED_TEXT,
                      tickfont=dict(color=MUTED_TEXT)),
            bar=dict(color=BLUE, thickness=0.3),
            bgcolor=CARD_BG,
            borderwidth=0,
            steps=[
                dict(range=[0, 15], color="#1b5e20"),     # dark green
                dict(range=[15, 20], color="#558b2f"),    # yellow-green
                dict(range=[20, 25], color="#f9a825"),    # yellow
                dict(range=[25, 35], color="#e65100"),    # orange
                dict(range=[35, 50], color="#b71c1c"),    # dark red
            ],
            threshold=dict(
                line=dict(color="white", width=3),
                thickness=0.8, value=current_vix,
            ),
        ),
    ))

    fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR,
        height=420, margin=dict(l=30, r=30, t=60, b=20),
        title=dict(text="VIX Regime Gauge", font=dict(size=16, color=TEXT_COLOR)),
    )
    return fig


def build_xly_xlp_panel(ratio_df: pd.DataFrame) -> go.Figure:
    """Build XLY/XLP ratio chart with 20-day MA and regime label."""
    fig = go.Figure()

    # 52-week range band
    hi = ratio_df["ratio"].max()
    lo = ratio_df["ratio"].min()
    fig.add_hrect(y0=lo, y1=hi, fillcolor="rgba(66,165,245,0.06)",
                  line_width=0, layer="below")

    # Ratio line
    fig.add_trace(go.Scatter(
        x=ratio_df.index, y=ratio_df["ratio"],
        mode="lines", name="XLY/XLP Ratio",
        line=dict(color=BLUE, width=2),
        hovertemplate="Ratio: %{y:.4f}<extra></extra>",
    ))

    # 20-day MA
    fig.add_trace(go.Scatter(
        x=ratio_df.index, y=ratio_df["ma20"],
        mode="lines", name="20-day MA",
        line=dict(color=MUTED_TEXT, width=1.5, dash="dash"),
        hovertemplate="MA20: %{y:.4f}<extra></extra>",
    ))

    # Regime label
    current_ratio = ratio_df["ratio"].iloc[-1]
    current_ma = ratio_df["ma20"].iloc[-1]
    risk_on = current_ratio > current_ma
    regime_text = "RISK-ON ▲" if risk_on else "RISK-OFF ▼"
    regime_color = GREEN if risk_on else RED

    fig.add_annotation(
        x=ratio_df.index[-1], y=current_ratio,
        text=f"<b>{regime_text}</b>  ({current_ratio:.4f})",
        showarrow=True, arrowhead=2, arrowcolor=regime_color,
        font=dict(size=14, color=regime_color),
        ax=-80, ay=-30,
    )

    # 52-week range labels
    fig.add_annotation(
        x=ratio_df.index[0], y=hi,
        text=f"52w High: {hi:.4f}", showarrow=False,
        font=dict(size=10, color=MUTED_TEXT), xanchor="left",
    )
    fig.add_annotation(
        x=ratio_df.index[0], y=lo,
        text=f"52w Low: {lo:.4f}", showarrow=False,
        font=dict(size=10, color=MUTED_TEXT), xanchor="left",
    )

    fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR,
        height=320, margin=dict(l=50, r=30, t=50, b=30),
        title=dict(text="XLY / XLP Ratio — Risk Appetite (252 days)",
                   font=dict(size=16, color=TEXT_COLOR)),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1,
                    font=dict(color=MUTED_TEXT)),
        yaxis=dict(title="Ratio", gridcolor="#2a2a2a"),
        xaxis=dict(gridcolor="#2a2a2a"),
    )
    return fig


def build_risk_spread_panel(spread_df: pd.DataFrame) -> go.Figure:
    """Build risk-on vs defensive spread line chart with regime signals."""
    fig = go.Figure()

    # Zero reference line
    fig.add_hline(y=0, line_dash="dot", line_color=MUTED_TEXT, line_width=1,
                  annotation_text="Parity", annotation_font_color=MUTED_TEXT,
                  annotation_font_size=10)

    # Regime background shading
    regime_colors = {
        "WIDENING": "rgba(38,166,154,0.08)",
        "NARROWING": "rgba(239,83,80,0.08)",
        "FLAT": "rgba(136,136,136,0.04)",
    }
    regimes = spread_df["regime"]
    i = 0
    while i < len(regimes):
        current_regime = regimes.iloc[i]
        start_idx = i
        while i < len(regimes) and regimes.iloc[i] == current_regime:
            i += 1
        end_idx = i - 1
        fig.add_vrect(
            x0=spread_df.index[start_idx], x1=spread_df.index[end_idx],
            fillcolor=regime_colors.get(current_regime, "rgba(0,0,0,0)"),
            line_width=0, layer="below",
        )

    # Spread line
    fig.add_trace(go.Scatter(
        x=spread_df.index, y=spread_df["spread"],
        mode="lines", name="Spread",
        line=dict(color=BLUE, width=2),
        hovertemplate="Spread: %{y:.2f}<extra></extra>",
    ))

    # 20-day MA
    fig.add_trace(go.Scatter(
        x=spread_df.index, y=spread_df["spread_ma"],
        mode="lines", name="20d MA",
        line=dict(color=MUTED_TEXT, width=1.5, dash="dash"),
        hovertemplate="MA20: %{y:.2f}<extra></extra>",
    ))

    # Current regime annotation
    current_regime = spread_df["regime"].iloc[-1]
    current_spread = spread_df["spread"].iloc[-1]
    regime_display = {
        "WIDENING": ("RISK-ON WIDENING ▲", GREEN),
        "NARROWING": ("DEFENSIVE WINNING ▼", RED),
        "FLAT": ("SPREAD FLAT ─", MUTED_TEXT),
    }
    label, color = regime_display.get(current_regime, ("UNKNOWN", MUTED_TEXT))

    fig.add_annotation(
        x=spread_df.index[-1], y=current_spread,
        text=f"<b>{label}</b>  ({current_spread:+.2f})",
        showarrow=True, arrowhead=2, arrowcolor=color,
        font=dict(size=14, color=color),
        ax=-120, ay=-30,
    )

    fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR,
        height=340, margin=dict(l=50, r=30, t=50, b=30),
        title=dict(
            text="Risk-On vs Defensive Spread — Capital Flow (XLY+XLK+XLF vs XLP+XLU+XLV)",
            font=dict(size=16, color=TEXT_COLOR),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1,
                    font=dict(color=MUTED_TEXT)),
        yaxis=dict(title="Spread (normalized)", gridcolor="#2a2a2a"),
        xaxis=dict(gridcolor="#2a2a2a"),
    )
    return fig


def build_watchlist_movers(movers_df: pd.DataFrame) -> go.Figure:
    """Build horizontal bar chart of top 5 gainers and top 5 losers."""
    if movers_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No watchlist data available",
                           showarrow=False, font=dict(color=RED, size=16))
        fig.update_layout(template="plotly_dark", paper_bgcolor=BG_COLOR,
                          plot_bgcolor=BG_COLOR, height=360)
        return fig

    top5 = movers_df.head(5).copy()
    bot5 = movers_df.tail(5).copy()
    display = pd.concat([bot5, top5])  # losers at bottom, gainers at top

    colors = [RED if p < 0 else GREEN for p in display["pct_change"]]

    fig = go.Figure(go.Bar(
        y=display["ticker"], x=display["pct_change"],
        orientation="h",
        marker_color=colors,
        text=[f"{p:+.2f}%" for p in display["pct_change"]],
        textposition="outside",
        textfont=dict(color=TEXT_COLOR, size=12),
        hovertemplate="%{y}: %{x:+.2f}%<extra></extra>",
    ))

    fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR,
        height=360, margin=dict(l=80, r=60, t=50, b=30),
        title=dict(text="Watchlist Movers — Top 5 Gainers / Top 5 Losers",
                   font=dict(size=16, color=TEXT_COLOR)),
        xaxis=dict(title="% Change", gridcolor="#2a2a2a", zeroline=True,
                   zerolinecolor=MUTED_TEXT, zerolinewidth=1),
        yaxis=dict(gridcolor="#2a2a2a"),
    )
    return fig


# ══════════════════════════════════════════════════════════════
#  PHASE 3 — HTML ASSEMBLY
# ══════════════════════════════════════════════════════════════

def assemble_dashboard(scorecard_fig, gauge_fig, ratio_fig, spread_fig, movers_fig) -> str:
    """Combine all panels into a single self-contained HTML file."""
    # First panel embeds plotly.js; rest reuse it
    scorecard_html = scorecard_fig.to_html(full_html=False, include_plotlyjs=True)
    gauge_html = gauge_fig.to_html(full_html=False, include_plotlyjs=False)
    ratio_html = ratio_fig.to_html(full_html=False, include_plotlyjs=False)
    spread_html = spread_fig.to_html(full_html=False, include_plotlyjs=False)
    movers_html = movers_fig.to_html(full_html=False, include_plotlyjs=False)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S CT")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QuantLab Morning Dashboard</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: {BG_COLOR};
    color: {TEXT_COLOR};
    font-family: 'Segoe UI', -apple-system, sans-serif;
  }}
  .header {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 24px 8px 24px;
    border-bottom: 1px solid #2a2a2a;
  }}
  .header h1 {{
    font-size: 22px; font-weight: 600; letter-spacing: 0.5px;
    color: {TEXT_COLOR};
  }}
  .header .timestamp {{
    font-size: 13px; color: {MUTED_TEXT};
  }}
  .grid-top {{
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 0;
    padding: 8px 12px;
  }}
  .panel {{
    padding: 4px 8px;
  }}
  .full-width {{
    padding: 4px 20px;
  }}
</style>
</head>
<body>
  <div class="header">
    <h1>QuantLab Morning Dashboard</h1>
    <div class="timestamp">Last Updated: {timestamp}</div>
  </div>

  <div class="grid-top">
    <div class="panel">{scorecard_html}</div>
    <div class="panel">{gauge_html}</div>
  </div>

  <div class="full-width">{ratio_html}</div>
  <div class="full-width">{spread_html}</div>
  <div class="full-width">{movers_html}</div>
</body>
</html>"""
    return html


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  QuantLab Morning Dashboard — Building...")
    print("=" * 60)

    # ── Fetch data ────────────────────────────────────────────
    print("\n[1/5] Fetching macro indices (VIX, SPX, NDX, RUT)...")
    try:
        macro_data = fetch_macro_indices()
        print(f"       ✓ Got {len(macro_data)} indices")
    except Exception as e:
        print(f"       ✗ Macro fetch failed: {e}")
        macro_data = {}

    print("[2/5] Fetching FRED series (HY Spread, Yield Curve)...")
    try:
        fred_data = fetch_fred_series()
        hy = fred_data.get("HY Spread")
        yc = fred_data.get("Yield Curve (10Y-2Y)")
        if hy is not None and not hy.empty:
            print(f"  ✅ HY Spread (FRED): {hy['value'].iloc[-1]:.2f}%")
        if yc is not None and not yc.empty:
            print(f"  ✅ Yield Curve (FRED): {yc['value'].iloc[-1]:.2f}%")
    except Exception as e:
        print(f"       ✗ FRED fetch failed: {e}")
        fred_data = {}

    print("[3/5] Fetching XLY/XLP ratio...")
    ratio_df = None
    try:
        ratio_df = fetch_xly_xlp()
        print(f"       ✓ {len(ratio_df)} trading days")
    except Exception as e:
        print(f"       ✗ XLY/XLP fetch failed: {e}")

    print("[4/5] Fetching risk-on vs defensive spread...")
    spread_df = None
    try:
        spread_df = fetch_risk_spread()
        print(f"       ✓ {len(spread_df)} trading days")
    except Exception as e:
        print(f"       ✗ Risk spread fetch failed: {e}")
        spread_df = pd.DataFrame()

    print("[5/5] Fetching watchlist movers...")
    try:
        movers_df = fetch_watchlist_movers()
        print(f"       ✓ {len(movers_df)} tickers processed")
    except Exception as e:
        print(f"       ✗ Watchlist fetch failed: {e}")
        movers_df = pd.DataFrame(columns=["ticker", "pct_change"])

    # ── Build panels ──────────────────────────────────────────
    print("\nBuilding panels...")
    scorecard_fig = build_macro_scorecard(macro_data, fred_data)
    gauge_fig = build_vix_gauge(macro_data)

    if ratio_df is not None and not ratio_df.empty:
        ratio_fig = build_xly_xlp_panel(ratio_df)
    else:
        ratio_fig = go.Figure()
        ratio_fig.add_annotation(text="XLY/XLP data unavailable",
                                 showarrow=False, font=dict(color=RED, size=16))
        ratio_fig.update_layout(template="plotly_dark", paper_bgcolor=BG_COLOR,
                                plot_bgcolor=BG_COLOR, height=320)

    movers_fig = build_watchlist_movers(movers_df)

    if spread_df is not None and not spread_df.empty:
        spread_fig = build_risk_spread_panel(spread_df)
    else:
        spread_fig = go.Figure()
        spread_fig.add_annotation(text="Risk spread data unavailable",
                                  showarrow=False, font=dict(color=RED, size=16))
        spread_fig.update_layout(template="plotly_dark", paper_bgcolor=BG_COLOR,
                                 plot_bgcolor=BG_COLOR, height=340)

    # ── Assemble & write ──────────────────────────────────────
    print("Assembling HTML...")
    html = assemble_dashboard(scorecard_fig, gauge_fig, ratio_fig, spread_fig, movers_fig)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")

    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"\n✓ Dashboard saved to: {OUTPUT_FILE}")
    print(f"  File size: {size_kb:.0f} KB")
    print(f"  ✅ Dashboard regenerated")
    print(f"\n  Open in VS Code: Ctrl+Shift+P → 'Simple Browser: Show'")
    print(f"  Enter: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
