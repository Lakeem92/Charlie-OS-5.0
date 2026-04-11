import sys, os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

from dotenv import load_dotenv
load_dotenv(r'C:\QuantLab\Data_Lab\.env', override=True)

import io
import math
import re
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import fredapi
import pandas as pd
import plotly.graph_objects as go
import requests
from plotly.subplots import make_subplots

from shared.config.env_loader import load_keys
from shared.data_router import DataRouter


OUTPUT_DIR = Path(r"C:\QuantLab\Data_Lab\scratch\dashboard_cta")
OUTPUT_FILE = OUTPUT_DIR / "index.html"
COT_URL = "https://www.cftc.gov/dea/newcot/deahistfo.zip"
TITAN_COT_URL = "https://research.titanfx.com/cftc/cot-sp500mini"

BG = "#0d1117"
CARD_BG = "#161b22"
TEXT = "#e6edf3"
MUTED = "#8b949e"
BORDER = "#30363d"
GREEN = "#26a69a"
LT_GREEN = "#66bb6a"
YELLOW = "#ffa726"
ORANGE = "#ef6c00"
RED = "#ef5350"
BLUE = "#42a5f5"
PINK = "#ec407a"
CYAN = "#26c6da"

WEIGHTS = {
    "COT Z-Score": 0.35,
    "XLY/XLP Z-Score": 0.30,
    "HY Spread Z-Score (Inv)": 0.20,
    "2s10s Curve Z-Score": 0.15,
}

SCORE_BANDS = [
    (1.0, 3.0, "CTA MAX SHORT — Exhaustion Zone (Contrarian Upside Risk)"),
    (3.1, 4.5, "Risk-Off — Systematic Selling Pressure"),
    (4.6, 5.5, "Neutral — No Clear Regime Signal"),
    (5.6, 7.0, "Risk-On — Systematic Buying Tailwind"),
    (7.1, 10.0, "CTA MAX LONG — Crowded Upside (Fade Risk)"),
]


def _clean_series(series: pd.Series) -> pd.Series:
    cleaned = pd.to_numeric(series, errors="coerce").dropna().copy()
    cleaned.index = pd.to_datetime(cleaned.index)
    if getattr(cleaned.index, "tz", None) is not None:
        cleaned.index = cleaned.index.tz_localize(None)
    return cleaned.sort_index()


def _close_series(df: pd.DataFrame, label: str) -> pd.Series:
    if df is None or df.empty:
        return pd.Series(dtype=float)
    close_col = "Close" if "Close" in df.columns else df.columns[0]
    return _clean_series(df[close_col].rename(label))


def _clamp(value: float | None, low: float = -3.0, high: float = 3.0) -> float | None:
    if value is None or pd.isna(value):
        return None
    return max(low, min(high, float(value)))


def _zscore_last(series: pd.Series, lookback: int) -> float | None:
    cleaned = _clean_series(series)
    if len(cleaned) < max(20, lookback // 2):
        return None
    window = cleaned.tail(lookback)
    std = window.std(ddof=0)
    if std is None or pd.isna(std) or std == 0:
        return None
    return float((window.iloc[-1] - window.mean()) / std)


def _pct_change(series: pd.Series, periods: int) -> float | None:
    cleaned = _clean_series(series)
    if len(cleaned) <= periods:
        return None
    base = cleaned.iloc[-periods - 1]
    latest = cleaned.iloc[-1]
    if pd.isna(base) or base == 0:
        return None
    return float((latest / base - 1) * 100.0)


def _diff_change(series: pd.Series, periods: int) -> float | None:
    cleaned = _clean_series(series)
    if len(cleaned) <= periods:
        return None
    return float(cleaned.iloc[-1] - cleaned.iloc[-periods - 1])


def _map_z_to_score(z_value: float | None) -> float | None:
    clamped = _clamp(z_value)
    if clamped is None:
        return None
    return 1 + ((clamped + 3) / 6) * 9


def _score_label(score: float | None) -> tuple[str, str]:
    if score is None:
        return "Unavailable", MUTED
    if score <= 3.0:
        return "CTA MAX SHORT — Exhaustion Zone (Contrarian Upside Risk)", RED
    if score <= 4.5:
        return "Risk-Off — Systematic Selling Pressure", ORANGE
    if score <= 5.5:
        return "Neutral — No Clear Regime Signal", YELLOW
    if score <= 7.0:
        return "Risk-On — Systematic Buying Tailwind", GREEN
    return "CTA MAX LONG — Crowded Upside (Fade Risk)", LT_GREEN


def _sparkline_svg(series: pd.Series, color: str, width: int = 160, height: int = 42) -> str:
    cleaned = _clean_series(series)
    if len(cleaned) < 2:
        return ""
    values = cleaned.tolist()
    lo, hi = min(values), max(values)
    spread = hi - lo if hi != lo else 1.0
    points = []
    for idx, value in enumerate(values):
        x = (idx / (len(values) - 1)) * width
        y = height - ((value - lo) / spread) * (height - 8) - 4
        points.append(f"{x:.1f},{y:.1f}")
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">' 
        f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2" />'
        "</svg>"
    )


def _fmt_value(value: float | None, suffix: str = "", decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.{decimals}f}{suffix}"


def _component_note(name: str) -> str:
    notes = {
        "COT Z-Score": "Systematic futures positioning: lower means CTAs are already leaning short.",
        "XLY/XLP Z-Score": "Discretionary versus Staples: a quick market-based read on appetite for cyclicality.",
        "HY Spread Z-Score (Inv)": "Credit stress proxy: tighter high-yield spreads support risk-taking.",
        "2s10s Curve Z-Score": "Macro slope signal: steeper curve tends to align with easier growth expectations.",
    }
    return notes.get(name, "")


def _fred() -> fredapi.Fred:
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise ValueError("FRED_API_KEY not found in environment")
    return fredapi.Fred(api_key=api_key)


def fetch_cot_data() -> tuple[pd.DataFrame, str | None]:
    try:
        response = requests.get(COT_URL, timeout=30)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            members = [name for name in zf.namelist() if name.lower().endswith((".csv", ".txt"))]
            if not members:
                raise RuntimeError("No CSV found inside COT zip")
            with zf.open(members[0]) as handle:
                df = pd.read_csv(handle, low_memory=False)

        df.columns = [col.lower() for col in df.columns]
        market_col = "market_and_exchange_names"
        needed = [
            "report_date_as_yyyy_mm_dd",
            "noncomm_positions_long_all",
            "noncomm_positions_short_all",
            "open_interest_all",
        ]
        missing = [col for col in [market_col] + needed if col not in df.columns]
        if missing:
            raise RuntimeError(f"Missing COT columns: {', '.join(missing)}")

        cot = df[df[market_col].astype(str).str.contains("E-MINI S&P 500", case=False, na=False)].copy()
        if cot.empty:
            raise RuntimeError("No E-MINI S&P 500 rows found in COT data")

        cot["date"] = pd.to_datetime(cot["report_date_as_yyyy_mm_dd"], errors="coerce")
        cot = cot.dropna(subset=["date"]).sort_values("date")
        for col in needed[1:]:
            cot[col] = pd.to_numeric(cot[col], errors="coerce")
        cot = cot.dropna(subset=needed[1:])
        cot["long_as_pct_oi"] = cot["noncomm_positions_long_all"] / cot["open_interest_all"] * 100.0
        cot["short_as_pct_oi"] = cot["noncomm_positions_short_all"] / cot["open_interest_all"] * 100.0
        cot["net_speculator"] = cot["noncomm_positions_long_all"] - cot["noncomm_positions_short_all"]
        cot["net_as_pct_oi"] = cot["net_speculator"] / cot["open_interest_all"] * 100.0
        cot = cot.tail(104).copy()
        rolling = cot["net_as_pct_oi"].rolling(52, min_periods=26)
        cot["z_score_52w"] = (cot["net_as_pct_oi"] - rolling.mean()) / rolling.std(ddof=0)
        cot["source"] = "cftc"
        return cot, None
    except Exception as exc:
        try:
            response = requests.get(TITAN_COT_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', response.text)
            if not match:
                raise RuntimeError("Titan fallback page missing structured data")
            payload = requests.models.complexjson.loads(match.group(1))
            rows = payload["props"]["pageProps"]["data"]
            titan = pd.DataFrame(rows, columns=["date", "noncomm_positions_long_all", "noncomm_positions_short_all", "aux"])
            titan["date"] = pd.to_datetime(titan["date"], errors="coerce")
            titan = titan.dropna(subset=["date"]).sort_values("date")
            titan["noncomm_positions_long_all"] = pd.to_numeric(titan["noncomm_positions_long_all"], errors="coerce")
            titan["noncomm_positions_short_all"] = pd.to_numeric(titan["noncomm_positions_short_all"], errors="coerce")
            titan = titan.dropna(subset=["noncomm_positions_long_all", "noncomm_positions_short_all"])
            titan["open_interest_all"] = titan["noncomm_positions_long_all"] + titan["noncomm_positions_short_all"]
            titan["long_as_pct_oi"] = titan["noncomm_positions_long_all"] / titan["open_interest_all"] * 100.0
            titan["short_as_pct_oi"] = titan["noncomm_positions_short_all"] / titan["open_interest_all"] * 100.0
            titan["net_speculator"] = titan["noncomm_positions_long_all"] - titan["noncomm_positions_short_all"]
            titan["net_as_pct_oi"] = titan["net_speculator"] / titan["open_interest_all"] * 100.0
            titan = titan.tail(104).copy()
            rolling = titan["net_as_pct_oi"].rolling(52, min_periods=26)
            titan["z_score_52w"] = (titan["net_as_pct_oi"] - rolling.mean()) / rolling.std(ddof=0)
            titan["source"] = "titan_proxy"
            return titan, f"Official CFTC archive unavailable ({exc}); using Titan weekly spec-position proxy."
        except Exception as titan_exc:
            return pd.DataFrame(), f"{exc}; Titan fallback failed: {titan_exc}"


def fetch_xly_xlp_ratio(start_date: str, end_date: str) -> pd.DataFrame:
    xly = _close_series(DataRouter.get_price_data("XLY", start_date, end_date=end_date), "XLY")
    xlp = _close_series(DataRouter.get_price_data("XLP", start_date, end_date=end_date), "XLP")
    aligned = pd.concat([xly, xlp], axis=1).dropna()
    if aligned.empty:
        return pd.DataFrame()
    ratio = (aligned["XLY"] / aligned["XLP"]).rename("ratio")
    out = ratio.to_frame()
    out["ma20"] = out["ratio"].rolling(20).mean()
    return out.dropna(subset=["ratio"])


def fetch_spx_series(start_date: str, end_date: str) -> pd.Series:
    df = DataRouter.get_price_data("^SPX", start_date, end_date=end_date, source="yfinance")
    return _close_series(df, "SPX")


def fetch_fred_series(series_id: str, days: int = 504) -> pd.Series:
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    series = _fred().get_series(series_id, observation_start=start)
    return _clean_series(series.rename(series_id))


def build_component_payload(cot_df: pd.DataFrame, ratio_df: pd.DataFrame, fred_payload: dict) -> list[dict]:
    cot_z = None if cot_df.empty else _zscore_last(cot_df.set_index("date")["net_as_pct_oi"], 52)
    ratio_z = None if ratio_df.empty else _zscore_last(ratio_df["ratio"], 252)
    hy_z = _zscore_last(fred_payload["hy"], 252)
    hy_inv = None if hy_z is None else -hy_z
    curve_z = _zscore_last(fred_payload["curve"], 252)

    items = [
        {"name": "COT Z-Score", "z": cot_z, "weight": WEIGHTS["COT Z-Score"]},
        {"name": "XLY/XLP Z-Score", "z": ratio_z, "weight": WEIGHTS["XLY/XLP Z-Score"]},
        {"name": "HY Spread Z-Score (Inv)", "z": hy_inv, "weight": WEIGHTS["HY Spread Z-Score (Inv)"]},
        {"name": "2s10s Curve Z-Score", "z": curve_z, "weight": WEIGHTS["2s10s Curve Z-Score"]},
    ]

    for item in items:
        item["clamped_z"] = _clamp(item["z"])
        item["component_score"] = _map_z_to_score(item["z"])
        item["weighted_score"] = None if item["component_score"] is None else item["component_score"] * item["weight"]
        item["note"] = _component_note(item["name"])
    return items


def build_daily_score_history(cot_df: pd.DataFrame, ratio_df: pd.DataFrame, fred_payload: dict, periods: int = 10) -> pd.DataFrame:
    today = pd.Timestamp(datetime.now().date())
    dates = pd.bdate_range(end=today, periods=60)

    if not cot_df.empty:
        cot_z = cot_df.set_index("date")["z_score_52w"].sort_index().reindex(dates, method="ffill")
    else:
        cot_z = pd.Series(index=dates, dtype=float)

    if not ratio_df.empty:
        ratio_roll = ratio_df["ratio"].rolling(252, min_periods=126)
        ratio_z = ((ratio_df["ratio"] - ratio_roll.mean()) / ratio_roll.std(ddof=0)).reindex(dates, method="ffill")
    else:
        ratio_z = pd.Series(index=dates, dtype=float)

    hy_series = fred_payload["hy"]
    if not hy_series.empty:
        hy_roll = hy_series.rolling(252, min_periods=126)
        hy_inv = (-((hy_series - hy_roll.mean()) / hy_roll.std(ddof=0))).reindex(dates, method="ffill")
    else:
        hy_inv = pd.Series(index=dates, dtype=float)

    curve_series = fred_payload["curve"]
    if not curve_series.empty:
        curve_roll = curve_series.rolling(252, min_periods=126)
        curve_z = ((curve_series - curve_roll.mean()) / curve_roll.std(ddof=0)).reindex(dates, method="ffill")
    else:
        curve_z = pd.Series(index=dates, dtype=float)

    hist = pd.DataFrame({
        "COT Z-Score": cot_z,
        "XLY/XLP Z-Score": ratio_z,
        "HY Spread Z-Score (Inv)": hy_inv,
        "2s10s Curve Z-Score": curve_z,
    }, index=dates)

    for name, weight in WEIGHTS.items():
        hist[f"{name}__score"] = hist[name].apply(_map_z_to_score)
        hist[f"{name}__weighted"] = hist[f"{name}__score"] * weight

    weighted_cols = [f"{name}__weighted" for name in WEIGHTS]
    hist[weighted_cols] = hist[weighted_cols].apply(pd.to_numeric, errors="coerce")
    hist["score"] = hist[weighted_cols].sum(axis=1, min_count=1).round(1)
    hist["label"] = hist["score"].apply(lambda x: _score_label(x)[0] if pd.notna(x) else "Unavailable")
    hist = hist.dropna(subset=["score"]).tail(periods)
    return hist


def build_history_chart(history_df: pd.DataFrame) -> str:
    if history_df.empty:
        return "<div class='history-empty'>Daily history unavailable</div>"
    plot_df = history_df.copy().sort_index()
    colors = [_score_label(score)[1] for score in plot_df["score"]]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=[idx.strftime("%m-%d") for idx in plot_df.index],
            y=plot_df["score"],
            marker=dict(color=colors),
            text=[f"{value:.1f}" for value in plot_df["score"]],
            textposition="outside",
            hovertemplate="%{x}<br>Score: %{y:.1f}<br>%{customdata}<extra></extra>",
            customdata=plot_df["label"],
            showlegend=False,
        )
    )
    fig.add_hrect(y0=1.0, y1=3.0, fillcolor="rgba(239,83,80,0.08)", line_width=0)
    fig.add_hrect(y0=3.1, y1=4.5, fillcolor="rgba(239,108,0,0.07)", line_width=0)
    fig.add_hrect(y0=4.6, y1=5.5, fillcolor="rgba(255,167,38,0.06)", line_width=0)
    fig.add_hrect(y0=5.6, y1=7.0, fillcolor="rgba(38,166,154,0.07)", line_width=0)
    fig.add_hrect(y0=7.1, y1=10.0, fillcolor="rgba(102,187,106,0.08)", line_width=0)
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=36, r=10, t=8, b=28),
        height=250,
        font=dict(color=TEXT, family="Segoe UI, Arial, sans-serif", size=11),
        yaxis=dict(range=[1, 10], title="Score", gridcolor="rgba(255,255,255,0.08)"),
        xaxis=dict(title="Session"),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False, "responsive": True})


def build_regime_flip_box(score: float | None, components: list[dict]) -> str:
    if score is None:
        return "<div class='flip-box'><div class='flip-title'>What Would Move The Score</div><div class='flip-body'>Composite score unavailable.</div></div>"

    boundaries = [3.1, 4.6, 5.6, 7.1]
    nearest_target = None
    direction = None
    for boundary in boundaries:
        gap = boundary - score
        if gap > 0:
            nearest_target = boundary
            direction = "up"
            break
    if nearest_target is None:
        lower_boundaries = [7.0, 5.5, 4.5, 3.0]
        for boundary in lower_boundaries:
            gap = score - boundary
            if gap > 0:
                nearest_target = boundary
                direction = "down"
                break

    if nearest_target is None:
        return "<div class='flip-box'><div class='flip-title'>What Would Move The Score</div><div class='flip-body'>Score is pinned at the edge of the range.</div></div>"

    delta_score = nearest_target - score
    candidates = []
    for item in components:
        if item["clamped_z"] is None:
            continue
        slope = 1.5 * item["weight"]
        if slope == 0:
            continue
        if delta_score > 0:
            headroom = (3 - item["clamped_z"]) * slope
        else:
            headroom = (item["clamped_z"] + 3) * slope
        if abs(headroom) < abs(delta_score):
            continue
        z_needed = delta_score / slope
        candidates.append((abs(z_needed), z_needed, item))

    if not candidates:
        return (
            "<div class='flip-box'><div class='flip-title'>What Would Move The Score</div>"
            f"<div class='flip-body'>Need {delta_score:+.1f} score points to reach {nearest_target:.1f}, but no single component has enough headroom on its own.</div></div>"
        )

    _, z_needed, item = min(candidates, key=lambda x: x[0])
    next_label = _score_label(nearest_target)[0]
    direction_word = "improves" if z_needed > 0 else "deteriorates"
    return (
        "<div class='flip-box'>"
        "<div class='flip-title'>What Would Move The Score</div>"
        f"<div class='flip-body'><strong>{item['name']}</strong> is the easiest single lever. If its z-score {direction_word} by about <strong>{z_needed:+.2f}</strong>, the composite would move roughly <strong>{delta_score:+.1f}</strong> points and cross into <strong>{next_label}</strong> at <strong>{nearest_target:.1f}</strong>.</div>"
        f"<div class='flip-foot'>Current score {score:.1f} | nearest boundary {nearest_target:.1f}</div>"
        "</div>"
    )


def describe_cot_flow(long_change: float | None, short_change: float | None) -> str:
    if long_change is None or short_change is None:
        return "Flow read unavailable because there is not enough positioning history to compare recent long and short participation."

    flat_threshold = 0.6
    rise_threshold = 1.0
    drop_threshold = -1.0

    if short_change <= drop_threshold and long_change >= rise_threshold:
        return (
            f"Short % OI is falling ({short_change:+.1f} pts over 4 weeks) while long % OI is rising ({long_change:+.1f} pts). "
            "That is the cleanest risk-on positioning handoff: shorts are getting squeezed out and fresh longs are replacing them."
        )
    if short_change <= drop_threshold and long_change > -flat_threshold:
        return (
            f"Short % OI is dropping ({short_change:+.1f} pts) but long % OI is only flat-to-mildly better ({long_change:+.1f} pts). "
            "That usually signals short covering first, which can lift price fast but is less durable than true long accumulation."
        )
    if long_change >= rise_threshold and short_change < rise_threshold:
        return (
            f"Long % OI is rising ({long_change:+.1f} pts) without a matching short build ({short_change:+.1f} pts). "
            "That points to fresh long initiation and a healthier systematic bid than a pure squeeze dynamic."
        )
    if long_change <= drop_threshold and short_change >= rise_threshold:
        return (
            f"Long % OI is falling ({long_change:+.1f} pts) while short % OI is rising ({short_change:+.1f} pts). "
            "That is a genuine risk-off repositioning signal: longs are being cut and fresh shorts are being added."
        )
    if abs(long_change) <= flat_threshold and abs(short_change) <= flat_threshold:
        return (
            f"Both long % OI ({long_change:+.1f} pts) and short % OI ({short_change:+.1f} pts) are basically flat over 4 weeks. "
            "That means futures positioning is not doing much work here, so price is being driven more by spot flows and macro headlines than by CTA repositioning."
        )
    if long_change >= rise_threshold and short_change >= rise_threshold:
        return (
            f"Both long % OI ({long_change:+.1f} pts) and short % OI ({short_change:+.1f} pts) are rising. "
            "That usually means gross exposure is expanding on both sides, which tends to produce a more two-way, volatile tape rather than a clean one-direction CTA trend."
        )
    if long_change <= drop_threshold and short_change <= drop_threshold:
        return (
            f"Both long % OI ({long_change:+.1f} pts) and short % OI ({short_change:+.1f} pts) are declining. "
            "That suggests de-grossing rather than directional conviction, which often leaves the market sensitive to the next catalyst because positioning has been lightened on both sides."
        )
    return (
        f"Long % OI is moving {long_change:+.1f} pts and short % OI is moving {short_change:+.1f} pts over 4 weeks. "
        "That is a mixed positioning tape: there is movement under the surface, but not a clean enough handoff to call it pure squeeze, pure long build, or pure de-risking."
    )


def build_score_card(score: float | None, label: str, color: str, components: list[dict], last_updated: str) -> str:
    rows = []
    for item in components:
        rows.append(
            f"<div class='mini-row'><span>{item['name']}</span><strong>{_fmt_value(item['z'], '', 2)}</strong></div>"
        )
    return f"""
    <div class="score-card">
      <div class="score-topline">Diet CTA Score</div>
      <div class="score-value" style="color:{color};">{_fmt_value(score, '', 1)}</div>
      <div class="score-label" style="color:{color};">{label}</div>
      <div class="score-subtitle">Based on COT + XLY/XLP + Credit + Curve</div>
      <div class="mini-grid">{''.join(rows)}</div>
      <div class="last-updated">Last Updated: {last_updated}</div>
    </div>
    """


def build_macro_card(title: str, current_text: str, change_text: str, sparkline: str, color: str, note: str) -> str:
    return f"""
    <div class="macro-card" style="border-color:{color};">
      <div class="macro-title">{title}</div>
      <div class="macro-value" style="color:{color};">{current_text}</div>
      <div class="macro-change">5D change: {change_text}</div>
      <div class="macro-spark">{sparkline}</div>
      <div class="macro-note">{note}</div>
    </div>
    """


def build_implication_card(title: str, stats_html: str, body: str, color: str) -> str:
    return f"""
    <div class="imp-card" style="border-color:{color};">
      <div class="imp-title">{title}</div>
      <div class="imp-stats">{stats_html}</div>
      <div class="imp-body">{body}</div>
    </div>
    """


def _trend_summary(change: float | None, higher_is_risk_on: bool) -> tuple[str, str, str]:
    if change is None:
        return "→", "Unavailable", "Not enough history to classify the trend."
    flat_threshold = 0.6
    if change > flat_threshold:
        if higher_is_risk_on:
            return "↑", "Rising", "This is improving in the risk-on direction."
        return "↑", "Rising", "This is worsening in the risk-off direction."
    if change < -flat_threshold:
        if higher_is_risk_on:
            return "↓", "Falling", "This is worsening in the risk-on direction."
        return "↓", "Falling", "This is improving because bearish exposure is coming out."
    return "→", "Flat", "Positioning is not shifting enough to create a clean directional read."


def build_positioning_trend_table(long_change: float | None, short_change: float | None, net_change: float | None) -> str:
    rows = []
    entries = [
        ("Long % OI", long_change, True),
        ("Short % OI", short_change, False),
        ("Net % OI", net_change, True),
    ]
    for label, change, higher_is_risk_on in entries:
        arrow, state, implication = _trend_summary(change, higher_is_risk_on)
        value_text = _fmt_value(change, " pts", 1)
        rows.append(
            f"<tr><td>{label}</td><td class='trend-arrow'>{arrow}</td><td>{state}</td><td>{value_text}</td><td>{implication}</td></tr>"
        )
    return (
        "<div class='trend-table-wrap'>"
        "<div class='imp-title'>Positioning Trend Table</div>"
        "<table class='trend-table'><thead><tr><th>Series</th><th></th><th>State</th><th>4W Move</th><th>What It Signals</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def build_cot_gauge(z_value: float | None, color: str) -> str:
    if z_value is None:
        return "<div class='gauge-wrap'><div class='gauge-arrow'>N/A</div></div>"
    arrow = "↑" if z_value > 0.4 else ("↓" if z_value < -0.4 else "→")
    descriptor = "Risk-On Lean" if z_value > 0.4 else ("Risk-Off Lean" if z_value < -0.4 else "Neutral")
    return f"""
    <div class="gauge-wrap">
      <div class="gauge-arrow" style="color:{color};">{arrow}</div>
      <div class="gauge-desc">{descriptor}</div>
    </div>
    """


def build_main_figure(cot_df: pd.DataFrame, ratio_df: pd.DataFrame, spx_series: pd.Series, components: list[dict]) -> go.Figure:
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=False,
        vertical_spacing=0.14,
        specs=[[{"secondary_y": True}], [{}], [{}]],
        subplot_titles=(
            "ES Futures: Non-Commercial Net Position (% of OI)",
            "XLY/XLP Risk Appetite Ratio",
            "Diet CTA Score Components",
        ),
    )

    if not cot_df.empty:
        fig.add_hrect(y0=-30, y1=-10, fillcolor="rgba(239,83,80,0.10)", line_width=0, row=1, col=1)
        fig.add_hrect(y0=10, y1=30, fillcolor="rgba(38,166,154,0.10)", line_width=0, row=1, col=1)
        fig.add_trace(
            go.Scatter(
                x=cot_df["date"],
                y=cot_df["long_as_pct_oi"],
                mode="lines",
                name="Long % OI",
                line=dict(color=LT_GREEN, width=2.0, shape="spline", smoothing=0.7),
                opacity=0.8,
                hovertemplate="%{x|%Y-%m-%d}<br>Long % OI: %{y:.2f}%<extra></extra>",
            ),
            row=1,
            col=1,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=cot_df["date"],
                y=cot_df["short_as_pct_oi"],
                mode="lines",
                name="Short % OI",
                line=dict(color=RED, width=2.0, shape="spline", smoothing=0.7),
                opacity=0.8,
                hovertemplate="%{x|%Y-%m-%d}<br>Short % OI: %{y:.2f}%<extra></extra>",
            ),
            row=1,
            col=1,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=cot_df["date"],
                y=cot_df["net_as_pct_oi"],
                mode="lines",
                name="Net % OI",
                line=dict(color=BLUE, width=2.5),
                hovertemplate="%{x|%Y-%m-%d}<br>%{y:.2f}%<extra></extra>",
            ),
            row=1,
            col=1,
            secondary_y=False,
        )
        latest = cot_df.iloc[-1]
        fig.add_trace(
            go.Scatter(
                x=[latest["date"]],
                y=[latest["net_as_pct_oi"]],
                mode="markers+text",
                text=[f"Current {latest['net_as_pct_oi']:.1f}%"],
                textposition="top right",
                marker=dict(size=11, color=YELLOW, line=dict(color=TEXT, width=1)),
                name="Current",
                showlegend=False,
            ),
            row=1,
            col=1,
            secondary_y=False,
        )
        if not spx_series.empty:
            aligned_spx = _clean_series(spx_series)
            fig.add_trace(
                go.Scatter(
                    x=aligned_spx.index,
                    y=aligned_spx.values,
                    mode="lines",
                    name="SPX",
                    line=dict(color=YELLOW, width=2.0),
                    opacity=0.85,
                    hovertemplate="%{x|%Y-%m-%d}<br>SPX: %{y:.0f}<extra></extra>",
                ),
                row=1,
                col=1,
                secondary_y=True,
            )
            fig.update_yaxes(title_text="SPX", row=1, col=1, secondary_y=True)
        fig.update_yaxes(title_text="% of Open Interest", row=1, col=1, secondary_y=False)

    if not ratio_df.empty:
        above = ratio_df["ratio"].where(ratio_df["ratio"] >= ratio_df["ma20"])
        below = ratio_df["ratio"].where(ratio_df["ratio"] < ratio_df["ma20"])
        fig.add_trace(
            go.Scatter(x=ratio_df.index, y=above, mode="lines", name="Ratio > 20D MA", line=dict(color=LT_GREEN, width=2.5)),
            row=2,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=ratio_df.index, y=below, mode="lines", name="Ratio < 20D MA", line=dict(color=RED, width=2.5)),
            row=2,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=ratio_df.index, y=ratio_df["ma20"], mode="lines", name="20D MA", line=dict(color=MUTED, width=1.6, dash="dash")),
            row=2,
            col=1,
        )
        latest_ratio = float(ratio_df["ratio"].iloc[-1])
        latest_ma = float(ratio_df["ma20"].iloc[-1])
        regime = "RISK-ON" if latest_ratio > latest_ma else "RISK-OFF"
        regime_color = LT_GREEN if latest_ratio > latest_ma else RED
        fig.add_annotation(
            x=ratio_df.index[-1],
            y=latest_ratio,
            xref="x2",
            yref="y2",
            text=f"{latest_ratio:.3f} | {regime}",
            showarrow=True,
            arrowcolor=regime_color,
            font=dict(color=regime_color, size=11),
            bgcolor="rgba(13,17,23,0.85)",
            bordercolor=regime_color,
            row=2,
            col=1,
        )
        fig.update_yaxes(title_text="XLY / XLP", row=2, col=1)

    usable = [item for item in components if item["weighted_score"] is not None]
    if usable:
        usable = list(reversed(usable))
        fig.add_trace(
            go.Bar(
                x=[item["weighted_score"] for item in usable],
                y=[item["name"] for item in usable],
                orientation="h",
                marker=dict(color=[LT_GREEN if (item["z"] or 0) >= 0 else RED for item in usable]),
                text=[f"w={item['weight']:.0%} | z={item['z']:.2f}" if item['z'] is not None else f"w={item['weight']:.0%} | z=N/A" for item in usable],
                textposition="outside",
                name="Contribution",
                hovertemplate="%{y}<br>Contribution: %{x:.2f}<extra></extra>",
                showlegend=False,
            ),
            row=3,
            col=1,
        )
        fig.update_xaxes(title_text="Weighted Score Contribution", row=3, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(color=TEXT, family="Segoe UI, Arial, sans-serif", size=12),
        height=1240,
        margin=dict(l=65, r=40, t=70, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def build_dashboard() -> tuple[Path, dict]:
    load_keys("paper")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    today = datetime.now()
    end_date = today.strftime("%Y-%m-%d")
    last_updated = today.strftime("%Y-%m-%d %I:%M %p CT")

    cot_df, cot_error = fetch_cot_data()
    ratio_df = fetch_xly_xlp_ratio("2023-01-01", end_date)
    spx_series = fetch_spx_series("2023-01-01", end_date)

    fred_payload = {"hy": pd.Series(dtype=float), "curve": pd.Series(dtype=float), "vix": pd.Series(dtype=float)}
    fred_errors = {}
    for key, series_id in [("hy", "BAMLH0A0HYM2"), ("curve", "T10Y2Y"), ("vix", "VIXCLS")]:
        try:
            fred_payload[key] = fetch_fred_series(series_id)
        except Exception as exc:
            fred_errors[key] = str(exc)

    components = build_component_payload(cot_df, ratio_df, fred_payload)
    usable_scores = [item["weighted_score"] for item in components if item["weighted_score"] is not None]
    score = round(sum(usable_scores), 1) if usable_scores else None
    label, score_color = _score_label(score)
    history_df = build_daily_score_history(cot_df, ratio_df, fred_payload)
    history_chart = build_history_chart(history_df)
    flip_box = build_regime_flip_box(score, components)

    main_fig = build_main_figure(cot_df, ratio_df, spx_series, components)
    chart_html = main_fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False, "responsive": True})

    hy_series = fred_payload["hy"]
    curve_series = fred_payload["curve"]
    vix_series = fred_payload["vix"]
    cot_series = pd.Series(dtype=float) if cot_df.empty else cot_df.set_index("date")["z_score_52w"]

    hy_change = _diff_change(hy_series, 5)
    curve_change = _diff_change(curve_series, 5)
    vix_change = _diff_change(vix_series, 5)
    cot_change = _diff_change(cot_series, 1)

    hy_color = GREEN if hy_change is not None and hy_change < 0 else RED
    curve_color = GREEN if curve_change is not None and curve_change > 0 else RED
    vix_color = GREEN if vix_change is not None and vix_change < 0 else RED
    cot_color = GREEN if (components[0]["z"] or 0) > 0 else RED

    macro_cards = "".join([
        build_macro_card(
            "HY Credit Spread",
            _fmt_value(hy_series.iloc[-1] if not hy_series.empty else None, "%", 2),
            _fmt_value(hy_change, " pts", 2),
            _sparkline_svg(hy_series.tail(30), hy_color),
            hy_color,
            "Lower spreads = cleaner credit backdrop for systematic buyers." if not hy_series.empty else fred_errors.get("hy", "Data unavailable"),
        ),
        build_macro_card(
            "2s10s Yield Curve",
            _fmt_value(curve_series.iloc[-1] if not curve_series.empty else None, "%", 2),
            _fmt_value(curve_change, " pts", 2),
            _sparkline_svg(curve_series.tail(30), curve_color),
            curve_color,
            "Steeper curve usually aligns with easier growth expectations." if not curve_series.empty else fred_errors.get("curve", "Data unavailable"),
        ),
        build_macro_card(
            "VIX",
            _fmt_value(vix_series.iloc[-1] if not vix_series.empty else None, "", 1),
            _fmt_value(vix_change, " pts", 2),
            _sparkline_svg(vix_series.tail(30), vix_color),
            vix_color,
            "Context only: falling vol helps trend persistence, rising vol compresses it." if not vix_series.empty else fred_errors.get("vix", "Data unavailable"),
        ),
        build_macro_card(
            "COT Z-Score",
            _fmt_value(components[0]["z"], "", 2),
            _fmt_value(cot_change, " z", 2),
            build_cot_gauge(components[0]["z"], cot_color),
            cot_color,
            "Higher = more systematic long exposure. Deep negatives can become contrarian fuel." if cot_error is None else f"COT download fallback: {cot_error}",
        ),
    ])

    cot_source = None if cot_df.empty else cot_df["source"].iloc[-1]
    cot_note = (
        "COT download unavailable. Composite score is using available components only."
        if cot_df.empty else
        "COT panel uses last 104 weekly observations from E-MINI S&P 500 non-commercial positioning."
        if cot_source == "cftc" else
        "COT panel is using a Titan weekly spec-position proxy because the official CFTC archive endpoint is unavailable today."
    )

    cot_implication = "COT data unavailable, so there is no direct read on whether systematic futures funds are already heavily long or short."
    cot_stats_html = "<span>Current: N/A</span><span>Z-Score: N/A</span><span>Zone: Unavailable</span>"
    if not cot_df.empty:
        latest_cot = cot_df.iloc[-1]
        cot_net = float(latest_cot["net_as_pct_oi"])
        long_pct = float(latest_cot["long_as_pct_oi"])
        short_pct = float(latest_cot["short_as_pct_oi"])
        cot_z = components[0]["z"]
        cot_zone = "Max Short / squeeze fuel" if cot_net <= -10 else ("Max Long / crowded" if cot_net >= 10 else "Middle zone")
        cot_4w = _diff_change(cot_df.set_index("date")["net_as_pct_oi"], 4)
        long_4w = _diff_change(cot_df.set_index("date")["long_as_pct_oi"], 4)
        short_4w = _diff_change(cot_df.set_index("date")["short_as_pct_oi"], 4)
        flow_read = describe_cot_flow(long_4w, short_4w)
        positioning_trend_table = build_positioning_trend_table(long_4w, short_4w, cot_4w)
        cot_stats_html = (
            f"<span>Net % OI: {cot_net:.1f}%</span>"
            f"<span>Long % OI: {long_pct:.1f}%</span>"
            f"<span>Short % OI: {short_pct:.1f}%</span>"
            f"<span>Z-Score: {_fmt_value(cot_z, '', 2)}</span>"
            f"<span>4W Change: {_fmt_value(cot_4w, ' pts', 1)}</span>"
        )
        if cot_net <= -10:
            cot_implication = f"Systematic futures positioning is still in a washed-out zone at {cot_net:.1f}% of OI. That means the market already carries a lot of short exposure, so fresh downside may need new macro stress while upside squeezes can accelerate faster than expected. <br><br><strong>Flow read:</strong> {flow_read}"
        elif cot_net >= 10:
            cot_implication = f"Systematic futures positioning is crowded long at {cot_net:.1f}% of OI. That is a supportive tape until it breaks, but it also means good news may be more fully priced and reversals can hit harder. <br><br><strong>Flow read:</strong> {flow_read}"
        else:
            cot_implication = f"Net positioning sits in the middle at {cot_net:.1f}% of OI, which means CTAs are not at an extreme. In this regime, price follow-through depends more on trend persistence than on forced positioning unwind. <br><br><strong>Flow read:</strong> {flow_read}"
    else:
        positioning_trend_table = build_positioning_trend_table(None, None, None)

    ratio_implication = "XLY/XLP ratio unavailable, so there is no live market-based read on cyclical appetite versus defensives."
    ratio_stats_html = "<span>Ratio: N/A</span><span>20D MA: N/A</span><span>Regime: Unavailable</span>"
    if not ratio_df.empty:
        latest_ratio = float(ratio_df["ratio"].iloc[-1])
        latest_ma = float(ratio_df["ma20"].iloc[-1])
        ratio_gap = ((latest_ratio / latest_ma) - 1) * 100 if latest_ma else None
        ratio_z = components[1]["z"]
        ratio_regime = "Risk-On" if latest_ratio > latest_ma else "Risk-Off"
        ratio_stats_html = (
            f"<span>Ratio: {latest_ratio:.3f}</span>"
            f"<span>20D MA: {latest_ma:.3f}</span>"
            f"<span>Z-Score: {_fmt_value(ratio_z, '', 2)}</span>"
        )
        if latest_ratio > latest_ma:
            ratio_implication = f"Discretionary is beating Staples, with the ratio {ratio_gap:+.1f}% above its 20-day average. That is the market saying it prefers cyclicality and growth sensitivity over safety."
        else:
            ratio_implication = f"Staples are holding up better than Discretionary, with the ratio {ratio_gap:+.1f}% versus its 20-day average. That is a defensive tell and usually means the market is not fully trusting the risk-on narrative."

    components_html = "".join(
        f"<div class='component-line'><strong>{item['name']}</strong><span>w={item['weight']:.0%} | z={_fmt_value(item['z'], '', 2)} | score={_fmt_value(item['component_score'], '', 2)}</span><em>{item['note']}</em></div>"
        for item in components
    )

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Diet CTA Dashboard</title>
            <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
      <style>
        body {{ margin: 0; background: radial-gradient(circle at top, #152033 0%, {BG} 42%, #080b10 100%); color: {TEXT}; font-family: Segoe UI, Arial, sans-serif; }}
        .wrap {{ max-width: 1480px; margin: 0 auto; padding: 28px 24px 40px; }}
        .hero {{ display: flex; justify-content: space-between; align-items: end; gap: 18px; margin-bottom: 22px; }}
        .hero h1 {{ margin: 0; font-size: 34px; }}
        .hero p {{ margin: 8px 0 0; color: {MUTED}; max-width: 940px; line-height: 1.45; }}
        .panel {{ background: linear-gradient(180deg, rgba(22,27,34,0.96) 0%, rgba(13,17,23,0.98) 100%); border: 1px solid {BORDER}; border-radius: 18px; padding: 18px; box-shadow: 0 10px 28px rgba(0,0,0,0.22); margin-bottom: 22px; }}
        .score-card {{ text-align: center; padding: 24px 18px 16px; }}
        .score-topline {{ font-size: 13px; color: {MUTED}; letter-spacing: 2px; text-transform: uppercase; }}
        .score-value {{ font-size: 86px; font-weight: 800; line-height: 1; margin: 8px 0 10px; }}
        .score-label {{ font-size: 22px; font-weight: 700; margin-bottom: 10px; }}
        .score-subtitle {{ color: {MUTED}; font-size: 14px; margin-bottom: 18px; }}
        .mini-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 10px; margin-top: 12px; }}
        .mini-row {{ padding: 12px 14px; border: 1px solid {BORDER}; border-radius: 12px; background: rgba(255,255,255,0.025); text-align: left; }}
        .mini-row span {{ display: block; color: {MUTED}; font-size: 11px; margin-bottom: 6px; }}
        .mini-row strong {{ font-size: 18px; }}
        .last-updated {{ margin-top: 14px; color: {MUTED}; font-size: 12px; }}
        .score-lower {{ display:grid; grid-template-columns: 1.15fr 1fr; gap: 16px; margin-top: 16px; text-align:left; }}
        .history-card, .flip-box {{ border: 1px solid {BORDER}; border-radius: 14px; padding: 14px; background: rgba(255,255,255,0.025); }}
        .history-title, .flip-title {{ font-size: 12px; letter-spacing: 1px; text-transform: uppercase; color: {MUTED}; margin-bottom: 10px; }}
        .history-empty {{ color: {MUTED}; font-size: 12px; }}
        .history-subtitle {{ color: {MUTED}; font-size: 12px; margin-bottom: 8px; line-height: 1.4; }}
        .flip-body {{ font-size: 13px; line-height: 1.5; color: {TEXT}; }}
        .flip-foot {{ margin-top: 10px; color: {MUTED}; font-size: 12px; }}
        .macro-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 16px; }}
        .imp-grid {{ display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 16px; margin-top: 14px; }}
        .imp-card {{ border: 1px solid {BORDER}; border-radius: 14px; padding: 14px; background: rgba(255,255,255,0.025); }}
        .imp-title {{ font-size: 12px; letter-spacing: 1px; text-transform: uppercase; color: {MUTED}; margin-bottom: 8px; }}
        .imp-stats {{ display:flex; flex-wrap:wrap; gap: 8px 14px; margin-bottom: 8px; }}
        .imp-stats span {{ font-size: 12px; color: {TEXT}; padding: 6px 10px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.03); }}
        .imp-body {{ font-size: 13px; line-height: 1.5; color: {TEXT}; }}
        .trend-table-wrap {{ margin-top: 14px; border: 1px solid {BORDER}; border-radius: 14px; padding: 14px; background: rgba(255,255,255,0.025); }}
        .trend-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
        .trend-table th, .trend-table td {{ padding: 10px 8px; border-top: 1px solid rgba(255,255,255,0.06); text-align: left; vertical-align: top; }}
        .trend-table thead th {{ border-top: none; color: {MUTED}; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-size: 11px; }}
        .trend-arrow {{ font-size: 18px; font-weight: 800; width: 24px; }}
        .macro-card {{ border: 1px solid {BORDER}; border-radius: 14px; padding: 14px; background: rgba(255,255,255,0.025); }}
        .macro-title {{ font-size: 12px; letter-spacing: 1px; text-transform: uppercase; color: {MUTED}; margin-bottom: 8px; }}
        .macro-value {{ font-size: 28px; font-weight: 800; margin-bottom: 4px; }}
        .macro-change {{ font-size: 12px; color: {MUTED}; margin-bottom: 6px; }}
        .macro-note {{ font-size: 12px; color: {TEXT}; line-height: 1.45; }}
        .macro-spark {{ min-height: 46px; margin: 6px 0 8px; }}
        .gauge-wrap {{ display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 42px; margin: 8px 0 10px; }}
        .gauge-arrow {{ font-size: 30px; font-weight: 800; }}
        .gauge-desc {{ font-size: 12px; color: {MUTED}; margin-top: 4px; }}
        .section-head {{ display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 12px; }}
        .section-head h2 {{ margin: 0; font-size: 22px; }}
        .section-note {{ color: {MUTED}; font-size: 13px; line-height: 1.45; }}
        .component-explain {{ display: grid; gap: 10px; margin-top: 12px; }}
        .component-line {{ padding: 12px 14px; border-radius: 12px; border: 1px solid {BORDER}; background: rgba(255,255,255,0.02); }}
        .component-line strong {{ display: block; font-size: 14px; margin-bottom: 4px; }}
        .component-line span {{ display: block; color: {MUTED}; font-size: 12px; margin-bottom: 6px; }}
        .component-line em {{ font-style: normal; color: {TEXT}; font-size: 12px; line-height: 1.4; }}
        @media (max-width: 980px) {{ .mini-grid, .macro-grid, .score-lower, .imp-grid {{ grid-template-columns: 1fr; }} .hero {{ flex-direction: column; align-items: flex-start; }} }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="hero">
          <div>
            <h1>Diet CTA Dashboard</h1>
            <p>Morning macro regime approximation of systematic positioning using COT futures exposure, XLY/XLP risk appetite, high-yield spreads, and the 2s10s curve. Built to show whether systematic funds are likely a tailwind, headwind, or already stretched.</p>
          </div>
        </div>
        <div class="panel">
          {build_score_card(score, label, score_color, components, last_updated)}
                    <div class="score-lower">
                        <div class="history-card">
                            <div class="history-title">Last 10 Daily Scores</div>
                            <div class="history-subtitle">Bar view of the last 10 business-day closes for the composite score, with regime bands in the background.</div>
                            {history_chart}
                        </div>
                        {flip_box}
                    </div>
        </div>
        <div class="panel">
          <div class="section-head">
            <h2>Positioning + Risk Appetite</h2>
            <div class="section-note">{cot_note}</div>
          </div>
          {chart_html}
                    <div class="imp-grid">
                        {build_implication_card("What The COT Chart Indicates", cot_stats_html, cot_implication, BLUE)}
                        {build_implication_card("What The XLY/XLP Chart Indicates", ratio_stats_html, ratio_implication, LT_GREEN if not ratio_df.empty and float(ratio_df['ratio'].iloc[-1]) > float(ratio_df['ma20'].iloc[-1]) else RED)}
                    </div>
                    {positioning_trend_table}
        </div>
        <div class="panel">
          <div class="section-head">
            <h2>Macro Signal Cards</h2>
            <div class="section-note">Green means improving in the risk-on direction. Red means deterioration or tighter systematic conditions.</div>
          </div>
          <div class="macro-grid">{macro_cards}</div>
        </div>
        <div class="panel">
          <div class="section-head">
            <h2>How To Read The Components</h2>
            <div class="section-note">Each component is clamped to a [-3, +3] z-range, mapped to a [1, 10] score, and then weighted into the final Diet CTA score.</div>
          </div>
          <div class="component-explain">{components_html}</div>
        </div>
      </div>
    </body>
    </html>
    """

    OUTPUT_FILE.write_text(html, encoding="utf-8")
    return OUTPUT_FILE, {
        "score": score,
        "label": label,
        "components": components,
        "history": history_df,
        "cot_error": cot_error,
        "fred_errors": fred_errors,
        "last_updated": last_updated,
    }


def main() -> tuple[Path, dict]:
    output_file, payload = build_dashboard()
    print(f"Diet CTA Score: {_fmt_value(payload['score'], '', 1)} | {payload['label']}")
    print(f"Dashboard saved to: {output_file}")
    return output_file, payload


if __name__ == "__main__":
    main()