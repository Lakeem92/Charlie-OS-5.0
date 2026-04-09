"""
Indicator Validation Test
--------------------------
Validates TrendStrengthCandles v2.1 and TrendStrengthLine v4.5 against
90 days of NVDA 5-minute intraday data from Alpaca via DataRouter.

Checks:
  1. Both indicators compute without error on real OHLCV data
  2. No NaN values in key output columns after warmup (260 bars — SMA50 + 200-bar z-score)
  3. Combined signal count (cyan_signal AND is_rising)
  4. Print summary: total bars, signal count, frequency %, first 5 timestamps

Run from workspace root:
    python shared/indicators/test_indicator_validation.py
"""

import sys
from pathlib import Path
from datetime import date, timedelta

# ── Make sure workspace root and shared/ are on sys.path ─────────────────
# REPO_ROOT  = C:\QuantLab\Data_Lab
# shared/    must also be on path so data_router.py's lazy import
#            "from config.api_clients import ..." can resolve config/
REPO_ROOT   = Path(__file__).resolve().parents[2]
SHARED_ROOT = REPO_ROOT / "shared"
sys.path.insert(0, str(SHARED_ROOT))
sys.path.insert(0, str(REPO_ROOT))

from shared.data_router import DataRouter
from shared.indicators.trend_strength_candles import TrendStrengthCandles
from shared.indicators.trend_strength_line import TrendStrengthLine

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TICKER = "NVDA"
END_DATE   = date.today().strftime("%Y-%m-%d")
START_DATE = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
TIMEFRAME  = "5min"
# True warmup for TrendStrengthCandles:
#   Method 3 (MA distance) needs SMA50 (50 bars) + 200-bar z-score = 250 bars.
#   Use 260 to give a small margin.
WARMUP     = 260

# Key columns to verify NaN-free after warmup
CANDLE_KEY_COLS = ["cs", "agreement", "is_strong_bull", "is_nr7", "cyan_signal"]
TSL_KEY_COLS    = ["trend_score", "slope", "is_rising", "is_dropping", "is_neutral"]


def validate():
    print("=" * 64)
    print("QuantLab Indicator Validation — TrendStrengthCandles v2.1")
    print("                             + TrendStrengthLine v4.5")
    print("=" * 64)
    print(f"Ticker     : {TICKER}")
    print(f"Date range : {START_DATE} → {END_DATE}")
    print(f"Timeframe  : {TIMEFRAME}")
    print()

    # ---------------------------------------------------------------------- #
    # 1. Fetch data                                                            #
    # ---------------------------------------------------------------------- #
    print("Fetching data via DataRouter (Alpaca primary)…")
    df = DataRouter.get_price_data(
        TICKER,
        start_date=START_DATE,
        end_date=END_DATE,
        timeframe=TIMEFRAME,
        study_type="indicator",
    )
    print(f"  Rows fetched : {len(df):,}")
    print(f"  Columns      : {list(df.columns)}")
    print()

    if df.empty:
        print("ERROR: No data returned. Check API keys and market hours.")
        sys.exit(1)

    # ---------------------------------------------------------------------- #
    # 2. Run TrendStrengthCandles v2.1                                        #
    # ---------------------------------------------------------------------- #
    print("Running TrendStrengthCandles v2.1…")
    candle_indicator = TrendStrengthCandles()
    df_candles = candle_indicator.compute(df)

    # Verify key columns exist
    for col in CANDLE_KEY_COLS:
        if col not in df_candles.columns:
            print(f"  ERROR: Missing column '{col}' in candle output!")
            sys.exit(1)

    # NaN check after warmup
    post_warmup = df_candles.iloc[WARMUP:]
    candle_nans = post_warmup[CANDLE_KEY_COLS].isna().sum()
    if candle_nans.any():
        print("  WARNING: NaN values found in candle columns post-warmup:")
        print(candle_nans[candle_nans > 0].to_string())
    else:
        print(f"  ✓ No NaN values in key candle columns after warmup ({WARMUP} bars)")

    cyan_count  = int(df_candles["cyan_signal"].sum())
    strong_bull = int(df_candles["is_strong_bull"].sum())
    nr7_count   = int(df_candles["is_nr7"].sum())

    print(f"  is_strong_bull (cs >= 70) : {strong_bull:,} bars")
    print(f"  is_nr7                    : {nr7_count:,} bars")
    print(f"  cyan_signal               : {cyan_count:,} bars  (strong_bull AND NOT nr7)")
    print()

    # ---------------------------------------------------------------------- #
    # 3. Run TrendStrengthLine v4.5                                           #
    # ---------------------------------------------------------------------- #
    print("Running TrendStrengthLine v4.5…")
    tsl_indicator = TrendStrengthLine()
    df_tsl = tsl_indicator.compute(df)

    # Verify key columns exist
    for col in TSL_KEY_COLS:
        if col not in df_tsl.columns:
            print(f"  ERROR: Missing column '{col}' in TSL output!")
            sys.exit(1)

    # NaN check after warmup
    post_warmup_tsl = df_tsl.iloc[WARMUP:]
    tsl_nans = post_warmup_tsl[TSL_KEY_COLS].isna().sum()
    if tsl_nans.any():
        print("  WARNING: NaN values found in TSL columns post-warmup:")
        print(tsl_nans[tsl_nans > 0].to_string())
    else:
        print(f"  ✓ No NaN values in key TSL columns after warmup ({WARMUP} bars)")

    rising_count = int(df_tsl["is_rising"].sum())
    print(f"  is_rising (slope > 0.25)  : {rising_count:,} bars")
    print()

    # ---------------------------------------------------------------------- #
    # 4. Combined signal: cyan_signal AND is_rising (same bar)               #
    # ---------------------------------------------------------------------- #
    print("Computing combined signal (cyan_signal AND is_rising)…")

    # Align on index — both DataFrames share the same source index
    combined = df_candles["cyan_signal"] & df_tsl["is_rising"]
    signal_count = int(combined.sum())
    total_bars   = len(combined)
    frequency_pct = (signal_count / total_bars * 100) if total_bars > 0 else 0.0

    print(f"  Total bars    : {total_bars:,}")
    print(f"  Signal bars   : {signal_count:,}")
    print(f"  Frequency     : {frequency_pct:.3f}%")
    print()

    # First 5 signal timestamps
    signal_rows = combined[combined].index
    if len(signal_rows) > 0:
        print("  First 5 signal timestamps:")
        for ts in signal_rows[:5]:
            cs_val    = df_candles.loc[ts, "cs"]
            slope_val = df_tsl.loc[ts, "slope"]
            print(f"    {ts}  cs={cs_val:+.1f}  slope={slope_val:+.4f}")
    else:
        print("  No combined signals found in this date range.")
    print()

    # ---------------------------------------------------------------------- #
    # 5. Summary                                                              #
    # ---------------------------------------------------------------------- #
    print("=" * 64)
    print("VALIDATION SUMMARY")
    print("=" * 64)
    print(f"  Cyan candle formula  : (cs >= 70) AND NOT is_nr7")
    print(f"    cs = clip(mean(pcZ_200, emaZ_200, maZ_200) * 100, -100, 100)")
    print(f"    pcZ/emaZ/maZ use 200-bar rolling z-score (ddof=0, no clamp)")
    print()
    print(f"  TSL is_rising formula: slope > 0.25")
    print(f"    trend_score = mean(normPc, normEma, normMa) * 100")
    print(f"    normX      = clip( clip(z_100, -2.5, 2.5) / 2.0, -1, 1 )")
    print(f"    raw_slope  = (trend_score - trend_score.shift(5)) / 5")
    print(f"    slope      = EMA(raw_slope, span=3, adjust=False)")
    print()
    print(f"  The two indicators use SEPARATE normalization windows")
    print(f"  (candle: 200-bar z-score | TSL: 100-bar clamped z-score)")
    print()
    print(f"  Data: {TICKER} {TIMEFRAME} {START_DATE} → {END_DATE}")
    print(f"  Total bars   : {total_bars:,}")
    print(f"  cyan_signal  : {cyan_count:,}")
    print(f"  is_rising    : {rising_count:,}")
    print(f"  COMBINED     : {signal_count:,}  ({frequency_pct:.3f}%)")
    print("=" * 64)

    return {
        "total_bars": total_bars,
        "cyan_count": cyan_count,
        "rising_count": rising_count,
        "combined_signal_count": signal_count,
        "signal_frequency_pct": frequency_pct,
    }


if __name__ == "__main__":
    validate()
