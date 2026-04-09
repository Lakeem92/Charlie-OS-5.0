"""
Trend Strength Candles v2.1 — Python
--------------------------------------
Exact translation of the ThinkScript "Trend Strength Candles v2.1" indicator.

THREE-METHOD CONSENSUS:
  Method 1: Price Change vs ATR (pcLookback=20)
  Method 2: EMA Slope vs ATR, smoothed (emaLen=21, emaSlopeSmooth=5)
  Method 3: MA Distance (EMA20 - SMA50) vs ATR

Z-SCORE WINDOW: 200 bars (population std, ddof=0 — matches ThinkScript StDev)

SIGNAL TIERS (cs = consensus score, clamped to [-100, +100]):
  cs >= 70            → STRONG BULL  ← CYAN CANDLE (primary signal)
  40 <= cs < 70       → BULL
  15 <= cs < 40       → WEAK BULL
  -15 < cs < 15       → NEUTRAL
  -40 < cs <= -15     → WEAK BEAR
  -70 < cs <= -40     → BEAR
  cs <= -70           → STRONG BEAR

CYAN CANDLE = is_strong_bull AND NOT is_nr7
  (NR7 overrides the candle to WHITE in ThinkScript; excluded from signals)

IMPORTANT: Do NOT share normalization state with TrendStrengthLine.
  The candle indicator uses zscoreLookback=200 without clamping.
  The TSL indicator uses normLen=100 with zClamp=2.5 and zToUnitRange=2.0.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TrendStrengthCandlesParams:
    pcLookback: int = 20
    emaLen: int = 21
    emaSlopeSmooth: int = 5
    ma1Type: str = "EMA"   # "EMA" or "SMA"
    ma1Len: int = 20
    ma2Type: str = "SMA"   # "SMA" or "EMA"
    ma2Len: int = 50
    atrLen: int = 14
    zscoreLookback: int = 200


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sma(x: pd.Series, n: int) -> pd.Series:
    return x.rolling(n, min_periods=n).mean()


def _ema(x: pd.Series, n: int) -> pd.Series:
    """Standard EMA using recursive (adjust=False) EWM with span."""
    return x.ewm(span=n, adjust=False, min_periods=n).mean()


def _rolling_std_pop(x: pd.Series, n: int) -> pd.Series:
    """Population std (ddof=0) — matches ThinkScript StDev behaviour."""
    return x.rolling(n, min_periods=n).std(ddof=0)


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def _zscore_200(x: pd.Series, n: int) -> pd.Series:
    """Rolling z-score over window n (population std, no clamping)."""
    mu = _sma(x, n)
    sd = _rolling_std_pop(x, n)
    return (x - mu) / sd.replace(0, np.nan)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class TrendStrengthCandles:
    """
    Trend Strength Candles v2.1 indicator.

    Usage::

        from shared.indicators.trend_strength_candles import TrendStrengthCandles
        indicator = TrendStrengthCandles()
        result = indicator.compute(df)  # df must have Open/High/Low/Close columns

    The primary signal column is ``cyan_signal`` (bool):
        cyan_signal = (cs >= 70) AND NOT is_nr7
    """

    def __init__(self, params: TrendStrengthCandlesParams | None = None):
        self.params = params or TrendStrengthCandlesParams()

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute Trend Strength Candles v2.1 signals.

        Parameters
        ----------
        df : pd.DataFrame
            OHLCV data with columns: Open, High, Low, Close (Volume optional).
            Column names are case-insensitive.

        Returns
        -------
        pd.DataFrame
            Original df with the following columns appended:

            cs              : float, consensus score clamped [-100, +100]
            agreement       : float, 0.33..1.0 — fraction of methods agreeing
            is_strong_bull  : bool, cs >= 70  (CYAN CANDLE region)
            is_bull         : bool, cs >= 40
            is_weak_bull    : bool, cs >= 15
            is_neutral      : bool, -15 < cs < 15
            is_weak_bear    : bool, cs <= -15
            is_bear         : bool, cs <= -40
            is_strong_bear  : bool, cs <= -70
            is_nr7          : bool, bar range < lowest of last 6 bar ranges
            cyan_signal     : bool, is_strong_bull AND NOT is_nr7  ← MAIN SIGNAL
        """
        p = self.params
        d = df.copy()
        d.columns = [c.lower() for c in d.columns]

        required = {"high", "low", "close"}
        missing = required - set(d.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        high  = d["high"].astype(float)
        low   = d["low"].astype(float)
        close = d["close"].astype(float)

        # ------------------------------------------------------------------ #
        # ATR — EMA of True Range                                             #
        # ------------------------------------------------------------------ #
        tr  = _true_range(high, low, close)
        atr = _ema(tr, p.atrLen)
        safe_atr = atr.replace(0, np.nan)

        # ------------------------------------------------------------------ #
        # Method 1: Price Change vs ATR                                       #
        # ------------------------------------------------------------------ #
        rawPc = (close - close.shift(p.pcLookback)) / safe_atr

        # ------------------------------------------------------------------ #
        # Method 2: EMA Slope vs ATR (smoothed with SMA)                     #
        # ------------------------------------------------------------------ #
        emaSeries    = _ema(close, p.emaLen)
        rawEmaSlope  = (emaSeries - emaSeries.shift(1)) / safe_atr
        rawEmaSlopeSm = _sma(rawEmaSlope, p.emaSlopeSmooth)

        # ------------------------------------------------------------------ #
        # Method 3: MA Distance vs ATR                                        #
        # ------------------------------------------------------------------ #
        ma1 = (_ema(close, p.ma1Len)
               if p.ma1Type.upper() == "EMA"
               else _sma(close, p.ma1Len))
        ma2 = (_sma(close, p.ma2Len)
               if p.ma2Type.upper() == "SMA"
               else _ema(close, p.ma2Len))
        rawMaDist = (ma1 - ma2) / safe_atr

        # ------------------------------------------------------------------ #
        # Z-score normalization — 200-bar rolling window, no clamping        #
        # (Matches ThinkScript StDev, population std, ddof=0)                #
        # ------------------------------------------------------------------ #
        pcZ  = _zscore_200(rawPc, p.zscoreLookback)
        emaZ = _zscore_200(rawEmaSlopeSm, p.zscoreLookback)
        maZ  = _zscore_200(rawMaDist, p.zscoreLookback)

        # ------------------------------------------------------------------ #
        # Consensus score — average of three z-scores, scaled +clamped       #
        # ThinkScript: cs = clip(mean(pcZ, emaZ, maZ) * 100, -100, +100)    #
        # ------------------------------------------------------------------ #
        consensusScore = (pcZ + emaZ + maZ) / 3.0
        cs = (consensusScore * 100.0).clip(-100.0, 100.0)

        # ------------------------------------------------------------------ #
        # Agreement factor                                                     #
        # ThinkScript: agreement = abs(pcSign + emaSign + maSign) / 3        #
        # ------------------------------------------------------------------ #
        pcSign  = np.where(pcZ > 0, 1, np.where(pcZ < 0, -1, 0))
        emaSign = np.where(emaZ > 0, 1, np.where(emaZ < 0, -1, 0))
        maSign  = np.where(maZ > 0, 1, np.where(maZ < 0, -1, 0))
        agreement = pd.Series(
            np.abs(pcSign + emaSign + maSign) / 3.0,
            index=d.index,
            dtype=float,
        )

        # ------------------------------------------------------------------ #
        # NR7: bar range smaller than ALL of the previous 6 ranges           #
        # ThinkScript: barRange < Lowest(barRange[1], 6)                     #
        # [1] means shift by 1, then Lowest over 6 = rolling min of 6 bars  #
        # ------------------------------------------------------------------ #
        bar_range  = high - low
        lowest_prev6 = bar_range.shift(1).rolling(6, min_periods=6).min()
        is_nr7      = bar_range < lowest_prev6

        # ------------------------------------------------------------------ #
        # Signal tiers (boolean columns)                                      #
        # ------------------------------------------------------------------ #
        is_strong_bull = cs >= 70.0
        is_bull        = cs >= 40.0
        is_weak_bull   = cs >= 15.0
        is_neutral     = (cs > -15.0) & (cs < 15.0)
        is_weak_bear   = cs <= -15.0
        is_bear        = cs <= -40.0
        is_strong_bear = cs <= -70.0

        # ------------------------------------------------------------------ #
        # PRIMARY SIGNAL: CYAN CANDLE                                         #
        # cs >= 70 AND NOT is_nr7                                             #
        # (NR7 disqualifies the bar — shown as WHITE in ThinkScript)         #
        # ------------------------------------------------------------------ #
        cyan_signal = is_strong_bull & ~is_nr7.fillna(False)

        # ------------------------------------------------------------------ #
        # Assemble output                                                      #
        # ------------------------------------------------------------------ #
        out = df.copy()
        out["cs"]             = cs.values
        out["agreement"]      = agreement.values
        out["is_strong_bull"] = is_strong_bull.values
        out["is_bull"]        = is_bull.values
        out["is_weak_bull"]   = is_weak_bull.values
        out["is_neutral"]     = is_neutral.values
        out["is_weak_bear"]   = is_weak_bear.values
        out["is_bear"]        = is_bear.values
        out["is_strong_bear"] = is_strong_bear.values
        out["is_nr7"]         = is_nr7.values
        out["cyan_signal"]    = cyan_signal.values

        return out
