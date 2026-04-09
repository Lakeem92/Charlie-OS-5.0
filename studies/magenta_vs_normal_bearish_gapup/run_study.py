import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

from pathlib import Path
from datetime import timedelta
import math
import warnings

import numpy as np
import pandas as pd

from shared.data_router import DataRouter
from shared.indicators.trend_strength_candles import TrendStrengthCandles

warnings.filterwarnings("ignore")

STUDY_DIR = Path(r"C:\QuantLab\Data_Lab\studies\magenta_vs_normal_bearish_gapup")
OUTPUT_DIR = STUDY_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_RESULTS = Path(r"C:\QuantLab\Data_Lab\studies\gap_fade_contrary_candle\outputs\results_analysis.csv")
OPENING_CACHE = OUTPUT_DIR / "opening_bar_metrics.csv"
ENRICHED_CSV = OUTPUT_DIR / "magenta_vs_normal_events.csv"
ENRICHED_ALL_CSV = OUTPUT_DIR / "magenta_vs_normal_events_all.csv"
SUMMARY_CSV = OUTPUT_DIR / "summary_by_group.csv"
SUMMARY_TXT = OUTPUT_DIR / "summary.txt"

SESSION_OPEN_ET = "09:30"
SESSION_CLOSE_ET = "16:00"
CHUNK_DAYS = 120
MIN_GAP = 0.02
BOOTSTRAP_N = 3000
RNG_SEED = 42


def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for c in df.columns:
        lc = c.lower()
        if lc == "open":
            rename[c] = "Open"
        elif lc == "high":
            rename[c] = "High"
        elif lc == "low":
            rename[c] = "Low"
        elif lc == "close":
            rename[c] = "Close"
        elif lc in ("volume", "vol"):
            rename[c] = "Volume"
    return df.rename(columns=rename)


def _two_prop_z_test(success_a: int, n_a: int, success_b: int, n_b: int) -> float:
    if n_a == 0 or n_b == 0:
        return float("nan")
    p_a = success_a / n_a
    p_b = success_b / n_b
    p_pool = (success_a + success_b) / (n_a + n_b)
    denom = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    if denom == 0:
        return float("nan")
    z = (p_a - p_b) / denom
    # two-sided p-value from normal CDF using erfc
    p_val = math.erfc(abs(z) / math.sqrt(2.0))
    return p_val


def _bootstrap_mean_diff_ci(a: np.ndarray, b: np.ndarray, n_boot: int, rng_seed: int) -> tuple[float, float, float]:
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    if len(a) == 0 or len(b) == 0:
        return (float("nan"), float("nan"), float("nan"))

    rng = np.random.default_rng(rng_seed)
    diffs = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        sa = rng.choice(a, size=len(a), replace=True)
        sb = rng.choice(b, size=len(b), replace=True)
        diffs[i] = sa.mean() - sb.mean()

    observed = float(a.mean() - b.mean())
    lo, hi = np.quantile(diffs, [0.025, 0.975])
    return observed, float(lo), float(hi)


def _confidence_tag(n: int) -> str:
    if n < 10:
        return "INSUFFICIENT"
    if n < 20:
        return "LOW"
    return "HIGH"


def _fetch_opening_metrics(events: pd.DataFrame) -> pd.DataFrame:
    needed_cols = ["ticker", "date", "cs", "is_nr7", "bar1_time", "data_ok"]

    if OPENING_CACHE.exists():
        cache = pd.read_csv(OPENING_CACHE)
        for col in needed_cols:
            if col not in cache.columns:
                cache[col] = np.nan
    else:
        cache = pd.DataFrame(columns=needed_cols)

    key_cols = ["ticker", "date"]
    event_keys = events[key_cols].drop_duplicates()
    cache_keys = cache[key_cols].drop_duplicates() if len(cache) else pd.DataFrame(columns=key_cols)

    pending = event_keys.merge(cache_keys, on=key_cols, how="left", indicator=True)
    pending = pending[pending["_merge"] == "left_only"][key_cols]

    if pending.empty:
        print("Opening-bar cache hit: no API pull needed.")
        return cache[needed_cols]

    print(f"Opening-bar enrichment pending events: {len(pending)}")
    pending_by_ticker = pending.groupby("ticker")["date"].apply(list).to_dict()

    rows = []
    total_tickers = len(pending_by_ticker)

    for idx, (ticker, dates) in enumerate(sorted(pending_by_ticker.items()), start=1):
        print(f"  [{idx}/{total_tickers}] {ticker}: loading intraday chunks")
        dates_ts = pd.to_datetime(dates)
        min_dt = dates_ts.min() - timedelta(days=40)
        max_dt = dates_ts.max() + timedelta(days=1)

        chunks = []
        cursor = min_dt
        while cursor <= max_dt:
            chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), max_dt)
            chunks.append((cursor.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")))
            cursor = chunk_end + timedelta(days=1)

        frames = []
        for start_str, end_str in chunks:
            try:
                intraday = DataRouter.get_price_data(
                    ticker,
                    start_str,
                    end_date=end_str,
                    timeframe="5min",
                    fallback=False,
                )
            except Exception:
                intraday = None

            if intraday is None or len(intraday) == 0:
                continue

            intraday = intraday.sort_index()
            frames.append(intraday)

        if not frames:
            for d in dates:
                rows.append({"ticker": ticker, "date": d, "cs": np.nan, "is_nr7": np.nan, "bar1_time": "", "data_ok": False})
            continue

        full = pd.concat(frames).sort_index()
        full = full[~full.index.duplicated(keep="last")]
        full = _normalize_cols(full)

        required = {"Open", "High", "Low", "Close"}
        if not required.issubset(full.columns):
            for d in dates:
                rows.append({"ticker": ticker, "date": d, "cs": np.nan, "is_nr7": np.nan, "bar1_time": "", "data_ok": False})
            continue

        try:
            ind = TrendStrengthCandles().compute(full)
        except Exception:
            for d in dates:
                rows.append({"ticker": ticker, "date": d, "cs": np.nan, "is_nr7": np.nan, "bar1_time": "", "data_ok": False})
            continue

        if isinstance(ind.index, pd.DatetimeIndex) and ind.index.tz is not None:
            ind.index = ind.index.tz_convert("US/Eastern")

        for d in dates:
            dts = pd.Timestamp(d)
            day = ind[ind.index.date == dts.date()]
            if day is None or len(day) == 0:
                rows.append({"ticker": ticker, "date": d, "cs": np.nan, "is_nr7": np.nan, "bar1_time": "", "data_ok": False})
                continue

            session = day.between_time(SESSION_OPEN_ET, SESSION_CLOSE_ET)
            if session is None or len(session) == 0:
                rows.append({"ticker": ticker, "date": d, "cs": np.nan, "is_nr7": np.nan, "bar1_time": "", "data_ok": False})
                continue

            bar1 = session.iloc[0]
            rows.append({
                "ticker": ticker,
                "date": d,
                "cs": float(bar1.get("cs", np.nan)),
                "is_nr7": bool(bar1.get("is_nr7", False)) if not pd.isna(bar1.get("is_nr7", np.nan)) else np.nan,
                "bar1_time": str(session.index[0]),
                "data_ok": True,
            })

    new_df = pd.DataFrame(rows, columns=needed_cols)
    merged = pd.concat([cache[needed_cols], new_df], ignore_index=True)
    merged = merged.drop_duplicates(subset=["ticker", "date"], keep="last")
    merged.to_csv(OPENING_CACHE, index=False)

    return merged


def main() -> None:
    if not SOURCE_RESULTS.exists():
        raise FileNotFoundError(f"Missing source results: {SOURCE_RESULTS}")

    src = pd.read_csv(SOURCE_RESULTS)
    base = src[
        (src["direction"] == "GAP_UP")
        & (src["candle_color"] == "BEARISH")
        & (src["abs_gap_pct"] >= MIN_GAP)
    ].copy()

    print(f"Base bearish gap-up events loaded: {len(base)}")

    opening = _fetch_opening_metrics(base[["ticker", "date"]].drop_duplicates())
    df = base.merge(opening, on=["ticker", "date"], how="left")

    # Group labels approved by user
    df["group"] = np.where(
        (df["cs"] <= -70) & (df["is_nr7"] == False),
        "magenta_max_bear",
        np.where(df["cs"] > -70, "bearish_non_magenta", "excluded_or_missing"),
    )

    usable = df[df["group"].isin(["magenta_max_bear", "bearish_non_magenta"])].copy()

    # Win definitions
    usable["win_from_open"] = usable["eod_return_from_open"] > 0
    usable["win_from_ft_entry"] = usable["eod_return"] > 0

    # Group summary
    out_rows = []
    for g, sub in usable.groupby("group"):
        n = len(sub)
        ft_n = int(sub["has_ft"].sum())
        ft_subset = sub[sub["has_ft"] == True]

        out_rows.append({
            "group": g,
            "n": n,
            "confidence": _confidence_tag(n),
            "win_rate_from_open_pct": sub["win_from_open"].mean() * 100,
            "avg_eod_return_from_open_pct": sub["eod_return_from_open"].mean() * 100,
            "ft_rate_pct": sub["has_ft"].mean() * 100,
            "ft_n": ft_n,
            "win_rate_from_ft_entry_pct": ft_subset["win_from_ft_entry"].mean() * 100 if len(ft_subset) else np.nan,
            "avg_hod_min": sub["hod_minutes_from_open"].mean(),
            "median_hod_min": sub["hod_minutes_from_open"].median(),
            "avg_lod_min": sub["lod_minutes_from_open"].mean(),
            "median_lod_min": sub["lod_minutes_from_open"].median(),
            "avg_ft_minutes": ft_subset["ft_minutes_from_open"].mean() if len(ft_subset) else np.nan,
            "median_ft_minutes": ft_subset["ft_minutes_from_open"].median() if len(ft_subset) else np.nan,
        })

    summary = pd.DataFrame(out_rows).sort_values("group")
    summary.to_csv(SUMMARY_CSV, index=False)

    # Pairwise tests and CI deltas
    a = usable[usable["group"] == "magenta_max_bear"]
    b = usable[usable["group"] == "bearish_non_magenta"]

    open_p = _two_prop_z_test(int(a["win_from_open"].sum()), len(a), int(b["win_from_open"].sum()), len(b))
    ft_p = _two_prop_z_test(int(a["has_ft"].sum()), len(a), int(b["has_ft"].sum()), len(b))

    hod_obs, hod_lo, hod_hi = _bootstrap_mean_diff_ci(
        a["hod_minutes_from_open"].to_numpy(dtype=float),
        b["hod_minutes_from_open"].to_numpy(dtype=float),
        BOOTSTRAP_N,
        RNG_SEED,
    )
    lod_obs, lod_lo, lod_hi = _bootstrap_mean_diff_ci(
        a["lod_minutes_from_open"].to_numpy(dtype=float),
        b["lod_minutes_from_open"].to_numpy(dtype=float),
        BOOTSTRAP_N,
        RNG_SEED + 1,
    )

    df.to_csv(ENRICHED_ALL_CSV, index=False)
    usable.to_csv(ENRICHED_CSV, index=False)

    lines = []
    lines.append("MAGENTA VS NORMAL BEARISH GAP-UP STUDY")
    lines.append("=" * 72)
    lines.append("Population: gap-up >= 2% + bearish bar-1 (from existing contrary-candle results)")
    lines.append("Group A: cs <= -70 AND NOT NR7")
    lines.append("Group B: bearish bar-1 with cs > -70")
    lines.append("")

    for _, r in summary.iterrows():
        lines.append(f"{r['group']} | n={int(r['n'])} | Confidence={r['confidence']}")
        lines.append(f"  Win rate (from open): {r['win_rate_from_open_pct']:.2f}%")
        lines.append(f"  FT rate (close <= open - 0.40*ATR at least once): {r['ft_rate_pct']:.2f}%")
        lines.append(f"  Win rate (FT-entry subset, n={int(r['ft_n'])}): {r['win_rate_from_ft_entry_pct']:.2f}%")
        lines.append(f"  Avg HoD: {r['avg_hod_min']:.1f} min | Median HoD: {r['median_hod_min']:.1f} min")
        lines.append(f"  Avg LoD: {r['avg_lod_min']:.1f} min | Median LoD: {r['median_lod_min']:.1f} min")
        lines.append(f"  Avg FT time: {r['avg_ft_minutes']:.1f} min | Median FT time: {r['median_ft_minutes']:.1f} min")
        lines.append("")

    lines.append("DIFFERENCE TESTS (A - B)")
    lines.append(f"  Win rate from open p-value (two-proportion z): {open_p:.6f}")
    lines.append(f"  FT rate p-value (two-proportion z): {ft_p:.6f}")
    lines.append(f"  HoD mean diff: {hod_obs:.2f} min | 95% CI [{hod_lo:.2f}, {hod_hi:.2f}]")
    lines.append(f"  LoD mean diff: {lod_obs:.2f} min | 95% CI [{lod_lo:.2f}, {lod_hi:.2f}]")

    SUMMARY_TXT.write_text("\n".join(lines), encoding="utf-8")

    print("\nStudy complete.")
    print(f"Enriched events (usable): {ENRICHED_CSV}")
    print(f"Enriched events (all):    {ENRICHED_ALL_CSV}")
    print(f"Group summary:   {SUMMARY_CSV}")
    print(f"Text summary:    {SUMMARY_TXT}")


if __name__ == "__main__":
    main()
