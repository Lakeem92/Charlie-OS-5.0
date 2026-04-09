"""
Trend Strength Candles v2 + NR7 + Momentum Extremes (Cap Finder) - Python
--------------------------------------------------------------------------
Translation of the user's ThinkScript into research-ready outputs.
No plotting, no colors—only numeric/boolean signals.

Core Outputs (v2+NR7):
- atr (EMA of True Range, atrLen)
- rawPc, raw_ema_slope_sm, rawMaDist
- pcZscore, emaZscore, maZscore (rolling z-score, zscoreLookback)
- consensusScore (avg of z-scores)
- agreement (0..1): how many signals agree on direction
- consensusScaled, consensusClamped (-100..100)
- is_nr7 (NR7 compression flag)
- trend_state (categorical bucket matching labels)

Cap Finder Outputs (Momentum Extremes):
- cap_rsi (Wilder's RSI)
- cap_ma (SMA or EMA)
- cap_vol_avg (SMA of volume)
- cap_below, cap_above, cap_vol_spike (boolean flags)
- oversoldExtreme, overboughtExtreme (boolean flags)
- momentum_extreme_state ("OVERSOLD", "OVERBOUGHT", "NONE")
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TrendStrengthParams:
    # Core Trend Strength parameters
    pcLookback: int = 20
    emaLen: int = 21
    emaSlopeSmooth: int = 5
    ma1Type: str = "EMA"   # "EMA" or "SMA"
    ma1Len: int = 20
    ma2Type: str = "SMA"   # "SMA" or "EMA"
    ma2Len: int = 50
    atrLen: int = 14
    zscoreLookback: int = 200
    
    # Cap Finder (Momentum Extremes) parameters
    enableMomentumExtremeOverride: bool = True
    cap_rsiLength: int = 14
    cap_rsiOversold: int = 30
    cap_rsiOverbought: int = 70
    cap_maType: str = "SMA"  # "SMA" or "EMA"
    cap_maLength: int = 50
    cap_percentageThreshold: float = 5.0
    cap_volumeMultiplier: float = 1.2
    cap_volumeLength: int = 20


def _sma(x: pd.Series, n: int) -> pd.Series:
    return x.rolling(n, min_periods=n).mean()


def _ema(x: pd.Series, n: int) -> pd.Series:
    # pandas EWM uses adjust=False to behave like standard EMA recursion
    return x.ewm(span=n, adjust=False, min_periods=n).mean()


def _rolling_std(x: pd.Series, n: int) -> pd.Series:
    # ThinkScript StDev is closer to population std; use ddof=0 as canonical
    return x.rolling(n, min_periods=n).std(ddof=0)


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def _zscore(x: pd.Series, n: int) -> pd.Series:
    mu = _sma(x, n)
    sd = _rolling_std(x, n)
    return (x - mu) / sd.replace(0, np.nan)


def _trend_state(consensus_clamped: pd.Series) -> pd.Series:
    # Buckets mirror the ThinkScript labels
    c = consensus_clamped
    out = pd.Series(index=c.index, dtype="object")
    out.loc[c >= 70] = "MAX_CONVICTION_BULL"
    out.loc[(c >= 50) & (c < 70)] = "STRONG_BULL"
    out.loc[(c >= 30) & (c < 50)] = "MILD_BULL"
    out.loc[(c >= 10) & (c < 30)] = "WEAK_BULL"
    out.loc[(c > -10) & (c <= 10)] = "NEUTRAL"
    out.loc[(c > -30) & (c <= -10)] = "WEAK_BEAR"
    out.loc[(c > -50) & (c <= -30)] = "MILD_BEAR"
    out.loc[(c > -70) & (c <= -50)] = "STRONG_BEAR"
    out.loc[c <= -70] = "MAX_CONVICTION_BEAR"
    return out


def _wilder_rsi(close: pd.Series, n: int) -> pd.Series:
    """
    Wilder's RSI using RMA (Wilder's EMA) smoothing.
    
    ThinkScript RSI() uses Wilder's smoothing (alpha = 1/n).
    This is equivalent to EWM with alpha=1/n (not span).
    """
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    # Wilder's smoothing: alpha = 1/n
    avg_gain = gain.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_trend_strength_nr7(
    df: pd.DataFrame,
    params: TrendStrengthParams = TrendStrengthParams(),
) -> pd.DataFrame:
    """
    Compute Trend Strength + NR7 signals from OHLCV.

    Required columns: open, high, low, close (volume optional).
    Returns a copy of df with added columns.
    """
    required = {"high", "low", "close"}
    missing = required - set(df.columns.str.lower())
    # If columns aren't lowercase, normalize mapping
    # We'll create a lowercase view for safety.
    d = df.copy()
    d.columns = [c.lower() for c in d.columns]
    missing = required - set(d.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    high = d["high"].astype(float)
    low = d["low"].astype(float)
    close = d["close"].astype(float)

    # ATR (EMA of TR), matching ThinkScript section 1
    tr = _true_range(high, low, close)
    atr = _ema(tr, params.atrLen)

    # Method 1: ATR-normalized price change over pcLookback
    pc_prev = close.shift(params.pcLookback)
    rawPc = (close - pc_prev) / atr.replace(0, np.nan)

    # Method 2: ATR-normalized EMA slope (smoothed)
    emaSeries = _ema(close, params.emaLen)
    raw_ema_slope = (emaSeries - emaSeries.shift(1)) / atr.replace(0, np.nan)
    raw_ema_slope_sm = _sma(raw_ema_slope, params.emaSlopeSmooth)

    # Method 3: MA distance (MA1 - MA2) normalized by ATR
    ma1 = _ema(close, params.ma1Len) if params.ma1Type.upper() == "EMA" else _sma(close, params.ma1Len)
    ma2 = _ema(close, params.ma2Len) if params.ma2Type.upper() == "EMA" else _sma(close, params.ma2Len)
    rawMaDist = (ma1 - ma2) / atr.replace(0, np.nan)

    # Z-score normalization (rolling)
    pcZ = _zscore(rawPc, params.zscoreLookback)
    emaZ = _zscore(raw_ema_slope_sm, params.zscoreLookback)
    maZ = _zscore(rawMaDist, params.zscoreLookback)

    # Consensus score
    consensusScore = (pcZ + emaZ + maZ) / 3.0

    # Agreement factor based on sign alignment
    pcSign = np.where(pcZ > 0, 1, np.where(pcZ < 0, -1, 0))
    emaSign = np.where(emaZ > 0, 1, np.where(emaZ < 0, -1, 0))
    maSign = np.where(maZ > 0, 1, np.where(maZ < 0, -1, 0))
    signSum = np.abs(pcSign + emaSign + maSign)
    agreement = signSum / 3.0  # 0, 1/3, 2/3, 1
    agreement = pd.Series(agreement, index=d.index).astype(float)

    # Scale + clamp consensus
    consensusScaled = consensusScore * 100.0
    consensusClamped = consensusScaled.clip(lower=-100, upper=100)

    # NR7 logic
    rng = (high - low)
    lowestPastRange = rng.shift(1).rolling(6, min_periods=6).min()
    is_nr7 = rng < lowestPastRange

    # trend_state buckets
    trend_state = _trend_state(consensusClamped)

    # =========================================================
    # CAP FINDER (MOMENTUM EXTREMES) LOGIC
    # =========================================================
    if "volume" not in d.columns:
        # If no volume data, set all Cap Finder outputs to NaN/False
        cap_rsi = pd.Series(np.nan, index=d.index)
        cap_ma = pd.Series(np.nan, index=d.index)
        cap_vol_avg = pd.Series(np.nan, index=d.index)
        cap_below = pd.Series(False, index=d.index)
        cap_above = pd.Series(False, index=d.index)
        cap_vol_spike = pd.Series(False, index=d.index)
        oversoldExtreme = pd.Series(False, index=d.index)
        overboughtExtreme = pd.Series(False, index=d.index)
        momentum_extreme_state = pd.Series("NONE", index=d.index)
    else:
        volume = d["volume"].astype(float)
        
        # Wilder's RSI
        cap_rsi = _wilder_rsi(close, params.cap_rsiLength)
        
        # Cap MA (SMA or EMA based on cap_maType)
        if params.cap_maType.upper() == "EMA":
            cap_ma = _ema(close, params.cap_maLength)
        else:
            cap_ma = _sma(close, params.cap_maLength)
        
        # Volume average (SMA)
        cap_vol_avg = _sma(volume, params.cap_volumeLength)
        
        # Boolean conditions
        threshold_factor = 1.0 - (params.cap_percentageThreshold / 100.0)
        cap_below = close < (cap_ma * threshold_factor)
        
        threshold_factor_above = 1.0 + (params.cap_percentageThreshold / 100.0)
        cap_above = close > (cap_ma * threshold_factor_above)
        
        cap_vol_spike = volume >= (cap_vol_avg * params.cap_volumeMultiplier)
        
        # Momentum extremes
        oversoldExtreme = (cap_rsi <= params.cap_rsiOversold) & cap_below & cap_vol_spike
        overboughtExtreme = (cap_rsi >= params.cap_rsiOverbought) & cap_above & cap_vol_spike
        
        # Momentum extreme state
        momentum_extreme_state = pd.Series("NONE", index=d.index, dtype="object")
        momentum_extreme_state.loc[oversoldExtreme] = "OVERSOLD"
        momentum_extreme_state.loc[overboughtExtreme] = "OVERBOUGHT"

    # Attach outputs (preserve all original outputs + add new Cap Finder outputs)
    out = df.copy()
    
    # Original outputs (13 columns)
    out["atr"] = atr.values
    out["rawPc"] = rawPc.values
    out["raw_ema_slope_sm"] = raw_ema_slope_sm.values
    out["rawMaDist"] = rawMaDist.values
    out["pcZscore"] = pcZ.values
    out["emaZscore"] = emaZ.values
    out["maZscore"] = maZ.values
    out["consensusScore"] = consensusScore.values
    out["agreement"] = agreement.values
    out["consensusScaled"] = consensusScaled.values
    out["consensusClamped"] = consensusClamped.values
    out["is_nr7"] = is_nr7.values
    out["trend_state"] = trend_state.values
    
    # Cap Finder outputs (9 new columns)
    out["cap_rsi"] = cap_rsi.values
    out["cap_ma"] = cap_ma.values
    out["cap_vol_avg"] = cap_vol_avg.values
    out["cap_below"] = cap_below.values
    out["cap_above"] = cap_above.values
    out["cap_vol_spike"] = cap_vol_spike.values
    out["oversoldExtreme"] = oversoldExtreme.values
    out["overboughtExtreme"] = overboughtExtreme.values
    out["momentum_extreme_state"] = momentum_extreme_state.values
    
    return out
