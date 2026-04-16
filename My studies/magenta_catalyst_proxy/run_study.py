"""
=============================================================
QUANTLAB STUDY — MAGENTA OPENING BAR + CATALYST PROXY
File: studies/magenta_catalyst_proxy/run_study.py
=============================================================

CORE QUESTION:
When a magenta candle (cs <= -70) fires at the open AND a
catalyst proxy is present (gap down >= 3% OR earnings overnight),
does the short-side edge materialize that was absent in the
naked magenta study?

HYPOTHESIS:
The naked magenta study showed 49.5% EOD win rate — below 50%.
The missing ingredient is catalyst. This study isolates magenta
opens where something REAL is driving the weakness. Expected
result: EOD win rate jumps to 60%+ on catalyst-confirmed signals.

BUILDS ON: studies/magenta_open_winrate/
USE THE SAME: TrendStrengthCandles, DataRouter

RETURN CONVENTION (shorts):
  return = (entry_price - forward_close) / entry_price
  Positive return = stock went DOWN = short is winning

WIN DEFINITIONS (dual):
  win_raw : return > 0        (any lower close)
  win_thr : return >= 0.001   (lower by at least 0.1%)
"""

import sys
import warnings
from pathlib import Path
from datetime import datetime, time as dtime

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "shared"))

import numpy as np
import pandas as pd

from shared.data_router import DataRouter
from shared.indicators.trend_strength_candles import TrendStrengthCandles

# ── paths ──────────────────────────────────────────────────────────────────────
STUDY_DIR   = Path(__file__).parent
OUTPUTS_DIR = STUDY_DIR / "outputs"
CHARTS_DIR  = OUTPUTS_DIR / "charts"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

SIGNALS_PATH   = OUTPUTS_DIR / "magenta_catalyst_signals.csv"
NAKED_MAG_PATH = ROOT / "studies" / "magenta_open_winrate" / "outputs" / "magenta_signals.csv"

# ── parameters ─────────────────────────────────────────────────────────────────
UNIVERSE = [
    "NVDA", "AMD",  "TSLA", "AAPL", "MSFT", "META",  "GOOGL", "AMZN",
    "SMCI", "MSTR", "COIN", "PLTR", "SOFI", "HOOD",  "ARM",   "AVGO",
    "MU",   "NFLX", "SPY",  "QQQ",
]

# Short-side quality tiers (from naked magenta study)
STRONG_SHORT = {"TSLA", "MSFT", "ARM", "QQQ", "NVDA", "MU"}
WEAK_SHORT   = {"PLTR", "NFLX", "AVGO"}
# UNKNOWN = everyone else

LOAD_START  = "2024-11-01"
STUDY_START = "2024-11-01"
STUDY_END   = "2025-02-28"
TIMEFRAME   = "5min"

FWD_WINDOWS = [6, 12, 24]
WIN_THR     = 0.001     # 0.1% threshold
GAP_THRESH  = -3.0      # gap must be <= this % to count as gap proxy
NAKED_EOD   = 49.5      # benchmark from naked magenta study

OPEN_WINDOW_START = dtime(9, 30)
OPEN_WINDOW_END   = dtime(10, 0)


# ── helpers ────────────────────────────────────────────────────────────────────

def _normalise_cols(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for c in df.columns:
        lc = c.lower()
        if lc == "open":              rename[c] = "Open"
        elif lc == "high":            rename[c] = "High"
        elif lc == "low":             rename[c] = "Low"
        elif lc == "close":           rename[c] = "Close"
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
    if dtime(9, 30) <= t < dtime(9, 35): return "FIRST_BAR"
    if dtime(9, 35) <= t < dtime(9, 45): return "EARLY_OPEN"
    if dtime(9, 45) <= t < dtime(10, 0): return "OPEN_WINDOW"
    return None


def assign_ticker_quality(ticker: str) -> str:
    if ticker in STRONG_SHORT: return "STRONG_SHORT"
    if ticker in WEAK_SHORT:   return "WEAK_SHORT"
    return "UNKNOWN"


def assign_catalyst_strength(gap_pct: float, is_earnings: bool) -> str:
    """Classify catalyst strength bucket from gap and earnings flags."""
    has_gap = gap_pct <= GAP_THRESH

    if is_earnings and has_gap:
        return "EARNINGS_GAP"
    if is_earnings and not has_gap:
        return "EARNINGS_FLAT"
    # gap only below
    if gap_pct <= -10.0:
        return "GAP_EXTREME"
    if gap_pct <= -5.0:
        return "GAP_LARGE"
    if gap_pct <= -3.0:
        return "GAP_SMALL"
    # no catalyst
    return "NONE"


def assign_group(cs: float, is_nr7: bool, has_gap: bool, is_earnings: bool) -> str:
    """
    Groups:
      A: magenta + ANY catalyst (gap OR earnings)
      B: magenta + gap only (no earnings)
      C: magenta + earnings only (gap < 3%)
      D: magenta + BOTH earnings AND gap
      E: naked magenta — no catalyst proxy
    Only A-E for cs <= -70, not-NR7 bars.
    All other bars are discarded (we are not tracking a baseline group here
    since the naked magenta study already provides that reference).
    """
    if cs > -70 or is_nr7:
        return None  # not a magenta bar -> exclude
    if is_earnings and has_gap:
        return "D"    # both triggers
    if is_earnings and not has_gap:
        return "C"    # earnings only
    if has_gap and not is_earnings:
        return "B"    # gap only
    # catalyst present from any angle already returned; if we're here — nothing
    return "E"        # naked magenta


# ══════════════════════════════════════════════════════════════════════════════
# EARNINGS DATE DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def _fetch_earnings_dates_yf(ticker: str) -> tuple[set[str], str]:
    """
    Returns (set_of_date_strings_YYYY-MM-DD, method_used).
    Dates represent sessions where earnings were reported OVERNIGHT
    (i.e. the report affects the opening of this session).
    """
    try:
        import yfinance as yf
    except ImportError:
        return set(), "yfinance_not_installed"

    tkr = yf.Ticker(ticker)
    dates: set[str] = set()
    method = "none"

    # ── Method 1: earnings_dates ───────────────────────────────────────────
    try:
        ed = tkr.earnings_dates
        if ed is not None and not ed.empty:
            for ts in ed.index:
                try:
                    # ts is a tz-aware timestamp
                    if hasattr(ts, "tz_convert"):
                        et_ts = ts.tz_convert("America/New_York")
                    else:
                        et_ts = ts
                    t = et_ts.time()
                    # After close (>= 16:00) → affects NEXT session
                    if t >= dtime(16, 0):
                        next_date = (et_ts + pd.Timedelta(days=1)).date()
                        dates.add(next_date.strftime("%Y-%m-%d"))
                    # Pre-market (< 9:30) → affects THIS session
                    elif t < dtime(9, 30):
                        dates.add(et_ts.date().strftime("%Y-%m-%d"))
                    # During market hours — treat as SAME session open
                    else:
                        dates.add(et_ts.date().strftime("%Y-%m-%d"))
                except Exception:
                    pass
            if dates:
                method = "earnings_dates"
                return dates, method
    except Exception:
        pass

    # ── Method 2: calendar ────────────────────────────────────────────────
    try:
        cal = tkr.calendar
        if cal is not None and not cal.empty:
            # calendar may contain 'Earnings Date' key
            for col in cal.columns if hasattr(cal, "columns") else []:
                if "earnings" in col.lower() or "date" in col.lower():
                    for v in cal[col].dropna():
                        try:
                            d = pd.Timestamp(v)
                            dates.add(d.strftime("%Y-%m-%d"))
                        except Exception:
                            pass
            if dates:
                method = "calendar"
                return dates, method
    except Exception:
        pass

    return dates, "unknown"


HARDCODED_EARNINGS: dict[str, list[str]] = {
    # Format: sessions (opening bar dates) affected by overnight earnings
    # Nov 2024 – Feb 2025 known earnings dates for the universe
    "NVDA":  ["2024-11-21"],
    "AMD":   ["2024-10-30"],        # Q3 2024
    "TSLA":  ["2024-10-24"],        # Q3 2024
    "AAPL":  ["2024-11-01"],        # Q4 FY2024
    "MSFT":  ["2024-10-31"],        # Q1 FY2025
    "META":  ["2024-10-31"],        # Q3 2024
    "GOOGL": ["2024-10-30"],        # Q3 2024
    "AMZN":  ["2024-10-31"],        # Q3 2024
    "SMCI":  ["2024-11-06"],        # Q1 FY2025 (delayed)
    "MSTR":  ["2024-10-31", "2025-02-06"],
    "COIN":  ["2024-11-08", "2025-02-13"],
    "PLTR":  ["2024-11-05", "2025-02-04"],
    "SOFI":  ["2024-10-30", "2025-01-28"],
    "HOOD":  ["2024-10-30", "2025-02-12"],
    "ARM":   ["2024-11-07", "2025-02-06"],
    "AVGO":  ["2024-12-13"],        # Q4 FY2024
    "MU":    ["2024-12-19", "2025-01-09"],
    "NFLX":  ["2024-10-18", "2025-01-22"],
    "SPY":   [],
    "QQQ":   [],
}


def build_earnings_lookup(universe: list[str]) -> dict[str, set[str]]:
    """
    Returns {ticker: {date_str, ...}} of overnight-earnings session dates.
    Tries yfinance first, falls back to hardcoded, logs results.
    """
    lookup: dict[str, set[str]] = {}
    log_lines: list[str] = []

    for ticker in universe:
        dates, method = _fetch_earnings_dates_yf(ticker)

        # Filter to study window
        start = pd.Timestamp(STUDY_START).date()
        end   = pd.Timestamp(STUDY_END).date()
        dates = {d for d in dates
                 if start <= pd.Timestamp(d).date() <= end}

        if not dates:
            # fall back to hardcoded
            hc = set(HARDCODED_EARNINGS.get(ticker, []))
            hc = {d for d in hc
                  if start <= pd.Timestamp(d).date() <= end}
            if hc:
                dates  = hc
                method = "hardcoded_fallback"
            else:
                method = "no_data"

        lookup[ticker] = dates
        n = len(dates)
        log_lines.append(f"  {ticker:<8}  method={method:<24}  n={n}  {sorted(dates)}")

    log_path = OUTPUTS_DIR / "earnings_detection_log.txt"
    log_path.write_text(
        "EARNINGS DATE DETECTION LOG\n"
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}\n"
        "=" * 72 + "\n" +
        "\n".join(log_lines),
        encoding="utf-8",
    )
    print(f"  ✓ Earnings detection log → {log_path.name}")
    return lookup


# ══════════════════════════════════════════════════════════════════════════════
# DAILY GAP COMPUTATION
# ══════════════════════════════════════════════════════════════════════════════

def build_gap_lookup(ticker: str) -> dict[str, float]:
    """
    Returns {date_str: gap_pct} where
      gap_pct = (daily_open - prev_daily_close) / prev_daily_close * 100
    Uses DataRouter with study_type='market_data' for daily bars.
    Falls back to yfinance if needed.
    """
    try:
        raw = DataRouter.get_price_data(
            ticker,
            start_date = LOAD_START,
            end_date   = STUDY_END,
            timeframe  = "1day",
            study_type = "market_data",
        )
    except Exception:
        raw = None

    # fallback to yfinance daily
    if raw is None or raw.empty:
        try:
            import yfinance as yf
            raw = yf.download(
                ticker,
                start=LOAD_START,
                end=STUDY_END,
                interval="1d",
                progress=False,
                auto_adjust=True,
            )
        except Exception:
            return {}

    if raw is None or raw.empty:
        return {}

    # yfinance can return MultiIndex columns — flatten to level 0
    if isinstance(raw.columns, pd.MultiIndex):
        raw = raw.copy()
        raw.columns = raw.columns.get_level_values(0)

    df = _normalise_cols(raw)
    if not {"Open", "Close"}.issubset(df.columns):
        return {}

    df = df.sort_index()
    # Shift close by 1 to get prev_close aligned to current row
    df["prev_close"] = df["Close"].shift(1)
    df = df.dropna(subset=["prev_close"])
    df["gap_pct"] = (df["Open"] - df["prev_close"]) / df["prev_close"] * 100

    # Normalize index to date
    idx = df.index
    if hasattr(idx, "tz") and idx.tz is not None:
        idx = idx.tz_convert("America/New_York")
    lookup: dict[str, float] = {}
    for ts, row in zip(idx, df.itertuples()):
        d = pd.Timestamp(ts).date().strftime("%Y-%m-%d")
        lookup[d] = float(row.gap_pct)
    return lookup


# ══════════════════════════════════════════════════════════════════════════════
# SIGNAL COMPUTATION PER TICKER
# ══════════════════════════════════════════════════════════════════════════════

def _compute_signals(
    df_et: pd.DataFrame,
    ticker: str,
    gap_lookup: dict[str, float],
    earnings_dates: set[str],
) -> list[dict]:
    """
    Walk opening window bars.
    Classify magenta bars into groups A-E based on catalyst proxy.
    Compute short-side forward returns.
    """
    study_start_dt = pd.Timestamp(STUDY_START, tz="America/New_York")
    study_end_dt   = pd.Timestamp(STUDY_END,   tz="America/New_York") + pd.Timedelta(days=1)

    close  = df_et["Close"].values
    open_  = df_et["Open"].values
    high   = df_et["High"].values
    low    = df_et["Low"].values
    cs_arr = df_et["cs"].values
    nr7_arr = df_et["is_nr7"].values
    n = len(df_et)

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

        # Skip unwarmed bars
        if np.isnan(cs_arr[i]):
            continue

        cs   = float(cs_arr[i])
        nr7  = bool(nr7_arr[i])

        # Fast exit — only process magenta bars
        if cs > -70 or nr7:
            continue

        date_str  = ts.strftime("%Y-%m-%d")
        gap_pct   = gap_lookup.get(date_str, 0.0)  # 0.0 if daily data missing
        is_earnings = date_str in earnings_dates
        has_gap   = gap_pct <= GAP_THRESH

        group = assign_group(cs, nr7, has_gap, is_earnings)
        if group is None:
            continue

        catalyst_strength = assign_catalyst_strength(gap_pct, is_earnings)

        if is_earnings and has_gap:
            catalyst_proxy = "BOTH"
        elif is_earnings:
            catalyst_proxy = "EARNINGS"
        elif has_gap:
            catalyst_proxy = "GAP"
        else:
            catalyst_proxy = "NONE"

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
                fwd[f"return_{w}bar"]  = np.nan
                fwd[f"win_raw_{w}bar"] = np.nan
                fwd[f"win_thr_{w}bar"] = np.nan
            else:
                fc  = close[tgt]
                ret = (entry_price - fc) / entry_price
                fwd[f"return_{w}bar"]  = ret
                fwd[f"win_raw_{w}bar"] = int(ret > 0)
                fwd[f"win_thr_{w}bar"] = int(ret >= WIN_THR)

        # ── EOD return + session MFE / MAE (short-side) ──────────────────
        day_key           = ts.normalize()
        session_positions = date_groups.get(day_key, [])
        after_entry       = [j for j in session_positions if j >= entry_i]

        if after_entry:
            last_j       = session_positions[-1]
            eod_close    = close[last_j]
            ret_eod      = (entry_price - eod_close) / entry_price
            win_raw_eod  = int(ret_eod > 0)
            win_thr_eod  = int(ret_eod >= WIN_THR)
            session_highs = high[after_entry[0]: after_entry[-1] + 1]
            session_lows  = low[after_entry[0]:  after_entry[-1] + 1]
            mfe_session  = (entry_price - float(np.nanmin(session_lows)))  / entry_price
            mae_session  = (float(np.nanmax(session_highs)) - entry_price) / entry_price
        else:
            ret_eod = win_raw_eod = win_thr_eod = np.nan
            mfe_session = mae_session = np.nan

        rows.append({
            "ticker":                  ticker,
            "signal_time":             ts.isoformat(),
            "signal_bar_bucket":       bucket,
            "entry_price":             round(entry_price, 4),
            "cs_score":                round(cs, 4),
            "gap_pct":                 round(gap_pct, 4),
            "is_earnings":             is_earnings,
            "catalyst_proxy":          catalyst_proxy,
            "catalyst_strength_bucket": catalyst_strength,
            "group":                   group,
            "group_primary":           "A" if group in ("B", "C", "D") else "E",
            "ticker_quality":          quality,
            **fwd,
            "return_eod":    ret_eod,
            "win_raw_eod":   win_raw_eod,
            "win_thr_eod":   win_thr_eod,
            "mfe_session":   mfe_session,
            "mae_session":   mae_session,
        })

    return rows


# ── per-ticker pipeline ────────────────────────────────────────────────────────

def process_ticker(
    ticker: str,
    earnings_lookup: dict[str, set[str]],
) -> pd.DataFrame | None:
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

    # Apply TrendStrengthCandles on full series (warmup included)
    df_c    = TrendStrengthCandles().compute(df)
    df_full = df.copy()
    df_full["cs"]     = df_c["cs"].values
    df_full["is_nr7"] = df_c["is_nr7"].values

    df_et = _to_et(df_full)

    # Build daily gap lookup for this ticker
    gap_lookup = build_gap_lookup(ticker)

    earnings_dates = earnings_lookup.get(ticker, set())

    rows = _compute_signals(df_et, ticker, gap_lookup, earnings_dates)

    counts = {g: sum(1 for r in rows if r["group"] == g) for g in "ABCDE"}
    print(
        f"{len(rows)} magenta open bars  "
        f"(A={counts['A']} B={counts['B']} C={counts['C']} "
        f"D={counts['D']} E={counts['E']})"
    )
    return pd.DataFrame(rows) if rows else None


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _wr_pair(sub: pd.DataFrame, raw_col: str, thr_col: str) -> tuple[str, str, int]:
    """Returns (win_raw_str, win_thr_str, n)."""
    s_raw = sub[sub[raw_col].notna()]
    s_thr = sub[sub[thr_col].notna()]
    if s_raw.empty:
        return "  n/a", "  n/a", 0
    raw_s = f"{s_raw[raw_col].mean()*100:5.1f}%"
    thr_s = f"{s_thr[thr_col].mean()*100:5.1f}%" if not s_thr.empty else "  n/a"
    return raw_s, thr_s, len(s_raw)


def _ret_str(sub: pd.DataFrame, col: str) -> str:
    s = sub[col].dropna()
    if s.empty: return "n/a"
    return f"avg {s.mean()*100:+.3f}%  med {s.median()*100:+.3f}%"


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY WRITERS
# ══════════════════════════════════════════════════════════════════════════════

WINDOWS = [
    (6,     "return_6bar",  "win_raw_6bar",  "win_thr_6bar"),
    (12,    "return_12bar", "win_raw_12bar", "win_thr_12bar"),
    (24,    "return_24bar", "win_raw_24bar", "win_thr_24bar"),
    ("EOD", "return_eod",   "win_raw_eod",   "win_thr_eod"),
]


def _group_df(df: pd.DataFrame, g: str) -> pd.DataFrame:
    """Return subset of df for the logical group.
    Group A (any catalyst) = union of groups B, C, D.
    Groups B/C/D/E are queried directly from the 'group' column.
    """
    if g == "A":
        return df[df["group"].isin(["B", "C", "D"])]
    return df[df["group"] == g]


def write_group_comparison(df: pd.DataFrame, path: Path) -> None:
    lines = [
        "=" * 80,
        "GROUP COMPARISON — MAGENTA OPENING BAR + CATALYST PROXY",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
        "Return: positive = stock went DOWN (short won). Dual win def: raw=any, thr=>=0.1%",
        "",
        "Groups:",
        "  A = Magenta + ANY catalyst (gap>=-3% OR earnings overnight)",
        "  B = Magenta + gap-down only (no earnings)",
        "  C = Magenta + earnings only (gap < -3%)",
        "  D = Magenta + BOTH earnings AND gap-down >= -3%",
        "  E = NAKED magenta — no catalyst proxy",
        "=" * 80, "",
    ]
    for w, rcol, rwcol, rtwcol in WINDOWS:
        label = f"{w}-bar ({w*5} min)" if isinstance(w, int) else "End-of-Day"
        lines.append(f"  Window: {label}")
        lines.append(f"  {'Grp':<5}  {'WinRaw':>7}  {'WinThr(0.1%)':>13}  {'n':>5}  Returns")
        lines.append(f"  {'-'*70}")
        for g in ["A", "B", "C", "D", "E"]:
            sub = _group_df(df, g)
            rw, rt, n = _wr_pair(sub, rwcol, rtwcol)
            ret_s = _ret_str(sub, rcol)
            lines.append(f"  {g:<5}  {rw:>7}  {rt:>13}  {n:>5}  {ret_s}")
        lines.append("")

    n_a = len(_group_df(df, "A"))
    if n_a < 80:
        lines.append(
            f"  ⚠  Group A n={n_a} — INSUFFICIENT SAMPLE (<80). "
            "Results are DIRECTIONAL ONLY, not statistically conclusive."
        )
    elif n_a < 100:
        lines.append(f"  ⚠  Group A n={n_a} — BORDERLINE SAMPLE SIZE (<100)")
    else:
        lines.append(f"  Group A total signals: {n_a}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ Saved {path.name}")


def write_gap_size_buckets(df: pd.DataFrame, path: Path) -> None:
    """GAP_SMALL vs GAP_LARGE vs GAP_EXTREME win rates."""
    # Group A + B only (gap signals)
    gap_df = df[df["group"].isin(["A", "B", "D"])].copy()

    buckets = ["GAP_SMALL", "GAP_LARGE", "GAP_EXTREME"]
    lines = [
        "=" * 76,
        "GAP SIZE BUCKET ANALYSIS — Groups A, B, D (gap-containing signals)",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
        "GAP_SMALL: gap -3% to -5%   GAP_LARGE: -5% to -10%   GAP_EXTREME: < -10%",
        "Return: positive = stock went DOWN. Dual win def.",
        "=" * 76, "",
    ]

    for bkt in buckets:
        sub = gap_df[gap_df["catalyst_strength_bucket"] == bkt]
        lines.append(f"  {bkt}  (n={len(sub)})")
        if len(sub) == 0:
            lines.append("    (no data)")
            lines.append("")
            continue
        # Gap stats
        gp = sub["gap_pct"].dropna()
        lines.append(
            f"    avg gap: {gp.mean():+.2f}%  "
            f"min: {gp.min():+.2f}%  max: {gp.max():+.2f}%"
        )
        for w, rcol, rwcol, rtwcol in WINDOWS:
            label = f"{w*5} min" if isinstance(w, int) else "EOD"
            rw, rt, n = _wr_pair(sub, rwcol, rtwcol)
            ret_s = _ret_str(sub, rcol)
            lines.append(
                f"    {label:>8}  win_raw={rw}  win_thr={rt}  (n={n})  {ret_s}"
            )
        lines.append("")

    # Gap size vs EOD return correlation
    sub_gap = gap_df[gap_df["gap_pct"].notna() & gap_df["return_eod"].notna()].copy()
    if len(sub_gap) > 5:
        corr = sub_gap["gap_pct"].corr(sub_gap["return_eod"])
        lines.append(
            f"  Gap size vs EOD short return correlation: r = {corr:.3f}"
        )
        lines.append(
            "  (negative r = bigger down-gap → bigger short win; "
            "positive r = gap fades / mean-reverts)"
        )
        lines.append("")

    # Per-ticker avg gap size
    lines.append("  Average gap size per ticker (gap signals only):")
    ticker_gaps = []
    for tkr, g in gap_df.groupby("ticker"):
        avg_g = g["gap_pct"].mean()
        ticker_gaps.append((tkr, avg_g, len(g)))
    ticker_gaps.sort(key=lambda x: x[1])
    for tkr, ag, n in ticker_gaps:
        lines.append(f"    {tkr:<8}  avg gap: {ag:+.2f}%  (n={n})")

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ Saved {path.name}")


def write_open_bucket_summary(df: pd.DataFrame, path: Path) -> None:
    sub_a   = _group_df(df, "A")
    buckets = ["FIRST_BAR", "EARLY_OPEN", "OPEN_WINDOW"]
    lines = [
        "=" * 72,
        "OPEN BUCKET WIN RATES — Group A (Magenta + ANY Catalyst) Only",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
        "Return: positive = stock went DOWN. Dual win definition.",
        "=" * 72, "",
    ]
    for bkt in buckets:
        sub = sub_a[sub_a["signal_bar_bucket"] == bkt]
        lines.append(f"  {bkt}  (n={len(sub)})")
        for w, rcol, rwcol, rtwcol in WINDOWS:
            label = f"{w*5} min" if isinstance(w, int) else "EOD"
            rw, rt, n = _wr_pair(sub, rwcol, rtwcol)
            lines.append(f"    {label:>8}  win_raw={rw}  win_thr={rt}  (n={n})")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ Saved {path.name}")


def write_per_ticker_summary(df: pd.DataFrame, path: Path) -> None:
    sub_a = _group_df(df, "A").copy()
    rows = []
    for tkr, g in sub_a.groupby("ticker"):
        s_raw = g[g["win_raw_eod"].notna()]
        s_thr = g[g["win_thr_eod"].notna()]
        rw = s_raw["win_raw_eod"].mean() * 100 if len(s_raw) > 0 else np.nan
        rt = s_thr["win_thr_eod"].mean() * 100 if len(s_thr) > 0 else np.nan
        rows.append((tkr, len(g), rw, rt, assign_ticker_quality(tkr)))

    rows.sort(key=lambda x: (np.isnan(x[2]), -(x[2] if not np.isnan(x[2]) else 0)))

    lines = [
        "=" * 80,
        "PER-TICKER EOD WIN RATES — Group A (Catalyst-Confirmed Magenta), Ranked",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
        "win_raw=any lower close   win_thr=lower by >=0.1% (noise-filtered)",
        "★ STRONG_SHORT  = win_raw_eod > 60%  (catalyst confirms short edge)",
        "✗ FADE_SHORT    = win_raw_eod < 40%  (bounce name even with catalyst)",
        "=" * 80, "",
        f"  {'Ticker':<8}  {'n':>4}  {'WinRaw EOD':>11}  {'WinThr EOD':>11}  Quality",
        f"  {'-'*65}",
    ]
    for tkr, n, rw, rt, qual in rows:
        rw_s = f"{rw:5.1f}%" if not np.isnan(rw) else "  n/a"
        rt_s = f"{rt:5.1f}%" if not np.isnan(rt) else "  n/a"
        flag = ""
        if not np.isnan(rw):
            if rw > 60:    flag = "  ★ STRONG_SHORT"
            elif rw < 40:  flag = "  ✗ FADE_SHORT"
        lines.append(f"  {tkr:<8}  {n:>4}  {rw_s:>11}  {rt_s:>11}  {qual}{flag}")

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ Saved {path.name}")


def write_catalyst_lift_summary(df: pd.DataFrame, path: Path) -> None:
    """THE PAYOFF TABLE: naked vs catalyst-confirmed win rates."""

    def _eod_wr(mask):
        s = df[mask & df["win_raw_eod"].notna()]
        if s.empty: return "  n/a", 0
        return f"{s['win_raw_eod'].mean()*100:5.1f}%", len(s)

    def _eod_wt(mask):
        s = df[mask & df["win_thr_eod"].notna()]
        if s.empty: return "  n/a", 0
        return f"{s['win_thr_eod'].mean()*100:5.1f}%", len(s)

    ga = df["group"].isin(["B", "C", "D"])   # A = any catalyst = union of B+C+D
    gb = df["group"] == "B"
    gc = df["group"] == "C"
    gd = df["group"] == "D"
    ge = df["group"] == "E"

    a_wr, a_n = _eod_wr(ga)
    a_wt, _   = _eod_wt(ga)
    b_wr, b_n = _eod_wr(gb)
    c_wr, c_n = _eod_wr(gc)
    d_wr, d_n = _eod_wr(gd)
    e_wr, e_n = _eod_wr(ge)

    try:
        a_f = float(a_wr.strip().replace("%", ""))
        lift = a_f - NAKED_EOD
        lift_str = f"+{lift:.1f}pp vs naked" if lift >= 0 else f"{lift:.1f}pp vs naked"
    except ValueError:
        lift_str = "n/a"

    lines = [
        "=" * 76,
        "CATALYST LIFT SUMMARY — THE PAYOFF TABLE",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
        "Return: positive = stock went DOWN (short won).",
        "=" * 76, "",
        f"  {'Signal Type':<40}  {'WinRaw EOD':>11}  {'WinThr EOD':>11}  n",
        f"  {'-'*70}",
        f"  {'Naked magenta EOD (prior study benchmark)':<40}  {NAKED_EOD:>10.1f}%           —",
        f"  {'Group E — Naked magenta (this study)':<40}  {e_wr:>11}              {e_n}",
        f"  {'Group A — Catalyst-confirmed (any)':<40}  {a_wr:>11}  {a_wt:>11}  {a_n}",
        f"  {'Group B — Gap-down only (no earnings)':<40}  {b_wr:>11}              {b_n}",
        f"  {'Group C — Earnings only (no big gap)':<40}  {c_wr:>11}              {c_n}",
        f"  {'Group D — BOTH earnings + gap (double)':<40}  {d_wr:>11}              {d_n}",
        "",
        f"  ▶ HEADLINE: Naked magenta {NAKED_EOD:.1f}%  →  Catalyst-confirmed {a_wr.strip()}",
        f"    Catalyst proxy added: {lift_str}",
        "",
    ]

    # Catalyst strength breakdown
    lines.append("  Catalyst Strength Buckets (all groups with catalyst):")
    for bkt in ["GAP_SMALL", "GAP_LARGE", "GAP_EXTREME", "EARNINGS_GAP", "EARNINGS_FLAT"]:
        sub = df[df["catalyst_strength_bucket"] == bkt]
        rw, rt, n = _wr_pair(sub, "win_raw_eod", "win_thr_eod")
        lines.append(f"    {bkt:<18}  win_raw={rw}  win_thr={rt}  (n={n})")
    lines.append("")

    # Sample size warning
    if a_n < 80:
        lines.append(
            f"  ⚠  Group A n={a_n} — INSUFFICIENT SAMPLE (<80). "
            "Results are DIRECTIONAL ONLY."
        )
    elif a_n < 100:
        lines.append(f"  ⚠  Group A n={a_n} — borderline sample size (<100).")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ Saved {path.name}")


# ══════════════════════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════════════════════

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

    groups = ["A", "B", "C", "D", "E"]
    labels = {
        "A": "A: Magenta+Catalyst",
        "B": "B: Gap Only",
        "C": "C: Earnings Only",
        "D": "D: Both",
        "E": "E: Naked Magenta",
    }
    windows_map = [
        (6,     "win_raw_6bar",  "30 min"),
        (12,    "win_raw_12bar", "60 min"),
        (24,    "win_raw_24bar", "120 min"),
        ("EOD", "win_raw_eod",   "EOD"),
    ]
    colors = ["#E040FB", "#AB47BC", "#FFA726", "#78909C"]

    fig = go.Figure()
    for (w, wcol, wlabel), color in zip(windows_map, colors):
        wr_vals = []
        for g in groups:
            sub = _group_df(df, g)
            sub = sub[sub[wcol].notna()]
            wr_vals.append(sub[wcol].mean() * 100 if len(sub) > 0 else 0.0)
        fig.add_trace(go.Bar(
            name=wlabel,
            x=[labels[g] for g in groups],
            y=[round(v, 2) for v in wr_vals],
            marker_color=color,
            text=[f"{v:.1f}%" for v in wr_vals],
            textposition="outside",
        ))

    fig.add_hline(y=50, line_dash="dash", line_color="gray",
                  annotation_text="50% baseline")
    fig.update_layout(
        title="Magenta Catalyst Proxy — Short Win Rate by Group (A–E)",
        yaxis_title="Win Rate % (positive = short won)",
        xaxis_title="Signal Group",
        barmode="group", template="plotly_dark",
        height=560, yaxis_range=[0, 100],
    )
    fig.write_html(str(path))
    print(f"  ✓ Saved {path.name}")


def chart_gap_size_vs_winrate(df: pd.DataFrame, path: Path) -> None:
    go = _try_plotly()
    if not go:
        print(f"  ⚠ plotly not installed — skipping {path.name}")
        return

    sub = df[df["gap_pct"].notna() & df["return_eod"].notna() &
             (df["group"].isin(["A", "B", "D"]))].copy()

    if sub.empty:
        print(f"  ⚠ no gap data — skipping {path.name}")
        return

    colors_map = {"GAP_SMALL": "#FFA726", "GAP_LARGE": "#E040FB",
                  "GAP_EXTREME": "#EF5350", "EARNINGS_GAP": "#66BB6A",
                  "EARNINGS_FLAT": "#26C6DA", "NONE": "#78909C"}

    fig = go.Figure()
    for bkt, grp in sub.groupby("catalyst_strength_bucket"):
        fig.add_trace(go.Scatter(
            x=grp["gap_pct"],
            y=grp["return_eod"] * 100,
            mode="markers",
            name=str(bkt),
            marker=dict(
                color=colors_map.get(str(bkt), "#78909C"),
                size=6, opacity=0.7,
            ),
        ))

    fig.add_hline(y=0, line_dash="dash", line_color="gray",
                  annotation_text="breakeven")
    fig.add_vline(x=GAP_THRESH, line_dash="dot", line_color="#FFA726",
                  annotation_text=f"gap threshold ({GAP_THRESH}%)")
    fig.update_layout(
        title="Gap Size vs EOD Short Return — Catalyst Signals",
        xaxis_title="Gap Pct % (negative = gap down)",
        yaxis_title="EOD Short Return % (positive = won)",
        template="plotly_dark", height=520,
    )
    fig.write_html(str(path))
    print(f"  ✓ Saved {path.name}")


def chart_catalyst_lift_summary(df: pd.DataFrame, path: Path) -> None:
    go = _try_plotly()
    if not go:
        print(f"  ⚠ plotly not installed — skipping {path.name}")
        return

    labels_all = [
        "Naked\n(benchmark)",
        "Group E\n(naked this study)",
        "Group A\n(any catalyst)",
        "Group B\n(gap only)",
        "Group C\n(earnings only)",
        "Group D\n(both)",
    ]
    masks = [None, "E", "A", "B", "C", "D"]
    wr_vals = [NAKED_EOD]  # first bar is the benchmark

    for g in ["E", "A", "B", "C", "D"]:
        sub = _group_df(df, g)
        sub = sub[sub["win_raw_eod"].notna()]
        wr_vals.append(sub["win_raw_eod"].mean() * 100 if len(sub) > 0 else 0.0)

    bar_colors = [
        "#78909C",   # benchmark
        "#9E9E9E",   # naked E
        "#E040FB",   # A — full catalyst
        "#AB47BC",   # B — gap
        "#FFA726",   # C — earnings
        "#66BB6A",   # D — both
    ]

    fig = go.Figure(go.Bar(
        x=["Naked\n(benchmark)", "Group E\n(naked)", "Group A\n(any catalyst)",
           "Group B\n(gap only)", "Group C\n(earnings only)", "Group D\n(both)"],
        y=[round(v, 2) for v in wr_vals],
        marker_color=bar_colors,
        text=[f"{v:.1f}%" for v in wr_vals],
        textposition="outside",
    ))
    fig.add_hline(y=50, line_dash="dash", line_color="gray",
                  annotation_text="50% baseline")
    fig.update_layout(
        title="Catalyst Lift — Naked Magenta vs Catalyst-Confirmed EOD Win Rate",
        yaxis_title="EOD Win Rate % (short side)",
        xaxis_title="Signal Group",
        template="plotly_dark",
        height=520, yaxis_range=[0, 100],
    )
    fig.write_html(str(path))
    print(f"  ✓ Saved {path.name}")


def chart_ticker_winrates_catalyst(df: pd.DataFrame, path: Path) -> None:
    go = _try_plotly()
    if not go:
        print(f"  ⚠ plotly not installed — skipping {path.name}")
        return

    sub_a = _group_df(df, "A").copy()
    rows = []
    for tkr, g in sub_a.groupby("ticker"):
        s = g[g["win_raw_eod"].notna()]
        wr = s["win_raw_eod"].mean() * 100 if len(s) > 0 else 0.0
        rows.append((tkr, wr, len(g)))

    rows.sort(key=lambda x: x[1])  # ascending for horizontal bar
    tickers = [r[0] for r in rows]
    wr_vals = [r[1] for r in rows]
    ns      = [r[2] for r in rows]

    bar_colors = []
    for w in wr_vals:
        if w > 60:   bar_colors.append("#E040FB")   # strong short
        elif w < 40: bar_colors.append("#66BB6A")   # fade / bounce
        else:        bar_colors.append("#78909C")   # neutral

    fig = go.Figure(go.Bar(
        x=wr_vals,
        y=tickers,
        orientation="h",
        marker_color=bar_colors,
        text=[f"{v:.1f}% (n={n})" for v, n in zip(wr_vals, ns)],
        textposition="outside",
    ))
    fig.add_vline(x=50, line_dash="dash", line_color="gray",
                  annotation_text="50% baseline")
    fig.update_layout(
        title="Per-Ticker EOD Win Rate — Group A (Catalyst-Confirmed Magenta)",
        xaxis_title="EOD Win Rate % (short side)",
        xaxis_range=[0, 105],
        template="plotly_dark", height=640,
    )
    fig.write_html(str(path))
    print(f"  ✓ Saved {path.name}")


# ══════════════════════════════════════════════════════════════════════════════
# REQUESTED NUMBERS CONSOLE REPORT
# ══════════════════════════════════════════════════════════════════════════════

def print_requested_numbers(df: pd.DataFrame) -> None:
    ga = df["group"].isin(["B", "C", "D"])   # A = any catalyst
    gb = df["group"] == "B"
    gc = df["group"] == "C"
    gd = df["group"] == "D"
    ge = df["group"] == "E"

    def _eod_raw(mask):
        s = df[mask & df["win_raw_eod"].notna()]
        if s.empty: return "n/a", 0
        return f"{s['win_raw_eod'].mean()*100:.1f}%", len(s)

    def _eod_thr(mask):
        s = df[mask & df["win_thr_eod"].notna()]
        if s.empty: return "n/a", 0
        return f"{s['win_thr_eod'].mean()*100:.1f}%", len(s)

    a_raw, a_n = _eod_raw(ga)
    a_thr, _   = _eod_thr(ga)
    b_raw, b_n = _eod_raw(gb)
    c_raw, c_n = _eod_raw(gc)
    d_raw, d_n = _eod_raw(gd)
    e_raw, e_n = _eod_raw(ge)

    # Gap size buckets
    gl_raw = _eod_raw(df["catalyst_strength_bucket"] == "GAP_LARGE")[0]
    gx_raw = _eod_raw(df["catalyst_strength_bucket"] == "GAP_EXTREME")[0]

    # Top / bottom 3 by EOD win rate in Group A
    by_tkr = []
    for tkr, g in df[ga].groupby("ticker"):
        s = g[g["win_raw_eod"].notna()]
        wr = s["win_raw_eod"].mean() * 100 if len(s) > 0 else np.nan
        by_tkr.append((tkr, wr, len(g)))
    by_tkr.sort(key=lambda x: (np.isnan(x[1]), -(x[1] if not np.isnan(x[1]) else 0)))

    try:
        a_f   = float(a_raw.replace("%", "").strip())
        lift  = a_f - NAKED_EOD
        headline = (
            f"Naked magenta {NAKED_EOD:.1f}%  →  Catalyst-confirmed {a_f:.1f}%  "
            f"(+{lift:.1f}pp)" if lift >= 0
            else
            f"Naked magenta {NAKED_EOD:.1f}%  →  Catalyst-confirmed {a_f:.1f}%  "
            f"({lift:.1f}pp)"
        )
    except ValueError:
        headline = f"Naked magenta {NAKED_EOD:.1f}%  →  Catalyst-confirmed {a_raw}"

    n_flag = ""
    if a_n < 80:
        n_flag = "  ⚠ INSUFFICIENT (<80) — DIRECTIONAL ONLY"
    elif a_n < 100:
        n_flag = "  ⚠ BORDERLINE (<100)"

    print()
    print("=" * 76)
    print("  REQUESTED NUMBERS — MAGENTA CATALYST PROXY STUDY")
    print("=" * 76)
    print(f"   1. Group A EOD win_raw  (catalyst-confirmed)  : {a_raw}  (n={a_n}){n_flag}")
    print(f"   2. Group A EOD win_thr  (0.1% threshold)      : {a_thr}")
    print(f"   3. Group B EOD win_raw  (gap only)             : {b_raw}  (n={b_n})")
    print(f"   4. Group C EOD win_raw  (earnings only)        : {c_raw}  (n={c_n})")
    print(f"   5. Group D EOD win_raw  (earnings + gap — both): {d_raw}  (n={d_n})")
    print(f"   6. Group E EOD win_raw  (naked magenta)        : {e_raw}  (n={e_n})")
    print(f"   7. GAP_LARGE  (-5% to -10%) EOD               : {gl_raw}")
    print(f"   8. GAP_EXTREME (< -10%)    EOD                : {gx_raw}")
    print(f"   9. Top 3 tickers by EOD win_raw (Group A):")
    for tkr, wr, n in by_tkr[:3]:
        wr_s = f"{wr:.1f}%" if not np.isnan(wr) else "n/a"
        print(f"        {tkr:<8} {wr_s}  (n={n})")
    print(f"  10. Bottom 3 tickers (bounce even with catalyst):")
    for tkr, wr, n in by_tkr[-3:]:
        wr_s = f"{wr:.1f}%" if not np.isnan(wr) else "n/a"
        print(f"        {tkr:<8} {wr_s}  (n={n})")
    print(f"  11. Group A total signals: {a_n}{n_flag}")
    print(f"  12. HEADLINE: {headline}")
    print("=" * 76)
    print()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print()
    print("=" * 76)
    print("  MAGENTA OPENING BAR + CATALYST PROXY STUDY (SHORT SIDE)")
    print(f"  Universe: {len(UNIVERSE)} tickers  |  Study: {STUDY_START} → {STUDY_END}")
    print("  Opening window: 09:30–10:00 ET")
    print("  Signal: cs <= -70, NOT NR7  +  gap <= -3% OR earnings overnight")
    print("  Groups: A=Catalyst  B=GapOnly  C=EarningsOnly  D=Both  E=Naked")
    print("  Return: positive = stock went DOWN (short won)")
    print("=" * 76)

    # ── Step 1: Build earnings lookup once for all tickers ───────────────────
    print("\n▷  Building earnings date lookup (yfinance → hardcoded fallback) …")
    earnings_lookup = build_earnings_lookup(UNIVERSE)

    # ── Step 2: Process each ticker ──────────────────────────────────────────
    all_chunks: list[pd.DataFrame] = []
    header_written = False

    for idx, ticker in enumerate(UNIVERSE, 1):
        print(f"\n[{idx:>2}/{len(UNIVERSE)}] {ticker}")
        result = process_ticker(ticker, earnings_lookup)

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
            ga_so_far    = sum(int((c["group"] == "A").sum()) for c in all_chunks)
            print(
                f"\n  >>> Progress: {idx}/{len(UNIVERSE)} tickers | "
                f"{total_so_far:,} magenta open bars | {ga_so_far} Group A <<<\n"
            )

    if not all_chunks:
        print("\n✗ No signals collected — check API keys and date range.")
        return

    full = pd.concat(all_chunks, ignore_index=True)

    # Group counts
    counts = {g: int((full["group"] == g).sum()) for g in "BCDE"}
    counts["A"] = counts["B"] + counts["C"] + counts["D"]   # A = union of B+C+D
    n_a    = counts["A"]

    print(f"\n{'=' * 76}")
    print(f"  TOTAL MAGENTA OPENING BARS : {len(full):,}")
    for g in "ABCDE":
        labels_ = {
            "A": "catalyst (any=B+C+D)",
            "B": "gap only",
            "C": "earnings only",
            "D": "both (gap+earn)",
            "E": "naked magenta",
        }
        print(f"  Group {g} ({labels_[g]:<22}) : {counts[g]}")
    if n_a < 80:
        print(
            f"\n  ⚠⚠  Group A n={n_a} — INSUFFICIENT SAMPLE (<80). "
            "Results are DIRECTIONAL ONLY, not statistically conclusive. ⚠⚠"
        )
    elif n_a < 100:
        print(f"\n  ⚠  Group A n={n_a} — borderline sample size (<100)")
    print(f"{'=' * 76}\n")

    # ── Step 3: Write summaries ──────────────────────────────────────────────
    print("▷  Writing summaries …")
    write_group_comparison(full,      OUTPUTS_DIR / "summary_group_comparison.txt")
    write_gap_size_buckets(full,      OUTPUTS_DIR / "summary_gap_size_buckets.txt")
    write_open_bucket_summary(full,   OUTPUTS_DIR / "summary_by_open_bucket.txt")
    write_per_ticker_summary(full,    OUTPUTS_DIR / "summary_by_ticker.txt")
    write_catalyst_lift_summary(full, OUTPUTS_DIR / "summary_catalyst_lift.txt")

    # ── Step 4: Build charts ─────────────────────────────────────────────────
    print("▷  Building charts …")
    chart_group_comparison(full,       CHARTS_DIR / "group_comparison.html")
    chart_gap_size_vs_winrate(full,    CHARTS_DIR / "gap_size_vs_winrate.html")
    chart_catalyst_lift_summary(full,  CHARTS_DIR / "catalyst_lift_summary.html")
    chart_ticker_winrates_catalyst(full, CHARTS_DIR / "ticker_winrates_catalyst.html")

    # ── Step 5: Print requested numbers ──────────────────────────────────────
    print_requested_numbers(full)

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"✅  All outputs saved to: {OUTPUTS_DIR}")
    print(f"   magenta_catalyst_signals.csv        → {len(full):,} rows")
    print("   summary_group_comparison.txt")
    print("   summary_gap_size_buckets.txt")
    print("   summary_by_open_bucket.txt")
    print("   summary_by_ticker.txt")
    print("   summary_catalyst_lift.txt")
    print("   earnings_detection_log.txt")
    print("   charts/group_comparison.html")
    print("   charts/gap_size_vs_winrate.html")
    print("   charts/catalyst_lift_summary.html")
    print("   charts/ticker_winrates_catalyst.html")
    print()


if __name__ == "__main__":
    main()
