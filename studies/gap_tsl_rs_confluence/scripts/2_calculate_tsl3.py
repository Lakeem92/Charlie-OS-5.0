"""
Step 2: TSL3 Indicator Recreation
Recreates the TrendStrength Line v4.5 indicator in Python.
Calculates TrendScore and Slope State for each bar.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from config import (
    TICKER, DATA_RAW, DATA_PROC,
    TSL_PC_LOOKBACK, TSL_EMA_LEN, TSL_EMA_SLOPE_SMOOTH,
    TSL_MA1_LEN, TSL_MA2_LEN, TSL_ATR_LEN, TSL_NORM_LEN,
    TSL_Z_CLAMP, TSL_Z_TO_UNIT, TSL_SIGNAL_LEN,
    TSL_SLOPE_LEN, TSL_SLOPE_SMOOTH, TSL_SLOPE_NEUTRAL_THRESHOLD
)


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Exponential ATR (True Range with EMA)."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Exponential Moving Average of TR
    atr = tr.ewm(span=period, adjust=False).mean()
    return atr


def zscore_normalize(series: pd.Series, lookback: int, clamp: float, divisor: float) -> pd.Series:
    """
    Z-score normalize a series:
    1. Calculate rolling mean and std over lookback
    2. Z = (value - mean) / std
    3. Clamp to [-clamp, +clamp]
    4. Scale to [-1, +1] by dividing by divisor and clamping
    """
    roll_mean = series.rolling(lookback).mean()
    roll_std = series.rolling(lookback).std()
    
    # Avoid division by zero
    roll_std = roll_std.replace(0, np.nan)
    
    z = (series - roll_mean) / roll_std
    
    # Clamp Z-score
    z = z.clip(-clamp, clamp)
    
    # Scale to [-1, +1]
    normalized = (z / divisor).clip(-1, 1)
    
    return normalized


def calculate_tsl3(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full TSL3 calculation pipeline.
    Returns DataFrame with all TSL3 columns appended.
    """
    df = df.copy()
    
    # 1. Calculate ATR
    df["atr"] = calculate_atr(df, TSL_ATR_LEN)
    
    # 2a. Price Change Method (PC)
    df["raw_pc"] = (df["Close"] - df["Close"].shift(TSL_PC_LOOKBACK)) / df["atr"]
    
    # 2b. EMA Slope Method
    df["ema21"] = df["Close"].ewm(span=TSL_EMA_LEN, adjust=False).mean()
    ema_slope_raw = (df["ema21"] - df["ema21"].shift(1)) / df["atr"]
    df["raw_ema_slope"] = ema_slope_raw.rolling(TSL_EMA_SLOPE_SMOOTH).mean()
    
    # 2c. MA Distance Method
    df["ema20"] = df["Close"].ewm(span=TSL_MA1_LEN, adjust=False).mean()
    df["sma50"] = df["Close"].rolling(TSL_MA2_LEN).mean()
    df["raw_ma_dist"] = (df["ema20"] - df["sma50"]) / df["atr"]
    
    # 3. Z-score normalize each method
    df["norm_pc"] = zscore_normalize(df["raw_pc"], TSL_NORM_LEN, TSL_Z_CLAMP, TSL_Z_TO_UNIT)
    df["norm_ema"] = zscore_normalize(df["raw_ema_slope"], TSL_NORM_LEN, TSL_Z_CLAMP, TSL_Z_TO_UNIT)
    df["norm_ma"] = zscore_normalize(df["raw_ma_dist"], TSL_NORM_LEN, TSL_Z_CLAMP, TSL_Z_TO_UNIT)
    
    # 4. Consensus: average of all three normalized methods
    df["consensus"] = df[["norm_pc", "norm_ema", "norm_ma"]].mean(axis=1)
    
    # 5. TrendScore = Consensus * 100 (range: -100 to +100)
    df["trend_score"] = df["consensus"] * 100
    
    # 6. Signal Line = 9-bar EMA of TrendScore
    df["signal_line"] = df["trend_score"].ewm(span=TSL_SIGNAL_LEN, adjust=False).mean()
    
    # 7. Slope Calculation
    # rawSlope = (TrendScore - TrendScore[SLOPE_LEN]) / SLOPE_LEN
    df["raw_slope"] = (df["trend_score"] - df["trend_score"].shift(TSL_SLOPE_LEN)) / TSL_SLOPE_LEN
    # slope = smoothed with EMA
    df["slope"] = df["raw_slope"].ewm(span=TSL_SLOPE_SMOOTH, adjust=False).mean()
    
    # Slope State: RISING (+1), NEUTRAL (0), DROPPING (-1)
    def classify_slope(s):
        if pd.isna(s):
            return np.nan
        if s > TSL_SLOPE_NEUTRAL_THRESHOLD:
            return 1  # RISING
        elif s < -TSL_SLOPE_NEUTRAL_THRESHOLD:
            return -1  # DROPPING
        else:
            return 0  # NEUTRAL
    
    df["slope_state"] = df["slope"].apply(classify_slope)
    
    # 8. Momentum = TrendScore - TrendScore[1]
    df["momentum"] = df["trend_score"] - df["trend_score"].shift(1)
    
    # 9. Acceleration = Momentum - Momentum[1]
    df["acceleration"] = df["momentum"] - df["momentum"].shift(1)
    
    # TS Zone classification
    def classify_ts_zone(ts):
        if pd.isna(ts):
            return np.nan
        if ts >= 70:
            return "OB"  # Overbought
        elif ts >= 30:
            return "BULL"
        elif ts > -30:
            return "NEUT"
        elif ts > -70:
            return "BEAR"
        else:
            return "OS"  # Oversold
    
    df["ts_zone"] = df["trend_score"].apply(classify_ts_zone)
    
    # Mark warmup period (first ~100 bars have incomplete normalization)
    df["warmup"] = df.index < TSL_NORM_LEN
    
    # Clean up intermediate columns
    df.drop(columns=["ema21", "ema20", "sma50", "raw_slope"], inplace=True, errors="ignore")
    
    return df


def main():
    print("=" * 60)
    print("STEP 2: TSL3 INDICATOR CALCULATION")
    print("=" * 60)
    print(f"Target Ticker: {TICKER}")
    print()
    
    # Process DAILY data
    daily_path = DATA_RAW / f"{TICKER}_daily.csv"
    if daily_path.exists():
        print(f"📊 Processing daily data from {daily_path}...")
        df_daily = pd.read_csv(daily_path, parse_dates=["Date"])
        df_daily = df_daily.sort_values("Date").reset_index(drop=True)
        
        df_daily_tsl = calculate_tsl3(df_daily)
        
        out_path = DATA_PROC / f"{TICKER}_daily_tsl3.csv"
        df_daily_tsl.to_csv(out_path, index=False)
        print(f"  ✅ Daily TSL3 calculated: {len(df_daily_tsl)} rows")
        print(f"     Warmup rows (first {TSL_NORM_LEN}): {df_daily_tsl['warmup'].sum()}")
        print(f"     Valid rows: {(~df_daily_tsl['warmup']).sum()}")
        print(f"  💾 Saved to {out_path}")
        
        # Show sample of TrendScore distribution
        valid = df_daily_tsl[~df_daily_tsl["warmup"]]
        if not valid.empty:
            print(f"\n  📈 TrendScore stats (post-warmup):")
            print(f"     Mean: {valid['trend_score'].mean():.2f}")
            print(f"     Std:  {valid['trend_score'].std():.2f}")
            print(f"     Min:  {valid['trend_score'].min():.2f}")
            print(f"     Max:  {valid['trend_score'].max():.2f}")
    else:
        print(f"  ⚠️ Daily data not found at {daily_path}")
    
    print()
    
    # Process INTRADAY data
    intraday_path = DATA_RAW / f"{TICKER}_5min.csv"
    if intraday_path.exists():
        print(f"📊 Processing 5-min intraday data from {intraday_path}...")
        df_5min = pd.read_csv(intraday_path, parse_dates=["datetime"])
        df_5min = df_5min.sort_values("datetime").reset_index(drop=True)
        
        df_5min_tsl = calculate_tsl3(df_5min)
        
        out_path = DATA_PROC / f"{TICKER}_5min_tsl3.csv"
        df_5min_tsl.to_csv(out_path, index=False)
        print(f"  ✅ Intraday TSL3 calculated: {len(df_5min_tsl)} rows")
        print(f"     Warmup rows: {df_5min_tsl['warmup'].sum()}")
        print(f"     Valid rows: {(~df_5min_tsl['warmup']).sum()}")
        print(f"  💾 Saved to {out_path}")
    else:
        print(f"  ⚠️ Intraday data not found at {intraday_path}")
    
    print()
    print("=" * 60)
    print("TSL3 CALCULATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
