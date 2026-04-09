"""
Query-mode computation — FORCED-ACTION MOMENTUM MAP (two-lens).

Deterministic strike selection + mechanical commentary.
No trade advice, no directional bias, no scoring.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .config import Config
from .logger import get_logger
from .schemas import ArbLevel, ArbLevelsOutput

log = get_logger("query_compute")

# ────────────────────────────────────────────────────────────
# 1. DATE HELPERS
# ────────────────────────────────────────────────────────────

def _third_friday(year: int, month: int) -> date:
    """Return the 3rd Friday of a given year/month (standard monthly OPEX)."""
    # 1st day of month
    first = date(year, month, 1)
    # weekday: Mon=0 … Fri=4
    dow = first.weekday()
    # first Friday
    first_fri = first + timedelta(days=(4 - dow) % 7)
    return first_fri + timedelta(weeks=2)


def next_monthly_opex(ref: date) -> date:
    """Return the next standard monthly OPEX (3rd Friday) on or after *ref*."""
    tf = _third_friday(ref.year, ref.month)
    if tf >= ref:
        return tf
    # advance to next month
    if ref.month == 12:
        return _third_friday(ref.year + 1, 1)
    return _third_friday(ref.year, ref.month + 1)


def _us_market_session(utc_now: datetime) -> str:
    """Rough session label from UTC time (EST = UTC-5)."""
    et = utc_now - timedelta(hours=5)
    h, m = et.hour, et.minute
    t = h * 60 + m
    if t < 4 * 60:
        return "OVERNIGHT"
    if t < 9 * 60 + 30:
        return "PRE-MARKET"
    if t < 16 * 60:
        return "RTH"
    if t < 20 * 60:
        return "AFTER-HOURS"
    return "OVERNIGHT"


# ────────────────────────────────────────────────────────────
# 2. STALENESS
# ────────────────────────────────────────────────────────────

def staleness_label(snap_date_str: str | None, today: date) -> str:
    """Return staleness label per spec.  Empty string = same session."""
    if not snap_date_str:
        return "OI DATE UNVERIFIED"
    try:
        snap_d = datetime.fromisoformat(snap_date_str.replace("Z", "+00:00")).date()
    except Exception:
        try:
            snap_d = date.fromisoformat(snap_date_str[:10])
        except Exception:
            return "OI DATE UNVERIFIED"
    delta = (today - snap_d).days
    if delta <= 0:
        return ""
    if delta <= 3:
        return f"PRIOR SESSION DATA ({snap_d.isoformat()})"
    if delta <= 7:
        return f"STALE — CONTEXT ONLY ({snap_d.isoformat()})"
    return "ANALYSIS INVALID — STALE OPTIONS DATA"


# ────────────────────────────────────────────────────────────
# 3. LENS SELECTION
# ────────────────────────────────────────────────────────────

def select_lenses(
    contracts: List[Dict[str, Any]],
    today: date,
) -> Tuple[Optional[str], Optional[str], bool]:
    """
    Pick front-week and closest-monthly expiration dates.

    Returns (front_week_exp, monthly_exp, monthly_is_proxy).
    Dates are ISO strings (YYYY-MM-DD).
    """
    exps = sorted({c["expiration"] for c in contracts if c.get("expiration")})
    if not exps:
        return None, None, False

    today_s = today.isoformat()

    # eligible = on or after today
    eligible = [e for e in exps if e >= today_s]
    if not eligible:
        eligible = exps  # fallback

    # Front week: nearest expiration
    front_week = eligible[0] if eligible else None

    # Monthly: 3rd Friday of this/next month
    target_monthly = next_monthly_opex(today).isoformat()

    monthly_exp: str | None = None
    monthly_proxy = False

    if target_monthly in eligible:
        monthly_exp = target_monthly
    else:
        # find closest within ±3 calendar days
        best = None
        best_dist = 999
        for e in eligible:
            try:
                d = abs((date.fromisoformat(e) - date.fromisoformat(target_monthly)).days)
            except Exception:
                continue
            if d <= 3 and d < best_dist:
                best = e
                best_dist = d
        if best:
            monthly_exp = best
            monthly_proxy = True
        else:
            # pick the furthest eligible as a rough proxy
            for e in reversed(eligible):
                if e != front_week:
                    monthly_exp = e
                    monthly_proxy = True
                    break

    # If front and monthly collide, try to bump monthly to next available
    if front_week and monthly_exp and front_week == monthly_exp:
        for e in eligible:
            if e != front_week:
                if date.fromisoformat(e) > date.fromisoformat(front_week):
                    monthly_exp = e
                    monthly_proxy = True
                    break

    return front_week, monthly_exp, monthly_proxy


# ────────────────────────────────────────────────────────────
# 4. PER-LENS STRIKE ANALYSIS
# ────────────────────────────────────────────────────────────

_TAG_CALL_WALL = "CALL WALL"
_TAG_PUT_WALL = "PUT WALL"
_TAG_PIN = "PIN/MAGNET"
_TAG_STEP = "STEP-CHANGE"
_TAG_VOLUME = "HIGH VOLUME"
_TAG_BRACKET = "NEAR-SPOT BRACKET"

# Template strings -------------------------------------------

_WHO_IS_FORCED = {
    _TAG_CALL_WALL: "Dealers hedging call exposure; momentum chasers may get pulled in on breach.",
    _TAG_PUT_WALL: "Dealers hedging put exposure; liquidation pressure can increase if support breaks.",
    _TAG_PIN: "Dealer hedging flows can dampen movement; price may gravitate to this strike into expiry.",
    _TAG_STEP: "A discrete positioning jump; hedging intensity can change quickly as spot enters this zone.",
    _TAG_VOLUME: "High turnover strike; can act as a battle line where hedging and speculation concentrate.",
}

_BREACH_CALL = "If breached, hedging demand can increase and price can travel faster toward the next call concentration."
_BREACH_PUT = "If breached, hedging flows can add pressure and price can travel faster toward the next put concentration."
_BREACH_PIN = "If breached, pinning influence weakens and price can shift toward the next nearest concentration."

_REJ_AWAY = "On rejection, price often snaps back toward the nearest high OI cluster closer to spot."
_REJ_PIN = "On rejection, gravity toward this strike can persist, especially near expiry."


def _breach_text(tag: str, side: str) -> str:
    if tag == _TAG_PIN:
        return _BREACH_PIN
    return _BREACH_CALL if side == "above" else _BREACH_PUT


def _reject_text(tag: str) -> str:
    if tag == _TAG_PIN:
        return _REJ_PIN
    return _REJ_AWAY


def analyse_lens(
    contracts: List[Dict[str, Any]],
    spot: float,
    expiration: str,
    cfg: Config,
) -> Dict[str, Any]:
    """
    Run deterministic strike selection for one expiration.

    Returns dict with keys: expiration, levels[], iv_atm, iv_near_median,
    snapshot_date.
    """
    lens_c = [c for c in contracts if c.get("expiration") == expiration]
    if not lens_c:
        return {"expiration": expiration, "levels": [], "iv_atm": None, "iv_near_median": None, "snapshot_date": None}

    df = pd.DataFrame(lens_c)
    for col in ("strike", "open_interest", "volume", "iv"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0
    df["option_type"] = df["type"].astype(str).str.lower().str[:1]

    # Snapshot date heuristic — can't easily get from Alpaca; use None
    snapshot_date: str | None = None

    # Aggregate by strike
    calls = df[df["option_type"] == "c"].groupby("strike").agg(
        call_oi=("open_interest", "sum"),
        call_vol=("volume", "sum"),
        call_iv=("iv", "mean"),
    )
    puts = df[df["option_type"] == "p"].groupby("strike").agg(
        put_oi=("open_interest", "sum"),
        put_vol=("volume", "sum"),
        put_iv=("iv", "mean"),
    )
    agg = pd.concat([calls, puts], axis=1).fillna(0)
    agg.index.name = "strike"
    agg = agg.reset_index()
    agg["total_oi"] = agg["call_oi"] + agg["put_oi"]
    agg["total_vol"] = agg["call_vol"] + agg["put_vol"]

    if agg.empty:
        return {"expiration": expiration, "levels": [], "iv_atm": None, "iv_near_median": None, "snapshot_date": snapshot_date}

    levels: Dict[float, Dict] = {}  # strike → level dict   (first tag wins)

    def _add(strike: float, tag: str, side: str, oi: int, vol: int) -> None:
        if strike in levels:
            return  # first tag wins
        levels[strike] = {
            "strike": round(float(strike), 2),
            "type": tag,
            "side": side,
            "oi": int(oi),
            "volume": int(vol),
            "who_is_forced": _WHO_IS_FORCED.get(tag, ""),
            "breach": _breach_text(tag, side),
            "rejection": _reject_text(tag),
        }

    # --- (1) Call wall above spot (top 5 by call_oi) ---
    above = agg[agg["strike"] > spot].nlargest(5, "call_oi")
    if not above.empty:
        top = above.iloc[0]
        _add(top["strike"], _TAG_CALL_WALL, "above", top["call_oi"], top["call_vol"])
        for _, r in above.iloc[1:].iterrows():
            if r["call_oi"] > 0:
                _add(r["strike"], _TAG_CALL_WALL, "above", r["call_oi"], r["call_vol"])

    # --- (2) Put wall below spot (top 5 by put_oi) ---
    below = agg[agg["strike"] < spot].nlargest(5, "put_oi")
    if not below.empty:
        top = below.iloc[0]
        _add(top["strike"], _TAG_PUT_WALL, "below", top["put_oi"], top["put_vol"])
        for _, r in below.iloc[1:].iterrows():
            if r["put_oi"] > 0:
                _add(r["strike"], _TAG_PUT_WALL, "below", r["put_oi"], r["put_vol"])

    # --- (3) High volume (top 3) ---
    if agg["total_vol"].max() > 0:
        top_vol = agg.nlargest(3, "total_vol")
        for _, r in top_vol.iterrows():
            side = "above" if r["strike"] >= spot else "below"
            _add(r["strike"], _TAG_VOLUME, side, r["total_oi"], r["total_vol"])

    # --- (4) Step-change: OI >= 2x local rolling median ---
    agg_sorted = agg.sort_values("strike").reset_index(drop=True)
    for otype, oi_col in [("c", "call_oi"), ("p", "put_oi")]:
        rolling_med = agg_sorted[oi_col].rolling(window=11, center=True, min_periods=3).median()
        for idx, row in agg_sorted.iterrows():
            med_val = rolling_med.iloc[idx]
            if med_val > 0 and row[oi_col] >= 2 * med_val:
                side = "above" if row["strike"] >= spot else "below"
                _add(row["strike"], _TAG_STEP, side, row["total_oi"], row["total_vol"])

    # --- (5) Near-spot bracket: 1 call above, 1 put below ---
    calls_above = agg[(agg["strike"] > spot) & (agg["call_oi"] > 0)].sort_values("strike")
    if not calls_above.empty:
        r = calls_above.iloc[0]
        _add(r["strike"], _TAG_BRACKET, "above", r["total_oi"], r["total_vol"])

    puts_below = agg[(agg["strike"] < spot) & (agg["put_oi"] > 0)].sort_values("strike", ascending=False)
    if not puts_below.empty:
        r = puts_below.iloc[0]
        _add(r["strike"], _TAG_BRACKET, "below", r["total_oi"], r["total_vol"])

    # --- PIN/MAGNET ---
    agg_cp = agg.copy()
    agg_cp["balance"] = (agg_cp["call_oi"] - agg_cp["put_oi"]).abs() / (agg_cp["call_oi"] + agg_cp["put_oi"] + 1)
    oi_70 = np.percentile(agg_cp["total_oi"], 70) if len(agg_cp) > 2 else 0
    pin_mask = (agg_cp["balance"] <= 0.25) & (agg_cp["total_oi"] >= oi_70)
    pins = agg_cp[pin_mask].copy()
    pins["dist"] = (pins["strike"] - spot).abs()
    pins = pins.nlargest(3, "total_oi")
    for _, r in pins.iterrows():
        side = "above" if r["strike"] >= spot else "below"
        _add(r["strike"], _TAG_PIN, side, r["total_oi"], r["total_vol"])

    # Trim to max 20 levels, sorted by distance from spot
    sorted_levels = sorted(levels.values(), key=lambda l: abs(l["strike"] - spot))
    final_levels = sorted_levels[:20]

    # --- IV summary ---
    iv_atm = _compute_atm_iv(df, spot)
    iv_near_median = _compute_near_median_iv(df, spot)

    return {
        "expiration": expiration,
        "levels": final_levels,
        "iv_atm": iv_atm,
        "iv_near_median": iv_near_median,
        "snapshot_date": snapshot_date,
    }


def _compute_atm_iv(df: pd.DataFrame, spot: float) -> float | None:
    """IV of the strike closest to spot."""
    if "iv" not in df.columns or df["iv"].sum() == 0:
        return None
    df2 = df[df["iv"] > 0].copy()
    if df2.empty:
        return None
    df2["dist"] = (df2["strike"] - spot).abs()
    closest = df2.loc[df2["dist"].idxmin()]
    iv = float(closest["iv"])
    return round(iv, 4) if iv > 0 else None


def _compute_near_median_iv(df: pd.DataFrame, spot: float, pct: float = 2.5) -> float | None:
    """Median IV of strikes within ±pct% of spot."""
    if "iv" not in df.columns or df["iv"].sum() == 0:
        return None
    band = spot * pct / 100
    near = df[(df["strike"] >= spot - band) & (df["strike"] <= spot + band) & (df["iv"] > 0)]
    if near.empty:
        return None
    med = float(near["iv"].median())
    return round(med, 4) if med > 0 else None


# ────────────────────────────────────────────────────────────
# 5. DIRECTIONAL PATHS (STRIKE CHAINS)
# ────────────────────────────────────────────────────────────

def build_paths(levels: List[Dict], spot: float) -> Dict[str, List[float]]:
    """Build upside/downside strike chains from levels list."""
    above = sorted([l["strike"] for l in levels if l["strike"] > spot])
    below = sorted([l["strike"] for l in levels if l["strike"] < spot], reverse=True)
    return {"upside": above, "downside": below}


# ────────────────────────────────────────────────────────────
# 6. VERDICT (3 lines — mechanical)
# ────────────────────────────────────────────────────────────

def compute_verdict(
    lens_a_levels: List[Dict],
    lens_b_levels: List[Dict],
    spot: float,
) -> Dict[str, str]:
    """Three-line verdict based only on OI topology."""
    all_levels = lens_a_levels + lens_b_levels

    pins_near = [l for l in all_levels if l["type"] == _TAG_PIN and abs(l["strike"] - spot) / spot < 0.02]
    walls_above = [l for l in all_levels if l["side"] == "above" and l["type"] in (_TAG_CALL_WALL, _TAG_PUT_WALL, _TAG_STEP)]
    walls_below = [l for l in all_levels if l["side"] == "below" and l["type"] in (_TAG_CALL_WALL, _TAG_PUT_WALL, _TAG_STEP)]

    # REGIME
    if len(pins_near) >= 2:
        regime = "DAMPENING / PINNING"
    elif not walls_above[:1] and not walls_below[:1]:
        regime = "UNVERIFIED"
    elif len(pins_near) == 0 and walls_above and walls_below:
        # check if nearest wall is far (>3% from spot)
        nearest_above = min((l["strike"] for l in walls_above), default=spot)
        nearest_below = max((l["strike"] for l in walls_below), default=spot)
        if (nearest_above - spot) / spot > 0.03 and (spot - nearest_below) / spot > 0.03:
            regime = "ACCELERATION"
        else:
            regime = "MIXED"
    else:
        regime = "MIXED"

    # PATH OF LEAST RESISTANCE
    above_sorted = sorted(walls_above, key=lambda l: l["strike"])
    below_sorted = sorted(walls_below, key=lambda l: l["strike"], reverse=True)
    first_up = above_sorted[0]["strike"] if above_sorted else None
    first_down = below_sorted[0]["strike"] if below_sorted else None

    if pins_near:
        nearest_pin = min(pins_near, key=lambda l: abs(l["strike"] - spot))
        upper = first_up or nearest_pin["strike"]
        lower = first_down or nearest_pin["strike"]
        path = f"PINNED between ${lower:,.2f} and ${upper:,.2f}"
    elif first_up and first_down:
        up_dist = first_up - spot
        down_dist = spot - first_down
        if up_dist < down_dist:
            path = f"UP toward ${first_up:,.2f}"
        elif down_dist < up_dist:
            path = f"DOWN toward ${first_down:,.2f}"
        else:
            path = f"PINNED between ${first_down:,.2f} and ${first_up:,.2f}"
    elif first_up:
        path = f"UP toward ${first_up:,.2f}"
    elif first_down:
        path = f"DOWN toward ${first_down:,.2f}"
    else:
        path = "UNVERIFIED"

    # REGIME FLIP
    flip_candidates = above_sorted + list(reversed(below_sorted))
    if flip_candidates:
        flip = min(flip_candidates, key=lambda l: abs(l["strike"] - spot))
        flip_text = (
            f"Structure flips if ${flip['strike']:,.2f} is breached because "
            f"dealer hedging reverses direction at that OI concentration."
        )
    else:
        flip_text = "No clear flip level identified from current OI topology."

    return {
        "regime": regime,
        "path_of_least_resistance": path,
        "regime_flip": flip_text,
    }


# ────────────────────────────────────────────────────────────
# 7. LOAD ARB LEVELS FROM TODAY'S RUN (IF AVAILABLE)
# ────────────────────────────────────────────────────────────

def load_arb_levels(ticker: str, data_dir: Path, today_str: str) -> List[Dict[str, Any]]:
    """Try to load arb_levels_<TICKER>.json from today's output dir."""
    arb_path = data_dir / today_str / f"arb_levels_{ticker}.json"
    if not arb_path.exists():
        return []
    try:
        with open(arb_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        verified = data.get("verified_levels", [])
        candidates = data.get("candidates", [])
        return verified + candidates
    except Exception as exc:
        log.warning("Could not load arb levels for %s: %s", ticker, exc)
        return []
