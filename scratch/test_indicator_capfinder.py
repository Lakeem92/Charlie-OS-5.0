"""
Test script for Trend Strength v2 + NR7 + Momentum Extremes (Cap Finder)
------------------------------------------------------------------------
Validates that the Cap Finder upgrade is correctly implemented.

Requirements:
- All 13 original outputs present
- All 9 new Cap Finder outputs present
- oversoldExtreme and overboughtExtreme counts are reasonable (not all True/False)
- momentum_extreme_state includes at least "NONE"

No API calls - synthetic data only.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.indicators.trend_strength_nr7 import (
    compute_trend_strength_nr7,
    TrendStrengthParams,
)


def generate_synthetic_ohlcv(n_rows: int = 300, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV with realistic patterns for testing."""
    np.random.seed(seed)
    
    # Start with a base price and add random walk
    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, n_rows)
    close = base_price * np.exp(np.cumsum(returns))
    
    # Generate OHLC with realistic relationships
    daily_range = np.abs(np.random.normal(0.02, 0.01, n_rows))
    high = close * (1 + daily_range * np.random.uniform(0.3, 1.0, n_rows))
    low = close * (1 - daily_range * np.random.uniform(0.3, 1.0, n_rows))
    open_price = low + (high - low) * np.random.uniform(0.2, 0.8, n_rows)
    
    # Generate volume with occasional spikes
    base_volume = 1_000_000
    volume = base_volume * (1 + np.abs(np.random.normal(0, 0.5, n_rows)))
    # Add volume spikes (20% of days)
    spike_indices = np.random.choice(n_rows, size=int(n_rows * 0.2), replace=False)
    volume[spike_indices] *= np.random.uniform(1.5, 3.0, len(spike_indices))
    
    # Create DataFrame
    df = pd.DataFrame({
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })
    
    return df


def main():
    print("=" * 70)
    print("CAP FINDER INDICATOR TEST")
    print("=" * 70)
    print()
    
    # Generate synthetic data
    print("Step 1: Generate synthetic OHLCV data (300 rows)")
    df = generate_synthetic_ohlcv(n_rows=300, seed=42)
    print(f"✓ Generated {len(df)} rows")
    print()
    
    # Run indicator with default params
    print("Step 2: Run indicator with default parameters")
    params = TrendStrengthParams()
    result = compute_trend_strength_nr7(df, params)
    print(f"✓ Indicator computed, result shape: {result.shape}")
    print()
    
    # Verify original outputs (13 columns)
    print("Step 3: Verify original outputs (backwards compatibility)")
    original_outputs = [
        "atr", "rawPc", "raw_ema_slope_sm", "rawMaDist",
        "pcZscore", "emaZscore", "maZscore", "consensusScore",
        "agreement", "consensusScaled", "consensusClamped",
        "is_nr7", "trend_state"
    ]
    
    missing_original = [col for col in original_outputs if col not in result.columns]
    if missing_original:
        print(f"✗ FAIL: Missing original outputs: {missing_original}")
        return False
    print(f"✓ All {len(original_outputs)} original outputs present")
    print()
    
    # Verify new Cap Finder outputs (9 columns)
    print("Step 4: Verify new Cap Finder outputs")
    capfinder_outputs = [
        "cap_rsi", "cap_ma", "cap_vol_avg",
        "cap_below", "cap_above", "cap_vol_spike",
        "oversoldExtreme", "overboughtExtreme", "momentum_extreme_state"
    ]
    
    missing_capfinder = [col for col in capfinder_outputs if col not in result.columns]
    if missing_capfinder:
        print(f"✗ FAIL: Missing Cap Finder outputs: {missing_capfinder}")
        return False
    print(f"✓ All {len(capfinder_outputs)} Cap Finder outputs present")
    print()
    
    # Check oversoldExtreme counts
    print("Step 5: Validate oversoldExtreme behavior")
    oversold_count = result["oversoldExtreme"].sum()
    oversold_pct = (oversold_count / len(result)) * 100
    print(f"  oversoldExtreme count: {oversold_count} ({oversold_pct:.1f}%)")
    
    if oversold_count == 0:
        print("  ⚠ WARNING: No oversold extremes detected (may be valid for this data)")
    elif oversold_count == len(result):
        print("  ✗ FAIL: All rows marked as oversold extreme (logic error)")
        return False
    else:
        print("  ✓ Reasonable oversold extreme count")
    print()
    
    # Check overboughtExtreme counts
    print("Step 6: Validate overboughtExtreme behavior")
    overbought_count = result["overboughtExtreme"].sum()
    overbought_pct = (overbought_count / len(result)) * 100
    print(f"  overboughtExtreme count: {overbought_count} ({overbought_pct:.1f}%)")
    
    if overbought_count == 0:
        print("  ⚠ WARNING: No overbought extremes detected (may be valid for this data)")
    elif overbought_count == len(result):
        print("  ✗ FAIL: All rows marked as overbought extreme (logic error)")
        return False
    else:
        print("  ✓ Reasonable overbought extreme count")
    print()
    
    # Check momentum_extreme_state values
    print("Step 7: Validate momentum_extreme_state")
    state_counts = result["momentum_extreme_state"].value_counts()
    print("  State distribution:")
    for state, count in state_counts.items():
        pct = (count / len(result)) * 100
        print(f"    {state}: {count} ({pct:.1f}%)")
    
    if "NONE" not in state_counts:
        print("  ✗ FAIL: 'NONE' state never appears (logic error)")
        return False
    print("  ✓ momentum_extreme_state includes 'NONE'")
    print()
    
    # Print last 10 rows of Cap Finder columns
    print("Step 8: Sample output (last 10 rows, Cap Finder columns only)")
    print("-" * 70)
    cap_cols = ["cap_rsi", "cap_below", "cap_above", "cap_vol_spike", 
                "oversoldExtreme", "overboughtExtreme", "momentum_extreme_state"]
    print(result[cap_cols].tail(10).to_string())
    print("-" * 70)
    print()
    
    # Final verdict
    print("=" * 70)
    print("✓ TEST PASSED")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  - Original outputs: {len(original_outputs)} columns ✓")
    print(f"  - Cap Finder outputs: {len(capfinder_outputs)} columns ✓")
    print(f"  - Total outputs: {len(original_outputs) + len(capfinder_outputs)} columns")
    print(f"  - oversoldExtreme: {oversold_count} occurrences")
    print(f"  - overboughtExtreme: {overbought_count} occurrences")
    print(f"  - momentum_extreme_state: {len(state_counts)} unique states")
    print()
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
