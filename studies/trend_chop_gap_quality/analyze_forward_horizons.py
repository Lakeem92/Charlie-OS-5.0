#!/usr/bin/env python3
"""
Analysis 4 -- Forward Horizon Returns

For event days (e.g., gap-up >= threshold), compute forward close-to-close
returns at each requested horizon (D1, D2, D5, ..., D10) and window stats.

Event filtering comes from the run_spec.yaml (event.type, gap_up_min, etc.).
Horizons and metrics also come from the spec.

All thresholds from config.yaml (LOCKED).  No trade advice.
"""
from __future__ import annotations

import os
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

from utils import atr, gap_pct, assign_gap_bin, safe_divide
from run_id import resolve_output_dirs, get_run_output_dir


def load_config() -> dict:
    with open(STUDY_DIR / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_spec() -> dict | None:
    """Load run_spec.yaml if it exists (check run folder first, then fallback)."""
    # Check run folder first (if env var is set)
    run_output_dir = get_run_output_dir()
    if run_output_dir:
        spec_path = run_output_dir / "summary" / "run_spec.yaml"
        if spec_path.exists():
            with open(spec_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
    # Fallback to default location
    spec_path = STUDY_DIR / "outputs" / "summary" / "run_spec.yaml"
    if spec_path.exists():
        with open(spec_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return None


def _identify_event_days(df: pd.DataFrame, event: dict,
                         cfg: dict) -> pd.DataFrame:
    """Filter DataFrame to event days based on spec event config."""
    df = df.copy().sort_index()
    event_type = event.get("type")

    if event_type == "gap_up":
        df["prev_close"] = df["close"].shift(1)
        df["gap_pct_val"] = gap_pct(df["open"], df["prev_close"])
        df = df.dropna(subset=["gap_pct_val"])

        gap_min = event.get("gap_up_min")
        gap_bin = event.get("gap_bin_label")

        if gap_bin:
            # Filter to specific bin
            gap_bins_cfg = cfg.get("gap_bins", [0.01, 0.03, 0.05, 0.08, 0.12, 0.20])
            df["gap_bin"] = df["gap_pct_val"].apply(
                lambda x: assign_gap_bin(x, gap_bins_cfg)
            )
            df = df[df["gap_bin"] == gap_bin]
        elif gap_min is not None:
            df = df[df["gap_pct_val"] >= gap_min]
        else:
            # Default: gap >= 1%
            df = df[df["gap_pct_val"] >= 0.01]
    else:
        # No event filter -- use all days (e.g. trend/chop analysis)
        pass

    return df


def analyze(tickers: list[str] | None = None,
            start: str | None = None,
            end: str | None = None,
            horizons: list[int] | None = None,
            window: dict | None = None,
            metrics: list[str] | None = None,
            event: dict | None = None) -> None:
    cfg = load_config()
    spec = load_spec()

    # Use run archive output dirs if env var is set, else fallback to default
    data_dir, tables_dir, charts_dir, summary_dir = resolve_output_dirs(STUDY_DIR)
    for d in [tables_dir, charts_dir, summary_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Resolve parameters from spec if not passed directly
    if spec:
        if horizons is None:
            horizons = spec.get("forward_horizons", {}).get("horizons", [1, 2])
        if window is None:
            window = spec.get("forward_horizons", {}).get("window")
        if metrics is None:
            metrics = spec.get("forward_horizons", {}).get("metrics",
                        ["win_rate_positive", "avg_return", "median_return"])
        if event is None:
            event = spec.get("event", {})
        if tickers is None:
            tickers = spec.get("tickers") or None

    # Defaults
    if not horizons:
        horizons = [1, 2]
    if not metrics:
        metrics = ["win_rate_positive", "avg_return", "median_return"]
    if not event:
        event = {"type": None, "gap_up_min": None, "gap_bin_label": None}

    csv_files = sorted(data_dir.glob("*_1D.csv"))
    if not csv_files:
        print("No daily CSV files found. Run collect_data.py first.")
        return

    max_horizon = max(horizons) if horizons else 2

    all_ticker_rows: list[dict] = []
    all_event_returns: list[pd.DataFrame] = []

    for csv_path in csv_files:
        ticker = csv_path.stem.replace("_1D", "")
        if tickers and ticker not in tickers:
            continue

        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        df.columns = [c.lower() for c in df.columns]

        if "close" not in df.columns:
            continue

        if start:
            df = df[df.index >= start]
        if end:
            df = df[df.index <= end]

        df = df.sort_index()

        if len(df) < cfg.get("atr_length", 14) + max_horizon + 2:
            print(f"WARNING: {ticker} insufficient data, skipping forward horizons.")
            continue

        # Compute ATR for context
        df["atr_val"] = atr(df["high"], df["low"], df["close"], cfg.get("atr_length", 14))

        # Identify event days
        event_df = _identify_event_days(df, event, cfg)
        if event_df.empty:
            print(f"{ticker}: 0 event days found, skipping.")
            continue

        # Compute forward returns for each horizon
        for k in horizons:
            col = f"ret_D{k}"
            event_df[col] = event_df["close"].shift(-k) / event_df["close"] - 1

        # Drop rows where we can't compute all horizons
        ret_cols = [f"ret_D{k}" for k in horizons]
        valid = event_df.dropna(subset=ret_cols)

        if valid.empty:
            print(f"{ticker}: no valid forward-return rows after horizon lookforward.")
            continue

        # Per-ticker stats for each horizon
        ticker_row: dict = {"ticker": ticker, "event_days": len(valid)}
        for k in horizons:
            col = f"ret_D{k}"
            series = valid[col]
            if "win_rate_positive" in metrics:
                ticker_row[f"win_rate_D{k}"] = round(safe_divide((series > 0).sum(), len(series)), 4)
            if "avg_return" in metrics:
                ticker_row[f"avg_ret_D{k}"] = round(series.mean(), 6)
            if "median_return" in metrics:
                ticker_row[f"med_ret_D{k}"] = round(series.median(), 6)

        # Window stats (e.g. D5-D10)
        if window:
            w_start, w_end = window["start"], window["end"]
            w_cols = [f"ret_D{k}" for k in range(w_start, w_end + 1) if f"ret_D{k}" in valid.columns]
            if w_cols:
                # Per-event average return across the window, then stats across events
                per_event_avg = valid[w_cols].mean(axis=1)
                ticker_row[f"win_rate_D{w_start}_D{w_end}"] = round(
                    safe_divide((per_event_avg > 0).sum(), len(per_event_avg)), 4
                )
                ticker_row[f"avg_ret_D{w_start}_D{w_end}"] = round(per_event_avg.mean(), 6)
                ticker_row[f"med_ret_D{w_start}_D{w_end}"] = round(per_event_avg.median(), 6)

        all_ticker_rows.append(ticker_row)
        valid_out = valid.copy()
        valid_out["ticker"] = ticker
        all_event_returns.append(valid_out)

    if not all_ticker_rows:
        print("No event days found across any ticker.")
        return

    # Per-ticker table
    ticker_df = pd.DataFrame(all_ticker_rows)
    ticker_df.to_csv(tables_dir / "forward_horizons_by_ticker.csv", index=False)
    print(f"Saved: forward_horizons_by_ticker.csv ({len(ticker_df)} tickers)")

    # Aggregate
    combined = pd.concat(all_event_returns, ignore_index=True)
    total_events = len(combined)
    agg: dict = {"total_event_days": total_events}

    ret_cols_existing = [c for c in combined.columns if c.startswith("ret_D")]
    for k in horizons:
        col = f"ret_D{k}"
        if col not in combined.columns:
            continue
        s = combined[col].dropna()
        if "win_rate_positive" in metrics:
            agg[f"win_rate_D{k}"] = round(safe_divide((s > 0).sum(), len(s)), 4)
        if "avg_return" in metrics:
            agg[f"avg_ret_D{k}"] = round(s.mean(), 6)
        if "median_return" in metrics:
            agg[f"med_ret_D{k}"] = round(s.median(), 6)

    if window:
        w_start, w_end = window["start"], window["end"]
        w_cols = [f"ret_D{k}" for k in range(w_start, w_end + 1) if f"ret_D{k}" in combined.columns]
        if w_cols:
            per_event_avg = combined[w_cols].mean(axis=1)
            agg[f"win_rate_D{w_start}_D{w_end}"] = round(
                safe_divide((per_event_avg > 0).sum(), len(per_event_avg)), 4
            )
            agg[f"avg_ret_D{w_start}_D{w_end}"] = round(per_event_avg.mean(), 6)
            agg[f"med_ret_D{w_start}_D{w_end}"] = round(per_event_avg.median(), 6)

    agg_df = pd.DataFrame([agg])
    agg_df.to_csv(tables_dir / "forward_horizons_aggregate.csv", index=False)
    print("Saved: forward_horizons_aggregate.csv")

    # ── Chart: win rate by horizon ───────────────────────────
    wr_cols = sorted([c for c in agg if c.startswith("win_rate_D") and "_D" not in c[10:]])
    if wr_cols:
        fig, ax = plt.subplots(figsize=(8, 5))
        x_labels = [c.replace("win_rate_", "") for c in wr_cols]
        y_vals = [agg[c] * 100 for c in wr_cols]
        bars = ax.bar(x_labels, y_vals, color="#2980b9", edgecolor="black", linewidth=0.5)
        ax.axhline(50, color="gray", linestyle="--", linewidth=0.8, label="50%")
        ax.set_ylabel("Win Rate %")
        ax.set_xlabel("Horizon")
        ev_label = ""
        if event.get("type") == "gap_up":
            if event.get("gap_bin_label"):
                ev_label = f" (gap-up {event['gap_bin_label']})"
            elif event.get("gap_up_min"):
                ev_label = f" (gap-up >= {event['gap_up_min']*100:.0f}%)"
        ax.set_title(f"Forward Win Rate by Horizon{ev_label} -- Aggregate")
        ax.set_ylim(0, max(max(y_vals) * 1.2, 55) if y_vals else 100)
        for bar, v in zip(bars, y_vals):
            ax.text(bar.get_x() + bar.get_width()/2, v + 0.5,
                    f"{v:.1f}%", ha="center", fontsize=9)
        ax.legend()
        plt.tight_layout()
        fig.savefig(charts_dir / "forward_horizons_win_rate.png", dpi=150)
        plt.close(fig)
        print("Saved: forward_horizons_win_rate.png")

    # ── Markdown summary ─────────────────────────────────────
    md = [
        "# Forward Horizon Returns Summary",
        "",
        f"**Run date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    ]
    if event.get("type") == "gap_up":
        if event.get("gap_bin_label"):
            md.append(f"**Event filter:** gap-up bin {event['gap_bin_label']}")
        elif event.get("gap_up_min"):
            md.append(f"**Event filter:** gap-up >= {event['gap_up_min']*100:.0f}%")
    md.append(f"**Horizons:** {horizons}")
    if window:
        md.append(f"**Window:** D{window['start']}-D{window['end']}")
    md.append(f"**Metrics:** {', '.join(metrics)}")
    md.append(f"**Total event days (aggregate):** {total_events}")
    md.append("")

    md.append("## Aggregate Results")
    md.append("")
    md.append("| Horizon | Win Rate | Avg Return | Median Return |")
    md.append("|---------|----------|------------|---------------|")
    for k in horizons:
        wr = agg.get(f"win_rate_D{k}", "")
        ar = agg.get(f"avg_ret_D{k}", "")
        mr = agg.get(f"med_ret_D{k}", "")
        wr_str = f"{wr*100:.1f}%" if isinstance(wr, (int, float)) else "N/A"
        ar_str = f"{ar*100:.2f}%" if isinstance(ar, (int, float)) else "N/A"
        mr_str = f"{mr*100:.2f}%" if isinstance(mr, (int, float)) else "N/A"
        md.append(f"| D{k} | {wr_str} | {ar_str} | {mr_str} |")

    if window:
        w_start, w_end = window["start"], window["end"]
        wr_w = agg.get(f"win_rate_D{w_start}_D{w_end}", "")
        ar_w = agg.get(f"avg_ret_D{w_start}_D{w_end}", "")
        mr_w = agg.get(f"med_ret_D{w_start}_D{w_end}", "")
        md.append(f"| D{w_start}-D{w_end} (window avg) | "
                  f"{wr_w*100:.1f}% | {ar_w*100:.2f}% | {mr_w*100:.2f}% |"
                  if isinstance(wr_w, (int, float)) else
                  f"| D{w_start}-D{w_end} | N/A | N/A | N/A |")

    md.extend([
        "",
        "## Definitions",
        "- **Forward return D_k:** close[t+k] / close[t] - 1",
        "- **Win rate:** fraction of events where forward return > 0",
        "- **Window avg:** for each event, average of returns across the window days; then compute win rate / avg / median across events",
        "",
        "## Per Ticker",
    ])
    for row in all_ticker_rows:
        md.append(f"- **{row['ticker']}**: {row['event_days']} events")

    md.append("")
    md.append("*No trade advice. Descriptive statistics only.*")

    (summary_dir / "forward_horizons_summary.md").write_text(
        "\n".join(md), encoding="utf-8"
    )
    print("Saved: forward_horizons_summary.md")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    args = parser.parse_args()
    analyze(tickers=args.tickers, start=args.start, end=args.end)


if __name__ == "__main__":
    main()
