"""
TSLA Basic Indicator Honesty Test
----------------------------------
Minimal test of Trend Strength + Cap Finder indicator behavioral separation.
Exactly 252 trading days, Alpaca only, no plots/notebooks.
"""

import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import shared utilities
from shared.data_router import DataRouter
from shared.indicators.trend_strength_nr7 import compute_trend_strength_nr7, TrendStrengthParams


def fetch_data(ticker: str, days: int = 252) -> pd.DataFrame:
    """Fetch exactly N trading days using DataRouter (enforces Alpaca for honesty_test)."""
    try:
        # Calculate date range (request extra calendar days to ensure enough trading days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 200)
        
        # Use DataRouter with study_type='honesty_test' to enforce Alpaca routing
        df = DataRouter.get_price_data(
            ticker=ticker,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            timeframe='daily',
            study_type='honesty_test'
        )
        
        if df is None or len(df) == 0:
            raise RuntimeError(f"No data returned for {ticker}")
        
        # Take exactly the last N trading days
        df = df.tail(days).copy()
        df.reset_index(drop=True, inplace=True)
        
        # Standardize column names to lowercase
        df.columns = [c.lower() for c in df.columns]
        
        return df
        
    except Exception as e:
        raise RuntimeError(f"Data fetch failed: {str(e)}")


def calculate_forward_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate forward returns and max adverse excursion."""
    result = df.copy()
    close = df['close']
    low = df['low']
    
    # Forward returns (percentage)
    result['fwd_1d_return'] = (close.shift(-1) / close - 1) * 100
    result['fwd_3d_return'] = (close.shift(-3) / close - 1) * 100
    result['fwd_5d_return'] = (close.shift(-5) / close - 1) * 100
    
    # Max adverse excursion: min(low[t+1:t+5]) vs close[t]
    max_adverse = []
    for i in range(len(df)):
        if i + 5 >= len(df):
            max_adverse.append(np.nan)
        else:
            entry_price = close.iloc[i]
            future_lows = low.iloc[i+1:i+6]
            worst_low = future_lows.min()
            mae = (worst_low / entry_price - 1) * 100
            max_adverse.append(mae)
    
    result['max_adverse_5d'] = max_adverse
    
    return result


def run_honesty_test():
    """Execute the minimal indicator honesty test."""
    log_lines = []
    
    def log_print(msg):
        print(msg)
        log_lines.append(msg)
    
    try:
        # Setup output directory
        output_dir = project_root / 'studies' / 'tsla_indicator_honesty'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        log_print("="*70)
        log_print("TSLA BASIC INDICATOR HONESTY TEST")
        log_print("="*70)
        log_print("Study Type: honesty_test")
        log_print("Ticker: TSLA")
        log_print("Lookback: 252 trading days")
        log_print("Data Source: Alpaca (enforced via DataRouter)")
        log_print("Indicators: Trend Strength, NR7, Momentum Extremes (Cap Finder)")
        log_print("")
        
        # Checkpoint 1: Fetch data
        log_print("[1/5] Fetching data...")
        df = fetch_data('TSLA', days=252)
        if df is None or len(df) == 0:
            raise RuntimeError("Data fetch returned no data")
        
        log_print(f"      ✓ Fetched {len(df)} daily bars")
        
        # Checkpoint 2: Calculate indicators
        log_print("[2/5] Computing indicators...")
        df = compute_trend_strength_nr7(df, TrendStrengthParams())
        log_print(f"      ✓ Indicators computed")
        
        # Checkpoint 3: Count events
        log_print("[3/5] Identifying momentum extreme events...")
        oversold_count = df['oversoldExtreme'].sum()
        overbought_count = df['overboughtExtreme'].sum()
        baseline_count = len(df)
        
        log_print(f"      Total bars: {baseline_count}")
        log_print(f"      Oversold extreme bars: {oversold_count}")
        log_print(f"      Overbought extreme bars: {overbought_count}")
        
        # Hard stop rule
        if oversold_count == 0 and overbought_count == 0:
            log_print("")
            log_print("⚠️  STOP: NO SIGNALS DETECTED")
            log_print("    Recommendation: Increase lookback period or adjust indicator parameters")
            
            # Save log
            log_file = output_dir / 'run_log.txt'
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(log_lines))
            
            return
        
        # Calculate forward metrics
        log_print("[4/5] Calculating forward returns and max adverse excursion...")
        df = calculate_forward_metrics(df)
        
        # Filter to bars with complete 5-day forward data
        df_analysis = df[df['fwd_5d_return'].notna()].copy()
        log_print(f"      ✓ {len(df_analysis)} bars with complete forward data")
        
        # Classify bars into three groups
        oversold_mask = df_analysis['oversoldExtreme'] == True
        overbought_mask = df_analysis['overboughtExtreme'] == True
        baseline_mask = ~oversold_mask & ~overbought_mask
        
        # Build results table
        results = []
        for label, mask in [('Baseline', baseline_mask), 
                           ('OversoldExtreme', oversold_mask), 
                           ('OverboughtExtreme', overbought_mask)]:
            group_df = df_analysis[mask]
            count = len(group_df)
            
            if count == 0:
                results.append({
                    'Group': label,
                    'Count': 0,
                    'Avg_1d_Return_%': np.nan,
                    'Avg_3d_Return_%': np.nan,
                    'Avg_5d_Return_%': np.nan,
                    'Avg_MaxAdverse_5d_%': np.nan
                })
            else:
                results.append({
                    'Group': label,
                    'Count': count,
                    'Avg_1d_Return_%': group_df['fwd_1d_return'].mean(),
                    'Avg_3d_Return_%': group_df['fwd_3d_return'].mean(),
                    'Avg_5d_Return_%': group_df['fwd_5d_return'].mean(),
                    'Avg_MaxAdverse_5d_%': group_df['max_adverse_5d'].mean()
                })
        
        results_df = pd.DataFrame(results)
        
        log_print("      ✓ Metrics computed")
        
        # Checkpoint 5: Save outputs
        log_print("[5/5] Saving results...")
        csv_file = output_dir / 'tsla_honesty_test_results.csv'
        results_df.to_csv(csv_file, index=False)
        
        log_file = output_dir / 'run_log.txt'
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_lines))
        
        log_print(f"      ✓ Results saved to: {csv_file}")
        log_print("")
        
        # Display results table
        log_print("="*70)
        log_print("RESULTS")
        log_print("="*70)
        print()
        print(results_df.to_string(index=False, float_format=lambda x: f'{x:.3f}' if not np.isnan(x) else 'N/A'))
        print()
        log_print("="*70)
        
        # Behavioral separation analysis
        log_print("")
        log_print("CONCLUSION:")
        log_print("-" * 70)
        
        # Check if we have enough data for meaningful comparison
        oversold_data = results_df[results_df['Group'] == 'OversoldExtreme']
        overbought_data = results_df[results_df['Group'] == 'OverboughtExtreme']
        baseline_data = results_df[results_df['Group'] == 'Baseline']
        
        if len(oversold_data) > 0 and len(overbought_data) > 0:
            oversold_5d = oversold_data['Avg_5d_Return_%'].iloc[0]
            overbought_5d = overbought_data['Avg_5d_Return_%'].iloc[0]
            baseline_5d = baseline_data['Avg_5d_Return_%'].iloc[0]
            
            # Check for meaningful separation (at least 1% difference from baseline)
            separation_threshold = 1.0
            
            oversold_diff = abs(oversold_5d - baseline_5d) if not np.isnan(oversold_5d) else 0
            overbought_diff = abs(overbought_5d - baseline_5d) if not np.isnan(overbought_5d) else 0
            
            if oversold_diff >= separation_threshold or overbought_diff >= separation_threshold:
                log_print("✓ Indicator shows behavioral separation")
                log_print(f"  Oversold vs Baseline: {oversold_5d:.3f}% vs {baseline_5d:.3f}% (diff: {oversold_diff:.3f}%)")
                log_print(f"  Overbought vs Baseline: {overbought_5d:.3f}% vs {baseline_5d:.3f}% (diff: {overbought_diff:.3f}%)")
            else:
                log_print("✗ Indicator does not show behavioral separation")
                log_print(f"  Oversold vs Baseline: {oversold_5d:.3f}% vs {baseline_5d:.3f}% (diff: {oversold_diff:.3f}%)")
                log_print(f"  Overbought vs Baseline: {overbought_5d:.3f}% vs {baseline_5d:.3f}% (diff: {overbought_diff:.3f}%)")
        else:
            log_print("⚠️  Insufficient signal data for behavioral separation analysis")
        
        log_print("="*70)
        
        # Save final log
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_lines))
        
    except Exception as e:
        log_print("")
        log_print(f"ERROR: {str(e)}")
        
        # Save error log
        output_dir = project_root / 'studies' / 'tsla_indicator_honesty'
        output_dir.mkdir(parents=True, exist_ok=True)
        log_file = output_dir / 'run_log.txt'
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_lines))
        
        raise


if __name__ == "__main__":
    run_honesty_test()
