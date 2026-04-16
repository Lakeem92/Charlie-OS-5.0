"""
Step 4: Gap Identification
Identifies gap-down and gap-up days with size classification.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from config import (
    TICKER, DATA_RAW, DATA_PROC,
    GAP_DOWN_MIN, GAP_DOWN_MAX, GAP_BANDS
)


def identify_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identify gap days and calculate various gap metrics.
    
    Gap is measured as: (Open - PrevClose) / PrevClose * 100
    """
    df = df.sort_values("Date").reset_index(drop=True)
    
    # Calculate gaps
    df["prev_close"] = df["Close"].shift(1)
    df["gap_pct"] = (df["Open"] - df["prev_close"]) / df["prev_close"] * 100
    
    # Gap direction
    df["gap_direction"] = df["gap_pct"].apply(
        lambda x: "UP" if x > 0 else ("DOWN" if x < 0 else "FLAT") if pd.notna(x) else np.nan
    )
    
    # Classify into gap bands
    def classify_gap_band(gap):
        if pd.isna(gap):
            return np.nan
        for (low, high, name) in GAP_BANDS:
            if low <= gap < high:
                return name
        if gap >= GAP_BANDS[-1][1]:
            return "Tiny+"  # Above the smallest gap band (positive)
        if gap < GAP_BANDS[0][0]:
            return "Crash+"  # Below the largest crash band
        if gap > 0:
            # Check positive gap bands (mirror of negative)
            if gap >= 1.5:
                return "Gap Up Large"
            elif gap >= 0.9:
                return "Gap Up Medium"
            elif gap >= 0.5:
                return "Gap Up Small"
            else:
                return "Gap Up Tiny"
        return "Unknown"
    
    df["gap_band"] = df["gap_pct"].apply(classify_gap_band)
    
    # Is it in the primary gap band we're studying?
    df["is_primary_gap_band"] = (
        (df["gap_pct"] >= GAP_DOWN_MIN) & 
        (df["gap_pct"] < GAP_DOWN_MAX)
    )
    
    # Calculate intraday returns relative to open
    df["open_to_close"] = (df["Close"] - df["Open"]) / df["Open"] * 100
    df["open_to_high"] = (df["High"] - df["Open"]) / df["Open"] * 100
    df["open_to_low"] = (df["Low"] - df["Open"]) / df["Open"] * 100
    df["intraday_range"] = (df["High"] - df["Low"]) / df["Open"] * 100
    
    # Reversal ratio: where did close fall within the day's range?
    # 1.0 = closed at high, 0.0 = closed at low
    df["reversal_ratio"] = (df["Close"] - df["Low"]) / (df["High"] - df["Low"])
    df["reversal_ratio"] = df["reversal_ratio"].clip(0, 1)
    
    return df


def main():
    print("=" * 60)
    print("STEP 4: GAP IDENTIFICATION")
    print("=" * 60)
    print(f"Target Ticker: {TICKER}")
    print(f"Primary Gap Band: {GAP_DOWN_MIN}% to {GAP_DOWN_MAX}%")
    print()
    
    # Load daily data
    daily_path = DATA_RAW / f"{TICKER}_daily.csv"
    if not daily_path.exists():
        print(f"❌ Daily data not found: {daily_path}")
        return
    
    print(f"📊 Loading daily data...")
    df = pd.read_csv(daily_path, parse_dates=["Date"])
    print(f"  {len(df)} trading days")
    
    # Identify gaps
    print(f"\n📈 Identifying gaps...")
    df_gaps = identify_gaps(df)
    
    # Save gap data
    out_cols = [
        "Date", "prev_close", "Open", "High", "Low", "Close", "Volume",
        "gap_pct", "gap_direction", "gap_band", "is_primary_gap_band",
        "open_to_close", "open_to_high", "open_to_low", 
        "intraday_range", "reversal_ratio"
    ]
    df_out = df_gaps[out_cols].copy()
    
    out_path = DATA_PROC / f"{TICKER}_gaps.csv"
    df_out.to_csv(out_path, index=False)
    print(f"  💾 Saved to {out_path}")
    
    # Summary statistics
    print(f"\n📊 Gap Distribution:")
    
    # Gap direction counts
    valid = df_out[df_out["gap_pct"].notna()]
    print(f"  Total trading days: {len(valid)}")
    
    gap_up = (valid["gap_direction"] == "UP").sum()
    gap_down = (valid["gap_direction"] == "DOWN").sum()
    gap_flat = (valid["gap_direction"] == "FLAT").sum()
    print(f"  Gap Up:   {gap_up} ({gap_up/len(valid)*100:.1f}%)")
    print(f"  Gap Down: {gap_down} ({gap_down/len(valid)*100:.1f}%)")
    print(f"  Flat:     {gap_flat} ({gap_flat/len(valid)*100:.1f}%)")
    
    # Gap band counts (for gap downs)
    print(f"\n  Gap Down Band Distribution:")
    gap_downs = valid[valid["gap_direction"] == "DOWN"]
    for (low, high, name) in GAP_BANDS:
        in_band = ((gap_downs["gap_pct"] >= low) & (gap_downs["gap_pct"] < high)).sum()
        print(f"    {name} ({low}% to {high}%): {in_band} days")
    
    # Primary gap band
    primary = valid["is_primary_gap_band"].sum()
    print(f"\n  🎯 Primary Band ({GAP_DOWN_MIN}% to {GAP_DOWN_MAX}%): {primary} days")
    
    # Show what happens on gap-down days (primary band)
    if primary > 0:
        primary_days = df_out[df_out["is_primary_gap_band"]]
        print(f"\n  📈 Primary Gap-Down Day Stats (N={primary}):")
        print(f"    Avg Gap Size: {primary_days['gap_pct'].mean():.2f}%")
        print(f"    Avg Open→Close: {primary_days['open_to_close'].mean():.2f}%")
        win_rate = (primary_days["open_to_close"] > 0).mean() * 100
        print(f"    Win Rate (close > open): {win_rate:.1f}%")
        print(f"    Avg Reversal Ratio: {primary_days['reversal_ratio'].mean():.2f}")
    
    print()
    print("=" * 60)
    print("GAP IDENTIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
