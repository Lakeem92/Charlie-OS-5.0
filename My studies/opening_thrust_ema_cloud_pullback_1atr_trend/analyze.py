#!/usr/bin/env python3
# pyright: reportGeneralTypeIssues=false
"""
Opening Thrust to EMA Cloud Pullback Study on Strong +/-1.0 ATR Trend Days.

Core event:
- On strong trend days, detect 0.70+ ATR opening thrust within bars 1-3.
- Anchor at first qualifying thrust bar.
- Evaluate cloud pullback depth and breach/flip behavior in next 12 bars (1 hour).

EMA cloud is ThinkScript-mirrored EMA10/EMA21 only.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yaml

import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

STUDY_DIR = Path(__file__).resolve().parent
ROOT_DIR = STUDY_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR / "tools" / "studies"))

from run_id import resolve_output_dirs  # type: ignore[import-not-found]
from shared.watchlist import get_watchlist

CT_TZ = "America/Chicago"
RTH_START = time(8, 30)
RTH_END = time(15, 0)


def load_config() -> dict:
    with open(STUDY_DIR / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze opening thrust to EMA cloud pullback behavior")
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    return parser.parse_args()


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
    if 0.70 <= x < 0.80:
        return "0.70-0.80"
    if 0.80 <= x < 1.00:
        return "0.80-1.00"
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


def _event_timing_bucket(trigger_ts: pd.Timestamp, event_ts: pd.Timestamp) -> str:
    delta_min = (event_ts - trigger_ts).total_seconds() / 60.0
    if delta_min <= 30:
        return "first_30m"
    if delta_min <= 60:
        return "second_30m"
    return "outside_next_hour"


def _session_tod_bucket(ts: pd.Timestamp) -> str:
    t = ts.timetz().replace(tzinfo=None)
    if time(8, 30) <= t < time(10, 0):
        return "morning"
    if time(10, 0) <= t < time(12, 30):
        return "midday"
    return "afternoon"


def _post_event_recovery(day: pd.DataFrame, event_ts: pd.Timestamp, direction: str) -> tuple[bool, float]:
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


def _build_direction_summary(events: pd.DataFrame, direction: str) -> dict:
    src = events if direction == "combined" else events[events["direction"] == direction]

    n_base = int(src["is_strong_trend_day"].sum())
    trig = src[src["triggered"]]
    n_trigger = len(trig)

    cloud_any = int(trig["cloud_touch_any"].sum())
    entry = int(trig["cloud_entry"].sum())
    touch_slow = int(trig["touch_ema21"].sum())
    breach = int(trig["directional_breach"].sum())
    flip = int(trig["cloud_flip"].sum())

    breach_df = trig[trig["directional_breach"]]
    flip_df = trig[trig["cloud_flip"]]

    if direction == "long":
        post_close_metric = "close_ge_plus1atr_after_event"
    elif direction == "short":
        post_close_metric = "close_le_minus1atr_after_event"
    else:
        post_close_metric = "close_still_strong_after_event"

    return {
        "direction": direction,
        "n_base_strong_trend_days": n_base,
        "n_triggered_opening_thrust": n_trigger,
        "trigger_rate_of_base": _safe_rate(n_trigger, n_base),
        "n_cloud_touch_any": cloud_any,
        "cloud_touch_any_rate_of_triggered": _safe_rate(cloud_any, n_trigger),
        "n_cloud_entry": entry,
        "cloud_entry_rate_of_triggered": _safe_rate(entry, n_trigger),
        "n_touch_ema21": touch_slow,
        "touch_ema21_rate_of_triggered": _safe_rate(touch_slow, n_trigger),
        "n_directional_breach": breach,
        "directional_breach_rate_of_triggered": _safe_rate(breach, n_trigger),
        "n_cloud_flip": flip,
        "cloud_flip_rate_of_triggered": _safe_rate(flip, n_trigger),
        "post_breach_new_extreme_rate": float(breach_df["new_extreme_after_breach"].mean()) if len(breach_df) else np.nan,
        "post_flip_new_extreme_rate": float(flip_df["new_extreme_after_flip"].mean()) if len(flip_df) else np.nan,
        "post_breach_still_strong_close_rate": float(breach_df[post_close_metric].mean()) if len(breach_df) else np.nan,
        "post_flip_still_strong_close_rate": float(flip_df[post_close_metric].mean()) if len(flip_df) else np.nan,
        "median_min_breach_to_new_extreme": float(breach_df["min_breach_to_new_extreme"].dropna().median()) if len(breach_df) else np.nan,
        "median_min_flip_to_new_extreme": float(flip_df["min_flip_to_new_extreme"].dropna().median()) if len(flip_df) else np.nan,
        "confidence": _confidence_label(n_trigger),
    }


def analyze() -> None:
    cfg = load_config()
    cli = parse_args()

    data_dir, tables_dir, charts_dir, summary_dir = resolve_output_dirs(STUDY_DIR)
    for d in (tables_dir, charts_dir, summary_dir):
        d.mkdir(parents=True, exist_ok=True)

    tickers = [t.upper() for t in cli.tickers] if cli.tickers else get_watchlist()

    all_rows: list[dict] = []
    manifest_rows: list[dict] = []

    atr_length = int(cfg.get("atr_length", 14))
    trend_mult = float(cfg.get("trend_day_atr_multiple", 1.0))
    threshold = float(cfg.get("opening_thrust_atr_threshold", 0.70))
    max_bar = int(cfg.get("opening_thrust_max_bar", 3))
    next_hour_bars = int(cfg.get("next_hour_bars", 12))
    ema_fast = int(cfg.get("ema_fast_length", 10))
    ema_slow = int(cfg.get("ema_slow_length", 21))

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
            session_close = float(day["close"].iloc[-1])

            long_cond = session_close >= session_open + trend_mult * atr_prev
            short_cond = session_close <= session_open - trend_mult * atr_prev
            is_strong = bool(long_cond or short_cond)
            if not is_strong:
                continue

            direction = "long" if long_cond else "short"

            first_n = day.iloc[:max_bar].copy()
            if direction == "long":
                first_n["thrust"] = (first_n["high"] - session_open) / atr_prev
            else:
                first_n["thrust"] = (session_open - first_n["low"]) / atr_prev
            first_n["thrust_cum"] = first_n["thrust"].cummax()

            trig_rel = _first_cross_index(first_n["thrust_cum"], threshold)
            triggered = trig_rel is not None

            base_row = {
                "ticker": ticker,
                "session_date": session_date,
                "direction": direction,
                "is_strong_trend_day": True,
                "atr14_prev": atr_prev,
                "session_open": session_open,
                "session_close": session_close,
                "close_from_open_atr": (session_close - session_open) / atr_prev if direction == "long" else (session_open - session_close) / atr_prev,
                "triggered": triggered,
                "trigger_bar_exact": np.nan,
                "trigger_by_bar2": False,
                "trigger_by_bar3": False,
                "trigger_magnitude_atr": np.nan,
                "trigger_magnitude_bucket": None,
                "trigger_time": pd.NaT,
                "cloud_touch_any": False,
                "touch_ema10": False,
                "cloud_entry": False,
                "touch_ema21": False,
                "cloud_contact_time": pd.NaT,
                "directional_breach": False,
                "directional_breach_time": pd.NaT,
                "directional_breach_timing_after_trigger": None,
                "cloud_flip": False,
                "cloud_flip_time": pd.NaT,
                "cloud_flip_timing_after_trigger": None,
                "new_extreme_after_breach": False,
                "min_breach_to_new_extreme": np.nan,
                "new_extreme_after_flip": False,
                "min_flip_to_new_extreme": np.nan,
                "close_ge_plus1atr_after_event": np.nan,
                "close_le_minus1atr_after_event": np.nan,
                "close_still_strong_after_event": np.nan,
                "breach_session_bucket": None,
                "flip_session_bucket": None,
            }

            if not triggered:
                all_rows.append(base_row)
                kept += 1
                continue

            trigger_idx = int(trig_rel)
            trigger_ts = first_n.index[trigger_idx]
            trigger_mag = float(first_n["thrust_cum"].iloc[trigger_idx])

            row = base_row.copy()
            row.update(
                {
                    "trigger_bar_exact": trigger_idx + 1,
                    "trigger_by_bar2": bool((trigger_idx + 1) <= 2),
                    "trigger_by_bar3": bool((trigger_idx + 1) <= 3),
                    "trigger_magnitude_atr": trigger_mag,
                    "trigger_magnitude_bucket": _bucket_trigger_magnitude(trigger_mag),
                    "trigger_time": trigger_ts,
                }
            )

            full_idx = day.index.get_loc(trigger_ts)
            next_hour = day.iloc[full_idx + 1 : full_idx + 1 + next_hour_bars].copy()
            if next_hour.empty:
                all_rows.append(row)
                kept += 1
                continue

            if direction == "long":
                row["touch_ema10"] = bool((next_hour["low"] <= next_hour["ema10"]).any())
                row["touch_ema21"] = bool((next_hour["low"] <= next_hour["ema21"]).any())
            else:
                row["touch_ema10"] = bool((next_hour["high"] >= next_hour["ema10"]).any())
                row["touch_ema21"] = bool((next_hour["high"] >= next_hour["ema21"]).any())

            row["cloud_entry"] = bool(next_hour.apply(_intersects_cloud, axis=1).any())
            row["cloud_touch_any"] = bool(row["touch_ema10"] or row["cloud_entry"] or row["touch_ema21"])

            contact_ts = _first_cloud_contact(next_hour)
            if contact_ts is not None:
                row["cloud_contact_time"] = contact_ts
                post_contact = next_hour[next_hour.index >= contact_ts]
            else:
                post_contact = pd.DataFrame(columns=next_hour.columns)

            if not post_contact.empty:
                if direction == "long":
                    breach_mask = post_contact["close"] < post_contact["ema21"]
                else:
                    breach_mask = post_contact["close"] > post_contact["ema10"]

                if breach_mask.any():
                    breach_ts = post_contact.index[breach_mask][0]
                    row["directional_breach"] = True
                    row["directional_breach_time"] = breach_ts
                    row["directional_breach_timing_after_trigger"] = _event_timing_bucket(trigger_ts, breach_ts)
                    row["breach_session_bucket"] = _session_tod_bucket(breach_ts)

                    recovered, mins = _post_event_recovery(day, breach_ts, direction)
                    row["new_extreme_after_breach"] = recovered
                    row["min_breach_to_new_extreme"] = mins

            flip_window = day.iloc[full_idx : full_idx + 1 + next_hour_bars].copy()
            flip_ts = _find_flip_time(flip_window, direction)
            if flip_ts is not None:
                row["cloud_flip"] = True
                row["cloud_flip_time"] = flip_ts
                row["cloud_flip_timing_after_trigger"] = _event_timing_bucket(trigger_ts, flip_ts)
                row["flip_session_bucket"] = _session_tod_bucket(flip_ts)

                recovered, mins = _post_event_recovery(day, flip_ts, direction)
                row["new_extreme_after_flip"] = recovered
                row["min_flip_to_new_extreme"] = mins

            row["close_ge_plus1atr_after_event"] = bool((session_close - session_open) / atr_prev >= trend_mult)
            row["close_le_minus1atr_after_event"] = bool((session_open - session_close) / atr_prev >= trend_mult)
            row["close_still_strong_after_event"] = bool(row["close_ge_plus1atr_after_event"] if direction == "long" else row["close_le_minus1atr_after_event"])

            all_rows.append(row)
            kept += 1

        manifest_rows.append({"ticker": ticker, "status": "ok", "rows": kept})

    events = pd.DataFrame(all_rows)
    if events.empty:
        (summary_dir / "analysis_summary.txt").write_text(
            "No qualifying strong trend-day sessions found for opening-thrust analysis.",
            encoding="utf-8",
        )
        pd.DataFrame(manifest_rows).to_csv(summary_dir / "analysis_manifest.csv", index=False)
        print("No qualifying sessions found.")
        return

    # Coerce datetimes for CSV stability.
    for col in [
        "trigger_time",
        "cloud_contact_time",
        "directional_breach_time",
        "cloud_flip_time",
    ]:
        if col in events.columns:
            events[col] = pd.to_datetime(events[col], errors="coerce")

    events.to_csv(data_dir / "events_opening_thrust_detailed.csv", index=False)

    # Tables required by prompt.
    overall = pd.DataFrame(
        [
            _build_direction_summary(events, "long"),
            _build_direction_summary(events, "short"),
            _build_direction_summary(events, "combined"),
        ]
    )
    overall.to_csv(tables_dir / "overall_sample_summary.csv", index=False)

    triggered = events[events["triggered"]].copy()

    timing_exact = (
        triggered.groupby(["direction", "trigger_bar_exact"]).size().reset_index(name="n")
    )
    timing_exact["denominator_n_triggered"] = timing_exact.groupby("direction")["n"].transform("sum")
    timing_exact["rate_of_triggered"] = timing_exact["n"] / timing_exact["denominator_n_triggered"]
    timing_exact.to_csv(tables_dir / "trigger_timing_exact_bar.csv", index=False)

    timing_cum_rows = []
    for direction in ["long", "short", "combined"]:
        src = triggered if direction == "combined" else triggered[triggered["direction"] == direction]
        den = len(src)
        by2 = int(src["trigger_by_bar2"].sum())
        by3 = int(src["trigger_by_bar3"].sum())
        timing_cum_rows.append(
            {
                "direction": direction,
                "n_triggered": den,
                "n_trigger_by_bar2": by2,
                "rate_trigger_by_bar2": _safe_rate(by2, den),
                "n_trigger_by_bar3": by3,
                "rate_trigger_by_bar3": _safe_rate(by3, den),
                "confidence": _confidence_label(den),
            }
        )
    pd.DataFrame(timing_cum_rows).to_csv(tables_dir / "trigger_timing_cumulative.csv", index=False)

    magnitude = (
        triggered.groupby(["direction", "trigger_magnitude_bucket"]).size().reset_index(name="n")
    )
    magnitude["denominator_n_triggered"] = magnitude.groupby("direction")["n"].transform("sum")
    magnitude["rate_of_triggered"] = magnitude["n"] / magnitude["denominator_n_triggered"]
    magnitude.to_csv(tables_dir / "trigger_magnitude_buckets.csv", index=False)

    cloud_depth_rows = []
    for direction in ["long", "short", "combined"]:
        src = triggered if direction == "combined" else triggered[triggered["direction"] == direction]
        den = len(src)
        cloud_depth_rows.append(
            {
                "direction": direction,
                "denominator_n_triggered": den,
                "n_cloud_touch_any": int(src["cloud_touch_any"].sum()),
                "rate_cloud_touch_any": float(src["cloud_touch_any"].mean()) if den else np.nan,
                "n_touch_ema10": int(src["touch_ema10"].sum()),
                "rate_touch_ema10": float(src["touch_ema10"].mean()) if den else np.nan,
                "n_cloud_entry": int(src["cloud_entry"].sum()),
                "rate_cloud_entry": float(src["cloud_entry"].mean()) if den else np.nan,
                "n_touch_ema21": int(src["touch_ema21"].sum()),
                "rate_touch_ema21": float(src["touch_ema21"].mean()) if den else np.nan,
                "confidence": _confidence_label(den),
            }
        )
    pd.DataFrame(cloud_depth_rows).to_csv(tables_dir / "cloud_touch_depth_rates.csv", index=False)

    breach_rows = []
    flip_rows = []
    for direction in ["long", "short", "combined"]:
        src = triggered if direction == "combined" else triggered[triggered["direction"] == direction]
        den = len(src)

        br = src[src["directional_breach"]]
        breach_rows.append(
            {
                "direction": direction,
                "denominator_n_triggered": den,
                "n_directional_breach": len(br),
                "directional_breach_rate_of_triggered": _safe_rate(len(br), den),
                "post_breach_new_extreme_rate": float(br["new_extreme_after_breach"].mean()) if len(br) else np.nan,
                "post_breach_still_strong_close_rate": float(br["close_still_strong_after_event"].mean()) if len(br) else np.nan,
                "median_min_breach_to_new_extreme": float(br["min_breach_to_new_extreme"].dropna().median()) if len(br) else np.nan,
                "confidence": _confidence_label(den),
            }
        )

        fl = src[src["cloud_flip"]]
        flip_rows.append(
            {
                "direction": direction,
                "denominator_n_triggered": den,
                "n_cloud_flip": len(fl),
                "cloud_flip_rate_of_triggered": _safe_rate(len(fl), den),
                "post_flip_new_extreme_rate": float(fl["new_extreme_after_flip"].mean()) if len(fl) else np.nan,
                "post_flip_still_strong_close_rate": float(fl["close_still_strong_after_event"].mean()) if len(fl) else np.nan,
                "median_min_flip_to_new_extreme": float(fl["min_flip_to_new_extreme"].dropna().median()) if len(fl) else np.nan,
                "confidence": _confidence_label(den),
            }
        )

    pd.DataFrame(breach_rows).to_csv(tables_dir / "directional_breach_rates_and_recovery.csv", index=False)
    pd.DataFrame(flip_rows).to_csv(tables_dir / "cloud_flip_rates_and_recovery.csv", index=False)

    # First 30m vs second 30m post-trigger split for breach/flip.
    timing_rows = []
    for direction in ["long", "short", "combined"]:
        src = triggered if direction == "combined" else triggered[triggered["direction"] == direction]
        den_breach = int(src["directional_breach"].sum())
        den_flip = int(src["cloud_flip"].sum())

        br = src[src["directional_breach"]]
        fl = src[src["cloud_flip"]]

        for bucket in ["first_30m", "second_30m"]:
            b_sub = br[br["directional_breach_timing_after_trigger"] == bucket]
            f_sub = fl[fl["cloud_flip_timing_after_trigger"] == bucket]
            timing_rows.append(
                {
                    "direction": direction,
                    "timing_bucket": bucket,
                    "denominator_n_breach": den_breach,
                    "n_breach_in_bucket": len(b_sub),
                    "rate_of_breach_events": _safe_rate(len(b_sub), den_breach),
                    "denominator_n_flip": den_flip,
                    "n_flip_in_bucket": len(f_sub),
                    "rate_of_flip_events": _safe_rate(len(f_sub), den_flip),
                }
            )
    pd.DataFrame(timing_rows).to_csv(tables_dir / "post_trigger_30m_split.csv", index=False)

    # Optional broader session context.
    session_ctx = triggered[triggered["directional_breach"]].groupby(["direction", "breach_session_bucket"]).size().reset_index(name="n")
    if not session_ctx.empty:
        session_ctx["denominator_n_breach"] = session_ctx.groupby("direction")["n"].transform("sum")
        session_ctx["rate_of_breach_events"] = session_ctx["n"] / session_ctx["denominator_n_breach"]
    session_ctx.to_csv(tables_dir / "session_context_breach_tod.csv", index=False)

    pd.DataFrame(manifest_rows).to_csv(summary_dir / "analysis_manifest.csv", index=False)

    overall_comb = overall[overall["direction"] == "combined"].iloc[0]
    text_lines = [
        "Opening Thrust to EMA Cloud Pullback Study (Strong +/-1.0 ATR Trend Days)",
        "=" * 86,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Universe: QuantLab watchlist ({len(tickers)} requested)",
        f"Date window: {cfg.get('start_date', '2024-01-01')} to {cfg.get('end_date', 'today')}",
        "",
        "Headline:",
        (
            f"Among {int(overall_comb['n_base_strong_trend_days'])} strong trend days, "
            f"{int(overall_comb['n_triggered_opening_thrust'])} triggered 0.70+ ATR in bars 1-3. "
            f"Within one hour after trigger, cloud touch-any occurred in {overall_comb['cloud_touch_any_rate_of_triggered']:.1%} and "
            f"directional breach occurred in {overall_comb['directional_breach_rate_of_triggered']:.1%} of triggered events."
        ),
        "",
        "Denominator Map:",
        "- Trigger rate denominator: all strong trend days (n_base_strong_trend_days)",
        "- Cloud depth / breach / flip denominators: triggered events only (n_triggered_opening_thrust)",
        "- Recovery denominators: breach-only or flip-only subsets",
        "",
        "Core interpretation:",
        "- This is a next-hour-only study after early thrust trigger, not whole-session eventual touch.",
        "- Long breach definition: close below EMA21 within next hour after cloud contact.",
        "- Short breach definition: close above EMA10 within next hour after cloud contact.",
        "- Cloud flip is reported as deeper structural layer and compared to initial breach outcomes.",
    ]
    (summary_dir / "analysis_summary.txt").write_text("\n".join(text_lines), encoding="utf-8")

    print("Analysis complete.")
    print(f"Events: {data_dir / 'events_opening_thrust_detailed.csv'}")
    print(f"Summary: {summary_dir / 'analysis_summary.txt'}")


if __name__ == "__main__":
    analyze()
