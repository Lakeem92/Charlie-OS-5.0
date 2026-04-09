"""
shared/indicators — Public API
------------------------------
Exports all indicator classes and legacy helpers.

New indicators (v2.1 / v4.5):
  TrendStrengthCandles  — Trend Strength Candles v2.1 (cyan signal, cs >= 70)
  TrendStrengthLine     — Trend Strength Line Gap-Aware v4.5 (is_rising)

Legacy (kept for backward compatibility):
  TrendStrengthNR7      — function-based, with Cap Finder; used by older studies
  compute_trend_strength_nr7, TrendStrengthParams
"""

# ── New class-based indicators ────────────────────────────────────────────
from shared.indicators.trend_strength_candles import (
    TrendStrengthCandles,
    TrendStrengthCandlesParams,
)
from shared.indicators.trend_strength_line import (
    TrendStrengthLine,
    TrendStrengthLineParams,
)

# ── Legacy function-based indicator (unchanged) ───────────────────────────
from shared.indicators.trend_strength_nr7 import (
    compute_trend_strength_nr7,
    TrendStrengthParams,
)

# ── TTM Squeeze ───────────────────────────────────────────────────────────
from shared.indicators.ttm_squeeze_adv import compute_ttm_squeeze_adv  # noqa: F401

__all__ = [
    # New
    "TrendStrengthCandles",
    "TrendStrengthCandlesParams",
    "TrendStrengthLine",
    "TrendStrengthLineParams",
    # Legacy
    "compute_trend_strength_nr7",
    "TrendStrengthParams",
]
