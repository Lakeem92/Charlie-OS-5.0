"""
Step 5: Confluence Event Detection
Finds days where all three conditions align:
1. Gap down in specified range
2. TSL3 slope state = RISING at market open (first 4 bars of 5-MINUTE chart)
3. Daily RS(Z) ≤ threshold (oversold relative strength)

CRITICAL: The TSL3 slope is measured on the 5-MINUTE INTRADAY chart, NOT daily.
This captures real-time momentum at the open.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import time
from config import (
    TICKER, DATA_PROC,
    GAP_DOWN_MIN, GAP_DOWN_MAX, GAP_BANDS,
    RS_OVERSOLD_THRESHOLD, RS_THRESHOLDS,
    SLOPE_STATES, GAP_OPEN_WINDOW_BARS
)


def get_opening_slope_state(df_5min: pd.DataFrame, date: pd.Timestamp) -> dict:
    """
    Get the slope state from the first 4 bars (9:30-9:50 AM ET) of a trading day.
    Returns dict with slope info or None if no data.
    """
    # Filter to the specific date
    day_data = df_5min[df_5min["date"] == date.date()]
    
    if day_data.empty:
        return None
    
    # Get first 4 bars of RTH (Regular Trading Hours start at 9:30 AM)
    # Filter for bars between 9:30 and 10:00 (first 30 min = 6 bars at 5-min)
    # We want first 4 bars: 9:30, 9:35, 9:40, 9:45
    rth_start = time(9, 30)
    rth_early = time(9, 50)  # First 20 minutes = 4 bars
    
    day_data = day_data.copy()
    day_data["time"] = pd.to_datetime(day_data["datetime"]).dt.time
    
    opening_bars = day_data[
        (day_data["time"] >= rth_start) & 
        (day_data["time"] < rth_early)
    ].head(GAP_OPEN_WINDOW_BARS)
    
    if opening_bars.empty:
        return None
    
    # Check if ANY of the first 4 bars shows RISING slope
    has_rising = (opening_bars["slope_state"] == 1).any()
    has_dropping = (opening_bars["slope_state"] == -1).any()
    
    # What was the first bar's slope state?
    first_slope_state = opening_bars.iloc[0]["slope_state"] if len(opening_bars) > 0 else np.nan
    
    # Find which bar first showed RISING (if any)
    rising_bars = opening_bars[opening_bars["slope_state"] == 1]
    bar_of_first_rising = rising_bars.index[0] - opening_bars.index[0] + 1 if not rising_bars.empty else np.nan
    
    # Get TrendScore and other metrics from first bar
    first_bar = opening_bars.iloc[0]
    
    return {
        "slope_state_at_open": first_slope_state,
        "has_rising_in_opening": has_rising,
        "has_dropping_in_opening": has_dropping,
        "bar_of_first_rising": bar_of_first_rising,
        "trend_score_at_open": first_bar.get("trend_score", np.nan),
        "ts_zone_at_open": first_bar.get("ts_zone", np.nan),
        "opening_bars_count": len(opening_bars),
    }


def detect_confluence_events(
    df_gaps: pd.DataFrame,
    df_daily_rs: pd.DataFrame,
    df_5min: pd.DataFrame,
    gap_min: float,
    gap_max: float,
    rs_threshold: float,
    slope_state_required: int
) -> pd.DataFrame:
    """
    Detect confluence events matching all three conditions.
    
    Args:
        df_gaps: Gap identification data
        df_daily_rs: Daily data with RS(Z) scores
        df_5min: 5-minute intraday data with TSL3
        gap_min: Minimum gap % (more negative = bigger gap down)
        gap_max: Maximum gap % (less negative = smaller gap down)
        rs_threshold: RS(Z) must be ≤ this value
        slope_state_required: 1=RISING, 0=NEUTRAL, -1=DROPPING
    
    Returns:
        DataFrame of confluence events
    """
    events = []
    
    # Filter to gap-down days in the specified range
    gap_days = df_gaps[
        (df_gaps["gap_pct"] >= gap_min) & 
        (df_gaps["gap_pct"] < gap_max) &
        (df_gaps["gap_direction"] == "DOWN")
    ].copy()
    
    for _, row in gap_days.iterrows():
        date = row["Date"]
        
        # Get prior day's RS(Z)
        # Find the row just before this date
        prior_rows = df_daily_rs[df_daily_rs["Date"] < date].tail(1)
        if prior_rows.empty:
            rs_z_prior = np.nan
            rs_class_prior = np.nan
            ts_zone_prior = np.nan
        else:
            prior = prior_rows.iloc[0]
            rs_z_prior = prior.get("rs_z", np.nan)
            rs_class_prior = prior.get("rs_class", np.nan)
            ts_zone_prior = prior.get("ts_zone", np.nan)
        
        # Get opening slope state from intraday data
        slope_info = get_opening_slope_state(df_5min, date)
        
        if slope_info is None:
            # No intraday data for this day
            slope_state_at_open = np.nan
            has_rising = False
            trend_score_at_open = np.nan
            ts_zone_at_open = np.nan
            bar_of_first_rising = np.nan
        else:
            slope_state_at_open = slope_info["slope_state_at_open"]
            has_rising = slope_info["has_rising_in_opening"]
            trend_score_at_open = slope_info["trend_score_at_open"]
            ts_zone_at_open = slope_info["ts_zone_at_open"]
            bar_of_first_rising = slope_info["bar_of_first_rising"]
        
        # Check all three confluence conditions
        # Condition 1: Gap is in range (already filtered)
        cond1_gap = True
        
        # Condition 2: Slope state matches requirement
        if slope_state_required == 1:
            cond2_slope = has_rising  # Any RISING in first 4 bars
        elif slope_state_required == -1:
            cond2_slope = slope_info["has_dropping_in_opening"] if slope_info else False
        else:
            cond2_slope = not has_rising and not (slope_info["has_dropping_in_opening"] if slope_info else False)
        
        # Condition 3: RS(Z) ≤ threshold
        cond3_rs = pd.notna(rs_z_prior) and rs_z_prior <= rs_threshold
        
        # Is this a primary event (all conditions met)?
        is_primary = cond1_gap and cond2_slope and cond3_rs
        
        event = {
            "date": date,
            "gap_pct": row["gap_pct"],
            "gap_band": row["gap_band"],
            "rs_z_prior": rs_z_prior,
            "rs_class_prior": rs_class_prior,
            "ts_zone_prior_daily": ts_zone_prior,
            "slope_state_at_open": slope_state_at_open,
            "trend_score_at_open": trend_score_at_open,
            "ts_zone_at_open": ts_zone_at_open,
            "bar_of_first_rising": bar_of_first_rising,
            "has_rising_in_opening": has_rising,
            "open": row["Open"],
            "high": row["High"],
            "low": row["Low"],
            "close": row["Close"],
            "open_to_close": row["open_to_close"],
            "open_to_high": row["open_to_high"],
            "open_to_low": row["open_to_low"],
            "reversal_ratio": row["reversal_ratio"],
            "cond1_gap": cond1_gap,
            "cond2_slope": cond2_slope,
            "cond3_rs": cond3_rs,
            "is_primary_event": is_primary,
        }
        events.append(event)
    
    return pd.DataFrame(events)


def main():
    print("=" * 60)
    print("STEP 5: CONFLUENCE EVENT DETECTION")
    print("=" * 60)
    print(f"Target Ticker: {TICKER}")
    print(f"Primary Gap Band: {GAP_DOWN_MIN}% to {GAP_DOWN_MAX}%")
    print(f"RS(Z) Threshold: ≤ {RS_OVERSOLD_THRESHOLD}")
    print(f"Slope Condition: RISING at open")
    print()
    
    # Load required data
    gaps_path = DATA_PROC / f"{TICKER}_gaps.csv"
    daily_rs_path = DATA_PROC / f"{TICKER}_daily_with_rs.csv"
    intraday_path = DATA_PROC / f"{TICKER}_5min_tsl3.csv"
    
    if not gaps_path.exists():
        print(f"❌ Gap data not found: {gaps_path}")
        return
    if not daily_rs_path.exists():
        print(f"❌ Daily RS data not found: {daily_rs_path}")
        return
    
    print(f"📊 Loading data...")
    df_gaps = pd.read_csv(gaps_path, parse_dates=["Date"])
    df_daily_rs = pd.read_csv(daily_rs_path, parse_dates=["Date"])
    print(f"  Gap data: {len(df_gaps)} days")
    print(f"  Daily RS data: {len(df_daily_rs)} days")
    
    # Load intraday data if available
    if intraday_path.exists():
        df_5min = pd.read_csv(intraday_path, parse_dates=["datetime"])
        df_5min["date"] = pd.to_datetime(df_5min["datetime"]).dt.date
        print(f"  Intraday data: {len(df_5min)} bars ({df_5min['date'].nunique()} days)")
        has_intraday = True
    else:
        print(f"  ⚠️ Intraday data not found - will use daily slope only")
        df_5min = pd.DataFrame()
        has_intraday = False
    
    # Detect PRIMARY confluence events
    print(f"\n🎯 Detecting PRIMARY confluence events...")
    df_primary = detect_confluence_events(
        df_gaps, df_daily_rs, df_5min,
        gap_min=GAP_DOWN_MIN,
        gap_max=GAP_DOWN_MAX,
        rs_threshold=RS_OVERSOLD_THRESHOLD,
        slope_state_required=1  # RISING
    )
    
    # Filter to actual confluence events
    primary_events = df_primary[df_primary["is_primary_event"]]
    
    out_path = DATA_PROC / f"{TICKER}_confluence_events.csv"
    df_primary.to_csv(out_path, index=False)
    print(f"  Gap-down days in primary band: {len(df_primary)}")
    print(f"  ✅ PRIMARY confluence events: {len(primary_events)}")
    print(f"  💾 Saved to {out_path}")
    
    if len(primary_events) > 0:
        print(f"\n  📈 Primary Event Stats:")
        print(f"    Avg Gap: {primary_events['gap_pct'].mean():.2f}%")
        print(f"    Avg RS(Z): {primary_events['rs_z_prior'].mean():.2f}")
        print(f"    Avg Open→Close: {primary_events['open_to_close'].mean():.2f}%")
        win_rate = (primary_events["open_to_close"] > 0).mean() * 100
        print(f"    Win Rate: {win_rate:.1f}%")
    
    # Generate ALL variants for robustness analysis
    print(f"\n📊 Generating ALL variant combinations...")
    all_variants = []
    
    for (gap_min, gap_max, gap_name) in GAP_BANDS:
        for rs_thresh in RS_THRESHOLDS:
            for slope_name, slope_val in SLOPE_STATES.items():
                df_var = detect_confluence_events(
                    df_gaps, df_daily_rs, df_5min,
                    gap_min=gap_min,
                    gap_max=gap_max,
                    rs_threshold=rs_thresh,
                    slope_state_required=slope_val
                )
                
                # Filter to actual events
                events = df_var[df_var["is_primary_event"]]
                
                for _, event in events.iterrows():
                    event_dict = event.to_dict()
                    event_dict["gap_band_variant"] = gap_name
                    event_dict["rs_threshold_variant"] = rs_thresh
                    event_dict["slope_variant"] = slope_name
                    all_variants.append(event_dict)
    
    df_all = pd.DataFrame(all_variants)
    
    if not df_all.empty:
        all_path = DATA_PROC / f"{TICKER}_all_variants.csv"
        df_all.to_csv(all_path, index=False)
        print(f"  ✅ Total variant events: {len(df_all)}")
        print(f"  💾 Saved to {all_path}")
        
        # Summary by variant type
        print(f"\n  📊 Events by Slope Type:")
        for slope_name in SLOPE_STATES.keys():
            cnt = (df_all["slope_variant"] == slope_name).sum()
            print(f"    {slope_name}: {cnt}")
    else:
        print(f"  ⚠️ No variant events found")
    
    print()
    print("=" * 60)
    print("CONFLUENCE DETECTION COMPLETE")
    print("=" * 60)
    
    if len(primary_events) == 0:
        print("\n⚠️ NOTE: No primary confluence events found.")
        print("   This could mean:")
        print("   1. The gap band is too narrow")
        print("   2. RS(Z) threshold is too strict")
        print("   3. Intraday data doesn't overlap with gap days")
        print("   4. The setup is genuinely rare (which is valuable info!)")
        print("   Consider checking variant results for other configurations.")


if __name__ == "__main__":
    main()
