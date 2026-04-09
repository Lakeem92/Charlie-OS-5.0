#!/usr/bin/env python3
# pyright: reportGeneralTypeIssues=false
"""
First Hour 50%+ ATR to EMA Cloud Pullback Study — analyze.py

Event detection:
- Within bars 1-12 (first RTH hour, 8:30-9:30 CT), detect when the cumulative
  move from session open reaches 50%+ of prior-day ATR14.
- Long trigger:  cummax((high - session_open) / atr14_prev) >= threshold in bars 1-12
- Short trigger: cummax((session_open - low) / atr14_prev) >= threshold in bars 1-12
- Long and short are independent; a session may yield 0, 1, or 2 trigger events.

After trigger bar: measure EMA10/21 cloud pullback in the next 12 bars (one hour).

Key timing split:
- trigger_bar_exact in [1-6]  → first_30m  (8:30-9:00 CT)
- trigger_bar_exact in [7-12] → second_30m (9:00-9:30 CT)

No trend-day pre-filter. Base denominator = all sessions with >= 20 RTH 5-min bars.
Analysis window enforced in-code: session_date >= config start_date (1-year lookback).
Only triggered events are written to events_detailed.csv.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, date, time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

STUDY_DIR = Path(__file__).resolve().parent
ROOT_DIR = STUDY_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR / "tools" / "studies"))

from run_id import resolve_output_dirs  # type: ignore[import-not-found]
from shared.watchlist import get_watchlist  # type: ignore[import-not-found]

CT_TZ = "America/Chicago"
RTH_START = time(8, 30)
RTH_END = time(15, 0)


# ─────────────────────────────────────────────────────────────────────────────
# Config & CLI
# ─────────────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    with open(STUDY_DIR / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze first-hour ATR50+ to EMA cloud pullback")
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    return parser.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions (mirrored from opening_thrust_ema_cloud_pullback_1atr_trend)
# ─────────────────────────────────────────────────────────────────────────────

def _confidence_label(n: int) -> str:
    if n < 10:
        return "INSUFFICIENT"
    if n < 20:
        return "LOW"
    return "RELIABLE"


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
    req = {"open", "high", "low", "close", "volume"}
    missing = req - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {path.name}: {sorted(missing)}")
    return _to_ct_index(df)


def _filter_rth_ct(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    times = out.index.time
    return out[(times >= RTH_START) & (times <= RTH_END)].copy()


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


def _ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def _first_cross_index(values: pd.Series, threshold: float) -> Optional[int]:
    for i, v in enumerate(values.tolist()):
        if v >= threshold:
            return i
    return None


def _bucket_trigger_magnitude(x: float) -> str:
    if 0.50 <= x < 0.70:
        return "0.50-0.70"
    if 0.70 <= x < 1.00:
        return "0.70-1.00"
    if x >= 1.00:
        return "1.00+"
    return "below_threshold"


def _intersects_cloud(row: pd.Series) -> bool:
    cloud_low = min(float(row["ema10"]), float(row["ema21"]))
    cloud_high = max(float(row["ema10"]), float(row["ema21"]))
    return float(row["high"]) >= cloud_low and float(row["low"]) <= cloud_high


def _first_cloud_contact(next_hour: pd.DataFrame) -> Optional[pd.Timestamp]:
    for ts, row in next_hour.iterrows():
        if _intersects_cloud(row):
            return ts
    return None


def _find_flip_time(window: pd.DataFrame, direction: str) -> Optional[pd.Timestamp]:
    if len(window) < 2:
        return None
    prev_fast = window["ema10"].shift(1)
    prev_slow = window["ema21"].shift(1)
    fast = window["ema10"]
    slow = window["ema21"]
    if direction == "long":
        cond = (prev_fast >= prev_slow) & (fast < slow)
    else:
        cond = (prev_fast <= prev_slow) & (fast > slow)
    idx = window.index[cond.fillna(False)]
    return idx[0] if len(idx) else None


def _post_event_recovery(
    day: pd.DataFrame, event_ts: pd.Timestamp, direction: str
) -> tuple[bool, float]:
    pre = day[day.index <= event_ts]
    post = day[day.index > event_ts]
    if pre.empty or post.empty:
        return False, np.nan
    if direction == "long":
        prior_extreme = float(pre["high"].max())
        crossed = post["high"] > prior_extreme
    else:
        prior_extreme = float(pre["low"].min())
        crossed = post["low"] < prior_extreme
    if not crossed.any():
        return False, np.nan
    first_ts = crossed.index[crossed][0]
    minutes = (first_ts - event_ts).total_seconds() / 60.0
    return True, float(minutes)


def _safe_rate(num: int, den: int) -> float:
    return float(num / den) if den else np.nan


# ─────────────────────────────────────────────────────────────────────────────
# Summary builders
# ─────────────────────────────────────────────────────────────────────────────

def _build_cloud_summary(
    trig: pd.DataFrame, direction: str, n_sessions: int
) -> dict:
    """
    Headline cloud metrics for one direction.
    Denominator for trigger rate:
      - long / short: n_sessions (one evaluation per session per direction)
      - combined: n_sessions * 2 (two evaluations per session)
    Denominator for cloud metrics: triggered events only.
    """
    src = trig if direction == "combined" else trig[trig["direction"] == direction]
    n_trig = len(src)
    n_eval = n_sessions * 2 if direction == "combined" else n_sessions
    br = src[src["directional_breach"]]
    fl = src[src["cloud_flip"]]
    return {
        "direction": direction,
        "n_sessions_evaluated": n_sessions,
        "n_direction_evaluations": n_eval,
        "n_triggered": n_trig,
        "trigger_rate_of_evaluations": _safe_rate(n_trig, n_eval),
        "n_cloud_touch_any": int(src["cloud_touch_any"].sum()),
        "cloud_touch_any_rate_of_triggered": _safe_rate(int(src["cloud_touch_any"].sum()), n_trig),
        "n_touch_ema10": int(src["touch_ema10"].sum()),
        "touch_ema10_rate_of_triggered": _safe_rate(int(src["touch_ema10"].sum()), n_trig),
        "n_cloud_entry": int(src["cloud_entry"].sum()),
        "cloud_entry_rate_of_triggered": _safe_rate(int(src["cloud_entry"].sum()), n_trig),
        "n_touch_ema21": int(src["touch_ema21"].sum()),
        "touch_ema21_rate_of_triggered": _safe_rate(int(src["touch_ema21"].sum()), n_trig),
        "n_directional_breach": len(br),
        "directional_breach_rate_of_triggered": _safe_rate(len(br), n_trig),
        "n_cloud_flip": len(fl),
        "cloud_flip_rate_of_triggered": _safe_rate(len(fl), n_trig),
        "post_breach_new_extreme_rate": float(br["new_extreme_after_breach"].mean()) if len(br) else np.nan,
        "median_min_breach_to_new_extreme": float(br["min_breach_to_new_extreme"].dropna().median()) if len(br) else np.nan,
        "post_flip_new_extreme_rate": float(fl["new_extreme_after_flip"].mean()) if len(fl) else np.nan,
        "median_min_flip_to_new_extreme": float(fl["min_flip_to_new_extreme"].dropna().median()) if len(fl) else np.nan,
        "confidence": _confidence_label(n_trig),
    }


def _build_timing_split_row(
    trig: pd.DataFrame, direction: str, bucket: str
) -> dict:
    """Cloud metrics for a specific direction × trigger_timing_bucket slice."""
    src = trig if direction == "combined" else trig[trig["direction"] == direction]
    grp = src[src["trigger_timing_bucket"] == bucket]
    n = len(grp)
    br = grp[grp["directional_breach"]]
    fl = grp[grp["cloud_flip"]]
    return {
        "direction": direction,
        "trigger_timing_bucket": bucket,
        "n_triggered_in_bucket": n,
        "n_cloud_touch_any": int(grp["cloud_touch_any"].sum()),
        "cloud_touch_any_rate": _safe_rate(int(grp["cloud_touch_any"].sum()), n),
        "n_cloud_entry": int(grp["cloud_entry"].sum()),
        "cloud_entry_rate": _safe_rate(int(grp["cloud_entry"].sum()), n),
        "n_touch_ema21": int(grp["touch_ema21"].sum()),
        "touch_ema21_rate": _safe_rate(int(grp["touch_ema21"].sum()), n),
        "n_directional_breach": len(br),
        "directional_breach_rate": _safe_rate(len(br), n),
        "n_cloud_flip": len(fl),
        "cloud_flip_rate": _safe_rate(len(fl), n),
        "post_breach_new_extreme_rate": float(br["new_extreme_after_breach"].mean()) if len(br) else np.nan,
        "post_flip_new_extreme_rate": float(fl["new_extreme_after_flip"].mean()) if len(fl) else np.nan,
        "confidence": _confidence_label(n),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main analysis loop
# ─────────────────────────────────────────────────────────────────────────────

def analyze() -> None:
    cfg = load_config()
    cli = parse_args()

    data_dir, tables_dir, charts_dir, summary_dir = resolve_output_dirs(STUDY_DIR)
    for d in (tables_dir, charts_dir, summary_dir):
        d.mkdir(parents=True, exist_ok=True)

    tickers = [t.upper() for t in cli.tickers] if cli.tickers else get_watchlist()

    # Resolve analysis window — enforce 1-year lookback in-code
    start_date_cfg = cli.start or cfg.get("start_date", "2025-04-08")
    end_raw = cfg.get("end_date", "today")
    end_date_cfg = cli.end or (
        datetime.now().strftime("%Y-%m-%d")
        if str(end_raw).lower() == "today"
        else str(end_raw)
    )
    analysis_start = date.fromisoformat(start_date_cfg)

    # Parameters
    atr_length = int(cfg.get("atr_length", 14))
    threshold = float(cfg.get("atr_threshold", 0.50))
    trigger_max_bar = int(cfg.get("trigger_max_bar", 12))
    next_hour_bars = int(cfg.get("next_hour_bars", 12))
    first_30m_max_bar = int(cfg.get("first_30m_max_bar", 6))
    ema_fast = int(cfg.get("ema_fast_length", 10))
    ema_slow = int(cfg.get("ema_slow_length", 21))

    event_rows: list[dict] = []
    manifest_rows: list[dict] = []
    sessions_evaluated: set[tuple[str, date]] = set()

    for ticker in tickers:
        daily_path = data_dir / f"{ticker}_1D.csv"
        intraday_path = data_dir / f"{ticker}_5Min.csv"

        if not daily_path.exists() or not intraday_path.exists():
            manifest_rows.append({"ticker": ticker, "status": "skipped_missing_data_files"})
            continue

        try:
            daily = _load_price_csv(daily_path)
            intraday = _load_price_csv(intraday_path)
        except Exception as exc:
            manifest_rows.append({"ticker": ticker, "status": f"load_error: {exc}"})
            continue

        intraday = _filter_rth_ct(intraday)
        if intraday.empty:
            manifest_rows.append({"ticker": ticker, "status": "skipped_no_rth_intraday"})
            continue

        daily_atr = _compute_daily_atr(daily, atr_length).dropna(subset=["atr14_prev"])
        if daily_atr.empty:
            manifest_rows.append({"ticker": ticker, "status": "skipped_no_atr_warmup"})
            continue

        intraday["session_date"] = intraday.index.date
        daily_by_date = daily_atr.set_index("session_date")

        kept = 0
        for session_date, day in intraday.groupby("session_date"):
            # Enforce 1-year analysis window (cached data may cover earlier dates)
            if session_date < analysis_start:
                continue
            if session_date not in daily_by_date.index:
                continue
            if len(day) < 20:
                continue

            atr_prev = float(daily_by_date.loc[session_date, "atr14_prev"])
            if not np.isfinite(atr_prev) or atr_prev <= 0:
                continue

            day = day.sort_index().copy()
            day["ema10"] = _ema(day["close"], ema_fast)
            day["ema21"] = _ema(day["close"], ema_slow)

            session_open = float(day["open"].iloc[0])

            # Register session for base denominator count
            sessions_evaluated.add((ticker, session_date))

            # ── Evaluate LONG and SHORT independently ───────────────────────
            for direction in ("long", "short"):
                first_hour = day.iloc[:trigger_max_bar].copy()

                if direction == "long":
                    first_hour["thrust"] = (first_hour["high"] - session_open) / atr_prev
                else:
                    first_hour["thrust"] = (session_open - first_hour["low"]) / atr_prev

                first_hour["thrust_cum"] = first_hour["thrust"].cummax()
                trig_rel = _first_cross_index(first_hour["thrust_cum"], threshold)

                if trig_rel is None:
                    continue  # no trigger this direction this session

                trigger_idx = int(trig_rel)
                trigger_ts = first_hour.index[trigger_idx]
                trigger_mag = float(first_hour["thrust_cum"].iloc[trigger_idx])
                trigger_bar_exact = trigger_idx + 1  # 1-based
                timing_bucket = (
                    "first_30m" if trigger_bar_exact <= first_30m_max_bar else "second_30m"
                )

                # Next-hour window: 12 bars after trigger bar
                full_idx = day.index.get_loc(trigger_ts)
                next_hour = day.iloc[full_idx + 1 : full_idx + 1 + next_hour_bars].copy()

                row: dict = {
                    "ticker": ticker,
                    "session_date": session_date,
                    "direction": direction,
                    "atr14_prev": atr_prev,
                    "session_open": session_open,
                    "trigger_bar_exact": trigger_bar_exact,
                    "trigger_timing_bucket": timing_bucket,
                    "trigger_magnitude_atr": trigger_mag,
                    "trigger_magnitude_bucket": _bucket_trigger_magnitude(trigger_mag),
                    "trigger_time": trigger_ts,
                    "cloud_touch_any": False,
                    "touch_ema10": False,
                    "cloud_entry": False,
                    "touch_ema21": False,
                    "cloud_contact_time": pd.NaT,
                    "directional_breach": False,
                    "directional_breach_time": pd.NaT,
                    "cloud_flip": False,
                    "cloud_flip_time": pd.NaT,
                    "new_extreme_after_breach": False,
                    "min_breach_to_new_extreme": np.nan,
                    "new_extreme_after_flip": False,
                    "min_flip_to_new_extreme": np.nan,
                }

                if next_hour.empty:
                    event_rows.append(row)
                    kept += 1
                    continue

                # ── Cloud touch depth ────────────────────────────────────────
                if direction == "long":
                    row["touch_ema10"] = bool((next_hour["low"] <= next_hour["ema10"]).any())
                    row["touch_ema21"] = bool((next_hour["low"] <= next_hour["ema21"]).any())
                else:
                    row["touch_ema10"] = bool((next_hour["high"] >= next_hour["ema10"]).any())
                    row["touch_ema21"] = bool((next_hour["high"] >= next_hour["ema21"]).any())

                row["cloud_entry"] = bool(next_hour.apply(_intersects_cloud, axis=1).any())
                row["cloud_touch_any"] = bool(
                    row["touch_ema10"] or row["cloud_entry"] or row["touch_ema21"]
                )

                # ── Directional breach (requires prior cloud contact) ────────
                contact_ts = _first_cloud_contact(next_hour)
                if contact_ts is not None:
                    row["cloud_contact_time"] = contact_ts
                    post_contact = next_hour[next_hour.index >= contact_ts]

                    if direction == "long":
                        breach_mask = post_contact["close"] < post_contact["ema21"]
                    else:
                        breach_mask = post_contact["close"] > post_contact["ema10"]

                    if breach_mask.any():
                        breach_ts = post_contact.index[breach_mask][0]
                        row["directional_breach"] = True
                        row["directional_breach_time"] = breach_ts
                        recovered, mins = _post_event_recovery(day, breach_ts, direction)
                        row["new_extreme_after_breach"] = recovered
                        row["min_breach_to_new_extreme"] = mins

                # ── Cloud flip (from trigger bar onward) ─────────────────────
                flip_window = day.iloc[full_idx : full_idx + 1 + next_hour_bars].copy()
                flip_ts = _find_flip_time(flip_window, direction)
                if flip_ts is not None:
                    row["cloud_flip"] = True
                    row["cloud_flip_time"] = flip_ts
                    recovered, mins = _post_event_recovery(day, flip_ts, direction)
                    row["new_extreme_after_flip"] = recovered
                    row["min_flip_to_new_extreme"] = mins

                event_rows.append(row)
                kept += 1

        manifest_rows.append({"ticker": ticker, "status": "ok", "events_written": kept})

    # ─────────────────────────────────────────────────────────────────────────
    # Build outputs
    # ─────────────────────────────────────────────────────────────────────────

    events = pd.DataFrame(event_rows)
    n_sessions = len(sessions_evaluated)

    if events.empty:
        (summary_dir / "analysis_summary.txt").write_text(
            "No trigger events found for the configured parameters and date range.",
            encoding="utf-8",
        )
        pd.DataFrame(manifest_rows).to_csv(summary_dir / "analysis_manifest.csv", index=False)
        print("No events found.")
        return

    # Coerce timestamp columns
    for col in ["trigger_time", "cloud_contact_time", "directional_breach_time", "cloud_flip_time"]:
        if col in events.columns:
            events[col] = pd.to_datetime(events[col], errors="coerce")

    events.to_csv(data_dir / "events_detailed.csv", index=False)
    print(f"Events written: {len(events)} rows -> data/events_detailed.csv")

    # ── Table 1: Overall sample summary ──────────────────────────────────────
    overall_rows = [
        _build_cloud_summary(events, "long", n_sessions),
        _build_cloud_summary(events, "short", n_sessions),
        _build_cloud_summary(events, "combined", n_sessions),
    ]
    overall = pd.DataFrame(overall_rows)
    overall.to_csv(tables_dir / "overall_sample_summary.csv", index=False)

    # ── Table 2: Cloud touch depth rates ─────────────────────────────────────
    cloud_depth_rows = []
    for direction in ["long", "short", "combined"]:
        src = events if direction == "combined" else events[events["direction"] == direction]
        n = len(src)
        cloud_depth_rows.append({
            "direction": direction,
            "n_triggered": n,
            "n_cloud_touch_any": int(src["cloud_touch_any"].sum()),
            "rate_cloud_touch_any": _safe_rate(int(src["cloud_touch_any"].sum()), n),
            "n_touch_ema10": int(src["touch_ema10"].sum()),
            "rate_touch_ema10": _safe_rate(int(src["touch_ema10"].sum()), n),
            "n_cloud_entry": int(src["cloud_entry"].sum()),
            "rate_cloud_entry": _safe_rate(int(src["cloud_entry"].sum()), n),
            "n_touch_ema21": int(src["touch_ema21"].sum()),
            "rate_touch_ema21": _safe_rate(int(src["touch_ema21"].sum()), n),
            "confidence": _confidence_label(n),
        })
    pd.DataFrame(cloud_depth_rows).to_csv(tables_dir / "cloud_touch_depth_rates.csv", index=False)

    # ── Table 3: Directional breach rates ────────────────────────────────────
    breach_rows = []
    for direction in ["long", "short", "combined"]:
        src = events if direction == "combined" else events[events["direction"] == direction]
        n = len(src)
        br = src[src["directional_breach"]]
        breach_rows.append({
            "direction": direction,
            "n_triggered": n,
            "n_directional_breach": len(br),
            "directional_breach_rate_of_triggered": _safe_rate(len(br), n),
            "post_breach_new_extreme_rate": float(br["new_extreme_after_breach"].mean()) if len(br) else np.nan,
            "median_min_breach_to_new_extreme": float(br["min_breach_to_new_extreme"].dropna().median()) if len(br) else np.nan,
            "confidence": _confidence_label(n),
        })
    pd.DataFrame(breach_rows).to_csv(tables_dir / "directional_breach_rates.csv", index=False)

    # ── Table 4: Cloud flip rates ─────────────────────────────────────────────
    flip_rows = []
    for direction in ["long", "short", "combined"]:
        src = events if direction == "combined" else events[events["direction"] == direction]
        n = len(src)
        fl = src[src["cloud_flip"]]
        flip_rows.append({
            "direction": direction,
            "n_triggered": n,
            "n_cloud_flip": len(fl),
            "cloud_flip_rate_of_triggered": _safe_rate(len(fl), n),
            "post_flip_new_extreme_rate": float(fl["new_extreme_after_flip"].mean()) if len(fl) else np.nan,
            "median_min_flip_to_new_extreme": float(fl["min_flip_to_new_extreme"].dropna().median()) if len(fl) else np.nan,
            "confidence": _confidence_label(n),
        })
    pd.DataFrame(flip_rows).to_csv(tables_dir / "cloud_flip_rates.csv", index=False)

    # ── Table 5: KEY — Timing split first_30m vs second_30m ──────────────────
    timing_split_rows = []
    for direction in ["long", "short", "combined"]:
        for bucket in ["first_30m", "second_30m"]:
            timing_split_rows.append(_build_timing_split_row(events, direction, bucket))
    timing_split_df = pd.DataFrame(timing_split_rows)
    timing_split_df.to_csv(tables_dir / "timing_split_30v60.csv", index=False)

    # ── Table 6: Trigger timing by bar (1-12) ────────────────────────────────
    timing_by_bar = (
        events.groupby(["direction", "trigger_bar_exact"])
        .size()
        .reset_index(name="n")
    )
    timing_by_bar["denominator_n_triggered"] = timing_by_bar.groupby("direction")["n"].transform("sum")
    timing_by_bar["rate_of_triggered"] = timing_by_bar["n"] / timing_by_bar["denominator_n_triggered"]
    timing_by_bar.to_csv(tables_dir / "trigger_timing_by_bar.csv", index=False)

    # ── Table 7: Trigger magnitude buckets ───────────────────────────────────
    magnitude = (
        events.groupby(["direction", "trigger_magnitude_bucket"])
        .size()
        .reset_index(name="n")
    )
    magnitude["denominator_n_triggered"] = magnitude.groupby("direction")["n"].transform("sum")
    magnitude["rate_of_triggered"] = magnitude["n"] / magnitude["denominator_n_triggered"]
    magnitude.to_csv(tables_dir / "trigger_magnitude_buckets.csv", index=False)

    # ── Manifest ──────────────────────────────────────────────────────────────
    pd.DataFrame(manifest_rows).to_csv(summary_dir / "analysis_manifest.csv", index=False)

    # ── Analysis summary text ─────────────────────────────────────────────────
    comb_row = overall[overall["direction"] == "combined"].iloc[0]
    long_row = overall[overall["direction"] == "long"].iloc[0]
    short_row = overall[overall["direction"] == "short"].iloc[0]

    def fmt(val: float, pct: bool = True, places: int = 1) -> str:
        if isinstance(val, float) and np.isnan(val):
            return "n/a"
        if pct:
            return f"{val:.{places}%}"
        return f"{val:.{places}f}"

    # Pull timing split rows for the combined summary table
    ts_first = timing_split_df[
        (timing_split_df["direction"] == "combined") &
        (timing_split_df["trigger_timing_bucket"] == "first_30m")
    ]
    ts_second = timing_split_df[
        (timing_split_df["direction"] == "combined") &
        (timing_split_df["trigger_timing_bucket"] == "second_30m")
    ]

    text_lines = [
        "First Hour 50%+ ATR to EMA Cloud Pullback Study",
        "=" * 72,
        f"Generated:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Universe:   QuantLab watchlist ({len(tickers)} requested)",
        f"Date window: {start_date_cfg} to {end_date_cfg}",
        f"Sessions evaluated: {n_sessions:,} unique (ticker-date) pairs",
        f"Parameters: ATR threshold={threshold:.0%}  trigger_max_bar={trigger_max_bar}  next_hour_bars={next_hour_bars}  ema={ema_fast}/{ema_slow}",
        "",
        "=" * 72,
        "TRIGGER INCIDENCE",
        "=" * 72,
        f"  Combined:  {int(comb_row['n_triggered']):,} events / {n_sessions * 2:,} evaluations = {fmt(comb_row['trigger_rate_of_evaluations'])}",
        f"  Long:      {int(long_row['n_triggered']):,} / {n_sessions:,} sessions = {fmt(long_row['trigger_rate_of_evaluations'])}",
        f"  Short:     {int(short_row['n_triggered']):,} / {n_sessions:,} sessions = {fmt(short_row['trigger_rate_of_evaluations'])}",
        "  NOTE: combined denominator = 2 × n_sessions (one long eval + one short eval per session)",
        "",
        "=" * 72,
        "NEXT-HOUR CLOUD PULLBACK DEPTH  (denominator = triggered events)",
        "=" * 72,
        f"  Cloud touch-any    — Combined: {fmt(comb_row['cloud_touch_any_rate_of_triggered'])}  |  Long: {fmt(long_row['cloud_touch_any_rate_of_triggered'])}  |  Short: {fmt(short_row['cloud_touch_any_rate_of_triggered'])}",
        f"  Cloud entry        — Combined: {fmt(comb_row['cloud_entry_rate_of_triggered'])}  |  Long: {fmt(long_row['cloud_entry_rate_of_triggered'])}  |  Short: {fmt(short_row['cloud_entry_rate_of_triggered'])}",
        f"  Touch EMA21        — Combined: {fmt(comb_row['touch_ema21_rate_of_triggered'])}  |  Long: {fmt(long_row['touch_ema21_rate_of_triggered'])}  |  Short: {fmt(short_row['touch_ema21_rate_of_triggered'])}",
        f"  Directional breach — Combined: {fmt(comb_row['directional_breach_rate_of_triggered'])}  |  Long: {fmt(long_row['directional_breach_rate_of_triggered'])}  |  Short: {fmt(short_row['directional_breach_rate_of_triggered'])}",
        f"  Cloud flip         — Combined: {fmt(comb_row['cloud_flip_rate_of_triggered'])}  |  Long: {fmt(long_row['cloud_flip_rate_of_triggered'])}  |  Short: {fmt(short_row['cloud_flip_rate_of_triggered'])}",
        "",
        "=" * 72,
        "KEY: TIMING SPLIT — FIRST 30 MIN (bars 1-6) vs SECOND 30 MIN (bars 7-12)  [COMBINED]",
        "=" * 72,
    ]

    if not ts_first.empty and not ts_second.empty:
        r1 = ts_first.iloc[0]
        r2 = ts_second.iloc[0]
        text_lines += [
            f"  {'Metric':<26} | {'first_30m':>12} | {'second_30m':>12}",
            f"  {'-'*26}-+-{'-'*12}-+-{'-'*12}",
            f"  {'n_triggered':<26} | {int(r1['n_triggered_in_bucket']):>12,} | {int(r2['n_triggered_in_bucket']):>12,}",
            f"  {'cloud_touch_any':<26} | {fmt(r1['cloud_touch_any_rate']):>12} | {fmt(r2['cloud_touch_any_rate']):>12}",
            f"  {'cloud_entry':<26} | {fmt(r1['cloud_entry_rate']):>12} | {fmt(r2['cloud_entry_rate']):>12}",
            f"  {'touch_ema21':<26} | {fmt(r1['touch_ema21_rate']):>12} | {fmt(r2['touch_ema21_rate']):>12}",
            f"  {'directional_breach':<26} | {fmt(r1['directional_breach_rate']):>12} | {fmt(r2['directional_breach_rate']):>12}",
            f"  {'cloud_flip':<26} | {fmt(r1['cloud_flip_rate']):>12} | {fmt(r2['cloud_flip_rate']):>12}",
            f"  {'post_breach_new_extreme':<26} | {fmt(r1['post_breach_new_extreme_rate']):>12} | {fmt(r2['post_breach_new_extreme_rate']):>12}",
            f"  {'confidence':<26} | {r1['confidence']:>12} | {r2['confidence']:>12}",
        ]

    text_lines += [
        "",
        "=" * 72,
        "POST-BREACH RECOVERY  (combined, denominator = breach events only)",
        "=" * 72,
        f"  Post-breach new extreme rate: {fmt(comb_row['post_breach_new_extreme_rate'])}",
        f"  Median min to new extreme:    {fmt(comb_row['median_min_breach_to_new_extreme'], pct=False)} min",
        f"  Post-flip new extreme rate:   {fmt(comb_row['post_flip_new_extreme_rate'])}",
        f"  Median min flip to extreme:   {fmt(comb_row['median_min_flip_to_new_extreme'], pct=False)} min",
        "",
        "=" * 72,
        "CONFIDENCE",
        "=" * 72,
        f"  Long:     {long_row['confidence']} (n={int(long_row['n_triggered'])})",
        f"  Short:    {short_row['confidence']} (n={int(short_row['n_triggered'])})",
        f"  Combined: {comb_row['confidence']} (n={int(comb_row['n_triggered'])})",
        "",
        "DENOMINATOR AUDIT",
        "  Trigger rate denominator:  n_sessions per direction; n_sessions*2 for combined",
        "  Cloud metrics denominator: triggered events only",
        "  Recovery denominator:      breach-only or flip-only subsets",
        "  Long breach definition:    close below EMA21 within next hour after cloud contact",
        "  Short breach definition:   close above EMA10 within next hour after cloud contact",
    ]

    (summary_dir / "analysis_summary.txt").write_text("\n".join(text_lines), encoding="utf-8")

    print("Analysis complete.")
    print(f"Events:   {data_dir / 'events_detailed.csv'} ({len(events)} rows)")
    print(f"Summary:  {summary_dir / 'analysis_summary.txt'}")
    print(f"Sessions: {n_sessions:,} | Long triggers: {int(long_row['n_triggered']):,} | Short triggers: {int(short_row['n_triggered']):,}")


if __name__ == "__main__":
    analyze()
