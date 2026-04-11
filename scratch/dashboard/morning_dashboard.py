"""
╔══════════════════════════════════════════════════════════╗
║         QuantLab Macro War Room — Phase 1               ║
║         Mini Bloomberg Terminal                          ║
╠══════════════════════════════════════════════════════════╣
║  Run:    python scratch/dashboard/morning_dashboard.py   ║
║  Output: scratch/dashboard/index.html                    ║
║  Panels:                                                 ║
║    1. Regime Command Center                              ║
║    2. Macro Scorecard                                    ║
║    3. Liquidity Engine                                   ║
║    4. Basket Battle                                      ║
║    5. Regime History + Tactical                          ║
║    6. Commodity Regime                                   ║
╚══════════════════════════════════════════════════════════╝
"""

import sys, os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

from dotenv import load_dotenv
load_dotenv(r'C:\QuantLab\Data_Lab\.env', override=True)

import math
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import fredapi
import yfinance as yf

from shared.data_router import DataRouter

# ── Global Constants ─────────────────────────────────────────
GREEN     = "#26a69a"
LT_GREEN  = "#66bb6a"
YELLOW    = "#ffa726"
DK_ORANGE = "#ef6c00"
RED       = "#ef5350"
BLUE      = "#42a5f5"
PURPLE    = "#ab47bc"
BG        = "#111111"
CARD_BG   = "#1a1a1a"
TEXT      = "#e0e0e0"
MUTED     = "#888888"
BORDER    = "#2a2a2a"

OUTPUT_DIR  = Path(r"C:\QuantLab\Data_Lab\scratch\dashboard")
OUTPUT_FILE = OUTPUT_DIR / "index.html"
COMPOSITE_CSV = Path(r"C:\QuantLab\Data_Lab\studies\regime_composite_score\outputs\data\composite_score_daily.csv")
FORWARD_CSV   = Path(r"C:\QuantLab\Data_Lab\studies\regime_composite_score\outputs\data\regime_forward_returns.csv")

# Panel accent colors
ACCENT = {
    1: "#ffa726",  # orange — regime
    2: "#42a5f5",  # blue — market data
    3: "#26a69a",  # teal — liquidity
    4: "#ab47bc",  # purple — battle
    5: "#888888",  # grey — history
    6: "#cd7f32",  # bronze — commodities
}

def _fred():
    """Get a fredapi.Fred instance."""
    return fredapi.Fred(api_key=os.environ.get('FRED_API_KEY'))


def _hex_to_rgb(h):
    h = h.lstrip('#')
    return ','.join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))


def _tz_strip(df):
    """Strip timezone from a DataFrame index if present."""
    if hasattr(df.index, 'tz') and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df


# ══════════════════════════════════════════════════════════════
#  PANEL 1 — REGIME COMMAND CENTER (ported from existing)
# ══════════════════════════════════════════════════════════════

def build_panel1_regime_command_center():
    """Build the 3-column regime banner using composite CSV data."""
    try:
        comp = pd.read_csv(COMPOSITE_CSV, parse_dates=['date'])
        comp = comp.dropna(subset=['composite_score'])
        if comp.empty:
            return '<div style="color:#ef5350;padding:20px;">Composite data unavailable</div>'

        latest = comp.iloc[-1]
        score = float(latest['composite_score'])
        regime = str(latest.get('regime', 'UNKNOWN'))
        date_str = str(latest['date'])[:10]

        # Z-scores
        z_vix = float(latest.get('z_vix', 0) or 0)
        z_hy = float(latest.get('z_hy', 0) or 0)
        z_yc = float(latest.get('z_t10y2y', 0) or 0)
        z_xlyxlp = float(latest.get('z_xlyxlp', 0) or 0)

        # Structural signal (z_vix_inv + z_hy_inv → stress)
        z_vix_inv = float(latest.get('z_vix_inv', 0) or 0)
        z_hy_inv = float(latest.get('z_hy_inv', 0) or 0)
        structural = (z_vix_inv + z_hy_inv) / 2

        # Tactical signal (z_xlyxlp + z_t10y2y → risk appetite)
        tactical = (z_xlyxlp + z_yc) / 2

        # Colors
        def score_color(s):
            if s > 1.0: return GREEN
            if s > 0: return LT_GREEN
            if s > -1.0: return YELLOW
            if s > -2.0: return DK_ORANGE
            return RED

        def signal_color(s):
            if s > 0.5: return GREEN
            if s > -0.5: return YELLOW
            return RED

        sc = score_color(score)
        stc = signal_color(structural)
        tac = signal_color(tactical)

        # Regime implication
        if score > 1.0:
            impl = "Clear skies — risk-on bias. Momentum strategies favored."
        elif score > 0:
            impl = "Mild risk-on — lean long but watch for deterioration."
        elif score > -1.0:
            impl = "Mild risk-off — mixed signals. Reduce size, be selective."
        elif score > -2.0:
            impl = "Risk-off — defensive posture. Fade rallies, respect fear."
        else:
            impl = "Extreme risk-off / CTA max short zone. Cash is a position."

        # 5-day trend
        if len(comp) >= 6:
            score_5d_ago = float(comp.iloc[-6]['composite_score']) if not pd.isna(comp.iloc[-6]['composite_score']) else score
            delta = score - score_5d_ago
            trend_arrow = "▲" if delta > 0.05 else ("▼" if delta < -0.05 else "─")
            trend_color = GREEN if delta > 0.05 else (RED if delta < -0.05 else MUTED)
        else:
            delta = 0
            trend_arrow = "─"
            trend_color = MUTED

        html = f"""
        <div style="display:grid;grid-template-columns:1fr 1.5fr 1fr;gap:16px;padding:16px;">
          <!-- Structural -->
          <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:16px;text-align:center;">
            <div style="font-size:11px;color:{MUTED};letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">Structural Signal</div>
            <div style="font-size:36px;font-weight:700;color:{stc};">{structural:+.2f}</div>
            <div style="font-size:11px;color:{MUTED};margin-top:4px;">VIX z={z_vix:.2f} | HY z={z_hy:.2f}</div>
            <div style="font-size:12px;color:{stc};margin-top:8px;">{'✅ Stress below average' if structural > 0 else '⚠️ Stress elevated'}</div>
          </div>
          <!-- Combined -->
          <div style="background:{CARD_BG};border:2px solid {sc};border-radius:8px;padding:16px;text-align:center;">
            <div style="font-size:11px;color:{MUTED};letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">Composite Regime Score</div>
            <div style="font-size:52px;font-weight:800;color:{sc};">{score:+.2f}</div>
            <div style="font-size:16px;font-weight:600;color:{sc};margin-top:2px;">{regime}</div>
            <div style="font-size:13px;color:{trend_color};margin-top:6px;">{trend_arrow} {delta:+.2f} (5d)</div>
            <div style="font-size:12px;color:{MUTED};margin-top:8px;">{impl}</div>
            <div style="font-size:10px;color:{MUTED};margin-top:6px;">as of {date_str}</div>
          </div>
          <!-- Tactical -->
          <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:16px;text-align:center;">
            <div style="font-size:11px;color:{MUTED};letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">Tactical Signal</div>
            <div style="font-size:36px;font-weight:700;color:{tac};">{tactical:+.2f}</div>
            <div style="font-size:11px;color:{MUTED};margin-top:4px;">XLY/XLP z={z_xlyxlp:.2f} | Yield z={z_yc:.2f}</div>
            <div style="font-size:12px;color:{tac};margin-top:8px;">{'✅ Risk appetite present' if tactical > 0 else '⚠️ Risk appetite fading'}</div>
          </div>
        </div>
        """
        return html
    except Exception as e:
        return f'<div style="color:{RED};padding:20px;">Panel 1 error: {e}</div>'


# ══════════════════════════════════════════════════════════════
#  PANEL 2 — MACRO SCORECARD (ported from existing)
# ══════════════════════════════════════════════════════════════

def _fetch_index(sym, lookback=90):
    """Fetch an index via yfinance through DataRouter."""
    start = (datetime.now() - timedelta(days=lookback + 10)).strftime("%Y-%m-%d")
    df = DataRouter.get_price_data(sym, start, source="yfinance")
    return _tz_strip(df.tail(lookback))


def _fetch_fred_series(series_id, lookback=90):
    """Fetch a FRED series."""
    start = (datetime.now() - timedelta(days=lookback + 30)).strftime("%Y-%m-%d")
    fred = _fred()
    s = fred.get_series(series_id, observation_start=start)
    return s.dropna().tail(lookback).to_frame(name="value")


def _sparkline_svg(values, width=120, height=32, color=GREEN):
    """Generate a tiny inline SVG sparkline."""
    if len(values) < 2:
        return ""
    vals = list(values)
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    points = []
    for i, v in enumerate(vals):
        x = (i / (len(vals) - 1)) * width
        y = height - ((v - mn) / rng) * (height - 4) - 2
        points.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(points)
    return f'<svg width="{width}" height="{height}" style="display:block;margin:4px auto;"><polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="1.5"/></svg>'


def _implication_text(label, current, change_5d):
    """Generate plain-English implication for a macro card."""
    if label == "VIX":
        if current > 30: return "🚨 Panic — fade mode, size down"
        if current > 25: return "⚠️ Elevated fear — volatile"
        if current > 20: return "🟡 Above normal — caution"
        if current > 15: return "✅ Normal vol environment"
        return "😴 Low vol — trend/momentum mode"
    elif label == "SPY":
        if change_5d > 2: return "🚀 Strong rally — momentum intact"
        if change_5d > 0: return "📈 Grinding higher"
        if change_5d > -2: return "📉 Mild weakness"
        return "🔴 Selling pressure — risk-off"
    elif label == "QQQ":
        if change_5d > 2: return "🚀 Tech leading — risk-on"
        if change_5d > 0: return "📈 Tech firm"
        if change_5d > -2: return "📉 Tech lagging"
        return "🔴 Tech under pressure"
    elif label == "IWM":
        if change_5d > 2: return "🚀 Small caps surging — breadth strong"
        if change_5d > 0: return "📈 Small caps firm"
        if change_5d > -2: return "📉 Small caps weak — breadth narrowing"
        return "🔴 Small caps selling off — risk-off"
    elif label == "HY Spread":
        if current > 5: return "🚨 Credit stress — risk-off signal"
        if current > 4: return "⚠️ Spreads widening — watch closely"
        if current > 3: return "🟡 Normal credit conditions"
        return "✅ Tight spreads — risk appetite strong"
    elif label == "Yield Curve":
        if current < 0: return "🔴 Inverted — recession signal active"
        if current < 0.25: return "⚠️ Flat — late cycle warning"
        if current < 0.75: return "🟡 Normalizing — steepening"
        return "✅ Healthy positive slope"
    return ""


def build_panel2_macro_scorecard():
    """Build the 6-card macro scorecard grid."""
    cards_html = ""
    card_configs = [
        ("VIX", "^VIX", "index", "Volatility Index"),
        ("SPY", "SPY", "etf", "S&P 500 ETF"),
        ("QQQ", "QQQ", "etf", "NASDAQ 100 ETF"),
        ("IWM", "IWM", "etf", "Russell 2000 ETF"),
        ("HY Spread", "BAMLH0A0HYM2", "fred", "High Yield OAS"),
        ("Yield Curve", "T10Y2Y", "fred", "10Y-2Y Spread"),
    ]

    for label, sym, src, desc in card_configs:
        try:
            if src == "index":
                df = _fetch_index(sym)
                vals = df["Close"].dropna()
            elif src == "etf":
                start = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
                df = DataRouter.get_price_data(sym, start)
                df = _tz_strip(df.tail(90))
                vals = df["Close"].dropna()
            else:  # fred
                df = _fetch_fred_series(sym)
                vals = df["value"].dropna()

            current = float(vals.iloc[-1])
            lb5 = min(5, len(vals) - 1)
            prev = float(vals.iloc[-(lb5 + 1)])
            change_5d = ((current - prev) / abs(prev)) * 100 if prev != 0 else 0

            # Color logic
            risk_off_up = {"VIX", "HY Spread"}
            if label in risk_off_up:
                color = RED if change_5d > 0 else GREEN
            else:
                color = GREEN if change_5d > 0 else RED

            arrow = "▲" if change_5d > 0 else "▼"
            sparkline = _sparkline_svg(vals.tail(30).values, color=color)
            impl = _implication_text(label, current, change_5d)

            # Format value
            if label in ("HY Spread", "Yield Curve"):
                val_str = f"{current:.2f}%"
            elif label == "VIX":
                val_str = f"{current:.1f}"
            else:
                val_str = f"${current:,.2f}"

            cards_html += f"""
            <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:14px;text-align:center;">
              <div style="font-size:10px;color:{MUTED};letter-spacing:1px;text-transform:uppercase;">{label}</div>
              <div style="font-size:10px;color:{MUTED};">{desc}</div>
              <div style="font-size:28px;font-weight:700;color:{TEXT};margin:4px 0;">{val_str}</div>
              {sparkline}
              <div style="font-size:12px;color:{color};margin-top:2px;">{arrow} {change_5d:+.2f}% (5d)</div>
              <div style="font-size:11px;color:{MUTED};margin-top:6px;line-height:1.3;">{impl}</div>
            </div>
            """
        except Exception as e:
            cards_html += f"""
            <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:14px;text-align:center;">
              <div style="font-size:10px;color:{MUTED};letter-spacing:1px;text-transform:uppercase;">{label}</div>
              <div style="color:{RED};font-size:12px;margin-top:12px;">Data unavailable</div>
              <div style="color:{MUTED};font-size:10px;">{e}</div>
            </div>
            """

    return f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:16px;">{cards_html}</div>'


# ══════════════════════════════════════════════════════════════
#  PANEL 3 — LIQUIDITY ENGINE
# ══════════════════════════════════════════════════════════════

def _fetch_fred_long(series_id, periods=156):
    """Fetch a FRED series with enough history for sparklines."""
    start = (datetime.now() - timedelta(days=int(periods * 7 / 5) + 60)).strftime("%Y-%m-%d")
    fred = _fred()
    s = fred.get_series(series_id, observation_start=start)
    return s.dropna()


def build_panel3_liquidity_engine():
    """Build the full Liquidity Engine panel: scorecard + charts + verdict."""
    # ── Fetch all data ────────────────────────────────────────
    m2 = nfci = stlfsi = fed_bs = gld_df = spy_df = None
    m2_yoy = 0
    fed_bs_change = 0
    nfci_val = 0
    stlfsi_val = 0
    gld_mom = 0

    # M2 Money Supply
    try:
        m2_raw = _fetch_fred_long("M2SL", 200)
        if len(m2_raw) >= 13:
            m2_yoy_series = (m2_raw / m2_raw.shift(12) - 1) * 100
            m2_yoy_series = m2_yoy_series.dropna()
            m2_yoy = float(m2_yoy_series.iloc[-1])
            m2 = m2_yoy_series.tail(24)
        print(f"  ✅ M2: YoY={m2_yoy:.1f}%")
    except Exception as e:
        print(f"  ⚠ M2 failed: {e}")

    # Fed Balance Sheet
    try:
        fed_raw = _fetch_fred_long("WALCL", 200)
        fed_raw_t = fed_raw / 1e6  # millions to trillions
        fed_bs = fed_raw_t.tail(156)
        current_fed = float(fed_bs.iloc[-1])
        fed_13w_ago = float(fed_bs.iloc[-min(13, len(fed_bs))]) if len(fed_bs) >= 2 else current_fed
        fed_bs_change = ((current_fed - fed_13w_ago) / fed_13w_ago) * 100 if fed_13w_ago != 0 else 0
        print(f"  ✅ Fed BS: ${current_fed:.2f}T, 13w chg={fed_bs_change:+.2f}%")
    except Exception as e:
        print(f"  ⚠ Fed BS failed: {e}")

    # NFCI
    try:
        nfci_raw = _fetch_fred_long("NFCI", 200)
        nfci = nfci_raw.tail(156)
        nfci_val = float(nfci.iloc[-1])
        print(f"  ✅ NFCI: {nfci_val:.3f}")
    except Exception as e:
        print(f"  ⚠ NFCI failed: {e}")

    # STLFSI
    try:
        stlfsi_raw = _fetch_fred_long("STLFSI4", 200)
        stlfsi = stlfsi_raw.tail(156)
        stlfsi_val = float(stlfsi.iloc[-1])
        print(f"  ✅ STLFSI: {stlfsi_val:.3f}")
    except Exception as e:
        print(f"  ⚠ STLFSI failed: {e}")

    # GLD
    try:
        start_gld = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
        gld_df = _tz_strip(DataRouter.get_price_data("GLD", start_gld).tail(60))
        gld_close = gld_df["Close"].dropna()
        gld_current = float(gld_close.iloc[-1])
        gld_20ago = float(gld_close.iloc[-min(20, len(gld_close))])
        gld_mom = ((gld_current - gld_20ago) / gld_20ago) * 100 if gld_20ago != 0 else 0
        print(f"  ✅ GLD: ${gld_current:.2f}, 20d mom={gld_mom:+.1f}%")
    except Exception as e:
        print(f"  ⚠ GLD failed: {e}")

    # SPY for Fed BS comparison
    try:
        start_spy = (datetime.now() - timedelta(days=3 * 365 + 60)).strftime("%Y-%m-%d")
        spy_df = _tz_strip(DataRouter.get_price_data("SPY", start_spy))
        print(f"  ✅ SPY: {len(spy_df)} days for liquidity chart")
    except Exception as e:
        print(f"  ⚠ SPY (liquidity) failed: {e}")

    # DXY attempt
    dxy_mom = None
    try:
        dxy_raw = yf.download("DX-Y.NYB", period="60d", progress=False)
        if dxy_raw is not None and not dxy_raw.empty:
            dxy_close = dxy_raw["Close"].dropna()
            if hasattr(dxy_close, 'columns'):
                dxy_close = dxy_close.iloc[:, 0]
            if len(dxy_close) >= 20:
                dxy_current = float(dxy_close.iloc[-1])
                dxy_20ago = float(dxy_close.iloc[-20])
                dxy_mom = ((dxy_current - dxy_20ago) / dxy_20ago) * 100
                print(f"  ✅ DXY: {dxy_current:.2f}, 20d={dxy_mom:+.1f}%")
    except Exception:
        pass

    # ── SECTION 3A — LIQUIDITY SCORECARD ROW ─────────────────
    scorecard_html = '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;padding:16px;">'

    # Card 1 — M2
    if m2 is not None and len(m2) > 0:
        m2_color = GREEN if m2_yoy > 0 else RED
        if m2_yoy > 8: m2_impl = "💧 Flooding — lots of fuel for risk assets"
        elif m2_yoy > 4: m2_impl = "💧 Healthy — supportive conditions"
        elif m2_yoy > 0: m2_impl = "💧 Slowing — watch for tightening effects"
        else: m2_impl = "🔴 Contracting — headwind for equities"
        m2_spark = _sparkline_svg(m2.values, color=m2_color)
        scorecard_html += f"""
        <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:14px;text-align:center;">
          <div style="font-size:10px;color:{MUTED};letter-spacing:1px;text-transform:uppercase;">M2 Money Supply</div>
          <div style="font-size:10px;color:{MUTED};">YoY % Change</div>
          <div style="font-size:28px;font-weight:700;color:{m2_color};margin:4px 0;">{m2_yoy:+.1f}%</div>
          {m2_spark}
          <div style="font-size:11px;color:{MUTED};margin-top:6px;line-height:1.3;">{m2_impl}</div>
        </div>"""
    else:
        scorecard_html += f'<div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:14px;text-align:center;"><div style="color:{RED};">M2 unavailable</div></div>'

    # Card 2 — Fed Balance Sheet
    if fed_bs is not None and len(fed_bs) > 0:
        fed_color = GREEN if fed_bs_change > 0 else RED
        if fed_bs_change > 0.1: fed_impl = "💧 QE Mode — Fed injecting liquidity"
        elif fed_bs_change < -0.1: fed_impl = "🔴 QT Mode — Fed draining liquidity"
        else: fed_impl = "⚠️ Neutral — no net liquidity change"
        fed_spark = _sparkline_svg(fed_bs.values, color=fed_color)
        scorecard_html += f"""
        <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:14px;text-align:center;">
          <div style="font-size:10px;color:{MUTED};letter-spacing:1px;text-transform:uppercase;">Fed Balance Sheet</div>
          <div style="font-size:10px;color:{MUTED};">Weekly (Trillions)</div>
          <div style="font-size:28px;font-weight:700;color:{TEXT};margin:4px 0;">${float(fed_bs.iloc[-1]):.2f}T</div>
          {fed_spark}
          <div style="font-size:12px;color:{fed_color};">13w: {fed_bs_change:+.2f}%</div>
          <div style="font-size:11px;color:{MUTED};margin-top:6px;line-height:1.3;">{fed_impl}</div>
        </div>"""
    else:
        scorecard_html += f'<div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:14px;text-align:center;"><div style="color:{RED};">Fed BS unavailable</div></div>'

    # Card 3 — NFCI
    if nfci is not None and len(nfci) > 0:
        nfci_color = GREEN if nfci_val < 0 else RED
        if nfci_val < -0.5: nfci_impl = "✅ Very loose — strong tailwind"
        elif nfci_val < 0: nfci_impl = "✅ Loose — conditions supportive"
        elif nfci_val < 0.5: nfci_impl = "⚠️ Tightening — conditions firming"
        elif nfci_val < 1.0: nfci_impl = "🚨 Tight — financial stress elevated"
        else: nfci_impl = "🚨 Crisis-level tightness"
        nfci_spark = _sparkline_svg(nfci.values, color=nfci_color)
        scorecard_html += f"""
        <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:14px;text-align:center;">
          <div style="font-size:10px;color:{MUTED};letter-spacing:1px;text-transform:uppercase;">NFCI</div>
          <div style="font-size:10px;color:{MUTED};">Financial Conditions</div>
          <div style="font-size:28px;font-weight:700;color:{nfci_color};margin:4px 0;">{nfci_val:+.3f}</div>
          {nfci_spark}
          <div style="font-size:11px;color:{MUTED};margin-top:6px;line-height:1.3;">{nfci_impl}</div>
        </div>"""
    else:
        scorecard_html += f'<div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:14px;text-align:center;"><div style="color:{RED};">NFCI unavailable</div></div>'

    # Card 4 — STLFSI
    if stlfsi is not None and len(stlfsi) > 0:
        st_color = GREEN if stlfsi_val < 0 else RED
        if stlfsi_val < 0: st_impl = "✅ Below-normal stress — clean environment"
        elif stlfsi_val < 1: st_impl = "🟡 Normal stress levels"
        elif stlfsi_val < 2: st_impl = "⚠️ Above-normal stress — size down"
        else: st_impl = "🚨 Significant financial stress"
        st_spark = _sparkline_svg(stlfsi.values, color=st_color)
        scorecard_html += f"""
        <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:14px;text-align:center;">
          <div style="font-size:10px;color:{MUTED};letter-spacing:1px;text-transform:uppercase;">St. Louis Stress</div>
          <div style="font-size:10px;color:{MUTED};">STLFSI4</div>
          <div style="font-size:28px;font-weight:700;color:{st_color};margin:4px 0;">{stlfsi_val:+.3f}</div>
          {st_spark}
          <div style="font-size:11px;color:{MUTED};margin-top:6px;line-height:1.3;">{st_impl}</div>
        </div>"""
    else:
        scorecard_html += f'<div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:14px;text-align:center;"><div style="color:{RED};">STLFSI unavailable</div></div>'

    # Card 5 — GLD
    if gld_df is not None and not gld_df.empty:
        gld_color = GREEN if gld_mom > 0 else RED
        gld_current = float(gld_df["Close"].dropna().iloc[-1])
        # Implication based on GLD + DXY
        if dxy_mom is not None:
            if gld_mom > 0 and dxy_mom < -0.5:
                gld_impl = "🔥 Dollar weakening — real inflation signal"
            elif gld_mom > 0 and dxy_mom > 0.5:
                gld_impl = "🛡️ Safe haven bid — risk-off fear"
            elif gld_mom < 0 and dxy_mom > 0.5:
                gld_impl = "📉 Dollar strength — deflationary signal"
            else:
                gld_impl = "😴 No clear signal from gold"
        else:
            if gld_mom > 2: gld_impl = "🔥 Gold surging"
            elif gld_mom > 0: gld_impl = "📈 Gold rising — mild bid"
            else: gld_impl = "📉 Gold falling — risk appetite"
        gld_spark = _sparkline_svg(gld_df["Close"].dropna().values, color=gld_color)
        scorecard_html += f"""
        <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:14px;text-align:center;">
          <div style="font-size:10px;color:{MUTED};letter-spacing:1px;text-transform:uppercase;">Gold (GLD)</div>
          <div style="font-size:10px;color:{MUTED};">vs Dollar Signal</div>
          <div style="font-size:28px;font-weight:700;color:{TEXT};margin:4px 0;">${gld_current:,.2f}</div>
          {gld_spark}
          <div style="font-size:12px;color:{gld_color};">20d: {gld_mom:+.1f}%</div>
          <div style="font-size:11px;color:{MUTED};margin-top:6px;line-height:1.3;">{gld_impl}</div>
        </div>"""
    else:
        scorecard_html += f'<div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:14px;text-align:center;"><div style="color:{RED};">GLD unavailable</div></div>'

    scorecard_html += '</div>'

    # ── SECTION 3B — LIQUIDITY DEEP DIVE CHARTS ──────────────
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "M2 Money Supply — Annual Growth Rate",
            "Fed Balance Sheet vs SPY — The Liquidity Correlation",
            "NFCI — Financial Conditions Index",
            "STLFSI — Financial Stress Index",
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.08,
        specs=[[{}, {"secondary_y": True}], [{}, {}]],
    )

    # TOP LEFT — M2 YoY bar chart
    try:
        m2_full = _fetch_fred_long("M2SL", 300)
        m2_yoy_full = ((m2_full / m2_full.shift(12)) - 1) * 100
        m2_yoy_full = m2_yoy_full.dropna().tail(36)
        bar_colors = [GREEN if v > 0 else RED for v in m2_yoy_full.values]
        fig.add_trace(go.Bar(
            x=m2_yoy_full.index, y=m2_yoy_full.values,
            marker_color=bar_colors, showlegend=False,
            hovertemplate="YoY: %{y:.1f}%<extra></extra>",
        ), row=1, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color=MUTED, line_width=1, row=1, col=1)
        current_m2_yoy = float(m2_yoy_full.iloc[-1])
        fig.add_annotation(
            x=m2_yoy_full.index[-1], y=current_m2_yoy,
            text=f"<b>Current: {current_m2_yoy:+.1f}%</b>",
            showarrow=True, arrowhead=2, arrowcolor=TEXT,
            font=dict(size=11, color=TEXT), ax=-60, ay=-30,
            row=1, col=1,
        )
    except Exception as e:
        fig.add_annotation(text=f"M2 chart error: {e}", row=1, col=1, showarrow=False, font=dict(color=RED))

    # TOP RIGHT — Fed BS vs SPY dual axis
    try:
        if fed_bs is not None and spy_df is not None:
            fed_3y = _fetch_fred_long("WALCL", 800)
            fed_3y = (fed_3y / 1e6).tail(156)  # trillions, ~3 years weekly
            fig.add_trace(go.Scatter(
                x=fed_3y.index, y=fed_3y.values,
                mode="lines", name="Fed BS ($T)",
                line=dict(color=YELLOW, width=2),
                hovertemplate="Fed: $%{y:.2f}T<extra></extra>",
            ), row=1, col=2, secondary_y=False)

            spy_3y = spy_df.tail(756)  # ~3 years daily
            fig.add_trace(go.Scatter(
                x=spy_3y.index, y=spy_3y["Close"].values,
                mode="lines", name="SPY",
                line=dict(color=GREEN, width=1.5),
                hovertemplate="SPY: $%{y:.2f}<extra></extra>",
            ), row=1, col=2, secondary_y=True)

            # QE/QT label
            qt_label = "QT ACTIVE" if fed_bs_change < -0.1 else ("QE ACTIVE" if fed_bs_change > 0.1 else "NEUTRAL")
            qt_color = RED if "QT" in qt_label else (GREEN if "QE" in qt_label else MUTED)
            fig.add_annotation(
                x=0.95, y=0.95, xref="x2 domain", yref="y2 domain",
                text=f"<b>{qt_label}</b>", showarrow=False,
                font=dict(size=13, color=qt_color),
                bgcolor=f"rgba({_hex_to_rgb(qt_color)},0.15)",
                bordercolor=qt_color, borderwidth=1, borderpad=4,
            )
    except Exception as e:
        fig.add_annotation(text=f"Fed/SPY error: {e}", row=1, col=2, showarrow=False, font=dict(color=RED))

    # BOTTOM LEFT — NFCI history
    try:
        if nfci is not None and len(nfci) > 0:
            fig.add_trace(go.Scatter(
                x=nfci.index, y=nfci.values,
                mode="lines", name="NFCI",
                line=dict(color="white", width=1.5),
                showlegend=False,
                hovertemplate="NFCI: %{y:.3f}<extra></extra>",
            ), row=2, col=1)
            # Background bands
            fig.add_hrect(y0=-2, y1=-0.5, fillcolor="rgba(38,166,154,0.15)", line_width=0, row=2, col=1)
            fig.add_hrect(y0=-0.5, y1=0, fillcolor="rgba(102,187,106,0.10)", line_width=0, row=2, col=1)
            fig.add_hrect(y0=0, y1=0.5, fillcolor="rgba(255,167,38,0.10)", line_width=0, row=2, col=1)
            fig.add_hrect(y0=0.5, y1=2, fillcolor="rgba(239,83,80,0.20)", line_width=0, row=2, col=1)
            fig.add_hline(y=0, line_dash="dash", line_color=MUTED, line_width=1, row=2, col=1)
            # Current dot
            nfci_dot_color = GREEN if nfci_val < 0 else RED
            fig.add_trace(go.Scatter(
                x=[nfci.index[-1]], y=[nfci_val],
                mode="markers+text", text=[f" {nfci_val:.3f}"],
                textposition="top right", textfont=dict(color=nfci_dot_color, size=11),
                marker=dict(color=nfci_dot_color, size=10),
                showlegend=False,
            ), row=2, col=1)
    except Exception as e:
        fig.add_annotation(text=f"NFCI chart error: {e}", row=2, col=1, showarrow=False, font=dict(color=RED))

    # BOTTOM RIGHT — STLFSI history
    try:
        if stlfsi is not None and len(stlfsi) > 0:
            fig.add_trace(go.Scatter(
                x=stlfsi.index, y=stlfsi.values,
                mode="lines", name="STLFSI",
                line=dict(color="white", width=1.5),
                showlegend=False,
                hovertemplate="STLFSI: %{y:.3f}<extra></extra>",
            ), row=2, col=2)
            fig.add_hrect(y0=-3, y1=0, fillcolor="rgba(38,166,154,0.15)", line_width=0, row=2, col=2)
            fig.add_hrect(y0=0, y1=1, fillcolor="rgba(255,167,38,0.10)", line_width=0, row=2, col=2)
            fig.add_hrect(y0=1, y1=2, fillcolor="rgba(239,83,80,0.15)", line_width=0, row=2, col=2)
            fig.add_hrect(y0=2, y1=5, fillcolor="rgba(239,83,80,0.25)", line_width=0, row=2, col=2)
            fig.add_hline(y=0, line_dash="dash", line_color=MUTED, line_width=1, row=2, col=2)
            st_dot_color = GREEN if stlfsi_val < 0 else RED
            fig.add_trace(go.Scatter(
                x=[stlfsi.index[-1]], y=[stlfsi_val],
                mode="markers+text", text=[f" {stlfsi_val:.3f}"],
                textposition="top right", textfont=dict(color=st_dot_color, size=11),
                marker=dict(color=st_dot_color, size=10),
                showlegend=False,
            ), row=2, col=2)
    except Exception as e:
        fig.add_annotation(text=f"STLFSI chart error: {e}", row=2, col=2, showarrow=False, font=dict(color=RED))

    fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG,
        height=700, margin=dict(l=50, r=50, t=50, b=30),
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(color=MUTED)),
    )
    fig.update_xaxes(gridcolor=BORDER, showgrid=False)
    fig.update_yaxes(gridcolor=BORDER)

    charts_html = fig.to_html(full_html=False, include_plotlyjs=False)

    # ── SECTION 3C — LIQUIDITY VERDICT ───────────────────────
    liq_score = 0
    if m2 is not None: liq_score += 1 if m2_yoy > 0 else -1
    if fed_bs is not None: liq_score += 1 if fed_bs_change > 0 else -1
    if nfci is not None: liq_score += 1 if nfci_val < 0 else -1
    if stlfsi is not None: liq_score += 1 if stlfsi_val < 0 else -1

    if liq_score >= 3:
        vbg = f"rgba({_hex_to_rgb(GREEN)},0.08)"
        vborder = GREEN
        vtitle = f"💧 LIQUIDITY SCORE: +{liq_score}/4 — EXPANDING"
        vdesc = "Money is flooding the system. Historically bullish for equities 60-90 days forward. Your composite score should improve if this sustains."
    elif liq_score >= 1:
        vbg = f"rgba({_hex_to_rgb(LT_GREEN)},0.08)"
        vborder = LT_GREEN
        vtitle = f"💧 LIQUIDITY SCORE: +{liq_score}/4 — SUPPORTIVE"
        vdesc = "Conditions favor risk-on positioning. Not a full tailwind but no meaningful headwind either."
    elif liq_score == 0:
        vbg = f"rgba({_hex_to_rgb(MUTED)},0.08)"
        vborder = MUTED
        vtitle = "⚠️ LIQUIDITY SCORE: 0/4 — NEUTRAL"
        vdesc = "Mixed signals from the macro plumbing. No directional edge from liquidity alone."
    elif liq_score >= -2:
        vbg = f"rgba({_hex_to_rgb(YELLOW)},0.08)"
        vborder = YELLOW
        vtitle = f"🔴 LIQUIDITY SCORE: {liq_score}/4 — TIGHTENING"
        vdesc = "Headwind building. Watch for composite score deterioration in coming weeks."
    else:
        vbg = f"rgba({_hex_to_rgb(RED)},0.08)"
        vborder = RED
        vtitle = f"🚨 LIQUIDITY SCORE: {liq_score}/4 — DRAINING"
        vdesc = "Significant headwind. Historically precedes equity weakness 60-90 days out. Reduce exposure."

    verdict_html = f"""
    <div style="background:{vbg};border:1px solid {vborder};border-radius:8px;padding:20px;margin:16px;">
      <div style="font-size:18px;font-weight:700;color:{vborder};">{vtitle}</div>
      <div style="font-size:13px;color:{TEXT};margin-top:8px;line-height:1.5;">{vdesc}</div>
    </div>
    """

    return scorecard_html + charts_html + verdict_html, liq_score


# ══════════════════════════════════════════════════════════════
#  PANEL 4 — BASKET BATTLE
# ══════════════════════════════════════════════════════════════

def compute_momentum_score(daily_returns):
    """Compute percentile-based momentum score (0-100)."""
    if daily_returns is None or len(daily_returns) < 10:
        return 50.0
    rolling_3d = (
        (1 + daily_returns)
        .rolling(3)
        .apply(lambda x: x.prod() - 1, raw=True)
        .dropna()
    )
    if len(rolling_3d) < 5:
        return 50.0
    hist = rolling_3d.tail(252)
    mean = float(hist.mean())
    std = float(hist.std())
    if std == 0:
        return 50.0
    z = (float(rolling_3d.iloc[-1]) - mean) / std
    percentile = (1.0 + math.erf(z / math.sqrt(2))) / 2.0 * 100.0
    return max(0.0, min(100.0, percentile))


def _momentum_gauge_html(label, score, color_accent):
    """Build HTML for a horizontal momentum gauge bar."""
    if score < 10:
        verdict = "OVERSOLD — Mean reversion setup"
        v_color = RED
    elif score < 30:
        verdict = "COOLING — Below-average momentum"
        v_color = YELLOW
    elif score < 70:
        verdict = "NEUTRAL — Within normal range"
        v_color = MUTED
    elif score < 90:
        verdict = "ELEVATED — Momentum intact"
        v_color = LT_GREEN
    else:
        verdict = "OVERBOUGHT — Pullback risk"
        v_color = GREEN

    # Build gauge with colored zones
    return f"""
    <div style="text-align:center;">
      <div style="font-size:12px;color:{MUTED};letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">{label}</div>
      <div style="position:relative;height:28px;background:linear-gradient(to right, {RED} 0%, {RED} 30%, {YELLOW} 30%, {YELLOW} 70%, {GREEN} 70%, {GREEN} 100%);border-radius:4px;margin:0 auto;max-width:350px;">
        <div style="position:absolute;left:{score:.0f}%;top:-2px;transform:translateX(-50%);width:4px;height:32px;background:white;border-radius:2px;"></div>
        <div style="position:absolute;left:{score:.0f}%;top:-20px;transform:translateX(-50%);font-size:16px;font-weight:700;color:white;">{score:.0f}</div>
      </div>
      <div style="font-size:12px;color:{v_color};margin-top:8px;font-weight:600;">{verdict}</div>
    </div>
    """


def build_panel4_basket_battle():
    """Build the Basket Battle panel with 20-day lookback."""
    risk_on_tickers = ["QQQ", "IWM", "ARKK", "SOXX", "IGV", "BITO", "SPY"]
    defensive_tickers = ["XLV", "XLF", "XLI", "XHB", "DIA", "XLP", "XLU", "TLT"]

    start = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

    all_data = {}
    for t in risk_on_tickers + defensive_tickers:
        try:
            df = _tz_strip(DataRouter.get_price_data(t, start))
            all_data[t] = df["Close"].dropna()
        except Exception as e:
            print(f"  ⚠ Basket fetch {t}: {e}")

    # Build close DataFrame
    close_df = pd.DataFrame(all_data).dropna()
    if len(close_df) < 21:
        return '<div style="color:#ef5350;padding:20px;">Insufficient data for Basket Battle</div>', "N/A"

    # Use last 20 trading days
    close_20 = close_df.tail(21)  # 21 rows = 20 days of returns

    # Normalize to 100 at day -20
    norm_20 = (close_20 / close_20.iloc[0]) * 100

    ro_cols = [c for c in risk_on_tickers if c in norm_20.columns]
    df_cols = [c for c in defensive_tickers if c in norm_20.columns]

    risk_on_line = norm_20[ro_cols].mean(axis=1)
    defensive_line = norm_20[df_cols].mean(axis=1)

    # Bollinger bands (3d rolling std * 1.5)
    ro_std = risk_on_line.rolling(3).std().fillna(0) * 1.5
    df_std = defensive_line.rolling(3).std().fillna(0) * 1.5

    # SECTION 4A — Main Battle Chart
    battle_fig = go.Figure()

    # Risk-On band
    battle_fig.add_trace(go.Scatter(
        x=risk_on_line.index, y=(risk_on_line + ro_std).values,
        mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    battle_fig.add_trace(go.Scatter(
        x=risk_on_line.index, y=(risk_on_line - ro_std).values,
        mode="lines", line=dict(width=0), fill="tonexty",
        fillcolor=f"rgba({_hex_to_rgb(GREEN)},0.15)", showlegend=False, hoverinfo="skip",
    ))
    # Defensive band
    battle_fig.add_trace(go.Scatter(
        x=defensive_line.index, y=(defensive_line + df_std).values,
        mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    battle_fig.add_trace(go.Scatter(
        x=defensive_line.index, y=(defensive_line - df_std).values,
        mode="lines", line=dict(width=0), fill="tonexty",
        fillcolor=f"rgba({_hex_to_rgb(RED)},0.15)", showlegend=False, hoverinfo="skip",
    ))
    # Main lines
    battle_fig.add_trace(go.Scatter(
        x=risk_on_line.index, y=risk_on_line.values,
        mode="lines", name="Risk-On",
        line=dict(color=GREEN, width=3),
        hovertemplate="Risk-On: %{y:.2f}<extra></extra>",
    ))
    battle_fig.add_trace(go.Scatter(
        x=defensive_line.index, y=defensive_line.values,
        mode="lines", name="Defensive",
        line=dict(color=RED, width=3),
        hovertemplate="Defensive: %{y:.2f}<extra></extra>",
    ))
    # Baseline
    battle_fig.add_hline(y=100, line_dash="dash", line_color="white", line_width=1, opacity=0.5)

    # Current spread
    ro_final = float(risk_on_line.iloc[-1])
    df_final = float(defensive_line.iloc[-1])
    spread = ro_final - df_final
    winner = "Risk-On" if spread > 0 else "Defensive"
    w_color = GREEN if spread > 0 else RED

    battle_fig.add_annotation(
        x=0.98, y=0.98, xref="paper", yref="paper",
        text=f"<b>{winner} leading by {abs(spread):.1f} pts</b>",
        showarrow=False, font=dict(size=13, color=w_color),
        bgcolor=f"rgba({_hex_to_rgb(w_color)},0.15)",
        bordercolor=w_color, borderwidth=1, borderpad=6,
    )

    battle_fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG,
        height=400, margin=dict(l=50, r=30, t=50, b=30),
        title=dict(text="Risk-On vs Defensive — 20-Day Basket Battle", font=dict(size=16, color=TEXT)),
        yaxis=dict(title="Indexed to 100 (20d ago)", gridcolor=BORDER),
        xaxis=dict(gridcolor=BORDER),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color=MUTED)),
    )
    battle_chart = battle_fig.to_html(full_html=False, include_plotlyjs=False)

    # SECTION 4B — Momentum Gauges
    ro_returns = risk_on_line.pct_change().dropna()
    df_returns = defensive_line.pct_change().dropna()
    # For better percentile calculation, use longer history
    try:
        long_start = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        spy_long = _tz_strip(DataRouter.get_price_data("SPY", long_start))
        ro_score = compute_momentum_score(spy_long["Close"].pct_change().dropna())
    except Exception:
        ro_score = compute_momentum_score(ro_returns)
    try:
        long_start = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        tlt_long = _tz_strip(DataRouter.get_price_data("TLT", long_start))
        df_score = compute_momentum_score(tlt_long["Close"].pct_change().dropna())
    except Exception:
        df_score = compute_momentum_score(df_returns)

    gauge_html = f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;padding:16px;">
      {_momentum_gauge_html("Risk-On Momentum (SPY)", ro_score, GREEN)}
      {_momentum_gauge_html("Defensive Momentum (TLT)", df_score, RED)}
    </div>
    """

    # SECTION 4C — Winner Banner
    banner_html = f"""
    <div style="background:rgba({_hex_to_rgb(w_color)},0.08);border:1px solid {w_color};border-radius:8px;padding:16px;margin:0 16px;text-align:center;">
      <span style="font-size:18px;font-weight:700;color:{w_color};">{winner.upper()} BASKET WINNING</span>
      <span style="font-size:14px;color:{TEXT};margin-left:12px;">20-day spread: {spread:+.1f} pts</span>
    </div>
    """

    # SECTION 4D — Constituent Tables
    # Get 5d and 1d returns for each ticker
    def _build_table(tickers, label):
        rows = ""
        records = []
        for t in tickers:
            if t not in all_data:
                continue
            s = all_data[t]
            if len(s) < 6:
                continue
            ret_1d = ((float(s.iloc[-1]) - float(s.iloc[-2])) / float(s.iloc[-2])) * 100
            ret_5d = ((float(s.iloc[-1]) - float(s.iloc[-min(6, len(s))])) / float(s.iloc[-min(6, len(s))])) * 100
            records.append((t, ret_5d, ret_1d))

        records.sort(key=lambda x: x[1], reverse=True)
        for t, r5, r1 in records:
            c5 = GREEN if r5 > 0 else RED
            c1 = GREEN if r1 > 0 else RED
            bar_w = min(abs(r5) * 15, 100)
            bar_c = GREEN if r5 > 0 else RED
            rows += f"""
            <tr>
              <td style="padding:4px 8px;color:{TEXT};font-weight:600;">{t}</td>
              <td style="padding:4px 8px;color:{c5};text-align:right;">{r5:+.2f}%</td>
              <td style="padding:4px 8px;color:{c1};text-align:right;">{r1:+.2f}%</td>
              <td style="padding:4px 8px;"><div style="height:10px;width:{bar_w:.0f}%;background:{bar_c};border-radius:2px;"></div></td>
            </tr>"""

        return f"""
        <div>
          <div style="font-size:12px;color:{MUTED};letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;text-align:center;">{label}</div>
          <table style="width:100%;border-collapse:collapse;font-size:12px;">
            <tr style="border-bottom:1px solid {BORDER};">
              <th style="padding:4px 8px;color:{MUTED};text-align:left;">Ticker</th>
              <th style="padding:4px 8px;color:{MUTED};text-align:right;">5d %</th>
              <th style="padding:4px 8px;color:{MUTED};text-align:right;">1d %</th>
              <th style="padding:4px 8px;color:{MUTED};">5d Bar</th>
            </tr>
            {rows}
          </table>
        </div>"""

    tables_html = f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:16px;">
      {_build_table(risk_on_tickers, "Risk-On Basket")}
      {_build_table(defensive_tickers, "Defensive Basket")}
    </div>
    """

    return battle_chart + gauge_html + banner_html + tables_html, winner


# ══════════════════════════════════════════════════════════════
#  PANEL 5 — REGIME HISTORY + TACTICAL
# ══════════════════════════════════════════════════════════════

def build_panel5_regime_history():
    """Build composite score history + XLY/XLP tactical chart."""
    panel_html = ""
    history_days = 0

    # CHART GROUP 1 — Composite Score vs SPY
    try:
        comp = pd.read_csv(COMPOSITE_CSV, parse_dates=['date'])
        comp = comp.dropna(subset=['composite_score'])
        comp = comp.tail(252)
        history_days = len(comp)

        fig1 = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.6, 0.4],
            vertical_spacing=0.06,
            subplot_titles=["Composite Regime Score", "SPY Price"],
        )

        # Row 1 — Composite score + regime bands
        fig1.add_trace(go.Scatter(
            x=comp['date'], y=comp['composite_score'],
            mode="lines", name="Composite",
            line=dict(color="white", width=2),
            hovertemplate="Score: %{y:.2f}<extra></extra>",
        ), row=1, col=1)

        # Regime bands
        fig1.add_hrect(y0=1.0, y1=3.0, fillcolor="rgba(38,166,154,0.15)", line_width=0, row=1, col=1)
        fig1.add_hrect(y0=0, y1=1.0, fillcolor="rgba(102,187,106,0.10)", line_width=0, row=1, col=1)
        fig1.add_hrect(y0=-1.0, y1=0, fillcolor="rgba(255,167,38,0.10)", line_width=0, row=1, col=1)
        fig1.add_hrect(y0=-2.0, y1=-1.0, fillcolor="rgba(239,108,0,0.15)", line_width=0, row=1, col=1)
        fig1.add_hrect(y0=-4.0, y1=-2.0, fillcolor="rgba(239,83,80,0.20)", line_width=0, row=1, col=1)

        for lv in [-2, -1, 0, 1]:
            fig1.add_hline(y=lv, line_dash="dash", line_color=MUTED, line_width=0.5, row=1, col=1)

        # Zone labels on right
        for val, lbl in [(1.5, "CLEAR SKIES"), (0.5, "MILD RISK-ON"), (-0.5, "MILD RISK-OFF"), (-1.5, "RISK-OFF"), (-2.5, "CTA MAX SHORT")]:
            fig1.add_annotation(
                x=1.02, y=val, xref="paper", yref="y",
                text=lbl, showarrow=False,
                font=dict(size=9, color=MUTED),
                xanchor="left",
            )

        # Current dot
        latest_score = float(comp['composite_score'].iloc[-1])
        sc = GREEN if latest_score > 0 else (YELLOW if latest_score > -1 else RED)
        fig1.add_trace(go.Scatter(
            x=[comp['date'].iloc[-1]], y=[latest_score],
            mode="markers+text", text=[f" {latest_score:.2f}"],
            textposition="top right", textfont=dict(color=sc, size=12),
            marker=dict(color=sc, size=10),
            showlegend=False,
        ), row=1, col=1)

        # Row 2 — SPY
        fig1.add_trace(go.Scatter(
            x=comp['date'], y=comp['SPY'],
            mode="lines", name="SPY",
            line=dict(color=GREEN, width=1.5),
            hovertemplate="SPY: $%{y:.2f}<extra></extra>",
        ), row=2, col=1)

        fig1.update_layout(
            template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG,
            height=500, margin=dict(l=50, r=80, t=50, b=30),
            title=dict(text="Regime Composite Score — 252 Days", font=dict(size=16, color=TEXT)),
            showlegend=False,
        )
        fig1.update_xaxes(gridcolor=BORDER)
        fig1.update_yaxes(gridcolor=BORDER)
        panel_html += fig1.to_html(full_html=False, include_plotlyjs=False)

    except Exception as e:
        panel_html += f'<div style="color:{RED};padding:20px;">Composite history error: {e}</div>'

    # CHART GROUP 2 — XLY/XLP Tactical
    try:
        start = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        xly = _tz_strip(DataRouter.get_price_data("XLY", start))
        xlp = _tz_strip(DataRouter.get_price_data("XLP", start))

        ratio_df = pd.DataFrame(index=xly.index)
        ratio_df["ratio"] = xly["Close"] / xlp["Close"].reindex(xly.index, method="ffill")
        ratio_df["ma20"] = ratio_df["ratio"].rolling(20).mean()
        ratio_df = ratio_df.dropna().tail(252)

        fig2 = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.7, 0.3],
            vertical_spacing=0.06,
            subplot_titles=["XLY/XLP Ratio + 20d MA", "5-Day Rate of Change"],
        )

        # Ratio line
        fig2.add_trace(go.Scatter(
            x=ratio_df.index, y=ratio_df["ratio"],
            mode="lines", name="XLY/XLP",
            line=dict(color=BLUE, width=2),
        ), row=1, col=1)

        # MA line
        fig2.add_trace(go.Scatter(
            x=ratio_df.index, y=ratio_df["ma20"],
            mode="lines", name="20d MA",
            line=dict(color=MUTED, width=1.5, dash="dash"),
        ), row=1, col=1)

        # Fill above/below MA
        above = ratio_df["ratio"].where(ratio_df["ratio"] >= ratio_df["ma20"])
        below = ratio_df["ratio"].where(ratio_df["ratio"] < ratio_df["ma20"])
        fig2.add_trace(go.Scatter(
            x=ratio_df.index, y=above,
            mode="lines", line=dict(width=0), showlegend=False,
        ), row=1, col=1)
        fig2.add_trace(go.Scatter(
            x=ratio_df.index, y=ratio_df["ma20"],
            mode="lines", line=dict(width=0), fill="tonexty",
            fillcolor="rgba(38,166,154,0.15)", showlegend=False,
        ), row=1, col=1)
        fig2.add_trace(go.Scatter(
            x=ratio_df.index, y=below,
            mode="lines", line=dict(width=0), showlegend=False,
        ), row=1, col=1)
        fig2.add_trace(go.Scatter(
            x=ratio_df.index, y=ratio_df["ma20"],
            mode="lines", line=dict(width=0), fill="tonexty",
            fillcolor="rgba(239,83,80,0.15)", showlegend=False,
        ), row=1, col=1)

        # Current dot + 52w range
        curr_ratio = float(ratio_df["ratio"].iloc[-1])
        curr_ma = float(ratio_df["ma20"].iloc[-1])
        hi = float(ratio_df["ratio"].max())
        lo = float(ratio_df["ratio"].min())
        risk_on = curr_ratio > curr_ma
        dot_color = GREEN if risk_on else RED
        signal = "RISK APPETITE RETURNING — ratio above 20d MA" if risk_on else "RISK APPETITE FADING — ratio below 20d MA"

        fig2.add_trace(go.Scatter(
            x=[ratio_df.index[-1]], y=[curr_ratio],
            mode="markers+text", text=[f" {curr_ratio:.3f}"],
            textposition="top right", textfont=dict(color=dot_color, size=11),
            marker=dict(color=dot_color, size=9), showlegend=False,
        ), row=1, col=1)

        fig2.add_annotation(
            x=0.02, y=0.98, xref="paper", yref="y domain",
            text=f"<b>{'✅' if risk_on else '⚠️'} {signal}</b>",
            showarrow=False, font=dict(size=11, color=dot_color),
            bgcolor=f"rgba({_hex_to_rgb(dot_color)},0.1)",
            bordercolor=dot_color, borderwidth=1, borderpad=4,
        )

        # 52w annotations
        fig2.add_annotation(x=ratio_df.index[0], y=hi, text=f"52w High: {hi:.3f}", showarrow=False, font=dict(size=9, color=MUTED), xanchor="left", row=1, col=1)
        fig2.add_annotation(x=ratio_df.index[0], y=lo, text=f"52w Low: {lo:.3f}", showarrow=False, font=dict(size=9, color=MUTED), xanchor="left", row=1, col=1)

        # Row 2 — 5d ROC bar chart
        roc_5d = ratio_df["ratio"].pct_change(5) * 100
        roc_5d = roc_5d.dropna()
        roc_colors = [GREEN if v > 0 else RED for v in roc_5d.values]
        fig2.add_trace(go.Bar(
            x=roc_5d.index, y=roc_5d.values,
            marker_color=roc_colors, showlegend=False,
            hovertemplate="5d ROC: %{y:.2f}%<extra></extra>",
        ), row=2, col=1)
        fig2.add_hline(y=0, line_dash="dash", line_color=MUTED, line_width=0.5, row=2, col=1)

        fig2.update_layout(
            template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG,
            height=420, margin=dict(l=50, r=30, t=50, b=30),
            title=dict(text="XLY/XLP — Tactical Risk Appetite (252 Days)", font=dict(size=16, color=TEXT)),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color=MUTED)),
        )
        fig2.update_xaxes(gridcolor=BORDER)
        fig2.update_yaxes(gridcolor=BORDER)
        panel_html += fig2.to_html(full_html=False, include_plotlyjs=False)

    except Exception as e:
        panel_html += f'<div style="color:{RED};padding:20px;">XLY/XLP tactical error: {e}</div>'

    return panel_html, history_days


# ══════════════════════════════════════════════════════════════
#  PANEL 6 — COMMODITY REGIME
# ══════════════════════════════════════════════════════════════

def build_panel6_commodity_regime():
    """Build the full Commodity Regime panel."""
    commodity_tickers = {
        "GLD": "Gold (GLD)",
        "SLV": "Silver (SLV)",
        "XLE": "Energy (XLE)",
        "USO": "Oil (USO)",
        "CPER": "Copper (CPER)",
        "DBA": "Agriculture (DBA)",
        "UNG": "Natural Gas (UNG)",
    }
    start_short = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    start_long = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")

    # Fetch short-term data for scorecard
    short_data = {}
    for t in commodity_tickers:
        try:
            df = _tz_strip(DataRouter.get_price_data(t, start_short))
            short_data[t] = df["Close"].dropna()
        except Exception as e:
            print(f"  ⚠ Commodity {t}: {e}")

    # Fetch long-term data for charts
    long_data = {}
    for t in ["GLD", "XLE", "USO", "CPER", "SPY"]:
        try:
            df = _tz_strip(DataRouter.get_price_data(t, start_long))
            long_data[t] = df["Close"].dropna()
        except Exception as e:
            print(f"  ⚠ Commodity long {t}: {e}")

    # DXY
    dxy_data = None
    dxy_20d_pct = None
    try:
        for dxy_sym in ["DX-Y.NYB", "^DXY"]:
            try:
                dxy_raw = yf.download(dxy_sym, period="300d", progress=False)
                if dxy_raw is not None and not dxy_raw.empty:
                    dxy_close = dxy_raw["Close"].dropna()
                    if hasattr(dxy_close, 'columns'):
                        dxy_close = dxy_close.iloc[:, 0]
                    if len(dxy_close) >= 20:
                        dxy_data = dxy_close
                        dxy_current = float(dxy_close.iloc[-1])
                        dxy_20ago = float(dxy_close.iloc[-20])
                        dxy_20d_pct = ((dxy_current - dxy_20ago) / dxy_20ago) * 100
                        print(f"  ✅ DXY ({dxy_sym}): {dxy_current:.2f}")
                        break
            except Exception:
                continue
    except Exception:
        pass

    # ── SECTION 6A — COMMODITY SCORECARD ─────────────────────
    def _commodity_implication(ticker, pct_20d):
        impls = {
            "GLD": [(3, "🔥 Gold surging — inflation/fear signal"), (0, "📈 Gold rising — mild safe haven bid"), (-999, "📉 Gold falling — risk-on or deflation")],
            "SLV": [(3, "🔥 Silver leading — industrial + monetary demand"), (0, "📈 Silver firm"), (-999, "📉 Silver weak — industrial demand fading")],
            "XLE": [(3, "⚠️ Energy leading — late-cycle warning"), (0, "📈 Energy firm — growth supportive"), (-999, "📉 Energy weak — growth concerns")],
            "USO": [(5, "🛢️ Oil surging — growth or supply shock"), (0, "📈 Oil stable — demand holding"), (-999, "📉 Oil falling — demand concerns")],
            "CPER": [(3, "⚡ Copper rising — growth expectations up"), (0, "📈 Copper stable"), (-999, "📉 Copper weak — growth slowdown signal")],
            "DBA": [(3, "🌾 Ag rising — food inflation building"), (0, "📈 Ag stable"), (-999, "📉 Ag weak")],
            "UNG": [(5, "🔥 NatGas surging — energy cost spike"), (0, "📈 NatGas stable"), (-999, "📉 NatGas weak")],
        }
        for threshold, txt in impls.get(ticker, []):
            if pct_20d >= threshold:
                return txt
        return ""

    cards_html = ""
    commodity_moms = {}  # Store 20d momentum for regime verdict

    for t, name in commodity_tickers.items():
        if t in short_data and len(short_data[t]) >= 20:
            s = short_data[t]
            current = float(s.iloc[-1])
            p5 = float(s.iloc[-min(6, len(s))])
            p20 = float(s.iloc[-min(21, len(s))])
            chg_5d = ((current - p5) / p5) * 100
            chg_20d = ((current - p20) / p20) * 100
            commodity_moms[t] = chg_20d
            color = GREEN if chg_20d > 0 else RED
            arrow5 = "▲" if chg_5d > 0 else "▼"
            impl = _commodity_implication(t, chg_20d)
            spark = _sparkline_svg(s.tail(20).values, color=color)

            cards_html += f"""
            <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:12px;text-align:center;">
              <div style="font-size:10px;color:{MUTED};letter-spacing:1px;text-transform:uppercase;">{t}</div>
              <div style="font-size:9px;color:{MUTED};">{name}</div>
              <div style="font-size:24px;font-weight:700;color:{TEXT};margin:2px 0;">${current:,.2f}</div>
              {spark}
              <div style="font-size:11px;color:{GREEN if chg_5d > 0 else RED};">{arrow5} {chg_5d:+.1f}% (5d)</div>
              <div style="font-size:11px;color:{color};">20d: {chg_20d:+.1f}%</div>
              <div style="font-size:10px;color:{MUTED};margin-top:4px;line-height:1.3;">{impl}</div>
            </div>"""
        else:
            cards_html += f"""
            <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:12px;text-align:center;">
              <div style="font-size:10px;color:{MUTED};">{t}</div>
              <div style="color:{RED};font-size:11px;">Unavailable</div>
            </div>"""

    # DXY card
    if dxy_data is not None and dxy_20d_pct is not None:
        dxy_current = float(dxy_data.iloc[-1])
        dxy_5ago = float(dxy_data.iloc[-min(6, len(dxy_data))])
        dxy_5d = ((dxy_current - dxy_5ago) / dxy_5ago) * 100
        dxy_c = GREEN if dxy_20d_pct > 0 else RED
        if dxy_20d_pct > 1: dxy_impl = "💵 Dollar strengthening — commodity headwind"
        elif dxy_20d_pct < -1: dxy_impl = "📉 Dollar weakening — commodity tailwind"
        else: dxy_impl = "💵 Dollar stable"
        dxy_spark = _sparkline_svg(dxy_data.tail(20).values, color=dxy_c)
        cards_html += f"""
        <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:12px;text-align:center;">
          <div style="font-size:10px;color:{MUTED};letter-spacing:1px;text-transform:uppercase;">DXY</div>
          <div style="font-size:9px;color:{MUTED};">US Dollar Index</div>
          <div style="font-size:24px;font-weight:700;color:{TEXT};margin:2px 0;">{dxy_current:.2f}</div>
          {dxy_spark}
          <div style="font-size:11px;color:{GREEN if dxy_5d > 0 else RED};">{'▲' if dxy_5d > 0 else '▼'} {dxy_5d:+.1f}% (5d)</div>
          <div style="font-size:11px;color:{dxy_c};">20d: {dxy_20d_pct:+.1f}%</div>
          <div style="font-size:10px;color:{MUTED};margin-top:4px;line-height:1.3;">{dxy_impl}</div>
        </div>"""
    else:
        cards_html += f"""
        <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:12px;text-align:center;">
          <div style="font-size:10px;color:{MUTED};">DXY</div>
          <div style="color:{RED};font-size:11px;">Unavailable</div>
        </div>"""

    scorecard_html = f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;padding:16px;">{cards_html}</div>'

    # ── SECTION 6B — COMMODITY DEEP DIVE CHARTS ──────────────
    chart_fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "GLD — Gold Price + 20d Momentum",
            "XLE vs SPY — Energy Relative Strength",
            "Oil + Copper — The Growth Barometers",
            "DXY — US Dollar Index (Master Key)" if dxy_data is not None else "SLV/GLD — Dollar Proxy Ratio",
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.08,
        specs=[[{"secondary_y": True}, {}], [{"secondary_y": True}, {"secondary_y": True}]],
    )

    # TOP LEFT — GLD Price + 20d ROC
    try:
        gld_long = long_data.get("GLD")
        if gld_long is not None and len(gld_long) > 20:
            gld_252 = gld_long.tail(252)
            gld_ma20 = gld_252.rolling(20).mean()
            chart_fig.add_trace(go.Scatter(
                x=gld_252.index, y=gld_252.values,
                mode="lines", name="GLD", line=dict(color="#ffd700", width=2),
                hovertemplate="GLD: $%{y:.2f}<extra></extra>",
            ), row=1, col=1, secondary_y=False)
            chart_fig.add_trace(go.Scatter(
                x=gld_ma20.index, y=gld_ma20.values,
                mode="lines", name="GLD 20d MA", line=dict(color=MUTED, width=1.5, dash="dash"),
                showlegend=False,
            ), row=1, col=1, secondary_y=False)
            # 20d ROC on secondary
            gld_roc = gld_252.pct_change(20) * 100
            gld_roc = gld_roc.dropna()
            roc_colors = [GREEN if v > 0 else RED for v in gld_roc.values]
            chart_fig.add_trace(go.Bar(
                x=gld_roc.index, y=gld_roc.values,
                marker_color=roc_colors, showlegend=False, opacity=0.4,
                hovertemplate="20d ROC: %{y:.1f}%<extra></extra>",
            ), row=1, col=1, secondary_y=True)

            # 52w high/low
            hi52 = float(gld_252.max())
            lo52 = float(gld_252.min())
            if float(gld_252.iloc[-1]) >= hi52 * 0.99:
                chart_fig.add_annotation(x=gld_252.index[-1], y=hi52, text="52w HIGH", showarrow=True, arrowcolor="#ffd700", font=dict(size=9, color="#ffd700"), row=1, col=1, secondary_y=False, ax=-40, ay=-20)

            # Annotation box — safe haven reading
            gld_20d_mom = commodity_moms.get("GLD", 0)
            # Check if VIX is available from composite
            try:
                comp = pd.read_csv(COMPOSITE_CSV, parse_dates=['date'])
                latest_vix = float(comp.iloc[-1].get('vix', 20))
            except Exception:
                latest_vix = 20
            safe_haven = gld_20d_mom > 2 and latest_vix > 20
            sh_text = "Safe Haven: ACTIVE" if safe_haven else "Safe Haven: INACTIVE"
            sh_color = YELLOW if safe_haven else MUTED

            chart_fig.add_annotation(
                x=0.02, y=0.98, xref="x domain", yref="y domain",
                text=f"<b>{sh_text}</b>", showarrow=False,
                font=dict(size=10, color=sh_color),
                bgcolor=f"rgba({_hex_to_rgb(sh_color)},0.15)",
                bordercolor=sh_color, borderwidth=1, borderpad=3,
                row=1, col=1,
            )
    except Exception as e:
        chart_fig.add_annotation(text=f"GLD error: {e}", row=1, col=1, showarrow=False, font=dict(color=RED))

    # TOP RIGHT — XLE vs SPY Relative Strength
    try:
        xle_long = long_data.get("XLE")
        spy_long = long_data.get("SPY")
        if xle_long is not None and spy_long is not None:
            common_idx = xle_long.index.intersection(spy_long.index)
            xle_a = xle_long.loc[common_idx].tail(252)
            spy_a = spy_long.loc[common_idx].tail(252)
            rs = (xle_a / xle_a.iloc[0]) / (spy_a / spy_a.iloc[0])
            rs_ma20 = rs.rolling(20).mean()

            chart_fig.add_trace(go.Scatter(
                x=rs.index, y=rs.values,
                mode="lines", name="XLE/SPY RS",
                line=dict(color="#ff6f00", width=2),
                hovertemplate="RS: %{y:.3f}<extra></extra>",
            ), row=1, col=2)
            chart_fig.add_trace(go.Scatter(
                x=rs_ma20.index, y=rs_ma20.values,
                mode="lines", name="RS 20d MA",
                line=dict(color=MUTED, width=1.5, dash="dash"),
                showlegend=False,
            ), row=1, col=2)
            chart_fig.add_hline(y=1.0, line_dash="dot", line_color="white", line_width=0.5, row=1, col=2)

            # Fill above/below 1.0
            above1 = rs.where(rs >= 1.0)
            chart_fig.add_trace(go.Scatter(x=rs.index, y=above1.values, mode="lines", line=dict(width=0), showlegend=False), row=1, col=2)
            ones = pd.Series(1.0, index=rs.index)
            chart_fig.add_trace(go.Scatter(x=rs.index, y=ones.values, mode="lines", line=dict(width=0), fill="tonexty", fillcolor="rgba(38,166,154,0.1)", showlegend=False), row=1, col=2)

            # Annotation
            rs_current = float(rs.iloc[-1])
            rs_slope = float(rs.iloc[-1] - rs.iloc[-min(20, len(rs))]) if len(rs) >= 2 else 0
            if rs_current > 1.0 and rs_slope > 0:
                ann = "⚠️ LATE CYCLE: Energy leading. Watch for composite deterioration."
                ann_c = YELLOW
            elif rs_current < 1.0:
                ann = "✅ Energy underperforming — not a late-cycle signal"
                ann_c = GREEN
            else:
                ann = "🟡 Energy outperforming but momentum fading"
                ann_c = YELLOW
            chart_fig.add_annotation(
                x=0.98, y=0.98, xref="x2 domain", yref="y2 domain",
                text=f"<b>{ann}</b>", showarrow=False,
                font=dict(size=9, color=ann_c),
                bgcolor=f"rgba({_hex_to_rgb(ann_c)},0.1)",
                bordercolor=ann_c, borderwidth=1, borderpad=3,
                xanchor="right",
            )
    except Exception as e:
        chart_fig.add_annotation(text=f"XLE/SPY error: {e}", row=1, col=2, showarrow=False, font=dict(color=RED))

    # BOTTOM LEFT — Oil + Copper Growth Barometers
    try:
        uso_long = long_data.get("USO")
        cper_long = long_data.get("CPER")
        if uso_long is not None and cper_long is not None:
            common = uso_long.index.intersection(cper_long.index)
            uso_n = (uso_long.loc[common].tail(252) / uso_long.loc[common].tail(252).iloc[0]) * 100
            cper_n = (cper_long.loc[common].tail(252) / cper_long.loc[common].tail(252).iloc[0]) * 100

            chart_fig.add_trace(go.Scatter(
                x=uso_n.index, y=uso_n.values,
                mode="lines", name="USO (Oil)",
                line=dict(color="#8b4513", width=2),
                hovertemplate="Oil: %{y:.1f}<extra></extra>",
            ), row=2, col=1, secondary_y=False)
            chart_fig.add_trace(go.Scatter(
                x=cper_n.index, y=cper_n.values,
                mode="lines", name="CPER (Copper)",
                line=dict(color="#b87333", width=2),
                hovertemplate="Copper: %{y:.1f}<extra></extra>",
            ), row=2, col=1, secondary_y=False)

            # Annotation
            uso_20d = commodity_moms.get("USO", 0)
            cper_20d = commodity_moms.get("CPER", 0)
            if uso_20d > 0 and cper_20d > 0:
                g_ann = "⚡ Oil + Copper confirming — growth strong"
                g_c = GREEN
            elif uso_20d < 0 and cper_20d < 0:
                g_ann = "📉 Both weak — growth slowdown signal"
                g_c = RED
            else:
                g_ann = "⚠️ Diverging — mixed growth signal"
                g_c = YELLOW
            chart_fig.add_annotation(
                x=0.02, y=0.98, xref="x3 domain", yref="y3 domain",
                text=f"<b>{g_ann}</b>", showarrow=False,
                font=dict(size=9, color=g_c),
                bgcolor=f"rgba({_hex_to_rgb(g_c)},0.1)",
                bordercolor=g_c, borderwidth=1, borderpad=3,
            )

            # CPER 20d ROC on secondary
            cper_roc = cper_n.pct_change(20) * 100
            cper_roc = cper_roc.dropna()
            roc_c = [GREEN if v > 0 else RED for v in cper_roc.values]
            chart_fig.add_trace(go.Bar(
                x=cper_roc.index, y=cper_roc.values,
                marker_color=roc_c, showlegend=False, opacity=0.3,
                hovertemplate="Copper 20d ROC: %{y:.1f}%<extra></extra>",
            ), row=2, col=1, secondary_y=True)
    except Exception as e:
        chart_fig.add_annotation(text=f"Oil/Copper error: {e}", row=2, col=1, showarrow=False, font=dict(color=RED))

    # BOTTOM RIGHT — DXY or SLV/GLD proxy
    try:
        if dxy_data is not None and len(dxy_data) >= 20:
            dxy_252 = dxy_data.tail(252)
            dxy_ma20 = dxy_252.rolling(20).mean()
            chart_fig.add_trace(go.Scatter(
                x=dxy_252.index, y=dxy_252.values,
                mode="lines", name="DXY",
                line=dict(color=BLUE, width=2),
                hovertemplate="DXY: %{y:.2f}<extra></extra>",
            ), row=2, col=2, secondary_y=False)
            chart_fig.add_trace(go.Scatter(
                x=dxy_ma20.index, y=dxy_ma20.values,
                mode="lines", name="DXY 20d MA",
                line=dict(color=MUTED, width=1.5, dash="dash"),
                showlegend=False,
            ), row=2, col=2, secondary_y=False)

            # DXY 20d ROC on secondary
            dxy_roc = dxy_252.pct_change(20) * 100
            dxy_roc = dxy_roc.dropna()
            dxy_roc_c = [RED if v > 0 else GREEN for v in dxy_roc.values]  # Inverted: dollar up = bad for commodities
            chart_fig.add_trace(go.Bar(
                x=dxy_roc.index, y=dxy_roc.values,
                marker_color=dxy_roc_c, showlegend=False, opacity=0.3,
                hovertemplate="DXY 20d ROC: %{y:.1f}%<extra></extra>",
            ), row=2, col=2, secondary_y=True)

            # Annotation
            if dxy_20d_pct is not None:
                if dxy_20d_pct < -0.5:
                    d_ann = "📉 Dollar weakening — tailwind for ALL commodities"
                    d_c = GREEN
                elif dxy_20d_pct > 0.5:
                    d_ann = "💵 Dollar strengthening — headwind for commodities"
                    d_c = RED
                else:
                    d_ann = "💵 Dollar stable — no FX distortion"
                    d_c = MUTED
                chart_fig.add_annotation(
                    x=0.98, y=0.98, xref="x4 domain", yref="y4 domain",
                    text=f"<b>{d_ann}</b>", showarrow=False,
                    font=dict(size=9, color=d_c),
                    bgcolor=f"rgba({_hex_to_rgb(d_c)},0.1)",
                    bordercolor=d_c, borderwidth=1, borderpad=3,
                    xanchor="right",
                )
        else:
            # Fallback: SLV/GLD ratio
            slv_s = short_data.get("SLV")
            gld_s = short_data.get("GLD")
            if slv_s is not None and gld_s is not None:
                common = slv_s.index.intersection(gld_s.index)
                ratio = slv_s.loc[common] / gld_s.loc[common]
                chart_fig.add_trace(go.Scatter(
                    x=ratio.index, y=ratio.values,
                    mode="lines", name="SLV/GLD",
                    line=dict(color=BLUE, width=2),
                ), row=2, col=2)
                chart_fig.add_annotation(
                    x=0.5, y=0.5, xref="x4 domain", yref="y4 domain",
                    text="DXY unavailable — using SLV/GLD as dollar proxy",
                    showarrow=False, font=dict(size=10, color=MUTED),
                )
    except Exception as e:
        chart_fig.add_annotation(text=f"DXY error: {e}", row=2, col=2, showarrow=False, font=dict(color=RED))

    chart_fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG,
        height=700, margin=dict(l=50, r=50, t=50, b=30),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(color=MUTED, size=10)),
    )
    chart_fig.update_xaxes(gridcolor=BORDER, showgrid=False)
    chart_fig.update_yaxes(gridcolor=BORDER)

    charts_html = chart_fig.to_html(full_html=False, include_plotlyjs=False)

    # ── SECTION 6C — COMMODITY REGIME VERDICT ────────────────
    gld_20d = commodity_moms.get("GLD", 0)
    xle_20d = commodity_moms.get("XLE", 0)
    uso_20d = commodity_moms.get("USO", 0)
    cper_20d = commodity_moms.get("CPER", 0)

    # Get SPY 20d for relative strength comparison
    spy_20d = 0
    try:
        spy_s = short_data.get("SPY") if "SPY" in short_data else None
        if spy_s is None and "SPY" in long_data:
            spy_s = long_data["SPY"].tail(40)
        if spy_s is not None and len(spy_s) >= 20:
            spy_20d = ((float(spy_s.iloc[-1]) - float(spy_s.iloc[-20])) / float(spy_s.iloc[-20])) * 100
    except Exception:
        pass

    gold_signal = "bullish" if gld_20d > 0 else "bearish"
    energy_signal = "leading" if xle_20d > spy_20d else "lagging"
    if uso_20d > 0 and cper_20d > 0:
        growth_signal = "bullish"
    elif uso_20d < 0 and cper_20d < 0:
        growth_signal = "bearish"
    else:
        growth_signal = "mixed"
    if dxy_20d_pct is not None:
        dollar_signal = "weak" if dxy_20d_pct < -0.5 else ("strong" if dxy_20d_pct > 0.5 else "neutral")
    else:
        dollar_signal = "neutral"

    # Determine regime
    if gold_signal == "bullish" and energy_signal == "leading":
        regime_label = "INFLATIONARY PRESSURE"
        regime_color = RED
        regime_desc = "Gold and energy both rising — inflation is the story. Fed stays hawkish. Growth stocks face headwind. Short bias on QQQ, watch XLE for continuation."
    elif growth_signal == "bullish" and gold_signal == "bearish":
        regime_label = "GROWTH COMMODITIES LEADING"
        regime_color = GREEN
        regime_desc = "Oil and copper rising, gold quiet — markets pricing real economic growth. Risk-on confirmation signal. Consistent with improving composite score."
    elif gold_signal == "bullish" and growth_signal == "bearish":
        regime_label = "SAFE HAVEN BID ACTIVE"
        regime_color = YELLOW
        regime_desc = "Gold rising, growth commodities weak — flight to safety. Confirms current risk-off structural regime. No commodity tailwind for equities."
    else:
        regime_label = "COMMODITIES DORMANT"
        regime_color = MUTED
        regime_desc = "No clear directional signal from commodities. Range-bound. Wait for breakout in GLD or Oil before drawing macro conclusions."

    # Connect to composite
    try:
        comp = pd.read_csv(COMPOSITE_CSV, parse_dates=['date'])
        comp = comp.dropna(subset=['composite_score'])
        comp_score = float(comp.iloc[-1]['composite_score'])
        comp_regime = str(comp.iloc[-1].get('regime', 'UNKNOWN'))
        comp_bullish = comp_score > 0

        if (regime_color == GREEN and comp_bullish) or (regime_color in [RED, YELLOW] and not comp_bullish):
            confirm_text = f"✅ CONFIRMS current {comp_regime} composite reading. Two independent signal sources aligned."
            confirm_color = GREEN
        else:
            confirm_text = f"⚠️ CONTRADICTS current {comp_regime} composite reading. Divergence worth watching — one signal is wrong."
            confirm_color = YELLOW
    except Exception:
        confirm_text = "Composite score unavailable for cross-reference."
        confirm_color = MUTED

    verdict_html = f"""
    <div style="background:rgba({_hex_to_rgb(regime_color)},0.08);border:1px solid {regime_color};border-radius:8px;padding:20px;margin:16px;">
      <div style="font-size:20px;font-weight:700;color:{regime_color};">{regime_label}</div>
      <div style="font-size:13px;color:{TEXT};margin-top:8px;line-height:1.5;">{regime_desc}</div>
      <div style="font-size:12px;color:{confirm_color};margin-top:10px;padding-top:10px;border-top:1px solid {BORDER};">{confirm_text}</div>
    </div>
    """

    return scorecard_html + charts_html + verdict_html, regime_label


# ══════════════════════════════════════════════════════════════
#  HTML ASSEMBLY
# ══════════════════════════════════════════════════════════════

def _panel_header(num, title):
    """Generate a styled panel header."""
    color = ACCENT.get(num, MUTED)
    return f"""
    <div style="padding:8px 0;">
      <div style="border-left:3px solid {color};padding-left:12px;margin:0 16px;">
        <span style="font-size:13px;font-weight:600;color:{MUTED};letter-spacing:3px;text-transform:uppercase;">█ PANEL {num} — {title}</span>
      </div>
    </div>
    <div style="border-top:1px solid {BORDER};margin:0 16px;"></div>
    """


def assemble_html(panel1, panel2, panel3, panel4, panel5, panel6):
    """Combine all panels into a single self-contained HTML file."""
    from zoneinfo import ZoneInfo
    now_ct = datetime.now(ZoneInfo("America/Chicago"))
    timestamp = now_ct.strftime("%Y-%m-%d %H:%M:%S CT")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QuantLab War Room — Phase 1</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: {BG};
    color: {TEXT};
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    line-height: 1.5;
  }}
  .header {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 24px 12px 24px;
    border-bottom: 1px solid {BORDER};
  }}
  .header h1 {{
    font-size: 22px; font-weight: 700; letter-spacing: 0.5px;
    color: {TEXT};
  }}
  .header .subtitle {{
    font-size: 13px; color: {MUTED}; margin-left: 8px;
  }}
  .header .timestamp {{
    font-size: 12px; color: {MUTED};
  }}
  .panel-content {{
    padding: 0 8px;
  }}
</style>
</head>
<body>
  <div class="header">
    <div>
      <h1>QuantLab War Room — Phase 1 <span class="subtitle">🖥️ Mini Bloomberg Terminal</span></h1>
    </div>
    <div class="timestamp">Last Updated: {timestamp}</div>
  </div>

  {_panel_header(1, "REGIME COMMAND CENTER")}
  <div class="panel-content">{panel1}</div>

  {_panel_header(2, "MACRO SCORECARD")}
  <div class="panel-content">{panel2}</div>

  {_panel_header(3, "LIQUIDITY ENGINE")}
  <div class="panel-content">{panel3}</div>

  {_panel_header(4, "BASKET BATTLE")}
  <div class="panel-content">{panel4}</div>

  {_panel_header(5, "REGIME HISTORY + TACTICAL")}
  <div class="panel-content">{panel5}</div>

  {_panel_header(6, "COMMODITY REGIME")}
  <div class="panel-content">{panel6}</div>

  <div style="padding:20px;text-align:center;color:{MUTED};font-size:11px;border-top:1px solid {BORDER};margin-top:20px;">
    QuantLab Macro War Room — Phase 1 | Generated {timestamp}
  </div>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  QuantLab Macro War Room — Phase 1 Build")
    print("=" * 60)

    # Track panel statuses for summary
    statuses = {}

    # ── Panel 1 ──────────────────────────────────────────────
    print("\n[1/6] Building Regime Command Center...")
    try:
        panel1_html = build_panel1_regime_command_center()
        # Extract regime for summary
        comp = pd.read_csv(COMPOSITE_CSV, parse_dates=['date']).dropna(subset=['composite_score'])
        p1_score = float(comp.iloc[-1]['composite_score'])
        p1_regime = str(comp.iloc[-1].get('regime', '?'))
        statuses['p1'] = f"Regime = {p1_regime} | {p1_score:+.2f}"
        print(f"  ✅ {statuses['p1']}")
    except Exception as e:
        panel1_html = f'<div style="color:{RED};padding:20px;">Panel 1 failed: {e}</div>'
        statuses['p1'] = f"FAILED: {e}"
        print(f"  ✗ {e}")

    # ── Panel 2 ──────────────────────────────────────────────
    print("\n[2/6] Building Macro Scorecard...")
    try:
        panel2_html = build_panel2_macro_scorecard()
        statuses['p2'] = "OK"
        print(f"  ✅ Scorecard built")
    except Exception as e:
        panel2_html = f'<div style="color:{RED};padding:20px;">Panel 2 failed: {e}</div>'
        statuses['p2'] = f"FAILED: {e}"
        print(f"  ✗ {e}")

    # ── Panel 3 ──────────────────────────────────────────────
    print("\n[3/6] Building Liquidity Engine...")
    try:
        panel3_html, liq_score = build_panel3_liquidity_engine()
        statuses['p3'] = f"Liquidity Score = {liq_score:+d}/4"
        print(f"  ✅ {statuses['p3']}")
    except Exception as e:
        panel3_html = f'<div style="color:{RED};padding:20px;">Panel 3 failed: {e}</div>'
        liq_score = 0
        statuses['p3'] = f"FAILED: {e}"
        print(f"  ✗ {e}")

    # ── Panel 4 ──────────────────────────────────────────────
    print("\n[4/6] Building Basket Battle...")
    try:
        panel4_html, basket_winner = build_panel4_basket_battle()
        statuses['p4'] = f"{basket_winner} basket leading"
        print(f"  ✅ {statuses['p4']}")
    except Exception as e:
        panel4_html = f'<div style="color:{RED};padding:20px;">Panel 4 failed: {e}</div>'
        statuses['p4'] = f"FAILED: {e}"
        print(f"  ✗ {e}")

    # ── Panel 5 ──────────────────────────────────────────────
    print("\n[5/6] Building Regime History + Tactical...")
    try:
        panel5_html, hist_days = build_panel5_regime_history()
        statuses['p5'] = f"History {hist_days} days loaded"
        print(f"  ✅ {statuses['p5']}")
    except Exception as e:
        panel5_html = f'<div style="color:{RED};padding:20px;">Panel 5 failed: {e}</div>'
        statuses['p5'] = f"FAILED: {e}"
        print(f"  ✗ {e}")

    # ── Panel 6 ──────────────────────────────────────────────
    print("\n[6/6] Building Commodity Regime...")
    try:
        panel6_html, commodity_regime = build_panel6_commodity_regime()
        statuses['p6'] = f"Commodity Regime = {commodity_regime}"
        print(f"  ✅ {statuses['p6']}")
    except Exception as e:
        panel6_html = f'<div style="color:{RED};padding:20px;">Panel 6 failed: {e}</div>'
        statuses['p6'] = f"FAILED: {e}"
        print(f"  ✗ {e}")

    # ── Assemble & Write ─────────────────────────────────────
    print("\nAssembling HTML...")
    html = assemble_html(panel1_html, panel2_html, panel3_html, panel4_html, panel5_html, panel6_html)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")

    size_kb = OUTPUT_FILE.stat().st_size / 1024

    print(f"""
╔══════════════════════════════════════════╗
║     QuantLab War Room — Build Complete   ║
╠══════════════════════════════════════════╣
║ Panel 1: {statuses.get('p1', 'N/A'):<31}║
║ Panel 2: {statuses.get('p2', 'N/A'):<31}║
║ Panel 3: {statuses.get('p3', 'N/A'):<31}║
║ Panel 4: {statuses.get('p4', 'N/A'):<31}║
║ Panel 5: {statuses.get('p5', 'N/A'):<31}║
║ Panel 6: {statuses.get('p6', 'N/A'):<31}║
║ Output: scratch/dashboard/index.html    ║
║ Size: {size_kb:.0f} KB{' ' * (32 - len(f'{size_kb:.0f} KB'))}║
╚══════════════════════════════════════════╝""")


if __name__ == "__main__":
    main()
