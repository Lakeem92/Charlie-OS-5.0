"""
Step 6: Forward Return Analysis
For each confluence event, measures what happened next.
Answers the core question: do these setups tend to reverse or continue?
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from scipy import stats
from config import (
    TICKER, DATA_RAW, DATA_PROC, TABLES,
    INTRADAY_RETURNS, DAILY_RETURNS
)


def calculate_forward_returns(df_events: pd.DataFrame, df_daily: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate forward returns for each event.
    
    Includes:
    - Intraday returns (already in event data)
    - T+1, T+2, T+3, T+5 returns
    """
    df_events = df_events.copy()
    df_daily = df_daily.sort_values("Date").reset_index(drop=True)
    
    # Create lookup for daily closes by date
    daily_close = df_daily.set_index("Date")["Close"].to_dict()
    daily_dates = sorted(df_daily["Date"].tolist())
    
    def get_forward_close(event_date, days_forward):
        """Get close price N trading days forward."""
        try:
            idx = daily_dates.index(event_date)
            future_idx = idx + days_forward
            if future_idx < len(daily_dates):
                return daily_close[daily_dates[future_idx]]
        except (ValueError, KeyError):
            pass
        return np.nan
    
    # Calculate forward returns
    for days in DAILY_RETURNS:
        col_name = f"T{days}_return"
        forward_closes = []
        for _, row in df_events.iterrows():
            event_date = row["date"]
            event_close = row["close"]
            future_close = get_forward_close(event_date, days)
            if pd.notna(future_close) and pd.notna(event_close) and event_close > 0:
                ret = (future_close - event_close) / event_close * 100
            else:
                ret = np.nan
            forward_closes.append(ret)
        df_events[col_name] = forward_closes
    
    return df_events


def calculate_statistics(returns: pd.Series, label: str = "Returns") -> dict:
    """Calculate comprehensive statistics for a return series."""
    valid = returns.dropna()
    
    if len(valid) == 0:
        return {"N": 0, "label": label}
    
    wins = valid[valid > 0]
    losses = valid[valid <= 0]
    
    # Basic stats
    stats_dict = {
        "label": label,
        "N": len(valid),
        "win_rate": len(wins) / len(valid) * 100 if len(valid) > 0 else 0,
        "mean_return": valid.mean(),
        "median_return": valid.median(),
        "std_return": valid.std(),
        "min_return": valid.min(),
        "max_return": valid.max(),
    }
    
    # Winner/loser breakdown
    stats_dict["avg_winner"] = wins.mean() if len(wins) > 0 else 0
    stats_dict["avg_loser"] = losses.mean() if len(losses) > 0 else 0
    
    # Profit factor
    gross_wins = wins.sum() if len(wins) > 0 else 0
    gross_losses = abs(losses.sum()) if len(losses) > 0 else 0
    stats_dict["profit_factor"] = gross_wins / gross_losses if gross_losses > 0 else np.inf
    
    # Sharpe-like ratio (mean / std)
    stats_dict["sharpe_like"] = valid.mean() / valid.std() if valid.std() > 0 else 0
    
    # T-test: is mean significantly different from 0?
    if len(valid) >= 2:
        t_stat, p_value = stats.ttest_1samp(valid, 0)
        stats_dict["t_stat"] = t_stat
        stats_dict["p_value"] = p_value
    else:
        stats_dict["t_stat"] = np.nan
        stats_dict["p_value"] = np.nan
    
    return stats_dict


def compare_to_baseline(event_returns: pd.Series, all_returns: pd.Series) -> dict:
    """
    Two-sample t-test: are event returns significantly different from all days?
    """
    event_valid = event_returns.dropna()
    all_valid = all_returns.dropna()
    
    result = {
        "event_N": len(event_valid),
        "baseline_N": len(all_valid),
        "event_mean": event_valid.mean() if len(event_valid) > 0 else np.nan,
        "baseline_mean": all_valid.mean() if len(all_valid) > 0 else np.nan,
        "event_std": event_valid.std() if len(event_valid) > 0 else np.nan,
        "baseline_std": all_valid.std() if len(all_valid) > 0 else np.nan,
    }
    
    # Two-sample t-test
    if len(event_valid) >= 2 and len(all_valid) >= 2:
        t_stat, p_value = stats.ttest_ind(event_valid, all_valid, equal_var=False)
        result["t_stat"] = t_stat
        result["p_value"] = p_value
        result["significant_5pct"] = p_value < 0.05
    else:
        result["t_stat"] = np.nan
        result["p_value"] = np.nan
        result["significant_5pct"] = False
    
    return result


def main():
    print("=" * 60)
    print("STEP 6: FORWARD RETURN ANALYSIS")
    print("=" * 60)
    print(f"Target Ticker: {TICKER}")
    print()
    
    # Ensure output directory exists
    TABLES.mkdir(parents=True, exist_ok=True)
    
    # Load data
    events_path = DATA_PROC / f"{TICKER}_confluence_events.csv"
    daily_path = DATA_RAW / f"{TICKER}_daily.csv"
    gaps_path = DATA_PROC / f"{TICKER}_gaps.csv"
    
    if not events_path.exists():
        print(f"❌ Confluence events not found: {events_path}")
        return
    if not daily_path.exists():
        print(f"❌ Daily data not found: {daily_path}")
        return
    
    print(f"📊 Loading data...")
    df_events = pd.read_csv(events_path, parse_dates=["date"])
    df_daily = pd.read_csv(daily_path, parse_dates=["Date"])
    df_gaps = pd.read_csv(gaps_path, parse_dates=["Date"]) if gaps_path.exists() else None
    
    # Filter to PRIMARY events
    primary_events = df_events[df_events["is_primary_event"] == True].copy()
    print(f"  Primary confluence events: {len(primary_events)}")
    
    if len(primary_events) == 0:
        print("\n⚠️ No primary confluence events to analyze.")
        print("   Check Step 5 output or try different parameters.")
        return
    
    # Calculate forward returns
    print(f"\n📈 Calculating forward returns...")
    primary_events = calculate_forward_returns(primary_events, df_daily)
    
    # Save detailed results
    out_path = TABLES / f"{TICKER}_primary_results.csv"
    primary_events.to_csv(out_path, index=False)
    print(f"  💾 Per-event details saved to {out_path}")
    
    # Calculate summary statistics
    print(f"\n📊 Summary Statistics:")
    print("-" * 40)
    
    summary_rows = []
    
    # Open-to-close (intraday)
    otc_stats = calculate_statistics(primary_events["open_to_close"], "Open→Close")
    summary_rows.append(otc_stats)
    print(f"\n  Open→Close Returns:")
    print(f"    N: {otc_stats['N']}")
    print(f"    Win Rate: {otc_stats['win_rate']:.1f}%")
    print(f"    Mean Return: {otc_stats['mean_return']:.2f}%")
    print(f"    Median Return: {otc_stats['median_return']:.2f}%")
    print(f"    Sharpe-like: {otc_stats['sharpe_like']:.2f}")
    print(f"    t-stat: {otc_stats['t_stat']:.2f}, p-value: {otc_stats['p_value']:.4f}")
    
    # Forward day returns
    for days in DAILY_RETURNS:
        col = f"T{days}_return"
        if col in primary_events.columns:
            fwd_stats = calculate_statistics(primary_events[col], f"T+{days}")
            summary_rows.append(fwd_stats)
            print(f"\n  T+{days} Returns:")
            print(f"    N: {fwd_stats['N']}")
            print(f"    Win Rate: {fwd_stats['win_rate']:.1f}%")
            print(f"    Mean Return: {fwd_stats['mean_return']:.2f}%")
    
    # Save summary stats
    df_summary = pd.DataFrame(summary_rows)
    summary_path = TABLES / f"{TICKER}_summary_stats.csv"
    df_summary.to_csv(summary_path, index=False)
    print(f"\n  💾 Summary stats saved to {summary_path}")
    
    # Baseline comparison
    print(f"\n📊 Baseline Comparison:")
    print("-" * 40)
    
    if df_gaps is not None:
        all_otc = df_gaps["open_to_close"].dropna()
        comparison = compare_to_baseline(primary_events["open_to_close"], all_otc)
        
        print(f"  Event Days (N={comparison['event_N']}):")
        print(f"    Mean: {comparison['event_mean']:.2f}%")
        print(f"    Std:  {comparison['event_std']:.2f}%")
        print(f"  All Days (N={comparison['baseline_N']}):")
        print(f"    Mean: {comparison['baseline_mean']:.2f}%")
        print(f"    Std:  {comparison['baseline_std']:.2f}%")
        print(f"  Difference: {comparison['event_mean'] - comparison['baseline_mean']:.2f}%")
        print(f"  t-stat: {comparison['t_stat']:.2f}, p-value: {comparison['p_value']:.4f}")
        
        sig = "YES" if comparison.get('significant_5pct', False) else "NO"
        print(f"  Significant at 5%? {sig}")
        
        # Save comparison
        comp_df = pd.DataFrame([comparison])
        comp_path = TABLES / f"{TICKER}_baseline_comparison.csv"
        comp_df.to_csv(comp_path, index=False)
        print(f"\n  💾 Baseline comparison saved to {comp_path}")
    
    # Conditional breakdowns
    print(f"\n📊 Conditional Breakdowns:")
    print("-" * 40)
    
    breakdowns = []
    
    # By gap size (use gap_band from events)
    if "gap_band" in primary_events.columns:
        print(f"\n  By Gap Band:")
        for band in primary_events["gap_band"].unique():
            subset = primary_events[primary_events["gap_band"] == band]
            if len(subset) >= 1:
                bd_stats = calculate_statistics(subset["open_to_close"], f"Gap: {band}")
                bd_stats["breakdown_type"] = "gap_band"
                bd_stats["breakdown_value"] = band
                breakdowns.append(bd_stats)
                print(f"    {band}: N={bd_stats['N']}, Win={bd_stats['win_rate']:.0f}%, Mean={bd_stats['mean_return']:.2f}%")
    
    # By RS(Z) class
    if "rs_class_prior" in primary_events.columns:
        print(f"\n  By RS(Z) Class:")
        for cls in primary_events["rs_class_prior"].dropna().unique():
            subset = primary_events[primary_events["rs_class_prior"] == cls]
            if len(subset) >= 1:
                bd_stats = calculate_statistics(subset["open_to_close"], f"RS: {cls}")
                bd_stats["breakdown_type"] = "rs_class"
                bd_stats["breakdown_value"] = cls
                breakdowns.append(bd_stats)
                print(f"    {cls}: N={bd_stats['N']}, Win={bd_stats['win_rate']:.0f}%, Mean={bd_stats['mean_return']:.2f}%")
    
    # By TrendScore zone (prior daily)
    if "ts_zone_prior_daily" in primary_events.columns:
        print(f"\n  By Prior Daily TS Zone:")
        for zone in primary_events["ts_zone_prior_daily"].dropna().unique():
            subset = primary_events[primary_events["ts_zone_prior_daily"] == zone]
            if len(subset) >= 1:
                bd_stats = calculate_statistics(subset["open_to_close"], f"TS Zone: {zone}")
                bd_stats["breakdown_type"] = "ts_zone"
                bd_stats["breakdown_value"] = zone
                breakdowns.append(bd_stats)
                print(f"    {zone}: N={bd_stats['N']}, Win={bd_stats['win_rate']:.0f}%, Mean={bd_stats['mean_return']:.2f}%")
    
    # By day of week
    if "date" in primary_events.columns:
        print(f"\n  By Day of Week:")
        primary_events["dow"] = pd.to_datetime(primary_events["date"]).dt.day_name()
        for dow in primary_events["dow"].dropna().unique():
            subset = primary_events[primary_events["dow"] == dow]
            if len(subset) >= 1:
                bd_stats = calculate_statistics(subset["open_to_close"], f"Day: {dow}")
                bd_stats["breakdown_type"] = "day_of_week"
                bd_stats["breakdown_value"] = dow
                breakdowns.append(bd_stats)
                print(f"    {dow}: N={bd_stats['N']}, Win={bd_stats['win_rate']:.0f}%, Mean={bd_stats['mean_return']:.2f}%")
    
    # Save breakdowns
    if breakdowns:
        bd_df = pd.DataFrame(breakdowns)
        bd_path = TABLES / f"{TICKER}_conditional_breakdowns.csv"
        bd_df.to_csv(bd_path, index=False)
        print(f"\n  💾 Conditional breakdowns saved to {bd_path}")
    
    print()
    print("=" * 60)
    print("FORWARD RETURN ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
