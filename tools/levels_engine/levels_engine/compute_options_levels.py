"""
Compute deterministic options key levels from contract data.

All thresholds are defined as module-level constants and documented.
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .config import Config
from .logger import get_logger
from .schemas import (
    OptionsLevelsOutput,
    OptionsLevelsDiagnostics,
    PinCandidate,
    StrikeLevel,
    VacuumWindow,
)

log = get_logger("compute_options")


# ── public entry point ──────────────────────────────────────

def compute_options_levels(
    ticker: str,
    spot: float,
    contracts: List[Dict[str, Any]],
    cfg: Config,
) -> OptionsLevelsOutput:
    """
    Take raw contract dicts and produce deterministic key levels.

    Parameters
    ----------
    ticker : str
    spot : float – underlying last price
    contracts : list[dict] – each with keys:
        symbol, type (c/p), strike, expiration, open_interest, volume, iv
    cfg : Config

    Returns
    -------
    OptionsLevelsOutput
    """
    from .utils.dates import iso_utc, utcnow

    asof = iso_utc(utcnow())

    if not contracts:
        log.warning("%s: no contracts — returning empty output", ticker)
        return OptionsLevelsOutput(
            ticker=ticker, spot=spot, asof_utc=asof,
            window_days=cfg.options_expiry_window_days,
            expirations_considered=0,
        )

    df = _build_dataframe(contracts, ticker, spot, asof)
    diag = _diagnostics(df, contracts)

    # Drop rows missing strike or type
    df = df.dropna(subset=["strike", "option_type"])
    df = df[df["strike"] > 0]

    # Strike aggregation
    agg = _aggregate_by_strike(df)

    call_wall = _wall(agg, "call_oi")
    put_wall = _wall(agg, "put_oi")

    top_calls = _top_n(agg, "call_oi", cfg.options_top_n)
    top_puts = _top_n(agg, "put_oi", cfg.options_top_n)

    pins = _pin_candidates(agg, cfg)
    vacuums = _vacuum_windows(agg, spot, cfg)
    near = _near_spot(agg, spot, cfg)

    exps = df["expiration"].nunique()

    return OptionsLevelsOutput(
        ticker=ticker,
        spot=spot,
        asof_utc=asof,
        window_days=cfg.options_expiry_window_days,
        expirations_considered=exps,
        call_wall=call_wall,
        put_wall=put_wall,
        top_call_clusters=top_calls,
        top_put_clusters=top_puts,
        pin_candidates=pins,
        vacuum_windows=vacuums,
        near_spot_levels=near,
        diagnostics=diag,
    )


# ── dataframe construction ──────────────────────────────────

def _build_dataframe(
    contracts: List[Dict], ticker: str, spot: float, asof: str
) -> pd.DataFrame:
    df = pd.DataFrame(contracts)
    df["ticker"] = ticker
    df["spot"] = spot
    df["asof"] = asof

    # normalise type column
    df["option_type"] = df["type"].str.lower().str[:1]  # c / p

    # ensure numerics
    for col in ("strike", "open_interest", "volume", "iv"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    # DTE
    df["expiration"] = pd.to_datetime(df["expiration"], errors="coerce", utc=True)
    df["dte"] = (df["expiration"] - pd.Timestamp.now(tz="UTC")).dt.days.clip(lower=0)

    return df


def _diagnostics(df: pd.DataFrame, raw: List[Dict]) -> OptionsLevelsDiagnostics:
    missing_oi = int((df.get("open_interest", pd.Series(dtype=float)) == 0).sum())
    return OptionsLevelsDiagnostics(
        contracts_count=len(raw),
        expirations_count=int(df["expiration"].nunique()) if "expiration" in df.columns else 0,
        missing_oi_count=missing_oi,
    )


# ── aggregation ─────────────────────────────────────────────

def _aggregate_by_strike(df: pd.DataFrame) -> pd.DataFrame:
    calls = df[df["option_type"] == "c"].groupby("strike")["open_interest"].sum().rename("call_oi")
    puts = df[df["option_type"] == "p"].groupby("strike")["open_interest"].sum().rename("put_oi")
    agg = pd.concat([calls, puts], axis=1).fillna(0).astype(int)
    agg["total_oi"] = agg["call_oi"] + agg["put_oi"]
    agg = agg.reset_index()
    return agg


# ── level detectors ─────────────────────────────────────────

def _wall(agg: pd.DataFrame, col: str) -> StrikeLevel | None:
    if agg.empty or agg[col].max() == 0:
        return None
    row = agg.loc[agg[col].idxmax()]
    return StrikeLevel(
        strike=float(row["strike"]),
        call_oi=int(row["call_oi"]),
        put_oi=int(row["put_oi"]),
        total_oi=int(row["total_oi"]),
    )


def _top_n(agg: pd.DataFrame, col: str, n: int) -> List[StrikeLevel]:
    top = agg.nlargest(n, col)
    return [
        StrikeLevel(
            strike=float(r["strike"]),
            call_oi=int(r["call_oi"]),
            put_oi=int(r["put_oi"]),
            total_oi=int(r["total_oi"]),
        )
        for _, r in top.iterrows()
    ]


def _pin_candidates(agg: pd.DataFrame, cfg: Config) -> List[PinCandidate]:
    """
    MAGNET / PIN CANDIDATES:
    - balance = abs(call - put) / (call + put + 1)
    - band: balance <= cfg.pin_balance_band  (default 0.25)
    - require total_oi >= 70th percentile
    - return top cfg.pin_max_results by total_oi
    """
    if agg.empty:
        return []
    agg = agg.copy()
    agg["balance"] = (
        (agg["call_oi"] - agg["put_oi"]).abs()
        / (agg["call_oi"] + agg["put_oi"] + 1)
    )
    threshold_oi = np.percentile(agg["total_oi"], cfg.pin_oi_percentile)
    mask = (agg["balance"] <= cfg.pin_balance_band) & (agg["total_oi"] >= threshold_oi)
    candidates = agg[mask].nlargest(cfg.pin_max_results, "total_oi")
    return [
        PinCandidate(
            strike=float(r["strike"]),
            total_oi=int(r["total_oi"]),
            balance=round(float(r["balance"]), 4),
        )
        for _, r in candidates.iterrows()
    ]


def _vacuum_windows(agg: pd.DataFrame, spot: float, cfg: Config) -> List[VacuumWindow]:
    """
    VACUUM WINDOWS:
    - Sort strikes ascending.
    - For each adjacent pair, compute avg OI = (total_oi_low + total_oi_high) / 2.
    - A "vacuum" interval is where avg OI is below the 30th percentile of total_oi.
    - Merge contiguous vacuum intervals.
    - Return up to cfg.vacuum_max_results closest to spot.
    """
    if len(agg) < 2:
        return []
    agg = agg.sort_values("strike").reset_index(drop=True)
    threshold = np.percentile(agg["total_oi"], cfg.vacuum_oi_percentile)

    windows: List[VacuumWindow] = []
    i = 0
    while i < len(agg) - 1:
        avg_oi = (agg.loc[i, "total_oi"] + agg.loc[i + 1, "total_oi"]) / 2
        if avg_oi < threshold:
            # start a contiguous vacuum window
            low = float(agg.loc[i, "strike"])
            high = float(agg.loc[i + 1, "strike"])
            oi_sum = avg_oi
            count = 1
            j = i + 1
            while j < len(agg) - 1:
                next_avg = (agg.loc[j, "total_oi"] + agg.loc[j + 1, "total_oi"]) / 2
                if next_avg < threshold:
                    high = float(agg.loc[j + 1, "strike"])
                    oi_sum += next_avg
                    count += 1
                    j += 1
                else:
                    break
            midpoint = (low + high) / 2
            windows.append(VacuumWindow(
                low_strike=low,
                high_strike=high,
                avg_oi=round(oi_sum / count, 1),
                distance_from_spot=round(abs(midpoint - spot), 2),
            ))
            i = j + 1
        else:
            i += 1

    # Sort by distance from spot, return closest N
    windows.sort(key=lambda w: w.distance_from_spot)
    return windows[: cfg.vacuum_max_results]


def _near_spot(agg: pd.DataFrame, spot: float, cfg: Config) -> List[StrikeLevel]:
    """Strikes within ±cfg.near_spot_pct of spot, top N by total OI."""
    if agg.empty:
        return []
    band = spot * cfg.near_spot_pct / 100
    mask = (agg["strike"] >= spot - band) & (agg["strike"] <= spot + band)
    near = agg[mask].nlargest(cfg.near_spot_max, "total_oi")
    return [
        StrikeLevel(
            strike=float(r["strike"]),
            call_oi=int(r["call_oi"]),
            put_oi=int(r["put_oi"]),
            total_oi=int(r["total_oi"]),
        )
        for _, r in near.iterrows()
    ]


# ── CSV export helper ───────────────────────────────────────

def build_strike_csv(contracts: List[Dict[str, Any]]) -> pd.DataFrame:
    """Build a per-strike summary CSV dataframe."""
    if not contracts:
        return pd.DataFrame(columns=["strike", "call_oi", "put_oi", "total_oi"])
    df = pd.DataFrame(contracts)
    df["option_type"] = df["type"].str.lower().str[:1]
    df["open_interest"] = pd.to_numeric(df.get("open_interest", 0), errors="coerce").fillna(0).astype(int)
    df["strike"] = pd.to_numeric(df["strike"], errors="coerce")
    calls = df[df["option_type"] == "c"].groupby("strike")["open_interest"].sum().rename("call_oi")
    puts = df[df["option_type"] == "p"].groupby("strike")["open_interest"].sum().rename("put_oi")
    out = pd.concat([calls, puts], axis=1).fillna(0).astype(int)
    out["total_oi"] = out["call_oi"] + out["put_oi"]
    return out.reset_index().sort_values("strike")
