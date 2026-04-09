"""
Step 7: Robustness Variants
Tests whether the edge (if any) is robust across parameter changes.
Prevents overfitting to one specific configuration.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from config import (
    TICKER, DATA_PROC, TABLES, CHARTS,
    GAP_BANDS, RS_THRESHOLDS, SLOPE_STATES
)


def calculate_variant_stats(returns: pd.Series) -> dict:
    """Calculate key statistics for a variant."""
    valid = returns.dropna()
    
    if len(valid) == 0:
        return {
            "N": 0,
            "win_rate": np.nan,
            "mean_return": np.nan,
            "median_return": np.nan,
            "t_stat": np.nan,
            "p_value": np.nan,
            "confidence": "NO DATA"
        }
    
    n = len(valid)
    win_rate = (valid > 0).mean() * 100
    mean_ret = valid.mean()
    median_ret = valid.median()
    
    # T-test
    if n >= 2:
        t_stat, p_value = stats.ttest_1samp(valid, 0)
    else:
        t_stat, p_value = np.nan, np.nan
    
    # Confidence assessment
    if n < 10:
        confidence = "LOW (N<10)"
    elif n < 30:
        confidence = "MEDIUM"
    else:
        confidence = "HIGH"
    
    return {
        "N": n,
        "win_rate": win_rate,
        "mean_return": mean_ret,
        "median_return": median_ret,
        "t_stat": t_stat,
        "p_value": p_value,
        "confidence": confidence
    }


def main():
    print("=" * 60)
    print("STEP 7: ROBUSTNESS VARIANTS")
    print("=" * 60)
    print(f"Target Ticker: {TICKER}")
    print(f"Variants: {len(GAP_BANDS)} gap bands × {len(RS_THRESHOLDS)} RS thresholds × {len(SLOPE_STATES)} slope states")
    print(f"Total combinations: {len(GAP_BANDS) * len(RS_THRESHOLDS) * len(SLOPE_STATES)}")
    print()
    
    # Ensure output directories exist
    TABLES.mkdir(parents=True, exist_ok=True)
    CHARTS.mkdir(parents=True, exist_ok=True)
    
    # Load all variants data
    variants_path = DATA_PROC / f"{TICKER}_all_variants.csv"
    
    if not variants_path.exists():
        print(f"❌ Variants data not found: {variants_path}")
        print("   Run Step 5 first to generate variant events.")
        return
    
    print(f"📊 Loading variant data...")
    df = pd.read_csv(variants_path, parse_dates=["date"])
    print(f"  Total variant events: {len(df)}")
    
    if len(df) == 0:
        print("\n⚠️ No variant events to analyze.")
        return
    
    # Build robustness matrix
    print(f"\n📊 Building robustness matrix...")
    
    results = []
    
    for (gap_min, gap_max, gap_name) in GAP_BANDS:
        for rs_thresh in RS_THRESHOLDS:
            for slope_name in SLOPE_STATES.keys():
                # Filter to this variant
                mask = (
                    (df["gap_band_variant"] == gap_name) &
                    (df["rs_threshold_variant"] == rs_thresh) &
                    (df["slope_variant"] == slope_name)
                )
                subset = df[mask]
                
                # Calculate stats
                var_stats = calculate_variant_stats(subset["open_to_close"])
                var_stats["gap_band"] = gap_name
                var_stats["gap_min"] = gap_min
                var_stats["gap_max"] = gap_max
                var_stats["rs_threshold"] = rs_thresh
                var_stats["slope_state"] = slope_name
                
                results.append(var_stats)
    
    df_matrix = pd.DataFrame(results)
    
    # Save matrix
    matrix_path = TABLES / f"{TICKER}_robustness_matrix.csv"
    df_matrix.to_csv(matrix_path, index=False)
    print(f"  💾 Robustness matrix saved to {matrix_path}")
    
    # Print summary
    print(f"\n📊 Robustness Summary:")
    print("-" * 60)
    
    # Best/worst variants
    valid_results = df_matrix[df_matrix["N"] >= 1].copy()
    
    if len(valid_results) == 0:
        print("  No variants with events found.")
    else:
        # Sort by win rate (for variants with N >= 10)
        high_conf = valid_results[valid_results["N"] >= 10]
        
        if len(high_conf) > 0:
            best = high_conf.loc[high_conf["win_rate"].idxmax()]
            worst = high_conf.loc[high_conf["win_rate"].idxmin()]
            
            print(f"\n  BEST variant (N≥10):")
            print(f"    Gap: {best['gap_band']}, RS≤{best['rs_threshold']}, Slope: {best['slope_state']}")
            print(f"    N={best['N']}, Win Rate={best['win_rate']:.1f}%, Mean={best['mean_return']:.2f}%")
            
            print(f"\n  WORST variant (N≥10):")
            print(f"    Gap: {worst['gap_band']}, RS≤{worst['rs_threshold']}, Slope: {worst['slope_state']}")
            print(f"    N={worst['N']}, Win Rate={worst['win_rate']:.1f}%, Mean={worst['mean_return']:.2f}%")
        
        # Rising slope summary
        rising = valid_results[valid_results["slope_state"] == "RISING"]
        if len(rising) > 0:
            print(f"\n  RISING slope variants: {len(rising)}")
            print(f"    Total events: {rising['N'].sum()}")
            # Weighted average win rate
            total_n = rising["N"].sum()
            if total_n > 0:
                weighted_wr = (rising["win_rate"] * rising["N"]).sum() / total_n
                print(f"    Weighted Win Rate: {weighted_wr:.1f}%")
    
    # Create heatmaps
    print(f"\n📊 Generating heatmap visualizations...")
    
    try:
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        for idx, slope_name in enumerate(SLOPE_STATES.keys()):
            ax = axes[idx]
            
            # Filter to this slope state
            subset = df_matrix[df_matrix["slope_state"] == slope_name].copy()
            
            if len(subset) == 0:
                ax.text(0.5, 0.5, "No Data", ha="center", va="center", fontsize=12)
                ax.set_title(f"Slope: {slope_name}")
                continue
            
            # Pivot for heatmap
            # X-axis: gap bands, Y-axis: RS thresholds
            pivot = subset.pivot(index="rs_threshold", columns="gap_band", values="win_rate")
            pivot_n = subset.pivot(index="rs_threshold", columns="gap_band", values="N")
            
            # Reorder columns by gap band order
            band_order = [name for (_, _, name) in GAP_BANDS]
            pivot = pivot[[c for c in band_order if c in pivot.columns]]
            pivot_n = pivot_n[[c for c in band_order if c in pivot_n.columns]]
            
            # Create annotation with N values
            annot = pivot_n.fillna(0).astype(int).astype(str)
            annot = "N=" + annot
            
            # Mask low-N cells
            mask = pivot_n < 10
            
            # Plot heatmap
            sns.heatmap(
                pivot,
                ax=ax,
                cmap="RdYlGn",
                center=50,
                vmin=0,
                vmax=100,
                annot=annot,
                fmt="",
                mask=mask,
                cbar=idx == 2,  # Only show colorbar on last plot
                cbar_kws={"label": "Win Rate %"} if idx == 2 else {}
            )
            
            ax.set_title(f"Slope: {slope_name}")
            ax.set_xlabel("Gap Band")
            ax.set_ylabel("RS(Z) Threshold")
        
        plt.tight_layout()
        
        heatmap_path = CHARTS / f"{TICKER}_robustness_heatmap.png"
        plt.savefig(heatmap_path, dpi=150, bbox_inches="tight")
        plt.close()
        
        print(f"  💾 Heatmap saved to {heatmap_path}")
    
    except Exception as e:
        print(f"  ⚠️ Could not generate heatmap: {e}")
    
    # Significance summary
    print(f"\n📊 Statistical Significance Summary:")
    print("-" * 60)
    
    sig_variants = df_matrix[(df_matrix["p_value"] < 0.05) & (df_matrix["N"] >= 10)]
    print(f"  Variants with p < 0.05 and N ≥ 10: {len(sig_variants)}")
    
    if len(sig_variants) > 0:
        print(f"\n  Significant variants:")
        for _, row in sig_variants.iterrows():
            direction = "↑" if row["mean_return"] > 0 else "↓"
            print(f"    {row['gap_band']} | RS≤{row['rs_threshold']} | {row['slope_state']}: "
                  f"N={row['N']}, WR={row['win_rate']:.0f}%, Mean={row['mean_return']:+.2f}% {direction}")
    
    # Bonferroni warning
    n_tests = len(df_matrix)
    bonferroni_thresh = 0.05 / n_tests
    print(f"\n  ⚠️ Multiple comparison warning:")
    print(f"     {n_tests} variants tested")
    print(f"     Bonferroni-corrected threshold: p < {bonferroni_thresh:.4f}")
    
    bonf_sig = df_matrix[(df_matrix["p_value"] < bonferroni_thresh) & (df_matrix["N"] >= 10)]
    print(f"     Variants surviving Bonferroni: {len(bonf_sig)}")
    
    print()
    print("=" * 60)
    print("ROBUSTNESS ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
