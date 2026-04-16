"""
QUANTLAB STUDY — CYAN OPENING BAR + RISING TSL WIN RATE
=========================================================
File: studies/cyan_open_rising_tsl/run_study.py

CORE QUESTION:
Does a stock that opens the session with a cyan candle (cs >= 70)
AND rising TSL (slope > 0.25) have a statistically meaningful
upside edge for the rest of that session?

WARMUP STRATEGY:
  Load data from LOAD_START (well before study start) so both indicators
  are warm before any opening bar is evaluated. No 20-bar session skip —
  the whole point is to capture the open.

2x2 COMPARISON GROUPS:
  A: Cyan open + Rising TSL       (primary signal)
  B: Cyan open, TSL NOT rising    (cyan alone)
  C: NOT cyan, Rising TSL         (TSL alone)
  D: Neither                      (baseline)
"""

import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "shared"))

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from datetime import datetime, time as dtime

from shared.data_router import DataRouter
from shared.indicators.trend_strength_candles import TrendStrengthCandles
from shared.indicators.trend_strength_line import TrendStrengthLine

# ── paths ─────────────────────────────────────────────────────────────────────
STUDY_DIR   = Path(__file__).parent
OUTPUTS_DIR = STUDY_DIR / "outputs"
CHARTS_DIR  = OUTPUTS_DIR / "charts"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

SIGNALS_PATH = OUTPUTS_DIR / "open_signals.csv"

# ── parameters ─────────────────────────────────────────────────────────────────
UNIVERSE = [
    "NVDA", "AMD",  "TSLA", "AAPL", "MSFT", "META",  "GOOGL", "AMZN",
    "SMCI", "MSTR", "COIN", "PLTR", "SOFI", "HOOD",  "ARM",   "AVGO",
    "MU",   "NFLX", "SPY",  "QQQ",
]

HIGH_QUALITY = {"MSFT", "ARM", "QQQ", "MU", "AVGO", "MSTR", "SPY", "NVDA"}
LOW_QUALITY  = {"META", "PLTR", "TSLA", "AMZN"}
MIDDLE       = {"GOOGL", "AAPL", "NFLX", "SMCI", "SOFI", "COIN", "HOOD", "AMD"}

# Alpaca IEX 5-min data returns ~25 bars/day; at that rate, indicators
# warm up (200 bars) in ~8 trading days. Load the full study window and
# accept that opening bar signals in the first ~8 trading days (≈Nov 1-12)
# will be excluded via the NaN guard in _compute_signals.
LOAD_START  = "2024-11-01"   # same as STUDY_START — IEX lookback is reliable here
STUDY_START = "2024-11-01"
STUDY_END   = "2025-02-28"
TIMEFRAME   = "5min"

FWD_WINDOWS = [6, 12, 24]    # bars
OPEN_WINDOW_START = dtime(9, 30)
OPEN_WINDOW_END   = dtime(10, 0)   # exclusive — bars < 10:00


# ── helpers ────────────────────────────────────────────────────────────────────

def _normalise_cols(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for c in df.columns:
        lc = c.lower()
        if lc == "open":   rename[c] = "Open"
        elif lc == "high":  rename[c] = "High"
        elif lc == "low":   rename[c] = "Low"
        elif lc == "close": rename[c] = "Close"
        elif lc in ("volume", "vol"): rename[c] = "Volume"
    return df.rename(columns=rename)


def _to_et(df: pd.DataFrame) -> pd.DataFrame:
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex):
        idx = pd.DatetimeIndex(idx)
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    df = df.copy()
    df.index = idx.tz_convert("America/New_York")
    return df


def assign_open_bucket(ts: pd.Timestamp) -> str | None:
    t = ts.time()
    if dtime(9, 30) <= t < dtime(9, 35):  return "FIRST_BAR"
    if dtime(9, 35) <= t < dtime(9, 45):  return "EARLY_OPEN"
    if dtime(9, 45) <= t < dtime(10, 0):  return "OPEN_WINDOW"
    return None


def assign_ticker_quality(ticker: str) -> str:
    if ticker in HIGH_QUALITY: return "HIGH"
    if ticker in LOW_QUALITY:  return "LOW"
    return "MIDDLE"


def assign_group(cyan: bool, rising: bool) -> str:
    if cyan and rising:      return "A"
    if cyan and not rising:  return "B"
    if not cyan and rising:  return "C"
    return "D"


# ── forward return helpers ─────────────────────────────────────────────────────

def _compute_signals(
    df_et: pd.DataFrame,
    ticker: str,
) -> list[dict]:
    """
    Walk every bar in the opening window for each date.
    Compute forward returns, EOD return, and session MFE/MAE.
    """
    study_start_dt = pd.Timestamp(STUDY_START, tz="America/New_York")
    study_end_dt   = pd.Timestamp(STUDY_END,   tz="America/New_York") + pd.Timedelta(days=1)

    close  = df_et["Close"].values
    open_  = df_et["Open"].values
    high   = df_et["High"].values
    low    = df_et["Low"].values
    cs_arr = df_et["cs"].values
    slope_arr  = df_et["slope_value"].values
    cyan_arr   = df_et["cyan_signal"].values
    rising_arr = df_et["is_rising"].values
    n = len(df_et)

    # Build date → positional range map for EOD / session MFE/MAE lookups
    dates = df_et.index.normalize()
    date_groups: dict[pd.Timestamp, list[int]] = {}
    for i, d in enumerate(dates):
        date_groups.setdefault(d, []).append(i)

    quality = assign_ticker_quality(ticker)
    rows = []

    for i, ts in enumerate(df_et.index):
        # Only study window dates
        if ts < study_start_dt or ts >= study_end_dt:
            continue

        bucket = assign_open_bucket(ts)
        if bucket is None:
            continue

        # Skip bars where indicators haven't warmed up (NaN cs or slope)
        if np.isnan(cs_arr[i]) or np.isnan(slope_arr[i]):
            continue

        cyan   = bool(cyan_arr[i])
        rising = bool(rising_arr[i])
        group  = assign_group(cyan, rising)

        # Entry = open of bar i+1
        entry_i = i + 1
        if entry_i >= n:
            continue
        entry_price = open_[entry_i]
        if entry_price <= 0 or np.isnan(entry_price):
            continue

        # ── forward returns at fixed bar offsets ──────────────────────────
        fwd = {}
        max_w = max(FWD_WINDOWS)
        for w in FWD_WINDOWS:
            tgt = i + w
            if tgt >= n:
                fwd[f"return_{w}bar"] = np.nan
                fwd[f"win_{w}bar"]    = np.nan
            else:
                ret = (close[tgt] - entry_price) / entry_price
                fwd[f"return_{w}bar"] = ret
                fwd[f"win_{w}bar"]    = int(ret > 0)

        # ── EOD return + session MFE / MAE ────────────────────────────────
        day_key = ts.normalize()
        session_positions = date_groups.get(day_key, [])

        # Session positions AFTER entry bar
        after_entry = [j for j in session_positions if j >= entry_i]

        if after_entry:
            last_j       = session_positions[-1]
            eod_close    = close[last_j]
            ret_eod      = (eod_close - entry_price) / entry_price
            win_eod      = int(ret_eod > 0)

            session_highs = high[after_entry[0]: after_entry[-1] + 1]
            session_lows  = low[after_entry[0]:  after_entry[-1] + 1]
            mfe_session = (float(np.nanmax(session_highs)) - entry_price) / entry_price
            mae_session = (entry_price - float(np.nanmin(session_lows))) / entry_price
        else:
            ret_eod = win_eod = np.nan
            mfe_session = mae_session = np.nan

        rows.append({
            "ticker":           ticker,
            "signal_time":      ts.isoformat(),
            "signal_bar_bucket": bucket,
            "entry_price":      round(entry_price, 4),
            "cs_score":         round(float(cs_arr[i]), 4),
            "slope_value":      round(float(slope_arr[i]), 6),
            "group":            group,
            "ticker_quality":   quality,
            **fwd,
            "return_eod":   ret_eod,
            "win_eod":      win_eod,
            "mfe_session":  mfe_session,
            "mae_session":  mae_session,
        })

    return rows


# ── per-ticker pipeline ────────────────────────────────────────────────────────

def process_ticker(ticker: str) -> pd.DataFrame | None:
    print(f"  Fetching {ticker} …", end=" ", flush=True)
    try:
        raw = DataRouter.get_price_data(
            ticker,
            start_date = LOAD_START,
            end_date   = STUDY_END,
            timeframe  = TIMEFRAME,
            study_type = "indicator",
        )
    except Exception as exc:
        print(f"✗ fetch failed: {exc}")
        return None

    if raw is None or raw.empty:
        print("✗ no data")
        return None

    df = _normalise_cols(raw)
    required = {"Open", "High", "Low", "Close"}
    if not required.issubset(df.columns):
        print("✗ missing OHLC columns")
        return None

    df = df[df["Close"].notna() & (df["Close"] > 0)].copy()
    if len(df) < 300:
        print(f"✗ only {len(df)} bars")
        return None

    # ── apply indicators on the FULL series (warmup included) ────────────
    candle_ind = TrendStrengthCandles()
    df_c = candle_ind.compute(df)

    tsl_ind = TrendStrengthLine()
    df_t = tsl_ind.compute(df)

    df_full = df.copy()
    df_full["cs"]          = df_c["cs"].values
    df_full["cyan_signal"] = df_c["cyan_signal"].values
    df_full["is_nr7"]      = df_c["is_nr7"].values
    df_full["slope_value"] = df_t["slope"].values
    df_full["is_rising"]   = df_t["is_rising"].values

    df_et = _to_et(df_full)

    # ── evaluate opening window signals ───────────────────────────────────
    rows = _compute_signals(df_et, ticker)

    group_counts = {}
    for r in rows:
        g = r["group"]
        group_counts[g] = group_counts.get(g, 0) + 1

    total = len(rows)
    a = group_counts.get("A", 0)
    b = group_counts.get("B", 0)
    c = group_counts.get("C", 0)
    d = group_counts.get("D", 0)
    print(f"{total} opening bars  (A={a} B={b} C={c} D={d})")

    if not rows:
        return None
    return pd.DataFrame(rows)


# ── summary writers ────────────────────────────────────────────────────────────

def _wr(sub: pd.DataFrame, win_col: str) -> str:
    s = sub[sub[win_col].notna()]
    if s.empty:
        return "  n/a"
    return f"{s[win_col].mean()*100:5.1f}%  (n={len(s)})"


def _ret(sub: pd.DataFrame, ret_col: str) -> str:
    s = sub[ret_col].dropna()
    if s.empty:
        return "  n/a"
    return f"avg {s.mean()*100:+.3f}%  med {s.median()*100:+.3f}%"


def write_group_comparison(df: pd.DataFrame, path: Path) -> None:
    windows = [(6, "return_6bar", "win_6bar"),
               (12, "return_12bar", "win_12bar"),
               (24, "return_24bar", "win_24bar"),
               ("EOD", "return_eod", "win_eod")]

    lines = ["=" * 72,
             "GROUP COMPARISON — OPENING BAR SIGNALS",
             f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
             "Groups: A=Cyan+Rising  B=Cyan-only  C=Rising-only  D=Neither(baseline)",
             "=" * 72, ""]

    for w, rcol, wcol in windows:
        label = f"{w}-bar ({w*5} min)" if isinstance(w, int) else "End-of-Day"
        lines.append(f"  Window: {label}")
        lines.append(f"  {'Group':<8} {'WinRate':>10}  {'Returns':>30}")
        lines.append(f"  {'-'*55}")
        for g in ["A", "B", "C", "D"]:
            sub = df[df["group"] == g]
            lines.append(f"  {g:<8} {_wr(sub, wcol):>10}  {_ret(sub, rcol):>30}")
        lines.append("")

    # flag if Group A is small
    n_a = len(df[df["group"] == "A"])
    if n_a < 100:
        lines.append(f"  ⚠  Group A n={n_a} — BORDERLINE SAMPLE SIZE (<100)")
    else:
        lines.append(f"  Group A total signals: {n_a}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ Saved {path.name}")


def write_open_bucket_summary(df: pd.DataFrame, path: Path) -> None:
    sub_a = df[df["group"] == "A"]
    windows = [(6, "win_6bar"), (12, "win_12bar"), (24, "win_24bar"), ("EOD", "win_eod")]
    buckets = ["FIRST_BAR", "EARLY_OPEN", "OPEN_WINDOW"]

    lines = ["=" * 72,
             "OPEN BUCKET WIN RATES — Group A (Cyan + Rising TSL) Only",
             f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
             "=" * 72, ""]

    for bkt in buckets:
        sub = sub_a[sub_a["signal_bar_bucket"] == bkt]
        lines.append(f"  {bkt}  (total n={len(sub)})")
        for w, wcol in windows:
            label = f"{w*5} min" if isinstance(w, int) else "EOD"
            lines.append(f"    {label:>8}  {_wr(sub, wcol)}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ Saved {path.name}")


def write_ticker_quality_summary(df: pd.DataFrame, path: Path) -> None:
    sub_a = df[df["group"] == "A"]
    windows = [(6, "win_6bar"), (12, "win_12bar"), (24, "win_24bar"), ("EOD", "win_eod")]

    lines = ["=" * 72,
             "TICKER QUALITY TIER WIN RATES — Group A Only",
             f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
             f"  HIGH: {sorted(HIGH_QUALITY)}",
             f"  LOW:  {sorted(LOW_QUALITY)}",
             f"  MID:  {sorted(MIDDLE)}",
             "=" * 72, ""]

    for tier in ["HIGH", "MIDDLE", "LOW"]:
        sub = sub_a[sub_a["ticker_quality"] == tier]
        lines.append(f"  {tier} quality  (total n={len(sub)})")
        for w, wcol in windows:
            label = f"{w*5} min" if isinstance(w, int) else "EOD"
            lines.append(f"    {label:>8}  {_wr(sub, wcol)}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ Saved {path.name}")


def write_per_ticker_summary(df: pd.DataFrame, path: Path) -> None:
    sub_a = df[df["group"] == "A"].copy()
    lines = ["=" * 72,
             "PER-TICKER WIN RATES (12-bar) — Group A Only, Ranked",
             f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
             "=" * 72, ""]

    rows = []
    for tkr, g in sub_a.groupby("ticker"):
        s = g[g["win_12bar"].notna()]
        wr = s["win_12bar"].mean() * 100 if len(s) > 0 else np.nan
        rows.append((tkr, len(g), wr, assign_ticker_quality(tkr)))

    rows.sort(key=lambda x: (x[2] is np.nan, -(x[2] or 0)))

    lines.append(f"  {'Ticker':<8} {'n':>5}  {'12-bar WinRate':>15}  {'Quality'}")
    lines.append(f"  {'-'*50}")
    for tkr, n, wr, qual in rows:
        wr_str = f"{wr:5.1f}%" if not np.isnan(wr) else "  n/a"
        lines.append(f"  {tkr:<8} {n:>5}  {wr_str:>15}  {qual}")

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ Saved {path.name}")


# ── charts ─────────────────────────────────────────────────────────────────────

def _try_plotly():
    try:
        import plotly.graph_objects as go
        return go
    except ImportError:
        return None


def chart_group_comparison(df: pd.DataFrame, path: Path) -> None:
    go = _try_plotly()
    if not go:
        print(f"  ⚠ plotly not installed — skipping {path.name}")
        return

    groups = ["A", "B", "C", "D"]
    group_labels = {
        "A": "A: Cyan+Rising",
        "B": "B: Cyan Only",
        "C": "C: Rising Only",
        "D": "D: Baseline",
    }
    windows_map = [(6, "win_6bar", "30 min"), (12, "win_12bar", "60 min"),
                   (24, "win_24bar", "120 min"), ("EOD", "win_eod", "EOD")]
    colors = ["#26C6DA", "#66BB6A", "#FFA726", "#EF5350"]

    fig = go.Figure()
    for (w, wcol, wlabel), color in zip(windows_map, colors):
        wr_vals = []
        for g in groups:
            sub = df[(df["group"] == g) & df[wcol].notna()]
            wr_vals.append(sub[wcol].mean() * 100 if len(sub) > 0 else 0.0)
        fig.add_trace(go.Bar(
            name=wlabel,
            x=[group_labels[g] for g in groups],
            y=[round(v, 2) for v in wr_vals],
            marker_color=color,
            text=[f"{v:.1f}%" for v in wr_vals],
            textposition="outside",
        ))

    fig.add_hline(y=50, line_dash="dash", line_color="gray",
                  annotation_text="50% baseline")
    fig.update_layout(
        title="Opening Bar Win Rate — Group A vs B vs C vs D",
        yaxis_title="Win Rate (%)", xaxis_title="Signal Group",
        barmode="group", template="plotly_dark",
        height=540, yaxis_range=[0, 100],
    )
    fig.write_html(str(path))
    print(f"  ✓ Saved {path.name}")


def chart_open_bucket(df: pd.DataFrame, path: Path) -> None:
    go = _try_plotly()
    if not go:
        print(f"  ⚠ plotly not installed — skipping {path.name}")
        return

    sub_a = df[df["group"] == "A"]
    buckets = ["FIRST_BAR", "EARLY_OPEN", "OPEN_WINDOW"]
    windows_map = [(6, "win_6bar", "30 min"), (12, "win_12bar", "60 min"),
                   (24, "win_24bar", "120 min"), ("EOD", "win_eod", "EOD")]
    colors = ["#26C6DA", "#66BB6A", "#FFA726", "#EF5350"]

    fig = go.Figure()
    for (w, wcol, wlabel), color in zip(windows_map, colors):
        wr_vals = []
        for bkt in buckets:
            sub = sub_a[(sub_a["signal_bar_bucket"] == bkt) & sub_a[wcol].notna()]
            wr_vals.append(sub[wcol].mean() * 100 if len(sub) > 0 else 0.0)
        fig.add_trace(go.Bar(
            name=wlabel, x=buckets,
            y=[round(v, 2) for v in wr_vals],
            marker_color=color,
            text=[f"{v:.1f}%" for v in wr_vals],
            textposition="outside",
        ))

    fig.add_hline(y=50, line_dash="dash", line_color="gray",
                  annotation_text="50% baseline")
    fig.update_layout(
        title="Win Rate by Open Sub-Bucket — Group A (Cyan + Rising TSL)",
        yaxis_title="Win Rate (%)", xaxis_title="Open Bucket",
        barmode="group", template="plotly_dark",
        height=520, yaxis_range=[0, 100],
    )
    fig.write_html(str(path))
    print(f"  ✓ Saved {path.name}")


def chart_ticker_quality(df: pd.DataFrame, path: Path) -> None:
    go = _try_plotly()
    if not go:
        print(f"  ⚠ plotly not installed — skipping {path.name}")
        return

    sub_a = df[df["group"] == "A"]
    tiers = ["HIGH", "MIDDLE", "LOW"]
    windows_map = [(6, "win_6bar", "30 min"), (12, "win_12bar", "60 min"),
                   (24, "win_24bar", "120 min"), ("EOD", "win_eod", "EOD")]
    colors = ["#26C6DA", "#66BB6A", "#FFA726", "#EF5350"]

    fig = go.Figure()
    for (w, wcol, wlabel), color in zip(windows_map, colors):
        wr_vals = []
        for tier in tiers:
            sub = sub_a[(sub_a["ticker_quality"] == tier) & sub_a[wcol].notna()]
            wr_vals.append(sub[wcol].mean() * 100 if len(sub) > 0 else 0.0)
        fig.add_trace(go.Bar(
            name=wlabel, x=tiers,
            y=[round(v, 2) for v in wr_vals],
            marker_color=color,
            text=[f"{v:.1f}%" for v in wr_vals],
            textposition="outside",
        ))

    fig.add_hline(y=50, line_dash="dash", line_color="gray",
                  annotation_text="50% baseline")
    fig.update_layout(
        title="Win Rate by Ticker Quality Tier — Group A (Cyan + Rising TSL)",
        yaxis_title="Win Rate (%)", xaxis_title="Quality Tier",
        barmode="group", template="plotly_dark",
        height=520, yaxis_range=[0, 100],
    )
    fig.write_html(str(path))
    print(f"  ✓ Saved {path.name}")


def chart_eod_distribution(df: pd.DataFrame, path: Path) -> None:
    go = _try_plotly()
    if not go:
        print(f"  ⚠ plotly not installed — skipping {path.name}")
        return

    data = df[df["group"] == "A"]["return_eod"].dropna() * 100

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=data, nbinsx=80,
        marker_color="#26C6DA", opacity=0.85,
        name="EOD return",
    ))
    fig.add_vline(x=0, line_dash="dash", line_color="white")
    fig.add_vline(x=data.mean(), line_dash="dot", line_color="#FFA726",
                  annotation_text=f"mean {data.mean():.2f}%",
                  annotation_position="top right")
    fig.update_layout(
        title="End-of-Day Return Distribution — Group A (Cyan + Rising TSL at Open)",
        xaxis_title="EOD Return (%)", yaxis_title="Count",
        template="plotly_dark", height=480,
    )
    fig.write_html(str(path))
    print(f"  ✓ Saved {path.name}")


# ── console snapshot ───────────────────────────────────────────────────────────

def print_requested_numbers(df: pd.DataFrame) -> None:
    """Print the 7 specific numbers requested in the spec."""
    def wr(mask, wcol):
        s = df[mask & df[wcol].notna()]
        if s.empty: return "n/a", 0
        return f"{s[wcol].mean()*100:.1f}%", len(s)

    ga = df["group"] == "A"
    gb = df["group"] == "B"
    gc = df["group"] == "C"
    gd = df["group"] == "D"
    hq = df["ticker_quality"] == "HIGH"
    fb = df["signal_bar_bucket"] == "FIRST_BAR"

    n_a = ga.sum()
    flag = "  ⚠ BORDERLINE SAMPLE SIZE (<100)" if n_a < 100 else ""

    print("\n" + "=" * 72)
    print("  REQUESTED NUMBERS — STUDY SPEC §REPORT BACK")
    print("=" * 72)
    r, n = wr(ga, "win_12bar");   print(f"  1. Group A  12-bar win rate : {r}  (n={n})")
    r, n = wr(ga, "win_eod");     print(f"     Group A  EOD   win rate  : {r}  (n={n}){flag}")
    r, n = wr(gb, "win_12bar");   print(f"  2. Group B  12-bar win rate : {r}  (cyan only, no TSL)")
    r, n = wr(gc, "win_12bar");   print(f"  3. Group C  12-bar win rate : {r}  (TSL only, no cyan)")
    r, n = wr(gd, "win_12bar");   print(f"  4. Group D  12-bar win rate : {r}  (baseline)")
    r, n = wr(ga & hq, "win_12bar"); print(f"  5. Group A HIGH quality 12-bar : {r}  (n={n})")
    r, n = wr(ga & fb, "win_12bar"); print(f"  6. Group A FIRST_BAR only 12-bar: {r}  (n={n})")
    print(f"  7. Group A total signals    : {n_a}{flag}")
    print("=" * 72 + "\n")


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "=" * 72)
    print("  CYAN OPENING BAR + RISING TSL WIN RATE STUDY")
    print(f"  Universe: {len(UNIVERSE)} tickers  |  Study: {STUDY_START} → {STUDY_END}")
    print(f"  Load from: {LOAD_START}  |  Timeframe: {TIMEFRAME}")
    print(f"  Opening window: 09:30–10:00 ET  |  Groups: A/B/C/D")
    print("=" * 72)

    all_chunks: list[pd.DataFrame] = []
    header_written = False

    for idx, ticker in enumerate(UNIVERSE, 1):
        print(f"\n[{idx:>2}/{len(UNIVERSE)}] {ticker}")
        result = process_ticker(ticker)

        if result is not None and not result.empty:
            all_chunks.append(result)
            result.to_csv(
                SIGNALS_PATH,
                mode   = "a" if header_written else "w",
                header = not header_written,
                index  = False,
            )
            header_written = True

        if idx % 5 == 0:
            total_so_far = sum(len(c) for c in all_chunks)
            ga_so_far    = sum((c["group"] == "A").sum() for c in all_chunks)
            print(f"\n  >>> Progress: {idx}/{len(UNIVERSE)} tickers | "
                  f"{total_so_far:,} total opening bars | {ga_so_far} Group A <<<\n")

    if not all_chunks:
        print("\n✗ No signals collected.")
        return

    full = pd.concat(all_chunks, ignore_index=True)
    n_a = (full["group"] == "A").sum()

    print(f"\n{'=' * 72}")
    print(f"  TOTAL OPENING BARS : {len(full):,}")
    print(f"  Group A signals    : {n_a}")
    print(f"  Group B signals    : {(full['group']=='B').sum()}")
    print(f"  Group C signals    : {(full['group']=='C').sum()}")
    print(f"  Group D signals    : {(full['group']=='D').sum()}")
    if n_a < 100:
        print(f"  ⚠  Group A n={n_a} — BORDERLINE SAMPLE SIZE (<100)")
    print(f"{'=' * 72}\n")

    print("▷  Writing summaries …")
    write_group_comparison(full,       OUTPUTS_DIR / "summary_group_comparison.txt")
    write_open_bucket_summary(full,    OUTPUTS_DIR / "summary_by_open_bucket.txt")
    write_ticker_quality_summary(full, OUTPUTS_DIR / "summary_by_ticker_quality.txt")
    write_per_ticker_summary(full,     OUTPUTS_DIR / "summary_by_ticker.txt")

    print("▷  Building charts …")
    chart_group_comparison(full, CHARTS_DIR / "group_comparison.html")
    chart_open_bucket(full,      CHARTS_DIR / "open_bucket_winrates.html")
    chart_ticker_quality(full,   CHARTS_DIR / "ticker_quality_comparison.html")
    chart_eod_distribution(full, CHARTS_DIR / "eod_return_distribution.html")

    print_requested_numbers(full)

    print(f"✅  All outputs saved to: {OUTPUTS_DIR}")
    print(f"   open_signals.csv                  → {len(full):,} rows")
    print(f"   summary_group_comparison.txt")
    print(f"   summary_by_open_bucket.txt")
    print(f"   summary_by_ticker_quality.txt")
    print(f"   summary_by_ticker.txt")
    print(f"   charts/group_comparison.html")
    print(f"   charts/open_bucket_winrates.html")
    print(f"   charts/ticker_quality_comparison.html")
    print(f"   charts/eod_return_distribution.html\n")


if __name__ == "__main__":
    main()
