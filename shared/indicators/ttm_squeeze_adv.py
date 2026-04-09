"""
Advanced TTM Squeeze (Tight + Soft) (Python)
-------------------------------------------
Translation of the user's ThinkScript:
- Keltner Channels use SMA(price,length) +/- nK * ATR(length, SIMPLE)
- Bollinger Bands use SMA(price,length) +/- nBB * StdDev(price,length)
- Tight squeeze: BB(2.0) inside KC
- Soft squeeze:  BB(1.7) inside KC
- Momentum: 4*price - SMA(SMA(SMA(SMA(price,length),length),length),length)

Outputs (added columns):
- squeeze_tight_on (bool)
- squeeze_soft_on (bool)
- squeeze_any_on (bool)
- squeeze_release (bool): any_on[-1] == True and any_on == False
- momentum (float)
- momentum_sign (+1/0/-1)
- momentum_accel (bool): momentum > momentum[1]
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TTMSqueezeParams:
    length: int = 20
    nK: float = 1.5
    nBB_tight: float = 2.0
    nBB_soft: float = 1.7


def _sma(x: pd.Series, n: int) -> pd.Series:
    return x.rolling(n, min_periods=n).mean()


def _rolling_std(x: pd.Series, n: int) -> pd.Series:
    # ThinkScript StDev closer to population std; use ddof=0 as canonical
    return x.rolling(n, min_periods=n).std(ddof=0)


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def _atr_simple(high: pd.Series, low: pd.Series, close: pd.Series, n: int) -> pd.Series:
    tr = _true_range(high, low, close)
    return _sma(tr, n)


def compute_ttm_squeeze_adv(
    df: pd.DataFrame,
    params: TTMSqueezeParams = TTMSqueezeParams(),
    price_col: str = "close",
) -> pd.DataFrame:
    """
    Compute Advanced TTM Squeeze (tight + soft) signals from OHLCV.

    Required columns: high, low, close (open/volume optional)
    Returns a copy with added columns.
    """
    d = df.copy()
    d.columns = [c.lower() for c in d.columns]

    required = {"high", "low", price_col.lower()}
    missing = required - set(d.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    high = d["high"].astype(float)
    low = d["low"].astype(float)
    price = d[price_col.lower()].astype(float)

    length = int(params.length)

    # Base calculations
    avg = _sma(price, length)
    atr = _atr_simple(high, low, price, length)  # SIMPLE ATR per ThinkScript
    upper_kc = avg + params.nK * atr
    lower_kc = avg - params.nK * atr

    sd = _rolling_std(price, length)

    upper_bb_tight = avg + params.nBB_tight * sd
    lower_bb_tight = avg - params.nBB_tight * sd

    upper_bb_soft = avg + params.nBB_soft * sd
    lower_bb_soft = avg - params.nBB_soft * sd

    # Squeeze conditions (BB inside KC)
    squeeze_tight_on = (upper_bb_tight < upper_kc) & (lower_bb_tight > lower_kc)
    squeeze_soft_on = (upper_bb_soft < upper_kc) & (lower_bb_soft > lower_kc)

    # Tight dominates soft
    squeeze_soft_on = squeeze_soft_on & (~squeeze_tight_on)

    squeeze_any_on = squeeze_tight_on | squeeze_soft_on
    squeeze_release = squeeze_any_on.shift(1).fillna(False) & (~squeeze_any_on.fillna(False))

    # Momentum component:
    # Momentum = 4*price - SMA(SMA(SMA(SMA(price,length),length),length),length)
    value_a = 4.0 * price
    sm1 = _sma(price, length)
    sm2 = _sma(sm1, length)
    sm3 = _sma(sm2, length)
    sm4 = _sma(sm3, length)
    momentum = value_a - sm4

    momentum_sign = np.where(momentum > 0, 1, np.where(momentum < 0, -1, 0))
    momentum_accel = momentum > momentum.shift(1)

    out = df.copy()
    out["kc_avg"] = avg.values
    out["kc_atr"] = atr.values
    out["upper_kc"] = upper_kc.values
    out["lower_kc"] = lower_kc.values
    out["bb_std"] = sd.values
    out["upper_bb_tight"] = upper_bb_tight.values
    out["lower_bb_tight"] = lower_bb_tight.values
    out["upper_bb_soft"] = upper_bb_soft.values
    out["lower_bb_soft"] = lower_bb_soft.values
    out["squeeze_tight_on"] = squeeze_tight_on.values
    out["squeeze_soft_on"] = squeeze_soft_on.values
    out["squeeze_any_on"] = squeeze_any_on.values
    out["squeeze_release"] = squeeze_release.values
    out["momentum"] = momentum.values
    out["momentum_sign"] = momentum_sign
    out["momentum_accel"] = momentum_accel.values
    return out
