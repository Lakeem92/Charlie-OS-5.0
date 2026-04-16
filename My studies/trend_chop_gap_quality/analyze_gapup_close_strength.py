#!/usr/bin/env python3
"""
Analysis 2 — Gap-Up Close Strength

Identifies gap-up days (gap >= 1%), bins them by gap size, and computes
the probability of a strong close vs weak close, plus same-day, next-day,
and 2-day forward returns per bin.

All thresholds from config.yaml (LOCKED).
"""
from __future__ import annotations

import sys
import yaml
import argparse
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

STUDY_DIR = Path(__file__).resolve().parent
ROOT_DIR = STUDY_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "tools" / "studies"))

from utils import atr, clv, range_multiple, gap_pct, assign_gap_bin, safe_divide
from run_id import resolve_output_dirs


def load_config() -> dict:
    with open(STUDY_DIR / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def analyze(tickers: list[str] | None = None,
            start: str | None = None,
            end: str | None = None) -> None:
    cfg = load_config()
    # Use run archive output dirs if env var is set, else fallback to default
    data_dir, tables_dir, charts_dir, summary_dir = resolve_output_dirs(STUDY_DIR)
    for d in [tables_dir, charts_dir, summary_dir]:
        d.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(data_dir.glob("*_1D.csv"))
    if not csv_files:
        print("No daily CSV files found in outputs/data/. Run collect_data.py first.")
        return

    gap_bins = cfg.get("gap_bins", [0.01, 0.03, 0.05, 0.08, 0.12, 0.20])
    all_gap_rows: list[dict] = []
    ticker_tables: list[pd.DataFrame] = []

    for csv_path in csv_files:
        ticker = csv_path.stem.replace("_1D", "")
        if tickers and ticker not in tickers:
            continue

        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        df.columns = [c.lower() for c in df.columns]

        if "close" not in df.columns or len(df) < cfg["atr_length"] + 2:
            continue

        if start:
            df = df[df.index >= start]
        if end:
            df = df[df.index <= end]

        df = df.sort_index()
        df["atr_val"] = atr(df["high"], df["low"], df["close"], cfg["atr_length"])
        df["clv_val"] = clv(df["high"], df["low"], df["close"])
        df["range_mult"] = range_multiple(df["high"], df["low"], df["atr_val"])
        df["prev_close"] = df["close"].shift(1)
        df["gap_pct"] = gap_pct(df["open"], df["prev_close"])

        # Forward returns
        df["same_day_ret"] = df["close"] / df["prev_close"] - 1
        df["next_close"] = df["close"].shift(-1)
        df["next_day_ret"] = df["next_close"] / df["close"] - 1
        df["close_t2"] = df["close"].shift(-2)
        df["two_day_ret"] = df["close_t2"] / df["close"] - 1

        # Filter to gap-up days (gap >= 1%)
        gap_df = df[df["gap_pct"] >= gap_bins[0]].copy()
        if gap_df.empty:
            continue

        gap_df["gap_bin"] = gap_df["gap_pct"].apply(
            lambda x: assign_gap_bin(x, gap_bins)
        )
        gap_df = gap_df[gap_df["gap_bin"] != ""]

        # Classify close strength
        gap_df["close_strong"] = (
            (gap_df["clv_val"] >= cfg["close_strong_clv_min"])
            & (gap_df["range_mult"] >= cfg["close_strong_range_atr_min"])
        )
        gap_df["close_weak"] = (
            (gap_df["clv_val"] <= cfg["close_weak_clv_max"])
            | (gap_df["close"] < gap_df["open"])
        )

        # Per-ticker, per-bin stats
        for gap_bin, grp in gap_df.groupby("gap_bin"):
            n = len(grp)
            row = {
                "ticker": ticker,
                "gap_bin": gap_bin,
                "n": n,
                "p_close_strong": safe_divide(grp["close_strong"].sum(), n),
                "p_close_weak": safe_divide(grp["close_weak"].sum(), n),
                "avg_same_day_ret": grp["same_day_ret"].mean(),
                "avg_next_day_ret": grp["next_day_ret"].mean(),
                "avg_two_day_ret": grp["two_day_ret"].mean(),
            }
            all_gap_rows.append(row)

    if not all_gap_rows:
        print("No gap-up days found in any ticker data.")
        return

    detail_df = pd.DataFrame(all_gap_rows)
    detail_df.to_csv(tables_dir / "gapup_stats_by_ticker.csv", index=False)
    print(f"Saved: gapup_stats_by_ticker.csv ({len(detail_df)} rows)")

    # ── Aggregate across tickers ─────────────────────────────
    agg_rows: list[dict] = []
    for gap_bin, grp in detail_df.groupby("gap_bin"):
        total_n = grp["n"].sum()
        # Weighted averages by n
        agg_rows.append({
            "gap_bin": gap_bin,
            "n": int(total_n),
            "p_close_strong": safe_divide(
                (grp["p_close_strong"] * grp["n"]).sum(), total_n
            ),
            "p_close_weak": safe_divide(
                (grp["p_close_weak"] * grp["n"]).sum(), total_n
            ),
            "avg_same_day_ret": safe_divide(
                (grp["avg_same_day_ret"] * grp["n"]).sum(), total_n
            ),
            "avg_next_day_ret": safe_divide(
                (grp["avg_next_day_ret"] * grp["n"]).sum(), total_n
            ),
            "avg_two_day_ret": safe_divide(
                (grp["avg_two_day_ret"] * grp["n"]).sum(), total_n
            ),
        })

    agg_df = pd.DataFrame(agg_rows)
    # Sort bins in order
    bin_order = []
    for i in range(len(gap_bins) - 1):
        lo = int(round(gap_bins[i] * 100))
        hi = int(round(gap_bins[i+1] * 100))
        bin_order.append(f"{lo}-{hi}%")
    bin_order.append(f"{int(round(gap_bins[-1]*100))}%+")

    agg_df["_sort"] = agg_df["gap_bin"].apply(
        lambda x: bin_order.index(x) if x in bin_order else 999
    )
    agg_df = agg_df.sort_values("_sort").drop(columns=["_sort"])
    agg_df.to_csv(tables_dir / "gapup_stats_aggregate.csv", index=False)
    print(f"Saved: gapup_stats_aggregate.csv ({len(agg_df)} bins)")

    # ── Chart: P(CloseStrong) by gap bin ─────────────────────
    fig, ax = plt.subplots(figsize=(9, 5))
    x_labels = agg_df["gap_bin"].tolist()
    y_vals = (agg_df["p_close_strong"] * 100).tolist()
    bars = ax.bar(x_labels, y_vals, color="#3498db", edgecolor="black", linewidth=0.5)
    ax.set_ylabel("P(CloseStrong) %")
    ax.set_xlabel("Gap-Up Bin")
    ax.set_title("P(Close Strong) by Gap-Up Size — Aggregate")
    ax.set_ylim(0, max(y_vals) * 1.3 if y_vals and max(y_vals) > 0 else 100)
    for bar, v in zip(bars, y_vals):
        ax.text(bar.get_x() + bar.get_width()/2, v + 0.5,
                f"{v:.1f}%", ha="center", fontsize=9)
    plt.tight_layout()
    chart_path = charts_dir / "gapup_close_strong_by_bin.png"
    fig.savefig(chart_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {chart_path.name}")

    # ── Markdown summary ─────────────────────────────────────
    md = [
        "# Gap-Up Close Strength Summary",
        "",
        f"**Run date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Gap threshold:** >= {gap_bins[0]*100:.0f}%",
        "",
        "## Aggregate by Gap Bin",
        "",
        "| Bin | N | P(CloseStrong) | P(CloseWeak) | Avg Same-Day | Avg Next-Day | Avg 2-Day |",
        "|-----|---|----------------|--------------|--------------|--------------|-----------|",
    ]
    for _, row in agg_df.iterrows():
        md.append(
            f"| {row['gap_bin']} | {int(row['n'])} | "
            f"{row['p_close_strong']*100:.1f}% | {row['p_close_weak']*100:.1f}% | "
            f"{row['avg_same_day_ret']*100:.2f}% | {row['avg_next_day_ret']*100:.2f}% | "
            f"{row['avg_two_day_ret']*100:.2f}% |"
        )
    md.extend([
        "",
        "## Definitions (Locked)",
        f"- CloseStrong: CLV >= {cfg['close_strong_clv_min']} AND Range/ATR >= {cfg['close_strong_range_atr_min']}",
        f"- CloseWeak: CLV <= {cfg['close_weak_clv_max']} OR close < open",
        f"- Gap bins: {gap_bins}",
        "",
        "*No trade advice. Descriptive statistics only.*",
    ])
    (summary_dir / "gapup_summary.md").write_text("\n".join(md), encoding="utf-8")
    print("Saved: gapup_summary.md")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    args = parser.parse_args()
    analyze(tickers=args.tickers, start=args.start, end=args.end)


if __name__ == "__main__":
    main()
