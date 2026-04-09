"""
Cyan Candle + Rising TSL Win Rate Study
========================================
Signal: cyan_signal=True (cs>=70 AND NOT nr7) AND is_rising=True (TSL slope>0.25)
Entry:  Open of bar N+1 (zero lookahead)
Universe: 20 tickers
Date Range: 2024-11-01 to 2025-02-28
Timeframe: 5-min bars via DataRouter (Alpaca)

FORWARD RETURN WINDOWS: 5, 10, 20 bars
Win = close[N+W] > entry_price

Warmup rules (per session):
  - Skip first 20 bars of each day (indicator warm-up)
  - Skip last 20 bars of each day (no full forward window guaranteed intra-day)
  Forward returns for kept signals use positional indexing across the series.
"""

import sys
import os
from pathlib import Path

# ── project root on path ──────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "shared"))   # data_router imports 'config.api_clients' bare

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from datetime import datetime

# ── lab imports ───────────────────────────────────────────────────────────────
from shared.data_router import DataRouter
from shared.indicators.trend_strength_candles import TrendStrengthCandles
from shared.indicators.trend_strength_line import TrendStrengthLine

# ── output dirs ───────────────────────────────────────────────────────────────
STUDY_DIR   = Path(__file__).parent
OUTPUTS_DIR = STUDY_DIR / "outputs"
CHARTS_DIR  = OUTPUTS_DIR / "charts"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# ── study parameters ──────────────────────────────────────────────────────────
UNIVERSE = [
    "NVDA", "AMD",  "TSLA", "AAPL", "MSFT", "META",  "GOOGL", "AMZN",
    "SMCI", "MSTR", "COIN", "PLTR", "SOFI", "HOOD",  "ARM",   "AVGO",
    "MU",   "NFLX", "SPY",  "QQQ",
]

START_DATE  = "2024-11-01"
END_DATE    = "2025-02-28"
TIMEFRAME   = "5min"
WARMUP_BARS = 20          # skip first N bars of each session
TAIL_BARS   = 20          # skip last N bars of each session (no fwd return)
FWD_WINDOWS = [5, 10, 20]

ALL_SIGNALS_PATH = OUTPUTS_DIR / "all_signals.csv"

# ── helper: ET time bucket ────────────────────────────────────────────────────
def assign_time_bucket(ts_et: pd.Timestamp) -> str:
    """Map an ET timestamp to a human-readable session bucket."""
    t = ts_et.time()
    from datetime import time as dtime
    if dtime(9,  30) <= t < dtime(9,  35):  return "Open_Bar"
    if dtime(9,  35) <= t < dtime(10, 30):  return "First_Hour"
    if dtime(10, 30) <= t < dtime(12,  0):  return "Mid_Morning"
    if dtime(12,  0) <= t < dtime(14,  0):  return "Midday"
    if dtime(14,  0) <= t < dtime(15,  0):  return "Power_Hour"
    if dtime(15,  0) <= t < dtime(15, 30):  return "Last_30"
    return "Other"

# ── helper: score bucket ──────────────────────────────────────────────────────
def assign_score_bucket(cs: float) -> str:
    if cs > 85:  return "Max_Bull"
    if cs >= 70: return "Strong_Bull"
    return "Below_Signal"

# ── helper: normalise column names from alpaca ────────────────────────────────
def _normalise_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure Open/High/Low/Close/Volume columns exist (title-case)."""
    rename_map = {}
    for col in df.columns:
        lc = col.lower()
        if lc == "open":   rename_map[col] = "Open"
        elif lc == "high":  rename_map[col] = "High"
        elif lc == "low":   rename_map[col] = "Low"
        elif lc == "close": rename_map[col] = "Close"
        elif lc in ("volume", "vol"): rename_map[col] = "Volume"
    return df.rename(columns=rename_map)

# ── helper: convert index to ET ───────────────────────────────────────────────
def _to_et(df: pd.DataFrame) -> pd.DataFrame:
    """Convert DatetimeIndex to America/New_York; returns new df."""
    idx = df.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    idx = idx.tz_convert("America/New_York")
    df = df.copy()
    df.index = idx
    return df

# ── per-session warmup / tail mask ────────────────────────────────────────────
def _valid_bar_mask(df_et: pd.DataFrame,
                    warmup: int = WARMUP_BARS,
                    tail: int   = TAIL_BARS) -> pd.Series:
    """
    Return boolean mask True for bars that are:
      - NOT within the first `warmup` bars of their calendar date
      - NOT within the last `tail` bars of their calendar date
    """
    dates = df_et.index.date
    valid = pd.Series(False, index=df_et.index)
    for d, grp in df_et.groupby(dates):
        if len(grp) <= warmup + tail:
            continue  # session too short — skip entirely
        idx_positions = range(len(grp))
        keep = [i for i in idx_positions if i >= warmup and i < len(grp) - tail]
        valid.loc[grp.index[keep]] = True
    return valid

# ── forward-return calculation ─────────────────────────────────────────────────
def _compute_forward_returns(
    df: pd.DataFrame,            # full series with Open/High/Low/Close (ET index)
    signal_indices: list[int],   # positional indices of signal bars
    windows: list[int],
) -> list[dict]:
    """
    For each signal bar at position i:
      entry_price = df["Open"].iloc[i + 1]
      return_W    = df["Close"].iloc[i + W] - entry_price   (W in windows)
      win_W       = return_W > 0
      mfe_20bar   = max(df["High"].iloc[i+1 : i+21]) - entry_price
      mae_20bar   = entry_price - min(df["Low"].iloc[i+1 : i+21])
    """
    rows = []
    close = df["Close"].values
    open_ = df["Open"].values
    high  = df["High"].values
    low   = df["Low"].values
    n     = len(df)
    max_w = max(windows)

    for i in signal_indices:
        entry_i = i + 1
        last_i  = i + max_w
        if entry_i >= n or last_i >= n:
            continue          # not enough future bars in data

        entry_price = open_[entry_i]
        if entry_price <= 0 or np.isnan(entry_price):
            continue

        row = {"_pos": i, "entry_price": entry_price}
        for w in windows:
            fwd_close = close[i + w]
            ret = (fwd_close - entry_price) / entry_price if entry_price else np.nan
            row[f"return_{w}bar"] = ret
            row[f"win_{w}bar"]    = int(ret > 0) if not np.isnan(ret) else np.nan

        # MFE / MAE over 20-bar window using High/Low
        fwd_slice_h = high[entry_i : entry_i + 20]
        fwd_slice_l = low[entry_i  : entry_i + 20]
        row["mfe_20bar"] = (np.nanmax(fwd_slice_h) - entry_price) / entry_price if len(fwd_slice_h) else np.nan
        row["mae_20bar"] = (entry_price - np.nanmin(fwd_slice_l)) / entry_price if len(fwd_slice_l) else np.nan

        rows.append(row)
    return rows

# ── process one ticker ─────────────────────────────────────────────────────────
def process_ticker(ticker: str) -> pd.DataFrame | None:
    """Fetch data, apply indicators, detect signals, compute returns."""
    print(f"  Fetching {ticker} …", end=" ", flush=True)
    try:
        raw = DataRouter.get_price_data(
            ticker,
            start_date = START_DATE,
            end_date   = END_DATE,
            timeframe  = TIMEFRAME,
            study_type = "indicator",
        )
    except Exception as exc:
        print(f"  ✗ Data fetch failed for {ticker}: {exc}")
        return None

    if raw is None or raw.empty:
        print(f"  ✗ No data for {ticker}")
        return None

    df = _normalise_cols(raw)
    required = {"Open", "High", "Low", "Close"}
    if not required.issubset(df.columns):
        print(f"  ✗ Missing OHLC columns for {ticker}")
        return None

    # drop NaN/zero close rows
    df = df[df["Close"].notna() & (df["Close"] > 0)].copy()
    if len(df) < 300:
        print(f"  ✗ Insufficient bars ({len(df)}) for {ticker}")
        return None

    # ── apply candle indicator ─────────────────────────────────────────────
    candle_ind = TrendStrengthCandles()
    df_c = candle_ind.compute(df)          # adds cs, cyan_signal, is_nr7, …

    # ── apply TSL indicator ───────────────────────────────────────────────
    tsl_ind = TrendStrengthLine()
    df_t = tsl_ind.compute(df)             # adds slope, is_rising, …

    # ── merge the two result sets into one aligned frame ──────────────────
    df_full = df.copy()
    df_full["cs"]           = df_c["cs"].values
    df_full["cyan_signal"]  = df_c["cyan_signal"].values
    df_full["is_nr7"]       = df_c["is_nr7"].values
    df_full["slope_value"]  = df_t["slope"].values
    df_full["is_rising"]    = df_t["is_rising"].values

    # ── convert index to ET for session / time-bucket logic ───────────────
    df_et = _to_et(df_full)

    # ── per-session valid mask ────────────────────────────────────────────
    valid_mask = _valid_bar_mask(df_et)

    # ── combined signal ───────────────────────────────────────────────────
    signal_mask = (
        valid_mask
        & df_et["cyan_signal"].fillna(False)
        & df_et["is_rising"].fillna(False)
    )

    signal_positions = [i for i, v in enumerate(signal_mask) if v]
    print(f"{len(signal_positions)} signals  ({len(df_et)} bars total)")

    if not signal_positions:
        return None

    # ── forward returns ────────────────────────────────────────────────────
    fwd_rows = _compute_forward_returns(df_et, signal_positions, FWD_WINDOWS)
    if not fwd_rows:
        return None

    # ── build output DataFrame ────────────────────────────────────────────
    records = []
    for row in fwd_rows:
        i = row["_pos"]
        bar  = df_et.iloc[i]
        time = df_et.index[i]

        time_bucket  = assign_time_bucket(time)
        score_bucket = assign_score_bucket(float(bar["cs"]))

        records.append({
            "ticker":        ticker,
            "signal_time":   time.isoformat(),
            "entry_price":   row["entry_price"],
            "cs_score":      round(float(bar["cs"]), 4),
            "slope_value":   round(float(bar["slope_value"]), 6),
            "return_5bar":   row.get("return_5bar"),
            "return_10bar":  row.get("return_10bar"),
            "return_20bar":  row.get("return_20bar"),
            "win_5bar":      row.get("win_5bar"),
            "win_10bar":     row.get("win_10bar"),
            "win_20bar":     row.get("win_20bar"),
            "mfe_20bar":     row.get("mfe_20bar"),
            "mae_20bar":     row.get("mae_20bar"),
            "time_bucket":   time_bucket,
            "score_bucket":  score_bucket,
        })

    return pd.DataFrame(records)


# ── write summary text ─────────────────────────────────────────────────────────
def write_summary_by_window(df: pd.DataFrame, path: Path) -> None:
    lines = ["=" * 60,
             "OVERALL WIN RATES BY FORWARD WINDOW",
             f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
             f"Total signals: {len(df):,}",
             "=" * 60, ""]
    for w in FWD_WINDOWS:
        col_w = f"win_{w}bar"
        col_r = f"return_{w}bar"
        sub = df[df[col_w].notna()]
        if sub.empty:
            continue
        wr  = sub[col_w].mean() * 100
        avg = sub[col_r].mean() * 100
        med = sub[col_r].median() * 100
        lines += [
            f"  {w}-bar window ({w*5} minutes):",
            f"    Signals evaluated : {len(sub):,}",
            f"    Win rate          : {wr:.1f}%",
            f"    Avg return        : {avg:+.3f}%",
            f"    Median return     : {med:+.3f}%",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ Saved {path.name}")


def write_summary_by_bucket(df: pd.DataFrame, bucket_col: str, path: Path,
                             title: str) -> None:
    bucket_order = (
        ["Open_Bar", "First_Hour", "Mid_Morning", "Midday", "Power_Hour", "Last_30"]
        if bucket_col == "time_bucket"
        else ["Strong_Bull", "Max_Bull"]
    )
    lines = ["=" * 68,
             title,
             f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
             "=" * 68, ""]

    for bkt in bucket_order:
        sub = df[df[bucket_col] == bkt]
        if sub.empty:
            lines += [f"  {bkt}: no signals", ""]
            continue
        lines.append(f"  {bkt}  (n={len(sub):,})")
        for w in FWD_WINDOWS:
            col_w = f"win_{w}bar"
            col_r = f"return_{w}bar"
            s = sub[sub[col_w].notna()]
            if s.empty:
                continue
            wr  = s[col_w].mean() * 100
            avg = s[col_r].mean() * 100
            lines.append(
                f"    {w:>2}-bar → win {wr:5.1f}%   avg ret {avg:+.3f}%   n={len(s)}"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ Saved {path.name}")


# ── plotly charts ──────────────────────────────────────────────────────────────
def _build_win_rate_bar_chart(df: pd.DataFrame, bucket_col: str,
                              bucket_order: list[str], title: str,
                              path: Path) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError:
        print(f"  ⚠ plotly not installed — skipping {path.name}")
        return

    fig = go.Figure()
    colors = ["#2196F3", "#4CAF50", "#FF9800"]

    for w, color in zip(FWD_WINDOWS, colors):
        col_w = f"win_{w}bar"
        wr_vals = []
        for bkt in bucket_order:
            sub = df[(df[bucket_col] == bkt) & df[col_w].notna()]
            wr_vals.append(sub[col_w].mean() * 100 if len(sub) > 0 else 0.0)
        fig.add_trace(go.Bar(
            name=f"{w}-bar win %",
            x=bucket_order,
            y=[round(v, 2) for v in wr_vals],
            marker_color=color,
            text=[f"{v:.1f}%" for v in wr_vals],
            textposition="outside",
        ))

    fig.add_hline(y=50, line_dash="dash", line_color="gray",
                  annotation_text="50% baseline")
    fig.update_layout(
        title=title,
        yaxis_title="Win Rate (%)",
        xaxis_title=bucket_col.replace("_", " ").title(),
        barmode="group",
        template="plotly_dark",
        height=520,
        yaxis_range=[0, 100],
    )
    fig.write_html(str(path))
    print(f"  ✓ Saved {path.name}")


def _build_return_distribution(df: pd.DataFrame, path: Path) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError:
        print(f"  ⚠ plotly not installed — skipping {path.name}")
        return

    col = "return_10bar"
    data = df[col].dropna() * 100    # in pct

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=data,
        nbinsx=80,
        marker_color="#26C6DA",
        opacity=0.85,
        name="10-bar return",
    ))
    fig.add_vline(x=0, line_dash="dash", line_color="white")
    fig.add_vline(x=data.mean(), line_dash="dot", line_color="#FF9800",
                  annotation_text=f"mean {data.mean():.2f}%",
                  annotation_position="top right")
    fig.update_layout(
        title="Distribution of 10-Bar Returns (Cyan+Rising TSL Signals)",
        xaxis_title="Return (%)",
        yaxis_title="Count",
        template="plotly_dark",
        height=480,
    )
    fig.write_html(str(path))
    print(f"  ✓ Saved {path.name}")


# ── main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    print("\n" + "=" * 68)
    print("  CYAN CANDLE + RISING TSL WIN RATE STUDY")
    print(f"  Universe: {len(UNIVERSE)} tickers  |  {START_DATE} → {END_DATE}")
    print(f"  Timeframe: {TIMEFRAME}  |  Warmup: {WARMUP_BARS} bars  |  Tail skip: {TAIL_BARS} bars")
    print("=" * 68)

    # ── initialise (or wipe) the running CSV ──────────────────────────────
    all_chunks: list[pd.DataFrame] = []
    header_written = False

    for idx, ticker in enumerate(UNIVERSE, 1):
        print(f"\n[{idx:>2}/{len(UNIVERSE)}] {ticker}")
        result = process_ticker(ticker)

        if result is not None and not result.empty:
            all_chunks.append(result)

            # ── append to CSV incrementally ───────────────────────────────
            result.to_csv(
                ALL_SIGNALS_PATH,
                mode   = "a" if header_written else "w",
                header = not header_written,
                index  = False,
            )
            header_written = True

        if idx % 5 == 0:
            total_so_far = sum(len(c) for c in all_chunks)
            print(f"\n  >>> Progress: {idx}/{len(UNIVERSE)} tickers  |  "
                  f"{total_so_far:,} signals accumulated <<<\n")

    # ── assemble full DataFrame ────────────────────────────────────────────
    if not all_chunks:
        print("\n✗ No signals collected — check API keys and data routing.")
        return

    full = pd.concat(all_chunks, ignore_index=True)
    print(f"\n{'=' * 68}")
    print(f"  TOTAL SIGNALS COLLECTED: {len(full):,}")
    print(f"  Tickers with signals  : {full['ticker'].nunique()}")
    print(f"{'=' * 68}\n")

    # ── summaries ─────────────────────────────────────────────────────────
    print("▷  Writing summaries …")
    write_summary_by_window(full, OUTPUTS_DIR / "summary_by_window.txt")

    write_summary_by_bucket(
        full, "time_bucket",
        OUTPUTS_DIR / "summary_by_time_bucket.txt",
        "WIN RATES BY TIME BUCKET (ET)",
    )

    write_summary_by_bucket(
        full, "score_bucket",
        OUTPUTS_DIR / "summary_by_score_bucket.txt",
        "WIN RATES BY SCORE BUCKET (Strong_Bull vs Max_Bull)",
    )

    # ── charts ────────────────────────────────────────────────────────────
    print("▷  Building charts …")
    _build_win_rate_bar_chart(
        full, "time_bucket",
        ["Open_Bar", "First_Hour", "Mid_Morning", "Midday", "Power_Hour", "Last_30"],
        "Win Rate by Time Bucket — Cyan Candle + Rising TSL",
        CHARTS_DIR / "winrate_by_time_bucket.html",
    )
    _build_win_rate_bar_chart(
        full, "score_bucket",
        ["Strong_Bull", "Max_Bull"],
        "Win Rate by Score Bucket — Cyan Candle + Rising TSL",
        CHARTS_DIR / "winrate_by_score_bucket.html",
    )
    _build_return_distribution(
        full,
        CHARTS_DIR / "return_distribution.html",
    )

    # ── quick console snapshot ────────────────────────────────────────────
    print("\n── Overall Win Rates ───────────────────────────────────────────")
    for w in FWD_WINDOWS:
        col = f"win_{w}bar"
        s = full[full[col].notna()]
        if not s.empty:
            print(f"   {w:>2}-bar : {s[col].mean()*100:.1f}%  (n={len(s):,})")

    print("\n── Win Rates by Ticker ─────────────────────────────────────────")
    for tkr, g in full.groupby("ticker"):
        w10 = g[g["win_10bar"].notna()]["win_10bar"]
        print(f"   {tkr:<6s}  n={len(g):>4}  10-bar win={w10.mean()*100:5.1f}%")

    print(f"\n✅  All outputs saved to:  {OUTPUTS_DIR}")
    print(f"   all_signals.csv      → {len(full):,} rows")
    print(f"   summary_by_window.txt")
    print(f"   summary_by_time_bucket.txt")
    print(f"   summary_by_score_bucket.txt")
    print(f"   charts/winrate_by_time_bucket.html")
    print(f"   charts/winrate_by_score_bucket.html")
    print(f"   charts/return_distribution.html\n")


if __name__ == "__main__":
    main()
