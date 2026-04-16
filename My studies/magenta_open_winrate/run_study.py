"""
QUANTLAB STUDY — MAGENTA OPENING BAR WIN RATE (SHORT SIDE)
===========================================================
File: studies/magenta_open_winrate/run_study.py

CORE QUESTION:
Does a stock that opens with a magenta candle (cs <= -70, MAX BEAR)
have a statistically meaningful downside edge for the rest of the session?

Short-side mirror of studies/cyan_open_rising_tsl. Same universe,
same date range, same 2x2 structure — built for direct comparison.

RETURN CONVENTION (shorts):
  return = (entry_price - forward_close) / entry_price
  Positive return = stock went DOWN = short is winning

WIN DEFINITIONS (dual):
  win_raw : return > 0        (any lower close)
  win_thr : return >= 0.001   (lower by at least 0.1% — filters noise)
"""

import sys
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

# ── paths ─────────────────────────────────────────────────────────────────────
STUDY_DIR    = Path(__file__).parent
OUTPUTS_DIR  = STUDY_DIR / "outputs"
CHARTS_DIR   = OUTPUTS_DIR / "charts"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

SIGNALS_PATH  = OUTPUTS_DIR / "magenta_signals.csv"
CYAN_CSV_PATH = ROOT / "studies" / "cyan_open_rising_tsl" / "outputs" / "open_signals.csv"

# ── parameters ─────────────────────────────────────────────────────────────────
UNIVERSE = [
    "NVDA", "AMD",  "TSLA", "AAPL", "MSFT", "META",  "GOOGL", "AMZN",
    "SMCI", "MSTR", "COIN", "PLTR", "SOFI", "HOOD",  "ARM",   "AVGO",
    "MU",   "NFLX", "SPY",  "QQQ",
]

HIGH_QUALITY = {"MSFT", "ARM", "QQQ", "MU", "AVGO", "MSTR", "SPY", "NVDA"}
LOW_QUALITY  = {"META", "PLTR", "TSLA", "AMZN"}
MIDDLE       = {"GOOGL", "AAPL", "NFLX", "SMCI", "SOFI", "COIN", "HOOD", "AMD"}

LOAD_START  = "2024-11-01"
STUDY_START = "2024-11-01"
STUDY_END   = "2025-02-28"
TIMEFRAME   = "5min"

FWD_WINDOWS      = [6, 12, 24]
WIN_THR          = 0.001   # 0.1% threshold for win_thr definition
OPEN_WINDOW_END  = dtime(10, 0)


# ── helpers ────────────────────────────────────────────────────────────────────

def _normalise_cols(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for c in df.columns:
        lc = c.lower()
        if lc == "open":    rename[c] = "Open"
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


def assign_group(cs: float, is_nr7: bool) -> str:
    """
    A: cs <= -70, NOT nr7         (magenta / max bear — primary signal)
    B: -70 < cs <= -50, NOT nr7   (strong bear, not max)
    C: cs <= -70, is_nr7          (NR7 disqualified — testing the override)
    D: everything else            (baseline)
    """
    if cs <= -70 and not is_nr7:   return "A"
    if -70 < cs <= -50 and not is_nr7: return "B"
    if cs <= -70 and is_nr7:       return "C"
    return "D"


# ── forward return computation (short-side) ───────────────────────────────────

def _compute_signals(df_et: pd.DataFrame, ticker: str) -> list[dict]:
    """Walk opening window bars, classify groups, compute short-side returns."""
    study_start_dt = pd.Timestamp(STUDY_START, tz="America/New_York")
    study_end_dt   = pd.Timestamp(STUDY_END,   tz="America/New_York") + pd.Timedelta(days=1)

    close  = df_et["Close"].values
    open_  = df_et["Open"].values
    high   = df_et["High"].values
    low    = df_et["Low"].values
    cs_arr = df_et["cs"].values
    nr7_arr = df_et["is_nr7"].values
    n = len(df_et)

    # date → positional indices for EOD / session lookups
    dates = df_et.index.normalize()
    date_groups: dict[pd.Timestamp, list[int]] = {}
    for i, d in enumerate(dates):
        date_groups.setdefault(d, []).append(i)

    quality = assign_ticker_quality(ticker)
    rows = []

    for i, ts in enumerate(df_et.index):
        if ts < study_start_dt or ts >= study_end_dt:
            continue

        bucket = assign_open_bucket(ts)
        if bucket is None:
            continue

        # Skip bars where indicator hasn't warmed up
        if np.isnan(cs_arr[i]):
            continue

        cs    = float(cs_arr[i])
        nr7   = bool(nr7_arr[i])
        group = assign_group(cs, nr7)

        # SHORT entry = open of bar i+1
        entry_i = i + 1
        if entry_i >= n:
            continue
        entry_price = open_[entry_i]
        if entry_price <= 0 or np.isnan(entry_price):
            continue

        # ── forward returns (short-side: positive = went down) ───────────
        fwd: dict = {}
        for w in FWD_WINDOWS:
            tgt = i + w
            if tgt >= n:
                for pfx in ("return", "win_raw", "win_thr"):
                    fwd[f"{pfx}_{w}bar"] = np.nan
            else:
                fwd_close = close[tgt]
                ret = (entry_price - fwd_close) / entry_price
                fwd[f"return_{w}bar"] = ret
                fwd[f"win_raw_{w}bar"] = int(ret > 0)
                fwd[f"win_thr_{w}bar"] = int(ret >= WIN_THR)

        # ── EOD return + session MFE / MAE (short-side) ──────────────────
        day_key          = ts.normalize()
        session_positions = date_groups.get(day_key, [])
        after_entry      = [j for j in session_positions if j >= entry_i]

        if after_entry:
            last_j       = session_positions[-1]
            eod_close    = close[last_j]
            ret_eod      = (entry_price - eod_close) / entry_price
            win_raw_eod  = int(ret_eod > 0)
            win_thr_eod  = int(ret_eod >= WIN_THR)

            session_highs = high[after_entry[0]: after_entry[-1] + 1]
            session_lows  = low[after_entry[0]:  after_entry[-1] + 1]
            # short MFE = how far it dropped in your favor
            mfe_session = (entry_price - float(np.nanmin(session_lows)))  / entry_price
            # short MAE = how far it went against you
            mae_session = (float(np.nanmax(session_highs)) - entry_price) / entry_price
        else:
            ret_eod = win_raw_eod = win_thr_eod = np.nan
            mfe_session = mae_session = np.nan

        rows.append({
            "ticker":            ticker,
            "signal_time":       ts.isoformat(),
            "signal_bar_bucket": bucket,
            "entry_price":       round(entry_price, 4),
            "cs_score":          round(cs, 4),
            "group":             group,
            "ticker_quality":    quality,
            **fwd,
            "return_eod":   ret_eod,
            "win_raw_eod":  win_raw_eod,
            "win_thr_eod":  win_thr_eod,
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
    if not {"Open", "High", "Low", "Close"}.issubset(df.columns):
        print("✗ missing OHLC columns")
        return None

    df = df[df["Close"].notna() & (df["Close"] > 0)].copy()
    if len(df) < 300:
        print(f"✗ only {len(df)} bars")
        return None

    df_c    = TrendStrengthCandles().compute(df)
    df_full = df.copy()
    df_full["cs"]       = df_c["cs"].values
    df_full["is_nr7"]   = df_c["is_nr7"].values

    df_et = _to_et(df_full)
    rows  = _compute_signals(df_et, ticker)

    counts = {g: sum(1 for r in rows if r["group"] == g) for g in "ABCD"}
    print(f"{len(rows)} opening bars  "
          f"(A={counts['A']} B={counts['B']} C={counts['C']} D={counts['D']})")

    return pd.DataFrame(rows) if rows else None


# ── summary helpers ────────────────────────────────────────────────────────────

def _wr(sub: pd.DataFrame, col: str) -> tuple[str, int]:
    s = sub[sub[col].notna()]
    if s.empty: return "  n/a", 0
    return f"{s[col].mean()*100:5.1f}%", len(s)


def _ret_str(sub: pd.DataFrame, col: str) -> str:
    s = sub[col].dropna()
    if s.empty: return "n/a"
    return f"avg {s.mean()*100:+.3f}%  med {s.median()*100:+.3f}%"


def _flag_ticker(sub_a: pd.DataFrame, ticker: str) -> str:
    """Return '★' if ticker qualifies as actionable short."""
    t = sub_a[sub_a["ticker"] == ticker]
    rw, _ = _wr(t, "win_raw_eod")
    rt, _ = _wr(t, "win_thr_eod")
    try:
        rw_f = float(rw.strip().replace("%", ""))
        rt_f = float(rt.strip().replace("%", ""))
        if rw_f > 60 and rt_f > 55:
            return "  ★ ACTIONABLE SHORT"
    except ValueError:
        pass
    return ""


# ── summary writers ────────────────────────────────────────────────────────────

def write_group_comparison(df: pd.DataFrame, path: Path) -> None:
    windows = [
        (6,     "return_6bar",   "win_raw_6bar",  "win_thr_6bar"),
        (12,    "return_12bar",  "win_raw_12bar", "win_thr_12bar"),
        (24,    "return_24bar",  "win_raw_24bar", "win_thr_24bar"),
        ("EOD", "return_eod",    "win_raw_eod",   "win_thr_eod"),
    ]
    lines = [
        "=" * 76,
        "GROUP COMPARISON — MAGENTA OPENING BAR (SHORT SIDE)",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
        "A=Magenta(cs<=-70,no-NR7)  B=StrongBear(-70<cs<=-50)  "
        "C=Magenta+NR7  D=Baseline",
        "Return convention: positive = stock went DOWN (short winning)",
        "=" * 76, "",
    ]
    for w, rcol, rwcol, rtwcol in windows:
        label = f"{w}-bar ({w*5} min)" if isinstance(w, int) else "End-of-Day"
        lines.append(f"  Window: {label}")
        lines.append(f"  {'Group':<6}  {'WinRaw':>8}  {'WinThr(0.1%)':>14}  {'Returns':>34}")
        lines.append(f"  {'-'*68}")
        for g in ["A", "B", "C", "D"]:
            sub = df[df["group"] == g]
            wr,  nr  = _wr(sub, rwcol)
            wt,  _   = _wr(sub, rtwcol)
            ret_s    = _ret_str(sub, rcol)
            lines.append(f"  {g:<6}  {wr:>8}  {wt:>14}  {ret_s:>34}  (n={nr})")
        lines.append("")

    n_a = int((df["group"] == "A").sum())
    if n_a < 100:
        lines.append(f"  ⚠  Group A n={n_a} — BORDERLINE SAMPLE SIZE (<100)")
    else:
        lines.append(f"  Group A total signals: {n_a}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ Saved {path.name}")


def write_open_bucket_summary(df: pd.DataFrame, path: Path) -> None:
    sub_a   = df[df["group"] == "A"]
    buckets = ["FIRST_BAR", "EARLY_OPEN", "OPEN_WINDOW"]
    windows = [
        (6,     "win_raw_6bar",  "win_thr_6bar"),
        (12,    "win_raw_12bar", "win_thr_12bar"),
        (24,    "win_raw_24bar", "win_thr_24bar"),
        ("EOD", "win_raw_eod",   "win_thr_eod"),
    ]
    lines = [
        "=" * 72,
        "OPEN BUCKET WIN RATES — Group A (Magenta, no NR7) Only",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
        "=" * 72, "",
    ]
    for bkt in buckets:
        sub = sub_a[sub_a["signal_bar_bucket"] == bkt]
        lines.append(f"  {bkt}  (n={len(sub)})")
        for w, rwcol, rtwcol in windows:
            label = f"{w*5} min" if isinstance(w, int) else "EOD"
            wr, _ = _wr(sub, rwcol)
            wt, _ = _wr(sub, rtwcol)
            lines.append(f"    {label:>8}  win_raw={wr}  win_thr={wt}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ Saved {path.name}")


def write_ticker_quality_summary(df: pd.DataFrame, path: Path) -> None:
    sub_a   = df[df["group"] == "A"]
    windows = [
        (6,     "win_raw_6bar",  "win_thr_6bar"),
        (12,    "win_raw_12bar", "win_thr_12bar"),
        (24,    "win_raw_24bar", "win_thr_24bar"),
        ("EOD", "win_raw_eod",   "win_thr_eod"),
    ]
    lines = [
        "=" * 72,
        "TICKER QUALITY TIER WIN RATES — Group A (Magenta) Only",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
        f"  HIGH:   {sorted(HIGH_QUALITY)}",
        f"  MIDDLE: {sorted(MIDDLE)}",
        f"  LOW:    {sorted(LOW_QUALITY)}",
        "(Tiers set by LONG-side performance in base study — inversion expected)",
        "=" * 72, "",
    ]
    for tier in ["HIGH", "MIDDLE", "LOW"]:
        sub = sub_a[sub_a["ticker_quality"] == tier]
        lines.append(f"  {tier} quality  (total n={len(sub)})")
        for w, rwcol, rtwcol in windows:
            label = f"{w*5} min" if isinstance(w, int) else "EOD"
            wr, _ = _wr(sub, rwcol)
            wt, _ = _wr(sub, rtwcol)
            lines.append(f"    {label:>8}  win_raw={wr}  win_thr={wt}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ Saved {path.name}")


def write_per_ticker_summary(df: pd.DataFrame, path: Path) -> None:
    sub_a = df[df["group"] == "A"]
    rows = []
    for tkr, g in sub_a.groupby("ticker"):
        s = g[g["win_raw_12bar"].notna()]
        rw = s["win_raw_12bar"].mean() * 100 if len(s) > 0 else np.nan
        rt_s = g[g["win_thr_12bar"].notna()]
        rt = rt_s["win_thr_12bar"].mean() * 100 if len(rt_s) > 0 else np.nan
        rows.append((tkr, len(g), rw, rt, assign_ticker_quality(tkr)))

    rows.sort(key=lambda x: (np.isnan(x[2]), -(x[2] if not np.isnan(x[2]) else 0)))

    lines = [
        "=" * 76,
        "PER-TICKER WIN RATES (12-bar) — Group A Magenta, Ranked",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
        "win_raw = any lower close     win_thr = lower by >=0.1%",
        "★ = win_raw_eod > 60% AND win_thr_eod > 55%  (actionable short)",
        "=" * 76, "",
        f"  {'Ticker':<8}  {'n':>4}  {'12-bar win_raw':>14}  {'12-bar win_thr':>14}  Quality",
        f"  {'-'*66}",
    ]
    for tkr, n, rw, rt, qual in rows:
        rw_s = f"{rw:5.1f}%" if not np.isnan(rw) else "  n/a"
        rt_s = f"{rt:5.1f}%" if not np.isnan(rt) else "  n/a"
        flag = _flag_ticker(sub_a, tkr)
        lines.append(f"  {tkr:<8}  {n:>4}  {rw_s:>14}  {rt_s:>14}  {qual}{flag}")

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ Saved {path.name}")


def write_cyan_vs_magenta_comparison(df_mag: pd.DataFrame, path: Path) -> None:
    lines = [
        "=" * 76,
        "CYAN (LONG) vs MAGENTA (SHORT) — OPENING BAR DIRECT COMPARISON",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
        "Cyan  = Group A from cyan_open_rising_tsl study (cs>=70, rising TSL)",
        "Magenta = Group A from this study (cs<=-70, no NR7, no TSL filter)",
        "=" * 76, "",
    ]

    # Load cyan data
    cyan_loaded = False
    df_cyan_a   = pd.DataFrame()
    if CYAN_CSV_PATH.exists():
        try:
            df_cyan = pd.read_csv(CYAN_CSV_PATH)
            df_cyan_a = df_cyan[df_cyan["group"] == "A"].copy()
            cyan_loaded = True
        except Exception as e:
            lines.append(f"  ⚠ Could not load cyan CSV: {e}")
    else:
        lines.append(f"  ⚠ Cyan CSV not found at: {CYAN_CSV_PATH}")

    df_mag_a = df_mag[df_mag["group"] == "A"].copy()

    def _safe_wr(df, col):
        s = df[df[col].notna()]
        return (s[col].mean() * 100, len(s)) if len(s) > 0 else (np.nan, 0)

    def _safe_ret(df, col):
        s = df[col].dropna()
        return (s.mean() * 100, s.median() * 100) if len(s) > 0 else (np.nan, np.nan)

    # Signal frequency
    mag_n = len(df_mag_a)
    lines.append(f"  Signal frequency (Group A):")
    lines.append(f"    Cyan    signals : {len(df_cyan_a) if cyan_loaded else 'n/a'}")
    lines.append(f"    Magenta signals : {mag_n}")
    lines.append("")

    # EOD comparison
    mag_eod_wr, mag_eod_n = _safe_wr(df_mag_a, "win_raw_eod")
    mag_eod_ret, mag_eod_med = _safe_ret(df_mag_a, "return_eod")
    lines.append("  EOD Win Rate (Group A only):")
    if cyan_loaded:
        cy_eod_wr, cy_eod_n = _safe_wr(df_cyan_a, "win_eod")
        cy_eod_ret, cy_eod_med = _safe_ret(df_cyan_a, "return_eod")
        lines.append(f"    Cyan    EOD win rate  : {cy_eod_wr:5.1f}%  avg {cy_eod_ret:+.3f}%  med {cy_eod_med:+.3f}%  (n={cy_eod_n})")
    else:
        lines.append("    Cyan    EOD win rate  : n/a (CSV not loaded)")
    lines.append(f"    Magenta EOD win rate  : {mag_eod_wr:5.1f}%  avg {mag_eod_ret:+.3f}%  med {mag_eod_med:+.3f}%  (n={mag_eod_n})")

    if cyan_loaded and not np.isnan(cy_eod_wr) and not np.isnan(mag_eod_wr):
        winner = "CYAN (long)" if cy_eod_wr > mag_eod_wr else "MAGENTA (short)"
        diff   = abs(cy_eod_wr - mag_eod_wr)
        lines.append(f"    >> HEADLINE: {winner} has more EOD edge (+{diff:.1f}pp)")
    lines.append("")

    # 12-bar comparison
    mag_12_wr, mag_12_n = _safe_wr(df_mag_a, "win_raw_12bar")
    lines.append("  12-bar Win Rate (Group A only):")
    if cyan_loaded:
        cy_12_wr, cy_12_n = _safe_wr(df_cyan_a, "win_12bar")
        lines.append(f"    Cyan    12-bar win rate : {cy_12_wr:5.1f}%  (n={cy_12_n})")
    lines.append(f"    Magenta 12-bar win rate : {mag_12_wr:5.1f}%  (n={mag_12_n})")
    lines.append("")

    # Top 5 tickers — magenta
    mag_by_tkr = []
    for tkr, g in df_mag_a.groupby("ticker"):
        s = g[g["win_raw_eod"].notna()]
        wr = s["win_raw_eod"].mean() * 100 if len(s) > 0 else np.nan
        mag_by_tkr.append((tkr, wr, len(g)))
    mag_by_tkr.sort(key=lambda x: (np.isnan(x[1]), -(x[1] if not np.isnan(x[1]) else 0)))

    lines.append("  Top 5 tickers — MAGENTA short edge (win_raw_eod, Group A):")
    for tkr, wr, n in mag_by_tkr[:5]:
        wr_s = f"{wr:.1f}%" if not np.isnan(wr) else "n/a"
        lines.append(f"    {tkr:<8}  {wr_s}  (n={n})")
    lines.append("")

    lines.append("  Bottom 5 tickers — weakest MAGENTA short edge:")
    for tkr, wr, n in mag_by_tkr[-5:]:
        wr_s = f"{wr:.1f}%" if not np.isnan(wr) else "n/a"
        lines.append(f"    {tkr:<8}  {wr_s}  (n={n})")
    lines.append("")

    # Cyan top/bottom tickers
    if cyan_loaded:
        cy_by_tkr = []
        for tkr, g in df_cyan_a.groupby("ticker"):
            s = g[g["win_eod"].notna()]
            wr = s["win_eod"].mean() * 100 if len(s) > 0 else np.nan
            cy_by_tkr.append((tkr, wr, len(g)))
        cy_by_tkr.sort(key=lambda x: (np.isnan(x[1]), -(x[1] if not np.isnan(x[1]) else 0)))
        lines.append("  Top 5 tickers — CYAN long edge (win_eod, Group A):")
        for tkr, wr, n in cy_by_tkr[:5]:
            wr_s = f"{wr:.1f}%" if not np.isnan(wr) else "n/a"
            lines.append(f"    {tkr:<8}  {wr_s}  (n={n})")
        lines.append("")
        lines.append("  Bottom 5 tickers — weakest CYAN long edge:")
        for tkr, wr, n in cy_by_tkr[-5:]:
            wr_s = f"{wr:.1f}%" if not np.isnan(wr) else "n/a"
            lines.append(f"    {tkr:<8}  {wr_s}  (n={n})")
        lines.append("")

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
    labels = {
        "A": "A: Magenta", "B": "B: Strong Bear",
        "C": "C: Magenta+NR7", "D": "D: Baseline",
    }
    windows = [(6, "win_raw_6bar", "30 min"), (12, "win_raw_12bar", "60 min"),
               (24, "win_raw_24bar", "120 min"), ("EOD", "win_raw_eod", "EOD")]
    colors = ["#E040FB", "#AB47BC", "#FFA726", "#78909C"]

    fig = go.Figure()
    for (w, wcol, wlabel), color in zip(windows, colors):
        wr_vals = []
        for g in groups:
            sub = df[(df["group"] == g) & df[wcol].notna()]
            wr_vals.append(sub[wcol].mean() * 100 if len(sub) > 0 else 0.0)
        fig.add_trace(go.Bar(
            name=wlabel, x=[labels[g] for g in groups],
            y=[round(v, 2) for v in wr_vals],
            marker_color=color,
            text=[f"{v:.1f}%" for v in wr_vals],
            textposition="outside",
        ))
    fig.add_hline(y=50, line_dash="dash", line_color="gray",
                  annotation_text="50% baseline")
    fig.update_layout(
        title="Magenta Opening Bar — Short Side Win Rate by Group",
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
    sub_a   = df[df["group"] == "A"]
    buckets = ["FIRST_BAR", "EARLY_OPEN", "OPEN_WINDOW"]
    windows = [(6, "win_raw_6bar", "30 min"), (12, "win_raw_12bar", "60 min"),
               (24, "win_raw_24bar", "120 min"), ("EOD", "win_raw_eod", "EOD")]
    colors = ["#E040FB", "#AB47BC", "#FFA726", "#78909C"]

    fig = go.Figure()
    for (w, wcol, wlabel), color in zip(windows, colors):
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
        title="Magenta Opening Bar — Win Rate by Open Sub-Bucket (Group A)",
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
    sub_a   = df[df["group"] == "A"]
    tiers   = ["HIGH", "MIDDLE", "LOW"]
    windows = [(6, "win_raw_6bar", "30 min"), (12, "win_raw_12bar", "60 min"),
               (24, "win_raw_24bar", "120 min"), ("EOD", "win_raw_eod", "EOD")]
    colors  = ["#E040FB", "#AB47BC", "#FFA726", "#78909C"]

    fig = go.Figure()
    for (w, wcol, wlabel), color in zip(windows, colors):
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
        title="Magenta Opening Bar — Win Rate by Ticker Quality Tier (Group A)",
        yaxis_title="Win Rate (%)", xaxis_title="Quality Tier (long-side basis)",
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
        marker_color="#E040FB", opacity=0.85,
        name="EOD short return",
    ))
    fig.add_vline(x=0, line_dash="dash", line_color="white")
    fig.add_vline(x=data.mean(), line_dash="dot", line_color="#FFA726",
                  annotation_text=f"mean {data.mean():.2f}%",
                  annotation_position="top right")
    fig.update_layout(
        title="EOD Return Distribution — Magenta Opening Bar (Group A, Short Side)",
        xaxis_title="Return % (positive = stock went down)",
        yaxis_title="Count",
        template="plotly_dark", height=480,
    )
    fig.write_html(str(path))
    print(f"  ✓ Saved {path.name}")


def chart_cyan_vs_magenta(df_mag: pd.DataFrame, path: Path) -> None:
    go = _try_plotly()
    if not go:
        print(f"  ⚠ plotly not installed — skipping {path.name}")
        return

    windows_mag = [(6, "win_raw_6bar"), (12, "win_raw_12bar"),
                   (24, "win_raw_24bar"), ("EOD", "win_raw_eod")]
    windows_cy  = [(6, "win_6bar"), (12, "win_12bar"),
                   (24, "win_24bar"), ("EOD", "win_eod")]
    labels = ["30 min", "60 min", "120 min", "EOD"]

    mag_a = df_mag[df_mag["group"] == "A"]
    mag_vals = [mag_a[mag_a[wc].notna()][wc].mean() * 100
                for _, wc in windows_mag]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Magenta (short)", x=labels,
        y=[round(v, 2) for v in mag_vals],
        marker_color="#E040FB",
        text=[f"{v:.1f}%" for v in mag_vals],
        textposition="outside",
    ))

    if CYAN_CSV_PATH.exists():
        try:
            df_cyan_a = pd.read_csv(CYAN_CSV_PATH)
            df_cyan_a = df_cyan_a[df_cyan_a["group"] == "A"]
            cy_vals = [df_cyan_a[df_cyan_a[wc].notna()][wc].mean() * 100
                       for _, wc in windows_cy]
            fig.add_trace(go.Bar(
                name="Cyan (long)", x=labels,
                y=[round(v, 2) for v in cy_vals],
                marker_color="#26C6DA",
                text=[f"{v:.1f}%" for v in cy_vals],
                textposition="outside",
            ))
        except Exception:
            pass

    fig.add_hline(y=50, line_dash="dash", line_color="gray",
                  annotation_text="50% baseline")
    fig.update_layout(
        title="Cyan (Long) vs Magenta (Short) — Opening Bar Win Rates",
        yaxis_title="Win Rate (%)", xaxis_title="Forward Window",
        barmode="group", template="plotly_dark",
        height=520, yaxis_range=[0, 100],
    )
    fig.write_html(str(path))
    print(f"  ✓ Saved {path.name}")


# ── console requested-numbers report ──────────────────────────────────────────

def print_requested_numbers(df: pd.DataFrame) -> None:
    ga = df["group"] == "A"
    gb = df["group"] == "B"
    gd = df["group"] == "D"
    hq = df["ticker_quality"] == "HIGH"
    fb = df["signal_bar_bucket"] == "FIRST_BAR"

    def _n(mask, col):
        s = df[mask & df[col].notna()]
        if s.empty: return "n/a", 0
        return f"{s[col].mean()*100:.1f}%", len(s)

    n_a = int(ga.sum())
    flag = "  ⚠ BORDERLINE (<100)" if n_a < 100 else ""

    # Top/bottom 3 by win_raw_eod
    mag_a = df[ga]
    by_tkr = []
    for tkr, g in mag_a.groupby("ticker"):
        s = g[g["win_raw_eod"].notna()]
        wr = s["win_raw_eod"].mean() * 100 if len(s) > 0 else np.nan
        by_tkr.append((tkr, wr, len(g)))
    by_tkr.sort(key=lambda x: (np.isnan(x[1]), -(x[1] if not np.isnan(x[1]) else 0)))

    # Cyan EOD
    cyan_eod = "n/a"
    if CYAN_CSV_PATH.exists():
        try:
            dc = pd.read_csv(CYAN_CSV_PATH)
            dc_a = dc[dc["group"] == "A"]
            s = dc_a[dc_a["win_eod"].notna()]
            if len(s) > 0:
                cyan_eod = f"{s['win_eod'].mean()*100:.1f}%"
        except Exception:
            pass

    mag_eod, mag_eod_n = _n(ga, "win_raw_eod")

    print("\n" + "=" * 72)
    print("  REQUESTED NUMBERS — MAGENTA STUDY SPEC")
    print("=" * 72)
    r, n = _n(ga, "win_raw_12bar");   print(f"  1a. Group A raw   12-bar  : {r}  (n={n})")
    r, n = _n(ga, "win_raw_eod");     print(f"      Group A raw   EOD     : {r}  (n={n}){flag}")
    r, n = _n(ga, "win_thr_12bar");   print(f"  1b. Group A thr   12-bar  : {r}  (0.1% threshold)")
    r, n = _n(ga, "win_thr_eod");     print(f"      Group A thr   EOD     : {r}")
    r, n = _n(gb, "win_raw_12bar");   print(f"  3.  Group B 12-bar        : {r}  (strong bear, -70<cs<=-50)")
    r, n = _n(gd, "win_raw_12bar");   print(f"  4.  Group D baseline 12-b : {r}")
    r, n = _n(ga & hq, "win_raw_12bar"); print(f"  5.  Group A HIGH tier 12b : {r}  (n={n})")
    r, n = _n(ga & fb, "win_raw_12bar"); print(f"  6.  Group A FIRST_BAR 12b : {r}  (n={n})")
    print(f"  7.  Top 3 short tickers (win_raw_eod):")
    for tkr, wr, n in by_tkr[:3]:
        print(f"        {tkr:<8} {wr:.1f}%  (n={n})")
    print(f"  8.  Bottom 3 short tickers:")
    for tkr, wr, n in by_tkr[-3:]:
        wr_s = f"{wr:.1f}%" if not np.isnan(wr) else "n/a"
        print(f"        {tkr:<8} {wr_s}  (n={n})")
    print(f"  9.  Group A total signals : {n_a}{flag}")
    print(f" 10.  HEADLINE — Magenta EOD : {mag_eod}  |  Cyan EOD : {cyan_eod}")

    if cyan_eod != "n/a" and mag_eod != "n/a":
        c_f = float(cyan_eod.replace("%", ""))
        m_f = float(mag_eod.replace("%", ""))
        winner = "CYAN (long)" if c_f > m_f else "MAGENTA (short)"
        print(f"        >> {winner} has more opening-bar EOD edge (+{abs(c_f-m_f):.1f}pp)")
    print("=" * 72 + "\n")


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "=" * 72)
    print("  MAGENTA OPENING BAR WIN RATE STUDY (SHORT SIDE)")
    print(f"  Universe: {len(UNIVERSE)} tickers  |  Study: {STUDY_START} -> {STUDY_END}")
    print(f"  Opening window: 09:30-10:00 ET  |  Signal: cs <= -70, NOT NR7")
    print(f"  Groups: A=Magenta  B=StrongBear  C=Magenta+NR7  D=Baseline")
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
                  f"{total_so_far:,} opening bars | {ga_so_far} Group A <<<\n")

    if not all_chunks:
        print("\n✗ No signals collected.")
        return

    full  = pd.concat(all_chunks, ignore_index=True)
    n_a   = int((full["group"] == "A").sum())
    print(f"\n{'=' * 72}")
    print(f"  TOTAL OPENING BARS : {len(full):,}")
    print(f"  Group A (magenta)  : {n_a}")
    print(f"  Group B (str bear) : {(full['group']=='B').sum()}")
    print(f"  Group C (mag+NR7)  : {(full['group']=='C').sum()}")
    print(f"  Group D (baseline) : {(full['group']=='D').sum()}")
    if n_a < 100:
        print(f"  ⚠  Group A n={n_a} — BORDERLINE SAMPLE SIZE (<100)")
    print(f"{'=' * 72}\n")

    print("▷  Writing summaries ...")
    write_group_comparison(full,       OUTPUTS_DIR / "summary_group_comparison.txt")
    write_open_bucket_summary(full,    OUTPUTS_DIR / "summary_by_open_bucket.txt")
    write_ticker_quality_summary(full, OUTPUTS_DIR / "summary_by_ticker_quality.txt")
    write_per_ticker_summary(full,     OUTPUTS_DIR / "summary_by_ticker.txt")
    write_cyan_vs_magenta_comparison(full, OUTPUTS_DIR / "summary_cyan_vs_magenta_comparison.txt")

    print("▷  Building charts ...")
    chart_group_comparison(full, CHARTS_DIR / "group_comparison.html")
    chart_open_bucket(full,      CHARTS_DIR / "open_bucket_winrates.html")
    chart_ticker_quality(full,   CHARTS_DIR / "ticker_quality_comparison.html")
    chart_eod_distribution(full, CHARTS_DIR / "eod_return_distribution.html")
    chart_cyan_vs_magenta(full,  CHARTS_DIR / "cyan_vs_magenta_eod.html")

    print_requested_numbers(full)

    print(f"✅  All outputs saved to: {OUTPUTS_DIR}")
    print(f"   magenta_signals.csv                     -> {len(full):,} rows")
    print(f"   summary_group_comparison.txt")
    print(f"   summary_by_open_bucket.txt")
    print(f"   summary_by_ticker_quality.txt")
    print(f"   summary_by_ticker.txt")
    print(f"   summary_cyan_vs_magenta_comparison.txt")
    print(f"   charts/group_comparison.html")
    print(f"   charts/open_bucket_winrates.html")
    print(f"   charts/ticker_quality_comparison.html")
    print(f"   charts/eod_return_distribution.html")
    print(f"   charts/cyan_vs_magenta_eod.html\n")


if __name__ == "__main__":
    main()
