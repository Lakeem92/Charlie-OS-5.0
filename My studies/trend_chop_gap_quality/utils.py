#!/usr/bin/env python3
"""
trend_chop_gap_quality — Shared utility helpers.

All functions are pure, unit-safe, and deterministic.
No trade advice. Descriptive computations only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ── Safe Math ────────────────────────────────────────────────

def safe_divide(a, b, default: float = 0.0) -> float:
    """Return a/b, or *default* when b is zero, None, or NaN."""
    try:
        if b is None or b == 0 or (isinstance(b, float) and np.isnan(b)):
            return default
        return float(a) / float(b)
    except (TypeError, ValueError, ZeroDivisionError):
        return default


# ── Core Indicators ──────────────────────────────────────────

def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """True Range = max(H-L, |H-Cprev|, |L-Cprev|)."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series,
        length: int = 14) -> pd.Series:
    """Average True Range (simple rolling mean of TR)."""
    tr = true_range(high, low, close)
    return tr.rolling(window=length, min_periods=length).mean()


def sma(series: pd.Series, length: int = 20) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=length, min_periods=length).mean()


# ── Price Structure Metrics ──────────────────────────────────

def clv(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """
    Close Location Value = (close - low) / (high - low).
    1.0 = closed at high, 0.0 = closed at low.
    """
    denom = high - low
    return (close - low) / denom.replace(0, np.nan)


def body_pct(open_: pd.Series, high: pd.Series,
             low: pd.Series, close: pd.Series) -> pd.Series:
    """
    Body as fraction of total range = |close-open| / (high-low).
    """
    denom = high - low
    return (close - open_).abs() / denom.replace(0, np.nan)


def range_multiple(high: pd.Series, low: pd.Series,
                   atr_series: pd.Series) -> pd.Series:
    """Day range / ATR.  >1 = wider than average."""
    return (high - low) / atr_series.replace(0, np.nan)


def gap_pct(open_today: pd.Series, close_prev: pd.Series) -> pd.Series:
    """Overnight gap as percentage: (open - prev_close) / prev_close."""
    return (open_today - close_prev) / close_prev.replace(0, np.nan)


# ── Intraday Helpers ─────────────────────────────────────────

def vwap(typical_price: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Cumulative VWAP = cumsum(typical_price * volume) / cumsum(volume).
    Caller must reset cumulative sums per day externally.
    """
    cum_tp_vol = (typical_price * volume).cumsum()
    cum_vol = volume.cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)


def typical_price(high: pd.Series, low: pd.Series,
                  close: pd.Series) -> pd.Series:
    """(High + Low + Close) / 3."""
    return (high + low + close) / 3.0


def compute_daily_vwap(df_intraday: pd.DataFrame) -> pd.Series:
    """
    Compute intraday VWAP reset per day.
    Expects columns: high, low, close, volume and a datetime index.
    """
    tp = typical_price(df_intraday["high"], df_intraday["low"],
                       df_intraday["close"])
    tp_vol = tp * df_intraday["volume"]

    # Group by date to reset cumulative sums
    dates = df_intraday.index.date
    cum_tp_vol = tp_vol.groupby(dates).cumsum()
    cum_vol = df_intraday["volume"].groupby(dates).cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)


def first_hour_window(df_day: pd.DataFrame,
                      or_minutes: int = 60) -> pd.DataFrame:
    """
    Extract the first-hour bars from an intraday DataFrame for a single day.
    Uses timestamps to determine the window (open bar + or_minutes).
    """
    if df_day.empty:
        return df_day
    start_ts = df_day.index[0]
    end_ts = start_ts + pd.Timedelta(minutes=or_minutes)
    return df_day.loc[start_ts:end_ts]


def or_break_time_minutes(df_day: pd.DataFrame, or_high: float) -> float:
    """
    Minutes from day open until the first bar that trades above OR high.
    If never breaks, returns 999.0 (sentinel).
    """
    if df_day.empty:
        return 999.0
    start_ts = df_day.index[0]
    breaks = df_day[df_day["high"] > or_high]
    if breaks.empty:
        return 999.0
    first_break = breaks.index[0]
    delta = (first_break - start_ts).total_seconds() / 60.0
    return delta


def pullback_depth(df_first_hour: pd.DataFrame, or_high: float,
                   or_low: float) -> float:
    """
    After OR high is printed in first hour, find the subsequent low.
    Depth = (OR_high - subsequent_low) / (OR_high - OR_low).
    Returns 0 if OR_high never printed or range is zero.
    """
    or_range = or_high - or_low
    if or_range <= 0:
        return 0.0

    # Find index where high first reaches or_high
    hit_indices = df_first_hour[df_first_hour["high"] >= or_high].index
    if len(hit_indices) == 0:
        return 0.0

    after_hit = df_first_hour.loc[hit_indices[0]:]
    if after_hit.empty:
        return 0.0

    sub_low = after_hit["low"].min()
    return safe_divide(or_high - sub_low, or_range, 0.0)


def reclaim_count(close_series: pd.Series,
                  vwap_series: pd.Series) -> int:
    """
    Count transitions where close crosses from below VWAP to above VWAP.
    """
    above = close_series > vwap_series
    transitions = above.astype(int).diff()
    # +1 diff means crossed from below (False) to above (True)
    return int((transitions == 1).sum())


# ── Gap Bin Labelling ────────────────────────────────────────

def assign_gap_bin(gap_val: float,
                   bins: list[float] | None = None) -> str:
    """
    Assign a gap percentage to a labelled bin.
    Default bins: [0.01, 0.03, 0.05, 0.08, 0.12, 0.20]
    Labels: '1-3%', '3-5%', '5-8%', '8-12%', '12-20%', '20%+'
    Returns '' if gap < first bin.
    """
    if bins is None:
        bins = [0.01, 0.03, 0.05, 0.08, 0.12, 0.20]

    labels = []
    for i in range(len(bins) - 1):
        low_pct = int(round(bins[i] * 100))
        high_pct = int(round(bins[i + 1] * 100))
        labels.append(f"{low_pct}-{high_pct}%")
    last_pct = int(round(bins[-1] * 100))
    labels.append(f"{last_pct}%+")

    if gap_val < bins[0]:
        return ""
    for i in range(len(bins) - 1):
        if bins[i] <= gap_val < bins[i + 1]:
            return labels[i]
    return labels[-1]
