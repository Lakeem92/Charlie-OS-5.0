"""
Step 3: RS(Z) Calculation
Calculates Relative Strength Z-score of TICKER vs BENCHMARK on daily timeframe.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from config import (
    TICKER, BENCHMARK, DATA_RAW, DATA_PROC,
    RS_LOOKBACK, RS_ZSCORE_WINDOW, RS_OVERSOLD_THRESHOLD
)


def calculate_rs_z(df_ticker: pd.DataFrame, df_bench: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Relative Strength Z-score.
    
    1. Calculate rolling returns for both ticker and benchmark
    2. Raw RS = ticker momentum - benchmark momentum
    3. Z-score normalize the RS
    4. Classify into categories
    """
    # Ensure both DataFrames have Date column and are sorted
    df_ticker = df_ticker.sort_values("Date").reset_index(drop=True)
    df_bench = df_bench.sort_values("Date").reset_index(drop=True)
    
    # Merge on Date to align
    df = df_ticker[["Date", "Close"]].copy()
    df.rename(columns={"Close": "ticker_close"}, inplace=True)
    
    df_b = df_bench[["Date", "Close"]].copy()
    df_b.rename(columns={"Close": "bench_close"}, inplace=True)
    
    df = df.merge(df_b, on="Date", how="inner")
    
    # Calculate rolling returns (momentum)
    df["ticker_mom"] = df["ticker_close"].pct_change(RS_LOOKBACK)
    df["bench_mom"] = df["bench_close"].pct_change(RS_LOOKBACK)
    
    # Raw RS = ticker momentum - benchmark momentum
    df["rs_raw"] = df["ticker_mom"] - df["bench_mom"]
    
    # Z-score normalize RS
    df["rs_mean"] = df["rs_raw"].rolling(RS_ZSCORE_WINDOW).mean()
    df["rs_std"] = df["rs_raw"].rolling(RS_ZSCORE_WINDOW).std()
    
    # Avoid division by zero
    df["rs_std"] = df["rs_std"].replace(0, np.nan)
    
    df["rs_z"] = (df["rs_raw"] - df["rs_mean"]) / df["rs_std"]
    
    # Classify RS(Z)
    def classify_rs(z):
        if pd.isna(z):
            return np.nan
        if z <= -1.0:
            return "Crushed"
        elif z <= -0.5:
            return "Weak"
        elif z < 0.5:
            return "Neutral"
        elif z < 1.0:
            return "Strong"
        else:
            return "Dominant"
    
    df["rs_class"] = df["rs_z"].apply(classify_rs)
    
    # Clean up intermediate columns
    df.drop(columns=["ticker_mom", "bench_mom", "rs_mean", "rs_std"], inplace=True)
    
    return df


def main():
    print("=" * 60)
    print("STEP 3: RS(Z) CALCULATION")
    print("=" * 60)
    print(f"Target Ticker: {TICKER}")
    print(f"Benchmark: {BENCHMARK}")
    print(f"Lookback: {RS_LOOKBACK} days")
    print(f"Z-score Window: {RS_ZSCORE_WINDOW} days")
    print()
    
    # Load daily data
    ticker_path = DATA_RAW / f"{TICKER}_daily.csv"
    bench_path = DATA_RAW / f"{BENCHMARK}_daily.csv"
    
    if not ticker_path.exists():
        print(f"❌ Ticker daily data not found: {ticker_path}")
        return
    if not bench_path.exists():
        print(f"❌ Benchmark daily data not found: {bench_path}")
        return
    
    print(f"📊 Loading daily data...")
    df_ticker = pd.read_csv(ticker_path, parse_dates=["Date"])
    df_bench = pd.read_csv(bench_path, parse_dates=["Date"])
    print(f"  {TICKER}: {len(df_ticker)} rows")
    print(f"  {BENCHMARK}: {len(df_bench)} rows")
    
    # Calculate RS(Z)
    print(f"\n📈 Calculating RS(Z)...")
    df_rs = calculate_rs_z(df_ticker, df_bench)
    print(f"  Merged rows: {len(df_rs)}")
    
    # Merge RS data back onto TSL3 daily data
    tsl_path = DATA_PROC / f"{TICKER}_daily_tsl3.csv"
    if tsl_path.exists():
        print(f"\n🔗 Merging RS(Z) with TSL3 data...")
        df_tsl = pd.read_csv(tsl_path, parse_dates=["Date"])
        
        # Merge RS columns
        df_merged = df_tsl.merge(
            df_rs[["Date", "ticker_close", "bench_close", "rs_raw", "rs_z", "rs_class"]],
            on="Date",
            how="left"
        )
        
        out_path = DATA_PROC / f"{TICKER}_daily_with_rs.csv"
        df_merged.to_csv(out_path, index=False)
        print(f"  ✅ Merged: {len(df_merged)} rows")
        print(f"  💾 Saved to {out_path}")
        
        # Show RS(Z) distribution
        valid = df_merged[df_merged["rs_z"].notna()]
        if not valid.empty:
            print(f"\n  📊 RS(Z) Distribution:")
            print(f"     Mean: {valid['rs_z'].mean():.2f}")
            print(f"     Std:  {valid['rs_z'].std():.2f}")
            print(f"     Min:  {valid['rs_z'].min():.2f}")
            print(f"     Max:  {valid['rs_z'].max():.2f}")
            
            print(f"\n  📊 RS(Z) Class Counts:")
            class_counts = valid["rs_class"].value_counts()
            for cls, cnt in class_counts.items():
                pct = cnt / len(valid) * 100
                print(f"     {cls}: {cnt} ({pct:.1f}%)")
            
            # Count days meeting threshold
            crushed = (valid["rs_z"] <= RS_OVERSOLD_THRESHOLD).sum()
            print(f"\n  🎯 Days with RS(Z) ≤ {RS_OVERSOLD_THRESHOLD}: {crushed} ({crushed/len(valid)*100:.1f}%)")
    else:
        print(f"  ⚠️ TSL3 data not found at {tsl_path}")
        print(f"     Saving RS(Z) data standalone...")
        df_rs.to_csv(DATA_PROC / f"{TICKER}_rs_z.csv", index=False)
    
    print()
    print("=" * 60)
    print("RS(Z) CALCULATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
