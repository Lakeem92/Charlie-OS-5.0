#!/usr/bin/env python3
"""
Intraday EMA Cloud Pullback and 21 EMA Structural Failure Study

Primary logic:
- Strong trend day filter: close-from-open >= +/-1.0 ATR14 (daily ATR, prior-day aligned)
- Intraday cloud: EMA10/EMA21 on 5-minute close (RTH only, CT)
- Pullback: directional touch/entry into cloud after early trend expansion
- Break: 5-minute candle CLOSE through EMA21 only (wicks ignored)
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import yaml

sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

STUDY_DIR = Path(__file__).resolve().parent
ROOT_DIR = STUDY_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR / "tools" / "studies"))

from shared.watchlist import get_watchlist
from run_id import resolve_output_dirs

CT_TZ = "America/Chicago"
RTH_START = time(8, 30)
RTH_END = time(15, 0)


def load_config() -> dict:
    with open(STUDY_DIR / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze EMA10/21 pullback and break behavior")
    parser.add_argument("--tickers", nargs="*", default=None, help="Optional ticker override")
    parser.add_argument("--start", default=None, help="Passthrough compatibility argument")
    parser.add_argument("--end", default=None, help="Passthrough compatibility argument")
    parser.add_argument("--intraday", default=None, help="Passthrough compatibility argument")
    return parser.parse_args()


def _confidence_label(n: int) -> str:
    if n < 10:
        return "INSUFFICIENT"
    if n < 20:
        return "LOW"
    return "RELIABLE"


def _safe_mean(series: pd.Series) -> float:
    if series.empty:
        return np.nan
    return float(series.mean())


def _safe_median(series: pd.Series) -> float:
    if series.empty:
        return np.nan
    return float(series.median())


def _to_ct_index(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    idx = pd.to_datetime(out.index, errors="coerce")
    if getattr(idx, "tz", None) is None:
        idx = idx.tz_localize("UTC")
    idx = idx.tz_convert(CT_TZ)
    out.index = idx
    out = out[~out.index.isna()].sort_index()
    return out


def _load_price_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df = df.set_index("timestamp")
    df.columns = [str(c).strip().lower() for c in df.columns]
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {path.name}: {sorted(missing)}")
    return _to_ct_index(df)


def _compute_daily_atr(df_daily: pd.DataFrame, atr_length: int) -> pd.DataFrame:
    out = df_daily.copy().sort_index()
    high = out["high"]
    low = out["low"]
    close = out["close"]

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    out["atr14"] = tr.rolling(atr_length).mean()
    out["atr14_prev"] = out["atr14"].shift(1)
    out["session_date"] = out.index.date
    return out


def _compute_ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def _filter_rth_ct(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    times = out.index.time
    mask = (times >= RTH_START) & (times <= RTH_END)
    return out[mask].copy()


def _tod_bucket(ts: pd.Timestamp) -> Optional[str]:
    t = ts.timetz().replace(tzinfo=None)
    if time(8, 30) <= t < time(10, 0):
        return "morning"
    if time(10, 0) <= t < time(12, 30):
        return "midday"
    if time(12, 30) <= t <= time(15, 0):
        return "afternoon"
    return None


def _bucket_early_expansion(x: float) -> str:
    if pd.isna(x):
        return "unclassified"
    if 0.50 <= x < 0.60:
        return "0.50-0.60"
    if 0.60 <= x < 0.70:
        return "0.60-0.70"
    if 0.70 <= x < 0.80:
        return "0.70-0.80"
    if 0.80 <= x < 1.00:
        return "0.80-1.00"
    if x >= 1.00:
        return "1.00+"
    return "<0.50"


def _intersects_cloud(row: pd.Series, lo_col: str, hi_col: str) -> bool:
    cloud_low = min(float(row[lo_col]), float(row[hi_col]))
    cloud_high = max(float(row[lo_col]), float(row[hi_col]))
    return float(row["high"]) >= cloud_low and float(row["low"]) <= cloud_high


def _favorable_close_quartile(day: pd.DataFrame, direction: str) -> bool:
    day_high = float(day["high"].max())
    day_low = float(day["low"].min())
    day_close = float(day["close"].iloc[-1])
    day_range = day_high - day_low
    if day_range <= 0:
        return False
    clv = (day_close - day_low) / day_range
    if direction == "long":
        return bool(clv >= 0.75)
    return bool(clv <= 0.25)


def _analyze_session(
    ticker: str,
    session_date: datetime.date,
    direction: str,
    day_5m: pd.DataFrame,
    session_open: float,
    session_close: float,
    atr_value: float,
) -> dict:
    day = day_5m.copy().sort_index()
    day["ema10"] = _compute_ema(day["close"], 10)
    day["ema21"] = _compute_ema(day["close"], 21)

    first_30 = day.iloc[:6].copy()
    if len(first_30) < 6:
        return {"exclude_reason": "insufficient_first_30m"}

    if direction == "long":
        first_30["expansion"] = (first_30["high"] - session_open) / atr_value
    else:
        first_30["expansion"] = (session_open - first_30["low"]) / atr_value

    early_expansion_atr = float(first_30["expansion"].max())
    expansion_peak_idx = first_30["expansion"].idxmax()
    early_bucket = _bucket_early_expansion(early_expansion_atr)

    # Determine precondition that trend-side positioning occurred before pullback checks.
    if direction == "long":
        trend_side_mask = day["close"] > day[["ema10", "ema21"]].max(axis=1)
    else:
        trend_side_mask = day["close"] < day[["ema10", "ema21"]].min(axis=1)

    trend_side_idxs = day.index[(trend_side_mask) & (day.index >= expansion_peak_idx)]
    if len(trend_side_idxs) == 0:
        return {
            "ticker": ticker,
            "session_date": session_date,
            "direction": direction,
            "atr14_prev": atr_value,
            "early_expansion_atr": early_expansion_atr,
            "early_expansion_bucket": early_bucket,
            "cloud_pullback": False,
            "ema21_break": False,
            "exclude_reason": "no_trend_side_after_expansion_peak",
        }

    pullback_time = None
    trend_confirm_time = trend_side_idxs[0]
    for ts, row in day.loc[day.index >= trend_confirm_time].iterrows():
        if _intersects_cloud(row, "ema10", "ema21"):
            pullback_time = ts
            break

    cloud_pullback = pullback_time is not None and pullback_time > expansion_peak_idx
    if not cloud_pullback:
        return {
            "ticker": ticker,
            "session_date": session_date,
            "direction": direction,
            "atr14_prev": atr_value,
            "session_open": session_open,
            "session_close": session_close,
            "close_from_open_atr": (session_close - session_open) / atr_value if direction == "long" else (session_open - session_close) / atr_value,
            "early_expansion_atr": early_expansion_atr,
            "early_expansion_bucket": early_bucket,
            "expansion_peak_time": expansion_peak_idx,
            "trend_confirm_time": trend_confirm_time,
            "cloud_pullback": False,
            "pullback_time": pd.NaT,
            "minutes_peak_to_pullback": np.nan,
            "ema21_break": False,
            "ema21_break_time": pd.NaT,
            "tod_bucket": None,
            "new_extreme_after_break": False,
            "structural_failure": np.nan,
            "close_ge_1atr_after_break": np.nan,
            "favorable_close_after_break": np.nan,
            "return_break_to_extreme": np.nan,
            "return_break_to_close": np.nan,
            "minutes_break_to_new_extreme": np.nan,
            "minutes_break_to_close": np.nan,
            "exclude_reason": "",
        }

    after_pullback = day.loc[day.index > pullback_time]
    if direction == "long":
        break_mask = after_pullback["close"] < after_pullback["ema21"]
    else:
        break_mask = after_pullback["close"] > after_pullback["ema21"]

    ema21_break = bool(break_mask.any())
    break_time = after_pullback.index[break_mask][0] if ema21_break else pd.NaT
    minutes_peak_to_pullback = (pullback_time - expansion_peak_idx).total_seconds() / 60.0

    out = {
        "ticker": ticker,
        "session_date": session_date,
        "direction": direction,
        "atr14_prev": atr_value,
        "session_open": session_open,
        "session_close": session_close,
        "close_from_open_atr": (session_close - session_open) / atr_value if direction == "long" else (session_open - session_close) / atr_value,
        "early_expansion_atr": early_expansion_atr,
        "early_expansion_bucket": early_bucket,
        "expansion_peak_time": expansion_peak_idx,
        "trend_confirm_time": trend_confirm_time,
        "cloud_pullback": True,
        "pullback_time": pullback_time,
        "minutes_peak_to_pullback": minutes_peak_to_pullback,
        "ema21_break": ema21_break,
        "ema21_break_time": break_time,
        "tod_bucket": _tod_bucket(break_time) if ema21_break else None,
        "new_extreme_after_break": False,
        "structural_failure": np.nan,
        "close_ge_1atr_after_break": np.nan,
        "favorable_close_after_break": np.nan,
        "return_break_to_extreme": np.nan,
        "return_break_to_close": np.nan,
        "minutes_break_to_new_extreme": np.nan,
        "minutes_break_to_close": np.nan,
        "exclude_reason": "",
    }

    if not ema21_break:
        return out

    break_bar_close = float(day.loc[break_time, "close"])
    pre_break = day.loc[day.index < break_time]
    post_break = day.loc[day.index > break_time]

    if pre_break.empty or post_break.empty:
        out["exclude_reason"] = "insufficient_pre_post_break_bars"
        return out

    if direction == "long":
        prior_extreme = float(pre_break["high"].max())
        post_extreme = float(post_break["high"].max())
        new_extreme = post_extreme > prior_extreme
        out["return_break_to_extreme"] = (post_extreme - break_bar_close) / break_bar_close
        out["return_break_to_close"] = (session_close - break_bar_close) / break_bar_close
        if new_extreme:
            first_new_extreme_ts = post_break.index[post_break["high"] > prior_extreme][0]
            out["minutes_break_to_new_extreme"] = (first_new_extreme_ts - break_time).total_seconds() / 60.0
    else:
        prior_extreme = float(pre_break["low"].min())
        post_extreme = float(post_break["low"].min())
        new_extreme = post_extreme < prior_extreme
        out["return_break_to_extreme"] = (break_bar_close - post_extreme) / break_bar_close
        out["return_break_to_close"] = (break_bar_close - session_close) / break_bar_close
        if new_extreme:
            first_new_extreme_ts = post_break.index[post_break["low"] < prior_extreme][0]
            out["minutes_break_to_new_extreme"] = (first_new_extreme_ts - break_time).total_seconds() / 60.0

    out["new_extreme_after_break"] = bool(new_extreme)
    out["structural_failure"] = bool(not new_extreme)
    out["close_ge_1atr_after_break"] = bool(
        ((session_close - session_open) / atr_value >= 1.0)
        if direction == "long"
        else ((session_open - session_close) / atr_value >= 1.0)
    )
    out["favorable_close_after_break"] = _favorable_close_quartile(day, direction)
    out["minutes_break_to_close"] = (day.index[-1] - break_time).total_seconds() / 60.0
    return out


def _summarize_direction(df_all: pd.DataFrame, direction_label: str) -> dict:
    if direction_label == "combined":
        df = df_all.copy()
    else:
        df = df_all[df_all["direction"] == direction_label].copy()

    n_base = len(df)
    df_pull = df[df["cloud_pullback"]]
    n_pull = len(df_pull)
    df_break = df_pull[df_pull["ema21_break"]]
    n_break = len(df_break)

    return {
        "direction": direction_label,
        "n_base": int(n_base),
        "n_pullback": int(n_pull),
        "pullback_rate": (float(n_pull) / n_base) if n_base else np.nan,
        "n_break": int(n_break),
        "break_rate_among_pullbacks": float(n_break / n_pull) if n_pull else np.nan,
        "new_extreme_rate_after_break": _safe_mean(df_break["new_extreme_after_break"]) if n_break else np.nan,
        "structural_failure_rate": _safe_mean(df_break["structural_failure"]) if n_break else np.nan,
        "close_ge_1atr_after_break_rate": _safe_mean(df_break["close_ge_1atr_after_break"]) if n_break else np.nan,
        "favorable_close_after_break_rate": _safe_mean(df_break["favorable_close_after_break"]) if n_break else np.nan,
        "avg_return_break_to_extreme": _safe_mean(df_break["return_break_to_extreme"]) if n_break else np.nan,
        "median_return_break_to_extreme": _safe_median(df_break["return_break_to_extreme"]) if n_break else np.nan,
        "avg_return_break_to_close": _safe_mean(df_break["return_break_to_close"]) if n_break else np.nan,
        "median_return_break_to_close": _safe_median(df_break["return_break_to_close"]) if n_break else np.nan,
        "median_min_break_to_new_extreme": _safe_median(df_break["minutes_break_to_new_extreme"].dropna()) if n_break else np.nan,
        "median_min_break_to_close": _safe_median(df_break["minutes_break_to_close"]) if n_break else np.nan,
        "confidence": _confidence_label(n_base),
    }


def _build_tod_table(df_all: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for direction in ["long", "short", "combined"]:
        src = df_all if direction == "combined" else df_all[df_all["direction"] == direction]
        src = src[src["ema21_break"]]
        for bucket in ["morning", "midday", "afternoon"]:
            d = src[src["tod_bucket"] == bucket]
            n = len(d)
            rows.append(
                {
                    "direction": direction,
                    "tod_bucket": bucket,
                    "n_break_events": int(n),
                    "pct_new_extreme_after_break": _safe_mean(d["new_extreme_after_break"]) if n else np.nan,
                    "pct_close_ge_1atr_after_break": _safe_mean(d["close_ge_1atr_after_break"]) if n else np.nan,
                    "pct_structural_failure": _safe_mean(d["structural_failure"]) if n else np.nan,
                    "median_minutes_break_to_new_extreme": _safe_median(d["minutes_break_to_new_extreme"].dropna()) if n else np.nan,
                    "confidence": _confidence_label(n),
                }
            )
    return pd.DataFrame(rows)


def _build_bucket_table(df_all: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    ordered = ["0.50-0.60", "0.60-0.70", "0.70-0.80", "0.80-1.00", "1.00+"]
    for direction in ["long", "short", "combined"]:
        src = df_all if direction == "combined" else df_all[df_all["direction"] == direction]
        for bucket in ordered:
            d = src[src["early_expansion_bucket"] == bucket]
            n = len(d)
            if n == 0:
                rows.append(
                    {
                        "direction": direction,
                        "early_expansion_bucket": bucket,
                        "n": 0,
                        "pct_cloud_pullback": np.nan,
                        "pct_ema21_break": np.nan,
                        "pct_new_extreme_given_break": np.nan,
                        "pct_close_ge_1atr_given_break": np.nan,
                        "median_min_peak_to_pullback": np.nan,
                        "median_min_break_to_new_extreme": np.nan,
                        "confidence": _confidence_label(0),
                    }
                )
                continue

            pull = d[d["cloud_pullback"]]
            brk = d[d["ema21_break"]]
            rows.append(
                {
                    "direction": direction,
                    "early_expansion_bucket": bucket,
                    "n": int(n),
                    "pct_cloud_pullback": _safe_mean(d["cloud_pullback"]),
                    "pct_ema21_break": _safe_mean(d["ema21_break"]),
                    "pct_new_extreme_given_break": _safe_mean(brk["new_extreme_after_break"]) if len(brk) else np.nan,
                    "pct_close_ge_1atr_given_break": _safe_mean(brk["close_ge_1atr_after_break"]) if len(brk) else np.nan,
                    "median_min_peak_to_pullback": _safe_median(pull["minutes_peak_to_pullback"].dropna()) if len(pull) else np.nan,
                    "median_min_break_to_new_extreme": _safe_median(brk["minutes_break_to_new_extreme"].dropna()) if len(brk) else np.nan,
                    "confidence": _confidence_label(n),
                }
            )
    return pd.DataFrame(rows)


def _save_charts(bucket_df: pd.DataFrame, tod_df: pd.DataFrame, charts_dir: Path) -> None:
    charts_dir.mkdir(parents=True, exist_ok=True)

    combo_bucket = bucket_df[bucket_df["direction"] == "combined"].copy()
    if not combo_bucket.empty:
        fig1 = px.bar(
            combo_bucket,
            x="early_expansion_bucket",
            y="pct_cloud_pullback",
            title="Cloud Pullback Rate by Early Expansion Bucket (Combined)",
            color_discrete_sequence=["#42a5f5"],
        )
        fig1.write_html(str(charts_dir / "cloud_pullback_rate_by_bucket.html"))

        fig2 = px.bar(
            combo_bucket,
            x="early_expansion_bucket",
            y="pct_ema21_break",
            title="21 EMA Close-Through Rate by Early Expansion Bucket (Combined)",
            color_discrete_sequence=["#ef5350"],
        )
        fig2.write_html(str(charts_dir / "ema21_break_rate_by_bucket.html"))

        fig3 = px.histogram(
            combo_bucket,
            x="early_expansion_bucket",
            y="n",
            histfunc="sum",
            title="Early Expansion Bucket Counts (Combined)",
            color_discrete_sequence=["#26a69a"],
        )
        fig3.write_html(str(charts_dir / "early_expansion_bucket_histogram.html"))

    combo_tod = tod_df[tod_df["direction"] == "combined"].copy()
    if not combo_tod.empty:
        fig4 = px.bar(
            combo_tod,
            x="tod_bucket",
            y="pct_structural_failure",
            title="21 EMA Break Structural Failure Rate by Time of Day (Combined)",
            color_discrete_sequence=["#ef5350"],
        )
        fig4.write_html(str(charts_dir / "tod_structural_failure_rate.html"))


def analyze() -> None:
    cfg = load_config()
    cli = parse_args()

    data_dir, tables_dir, charts_dir, summary_dir = resolve_output_dirs(STUDY_DIR)
    tables_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    tickers = [t.upper() for t in cli.tickers] if cli.tickers else get_watchlist()
    manifest = []
    all_rows: list[dict] = []

    for ticker in tickers:
        daily_path = data_dir / f"{ticker}_1D.csv"
        intraday_path = data_dir / f"{ticker}_5Min.csv"
        if not daily_path.exists() or not intraday_path.exists():
            manifest.append({"ticker": ticker, "status": "skipped_missing_data_files"})
            continue

        try:
            daily = _load_price_csv(daily_path)
            intra = _load_price_csv(intraday_path)
        except Exception as exc:
            manifest.append({"ticker": ticker, "status": f"load_error: {exc}"})
            continue

        intra = _filter_rth_ct(intra)
        if intra.empty:
            manifest.append({"ticker": ticker, "status": "skipped_no_rth_intraday"})
            continue

        daily_atr = _compute_daily_atr(daily, int(cfg.get("atr_length", 14)))
        daily_atr = daily_atr.dropna(subset=["atr14_prev"])
        if daily_atr.empty:
            manifest.append({"ticker": ticker, "status": "skipped_no_atr_warmup"})
            continue

        intra["session_date"] = intra.index.date
        daily_by_date = daily_atr.set_index("session_date")

        ticker_rows = 0
        for session_date, day in intra.groupby("session_date"):
            if session_date not in daily_by_date.index:
                continue

            if len(day) < 12:
                continue

            atr_prev = float(daily_by_date.loc[session_date, "atr14_prev"])
            if not np.isfinite(atr_prev) or atr_prev <= 0:
                continue

            session_open = float(day["open"].iloc[0])
            session_close = float(day["close"].iloc[-1])

            long_cond = session_close >= session_open + float(cfg.get("trend_day_atr_multiple", 1.0)) * atr_prev
            short_cond = session_close <= session_open - float(cfg.get("trend_day_atr_multiple", 1.0)) * atr_prev

            if not (long_cond or short_cond):
                continue

            direction = "long" if long_cond else "short"
            row = _analyze_session(
                ticker=ticker,
                session_date=session_date,
                direction=direction,
                day_5m=day,
                session_open=session_open,
                session_close=session_close,
                atr_value=atr_prev,
            )

            if "exclude_reason" in row and row.get("exclude_reason") == "insufficient_first_30m":
                continue

            all_rows.append(row)
            ticker_rows += 1

        manifest.append({"ticker": ticker, "status": "ok", "rows": ticker_rows})

    events = pd.DataFrame(all_rows)
    if events.empty:
        (summary_dir / "analysis_summary.txt").write_text(
            "No qualifying +/-1.0 ATR close-from-open sessions were found in loaded data.",
            encoding="utf-8",
        )
        pd.DataFrame(manifest).to_csv(summary_dir / "analysis_manifest.csv", index=False)
        print("No qualifying sessions found.")
        return

    # Ensure datetime-like columns are serializable.
    for col in ["expansion_peak_time", "trend_confirm_time", "pullback_time", "ema21_break_time"]:
        if col in events.columns:
            events[col] = pd.to_datetime(events[col], errors="coerce")

    # Required core tables
    overall_rows = [
        _summarize_direction(events, "long"),
        _summarize_direction(events, "short"),
        _summarize_direction(events, "combined"),
    ]
    overall_df = pd.DataFrame(overall_rows)

    cloud_df = overall_df[["direction", "n_base", "n_pullback", "pullback_rate", "confidence"]].copy()
    break_df = overall_df[["direction", "n_pullback", "n_break", "break_rate_among_pullbacks", "confidence"]].copy()
    post_break_df = overall_df[
        [
            "direction",
            "n_break",
            "new_extreme_rate_after_break",
            "structural_failure_rate",
            "close_ge_1atr_after_break_rate",
            "favorable_close_after_break_rate",
            "avg_return_break_to_extreme",
            "median_return_break_to_extreme",
            "avg_return_break_to_close",
            "median_return_break_to_close",
            "median_min_break_to_new_extreme",
            "median_min_break_to_close",
            "confidence",
        ]
    ].copy()

    tod_df = _build_tod_table(events)
    bucket_df = _build_bucket_table(events)

    # Persist tables / data
    events.to_csv(data_dir / "events_detailed.csv", index=False)
    overall_df.to_csv(tables_dir / "overall_sample_summary.csv", index=False)
    cloud_df.to_csv(tables_dir / "cloud_pullback_stats.csv", index=False)
    break_df.to_csv(tables_dir / "ema21_close_through_stats.csv", index=False)
    post_break_df.to_csv(tables_dir / "post_break_recovery_failure_stats.csv", index=False)
    tod_df.to_csv(tables_dir / "time_of_day_break_outcomes.csv", index=False)
    bucket_df.to_csv(tables_dir / "early_expansion_bucket_stats.csv", index=False)
    pd.DataFrame(manifest).to_csv(summary_dir / "analysis_manifest.csv", index=False)

    _save_charts(bucket_df, tod_df, charts_dir)

    combined = overall_df[overall_df["direction"] == "combined"].iloc[0]
    text_lines = [
        "Intraday EMA Cloud Pullback and 21 EMA Structural Failure Study (EMA10/EMA21)",
        "=" * 78,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Universe: QuantLab watchlist ({len(tickers)} tickers requested)",
        f"Date window: {cfg.get('start_date', '2024-01-01')} to {cfg.get('end_date', 'today')} (data availability bounded)",
        "",
        "Headline:",
        (
            f"Across {int(combined['n_base'])} strong +/-1.0 ATR close-from-open sessions, "
            f"cloud pullbacks occurred in {combined['pullback_rate']:.1%} of cases and "
            f"EMA21 close-through events occurred in {combined['break_rate_among_pullbacks']:.1%} of pullbacks."
        ),
        "",
        "Key Findings:",
        f"- Base sample: long={int(overall_df.loc[overall_df.direction=='long','n_base'].iloc[0])}, short={int(overall_df.loc[overall_df.direction=='short','n_base'].iloc[0])}, combined={int(combined['n_base'])}",
        f"- Cloud pullback rate (combined): {combined['pullback_rate']:.1%}",
        f"- 21 EMA close-through rate among pullbacks (combined): {combined['break_rate_among_pullbacks']:.1%}",
        f"- New session extreme after break (combined): {combined['new_extreme_rate_after_break']:.1%}",
        f"- Structural failure rate after break (combined): {combined['structural_failure_rate']:.1%}",
        f"- Favorable close quartile after break (combined): {combined['favorable_close_after_break_rate']:.1%}",
        "",
        "Interpretation:",
        "- Pullbacks to the EMA cloud can be normal behavior on strong trend days; the practical stop question is the close-through frequency and post-break recovery profile.",
        "- EMA21 close-through events are evaluated as kill switch only when no new post-break session extreme occurs.",
        "- Time-of-day and early-expansion bucket tables should be used to decide whether 70% ATR behaves as a discrete inflection or part of a gradient.",
        "",
        "Sanity Checks Applied:",
        "- No-lookahead ATR alignment via prior-day ATR14 (atr14_prev).",
        "- Pullback detection occurs after first-30-minute expansion peak.",
        "- EMA21 break detection occurs strictly after pullback start.",
        "- New extreme checks only use bars after the break timestamp.",
        "- RTH-only filtering in Central Time (08:30-15:00 CT).",
        "",
        f"Confidence: {_confidence_label(int(combined['n_base']))} (n={int(combined['n_base'])})",
    ]

    (summary_dir / "analysis_summary.txt").write_text("\n".join(text_lines), encoding="utf-8")
    print("Analysis complete.")
    print(f"Events: {data_dir / 'events_detailed.csv'}")
    print(f"Summary: {summary_dir / 'analysis_summary.txt'}")


if __name__ == "__main__":
    analyze()
    analyze()
