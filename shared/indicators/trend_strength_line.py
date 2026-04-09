"""
Trend Strength Line (TSL) Gap-Aware v4.5 — Python
---------------------------------------------------
Exact translation of the ThinkScript "Trend Strength Line - GAP-AWARE v4.5".

Uses the SAME three raw methods as TrendStrengthCandles v2.1 but applies a
DIFFERENT normalization:

  normLen=100 (not 200)
  zClamp=2.5  — z-score is clamped to [-2.5, +2.5] before scaling
  zToUnitRange=2.0 — divisor to map clamped z into [-1, +1]

  normX = clip( clip(z, -2.5, 2.5) / 2.0, -1.0, 1.0 )

Then:
  trendScore = mean(normPc, normEma, normMa) * 100   # range [-100, +100]

SLOPE STATE:
  rawSlope  = (trendScore - trendScore.shift(5)) / 5
  slope     = EMA(rawSlope, span=3)        # EWM adjust=False
  isRising  = slope > 0.25
  isDropping= slope < -0.25
  else NEUTRAL

IMPORTANT: This indicator's normalization is INDEPENDENT of TrendStrengthCandles.
  Do NOT share rolling windows or computed z-scores between the two indicators.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TrendStrengthLineParams:
    # Shared raw-method inputs (same defaults as candle indicator)
    pcLookback: int = 20
    emaLen: int = 21
    emaSlopeSmooth: int = 5
    ma1Type: str = "EMA"   # "EMA" or "SMA"
    ma1Len: int = 20
    ma2Type: str = "SMA"   # "SMA" or "EMA"
    ma2Len: int = 50
    atrLen: int = 14

    # TSL-specific normalization parameters — DIFFERENT from candle indicator
    normLen: int = 100
    zClamp: float = 2.5
    zToUnitRange: float = 2.0

    # Slope detection parameters
    slopeLen: int = 5
    slopeSmoothLen: int = 3
    slopeNeutralThreshold: float = 0.25

    # Signal line
    signalLen: int = 9


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


def _clamp_zscore_normalize(
    x: pd.Series,
    n: int,
    z_clamp: float,
    z_to_unit: float,
) -> pd.Series:
    """
    TSL v4.5 clamped z-score normalization:

        z       = (x - rolling_mean(x, n)) / rolling_std(x, n)
        clamped = clip(z, -z_clamp, +z_clamp)
        normed  = clip(clamped / z_to_unit, -1.0, +1.0)

    ThinkScript equivalent:
        Max(-1, Min(1, Max(-zClamp, Min(zClamp, (raw - avg) / std)) / zToUnitRange))
    """
    mu = _sma(x, n)
    sd = _rolling_std_pop(x, n).replace(0, np.nan)
    z       = (x - mu) / sd
    clamped = z.clip(-z_clamp, z_clamp)
    normed  = (clamped / z_to_unit).clip(-1.0, 1.0)
    return normed


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class TrendStrengthLine:
    """
    Trend Strength Line (TSL) Gap-Aware v4.5 indicator.

    Usage::

        from shared.indicators.trend_strength_line import TrendStrengthLine
        indicator = TrendStrengthLine()
        result = indicator.compute(df)

    Key signal column is ``is_rising`` (bool):
        is_rising = slope > 0.25

    Combined with TrendStrengthCandles for the primary entry signal:
        signal = cyan_signal & is_rising   # same bar
        entry  = next_bar_open             # zero lookahead
    """

    def __init__(self, params: TrendStrengthLineParams | None = None):
        self.params = params or TrendStrengthLineParams()

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute TSL Gap-Aware v4.5 signals.

        Parameters
        ----------
        df : pd.DataFrame
            OHLCV data with columns: Open, High, Low, Close (Volume optional).
            Column names are case-insensitive.

        Returns
        -------
        pd.DataFrame
            Original df with the following columns appended:

            trend_score  : float [-100, +100] — clamped normalized consensus
            slope        : float — smoothed 5-bar slope of trend_score
            is_rising    : bool, slope > 0.25   ← TSL RISING SIGNAL
            is_dropping  : bool, slope < -0.25
            is_neutral   : bool, not rising and not dropping
            signal_line  : float — EMA-9 of trend_score
            momentum     : float — trend_score - trend_score.shift(1)
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
        emaSeries     = _ema(close, p.emaLen)
        rawEmaSlope   = (emaSeries - emaSeries.shift(1)) / safe_atr
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
        # TSL v4.5 clamped z-score normalization                             #
        # normLen=100, zClamp=2.5, zToUnitRange=2.0                         #
        # normX = clip( clip(z, -2.5, 2.5) / 2.0, -1.0, +1.0 )            #
        # INDEPENDENT from the candle indicator's 200-bar z-score           #
        # ------------------------------------------------------------------ #
        normPc  = _clamp_zscore_normalize(rawPc,         p.normLen, p.zClamp, p.zToUnitRange)
        normEma = _clamp_zscore_normalize(rawEmaSlopeSm, p.normLen, p.zClamp, p.zToUnitRange)
        normMa  = _clamp_zscore_normalize(rawMaDist,     p.normLen, p.zClamp, p.zToUnitRange)

        # ------------------------------------------------------------------ #
        # trendScore = mean(normPc, normEma, normMa) * 100                  #
        # ------------------------------------------------------------------ #
        trend_score = ((normPc + normEma + normMa) / 3.0) * 100.0

        # ------------------------------------------------------------------ #
        # Slope state                                                          #
        # rawSlope = (trendScore - trendScore[slopeLen]) / slopeLen          #
        # slope    = EMA(rawSlope, span=slopeSmoothLen)                      #
        # ------------------------------------------------------------------ #
        raw_slope = (trend_score - trend_score.shift(p.slopeLen)) / p.slopeLen
        slope     = raw_slope.ewm(span=p.slopeSmoothLen, adjust=False).mean()

        is_rising   = slope > p.slopeNeutralThreshold
        is_dropping = slope < -p.slopeNeutralThreshold
        is_neutral  = ~is_rising & ~is_dropping

        # ------------------------------------------------------------------ #
        # Signal line (EMA-9 of trend_score) and momentum                    #
        # ------------------------------------------------------------------ #
        signal_line = trend_score.ewm(span=p.signalLen, adjust=False).mean()
        momentum    = trend_score - trend_score.shift(1)

        # ------------------------------------------------------------------ #
        # Assemble output                                                      #
        # ------------------------------------------------------------------ #
        out = df.copy()
        out["trend_score"]  = trend_score.values
        out["slope"]        = slope.values
        out["is_rising"]    = is_rising.values
        out["is_dropping"]  = is_dropping.values
        out["is_neutral"]   = is_neutral.values
        out["signal_line"]  = signal_line.values
        out["momentum"]     = momentum.values

        return out
