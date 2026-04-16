"""
Step 8: Generate Report
Creates a human-readable summary report of all findings.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime
from config import (
    TICKER, BENCHMARK, DATA_PROC, TABLES, REPORTS, CHARTS,
    GAP_DOWN_MIN, GAP_DOWN_MAX, RS_OVERSOLD_THRESHOLD,
    START_DATE, END_DATE
)


def format_pct(val, decimals=2):
    """Format a percentage value."""
    if pd.isna(val):
        return "N/A"
    return f"{val:.{decimals}f}%"


def format_float(val, decimals=2):
    """Format a float value."""
    if pd.isna(val):
        return "N/A"
    return f"{val:.{decimals}f}"


def interpret_pvalue(p):
    """Interpret a p-value for reporting."""
    if pd.isna(p):
        return "Cannot determine"
    if p < 0.01:
        return f"Highly significant (p={p:.4f})"
    elif p < 0.05:
        return f"Significant (p={p:.4f})"
    elif p < 0.10:
        return f"Marginally significant (p={p:.4f})"
    else:
        return f"Not significant (p={p:.4f})"


def assess_verdict(summary_stats, baseline_comp, robustness_matrix):
    """Generate an overall verdict based on the data."""
    
    # Check if we have enough data
    if summary_stats is None or len(summary_stats) == 0:
        return "INSUFFICIENT DATA", "Not enough confluence events to analyze."
    
    n = summary_stats.iloc[0]["N"]
    if n < 10:
        return "INSUFFICIENT DATA", f"Only {n} events found. Need at least 10 for reliable conclusions."
    
    win_rate = summary_stats.iloc[0]["win_rate"]
    mean_ret = summary_stats.iloc[0]["mean_return"]
    p_value = summary_stats.iloc[0]["p_value"]
    
    # Check statistical significance
    is_significant = pd.notna(p_value) and p_value < 0.05
    
    # Check robustness
    if robustness_matrix is not None:
        high_conf = robustness_matrix[(robustness_matrix["N"] >= 10) & 
                                       (robustness_matrix["slope_state"] == "RISING")]
        if len(high_conf) > 0:
            robust_win_rates = high_conf["win_rate"].dropna()
            is_robust = (robust_win_rates > 50).mean() > 0.5  # >50% of variants profitable
        else:
            is_robust = False
    else:
        is_robust = False
    
    # Determine verdict
    if is_significant and is_robust and win_rate > 55 and mean_ret > 0:
        verdict = "TRADEABLE EDGE"
        reason = f"Win rate {win_rate:.1f}%, mean return {mean_ret:+.2f}%, statistically significant, and robust across variants."
    elif is_significant and win_rate > 50 and mean_ret > 0:
        verdict = "DEVELOPING"
        reason = f"Promising signal (WR={win_rate:.1f}%, mean={mean_ret:+.2f}%) but needs more data or robustness testing."
    elif n >= 30 and not is_significant:
        verdict = "NO EDGE"
        reason = f"Sufficient sample size ({n}) but results are not statistically significant."
    elif n < 30:
        verdict = "DEVELOPING"
        reason = f"Sample size ({n}) is too small for definitive conclusions. Continue collecting data."
    else:
        verdict = "NO EDGE"
        reason = f"Results do not support a tradeable edge."
    
    return verdict, reason


def main():
    print("=" * 60)
    print("STEP 8: REPORT GENERATION")
    print("=" * 60)
    print(f"Target Ticker: {TICKER}")
    print()
    
    # Ensure output directory exists
    REPORTS.mkdir(parents=True, exist_ok=True)
    
    # Load all available data
    summary_path = TABLES / f"{TICKER}_summary_stats.csv"
    primary_path = TABLES / f"{TICKER}_primary_results.csv"
    baseline_path = TABLES / f"{TICKER}_baseline_comparison.csv"
    breakdown_path = TABLES / f"{TICKER}_conditional_breakdowns.csv"
    robustness_path = TABLES / f"{TICKER}_robustness_matrix.csv"
    heatmap_path = CHARTS / f"{TICKER}_robustness_heatmap.png"
    
    summary_stats = pd.read_csv(summary_path) if summary_path.exists() else None
    primary_results = pd.read_csv(primary_path) if primary_path.exists() else None
    baseline_comp = pd.read_csv(baseline_path) if baseline_path.exists() else None
    breakdowns = pd.read_csv(breakdown_path) if breakdown_path.exists() else None
    robustness = pd.read_csv(robustness_path) if robustness_path.exists() else None
    
    # Generate verdict
    verdict, verdict_reason = assess_verdict(summary_stats, baseline_comp, robustness)
    
    # Build report
    report_lines = []
    
    # Header
    report_lines.append(f"# Gap Bias + TSL3 + RS(Z) Confluence Study: {TICKER}")
    report_lines.append("")
    report_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report_lines.append(f"**Data Range:** {START_DATE} to {END_DATE or 'present'}")
    report_lines.append("")
    
    # Study Question
    report_lines.append("## Study Question")
    report_lines.append("")
    report_lines.append(f"When **{TICKER}** gaps down **{GAP_DOWN_MIN}% to {GAP_DOWN_MAX}%** and the TSL3 indicator ")
    report_lines.append(f"slope is **RISING** at the open, does {TICKER} tend to close higher or lower — ")
    report_lines.append(f"especially when its daily RS(Z) vs {BENCHMARK} is **≤ {RS_OVERSOLD_THRESHOLD}** (oversold)?")
    report_lines.append("")
    
    # Key Findings
    report_lines.append("## Key Findings")
    report_lines.append("")
    
    if summary_stats is not None and len(summary_stats) > 0:
        otc = summary_stats.iloc[0]
        report_lines.append(f"- **Events Found:** {otc['N']}")
        report_lines.append(f"- **Win Rate (close > open):** {format_pct(otc['win_rate'], 1)}")
        report_lines.append(f"- **Mean Return:** {format_pct(otc['mean_return'])}")
        report_lines.append(f"- **Statistical Significance:** {interpret_pvalue(otc['p_value'])}")
        
        if baseline_comp is not None and len(baseline_comp) > 0:
            bc = baseline_comp.iloc[0]
            diff = bc.get("event_mean", 0) - bc.get("baseline_mean", 0)
            report_lines.append(f"- **vs Baseline:** {format_pct(diff)} better than average day")
            sig = "Yes" if bc.get("significant_5pct", False) else "No"
            report_lines.append(f"- **Statistically Different from Random?** {sig}")
    else:
        report_lines.append("- No confluence events found matching the criteria.")
    
    report_lines.append("")
    report_lines.append(f"### Verdict: **{verdict}**")
    report_lines.append(f"_{verdict_reason}_")
    report_lines.append("")
    
    # Primary Setup Results
    report_lines.append("## Primary Setup Results")
    report_lines.append("")
    
    if primary_results is not None and len(primary_results) > 0:
        report_lines.append("| Date | Gap % | RS(Z) | Open | Close | Open→Close |")
        report_lines.append("|------|-------|-------|------|-------|------------|")
        
        for _, row in primary_results.head(20).iterrows():
            date_str = str(row.get("date", ""))[:10]
            gap = format_pct(row.get("gap_pct"), 2)
            rsz = format_float(row.get("rs_z_prior"), 2)
            open_p = format_float(row.get("open"), 2)
            close_p = format_float(row.get("close"), 2)
            otc = format_pct(row.get("open_to_close"), 2)
            report_lines.append(f"| {date_str} | {gap} | {rsz} | {open_p} | {close_p} | {otc} |")
        
        if len(primary_results) > 20:
            report_lines.append(f"| ... | ... | ... | ... | ... | ... |")
            report_lines.append(f"| *(showing 20 of {len(primary_results)} events)* |")
    else:
        report_lines.append("No primary events to display.")
    
    report_lines.append("")
    
    # Statistical Summary
    report_lines.append("## Statistical Summary")
    report_lines.append("")
    
    if summary_stats is not None and len(summary_stats) > 0:
        report_lines.append("| Metric | Open→Close | T+1 | T+2 | T+3 | T+5 |")
        report_lines.append("|--------|------------|-----|-----|-----|-----|")
        
        # Find stats for each return type
        metrics = ["N", "win_rate", "mean_return", "median_return", "t_stat", "p_value"]
        metric_labels = ["N", "Win Rate", "Mean Return", "Median Return", "t-statistic", "p-value"]
        
        for metric, label in zip(metrics, metric_labels):
            row_vals = []
            for col_label in ["Open→Close", "T+1", "T+2", "T+3", "T+5"]:
                match = summary_stats[summary_stats["label"] == col_label]
                if len(match) > 0:
                    val = match.iloc[0][metric]
                    if metric in ["win_rate", "mean_return", "median_return"]:
                        row_vals.append(format_pct(val, 1))
                    elif metric == "p_value":
                        row_vals.append(f"{val:.4f}" if pd.notna(val) else "N/A")
                    else:
                        row_vals.append(format_float(val, 2) if metric != "N" else str(int(val)) if pd.notna(val) else "N/A")
                else:
                    row_vals.append("-")
            
            report_lines.append(f"| {label} | " + " | ".join(row_vals) + " |")
    else:
        report_lines.append("No summary statistics available.")
    
    report_lines.append("")
    
    # Baseline Comparison
    report_lines.append("## Baseline Comparison")
    report_lines.append("")
    
    if baseline_comp is not None and len(baseline_comp) > 0:
        bc = baseline_comp.iloc[0]
        report_lines.append("| Measure | Confluence Events | All Trading Days |")
        report_lines.append("|---------|-------------------|------------------|")
        report_lines.append(f"| N | {int(bc.get('event_N', 0))} | {int(bc.get('baseline_N', 0))} |")
        report_lines.append(f"| Mean Return | {format_pct(bc.get('event_mean'))} | {format_pct(bc.get('baseline_mean'))} |")
        report_lines.append(f"| Std Dev | {format_pct(bc.get('event_std'))} | {format_pct(bc.get('baseline_std'))} |")
        report_lines.append("")
        report_lines.append(f"**t-statistic:** {format_float(bc.get('t_stat'))}")
        report_lines.append(f"**p-value:** {format_float(bc.get('p_value'), 4)}")
        sig = "✅ Yes" if bc.get("significant_5pct", False) else "❌ No"
        report_lines.append(f"**Significantly different at 5%?** {sig}")
    else:
        report_lines.append("No baseline comparison available.")
    
    report_lines.append("")
    
    # Conditional Analysis
    report_lines.append("## Conditional Analysis")
    report_lines.append("")
    
    if breakdowns is not None and len(breakdowns) > 0:
        # Group by breakdown type
        for bd_type in breakdowns["breakdown_type"].unique():
            type_label = bd_type.replace("_", " ").title()
            report_lines.append(f"### By {type_label}")
            report_lines.append("")
            report_lines.append("| Value | N | Win Rate | Mean Return |")
            report_lines.append("|-------|---|----------|-------------|")
            
            type_data = breakdowns[breakdowns["breakdown_type"] == bd_type]
            for _, row in type_data.iterrows():
                val = row["breakdown_value"]
                n = int(row["N"]) if pd.notna(row["N"]) else 0
                wr = format_pct(row["win_rate"], 0)
                mr = format_pct(row["mean_return"])
                report_lines.append(f"| {val} | {n} | {wr} | {mr} |")
            
            report_lines.append("")
    else:
        report_lines.append("No conditional breakdowns available.")
    
    report_lines.append("")
    
    # Robustness Check
    report_lines.append("## Robustness Check")
    report_lines.append("")
    
    if robustness is not None and len(robustness) > 0:
        report_lines.append(f"Tested **{len(robustness)}** parameter combinations ")
        report_lines.append(f"(gap bands × RS thresholds × slope states).")
        report_lines.append("")
        
        # Summary of RISING slope variants
        rising = robustness[robustness["slope_state"] == "RISING"]
        high_conf_rising = rising[rising["N"] >= 10]
        
        if len(high_conf_rising) > 0:
            profitable = (high_conf_rising["win_rate"] > 50).sum()
            report_lines.append(f"**RISING slope variants with N≥10:** {len(high_conf_rising)}")
            report_lines.append(f"**Profitable (WR>50%):** {profitable} ({profitable/len(high_conf_rising)*100:.0f}%)")
            
            best = high_conf_rising.loc[high_conf_rising["win_rate"].idxmax()]
            report_lines.append(f"\n**Best variant:** {best['gap_band']} gap, RS≤{best['rs_threshold']}, RISING")
            report_lines.append(f"  - N={int(best['N'])}, Win Rate={format_pct(best['win_rate'], 0)}, Mean={format_pct(best['mean_return'])}")
        else:
            report_lines.append("_No high-confidence RISING slope variants._")
        
        report_lines.append("")
        
        if heatmap_path.exists():
            report_lines.append(f"See heatmap: `{heatmap_path.relative_to(REPORTS.parent)}`")
            report_lines.append("")
    else:
        report_lines.append("No robustness analysis available.")
    
    report_lines.append("")
    
    # Confidence Assessment
    report_lines.append("## Confidence Assessment")
    report_lines.append("")
    
    n_events = summary_stats.iloc[0]["N"] if summary_stats is not None and len(summary_stats) > 0 else 0
    
    if n_events >= 30:
        sample_size = "✅ Adequate"
    elif n_events >= 10:
        sample_size = "⚠️ Marginal"
    else:
        sample_size = "❌ Insufficient"
    
    report_lines.append(f"- **Sample Size:** {n_events} events - {sample_size}")
    
    if summary_stats is not None and len(summary_stats) > 0:
        p = summary_stats.iloc[0]["p_value"]
        report_lines.append(f"- **Statistical Significance:** {interpret_pvalue(p)}")
    
    # Robustness assessment
    if robustness is not None:
        rising_hc = robustness[(robustness["slope_state"] == "RISING") & (robustness["N"] >= 10)]
        if len(rising_hc) > 0:
            prof_pct = (rising_hc["win_rate"] > 50).mean() * 100
            if prof_pct >= 70:
                rob_status = "✅ Strong (>70% of variants profitable)"
            elif prof_pct >= 50:
                rob_status = "⚠️ Moderate (50-70% of variants profitable)"
            else:
                rob_status = "❌ Weak (<50% of variants profitable)"
            report_lines.append(f"- **Robustness:** {rob_status}")
        else:
            report_lines.append("- **Robustness:** Cannot assess (insufficient high-N variants)")
    
    report_lines.append("")
    report_lines.append(f"### VERDICT: {verdict}")
    report_lines.append(f"_{verdict_reason}_")
    report_lines.append("")
    
    # Methodology reference
    report_lines.append("## Methodology")
    report_lines.append("")
    report_lines.append("See `docs/METHODOLOGY.md` for full calculation details.")
    report_lines.append("")
    
    # Assumptions & Limitations
    report_lines.append("## Assumptions & Limitations")
    report_lines.append("")
    report_lines.append("- TSL3 is a Python recreation; minor floating-point differences from ThinkorSwim are possible.")
    report_lines.append("- Intraday data limited to ~60 days via yfinance; daily analysis has full history.")
    report_lines.append("- RS(Z) uses prior day's close — no look-ahead bias.")
    report_lines.append("- Gap classification uses open vs prior close — pre-market prints not considered.")
    report_lines.append("- Multiple statistical tests inflate Type I error risk; interpret with caution.")
    report_lines.append("")
    
    # Write report
    report_path = REPORTS / f"{TICKER}_gap_tsl_rs_study.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    
    print(f"✅ Report generated: {report_path}")
    print()
    print("=" * 60)
    print("REPORT GENERATION COMPLETE")
    print("=" * 60)
    print(f"\n📄 Open the report at: {report_path}")


if __name__ == "__main__":
    main()
