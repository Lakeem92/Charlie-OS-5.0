#!/usr/bin/env python3
"""
Analysis 1 — Trend vs Chop Day Classification (Uptrend Regime Only)

Reads daily CSVs, computes ATR14 / SMA20 / SMA slope, filters to uptrend
days (method A), classifies each day as TREND_BULL / CHOP / NEUTRAL, and
writes per-ticker + aggregate tables plus a markdown summary.

All thresholds are loaded from config.yaml (LOCKED — do not tune).
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

from utils import atr, sma, clv, body_pct, range_multiple, safe_divide
from run_id import resolve_output_dirs


def load_config() -> dict:
    with open(STUDY_DIR / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def classify_days(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Add indicator columns and classify each row."""

    # Core indicators
    df = df.copy()
    df["atr"] = atr(df["high"], df["low"], df["close"], cfg["atr_length"])
    df["sma20"] = sma(df["close"], cfg["sma_length"])
    df["sma20_prev"] = df["sma20"].shift(cfg["sma_slope_lookback"])
    df["clv"] = clv(df["high"], df["low"], df["close"])
    df["body_pct"] = body_pct(df["open"], df["high"], df["low"], df["close"])
    df["range_mult"] = range_multiple(df["high"], df["low"], df["atr"])

    # Uptrend regime (method A)
    df["uptrend"] = (df["close"] > df["sma20"]) & (df["sma20"] > df["sma20_prev"])

    # Classify
    is_green = df["close"] > df["open"]
    trend_cond = (
        (df["clv"] >= cfg["trend_day_clv_min"])
        & (df["range_mult"] >= cfg["trend_day_range_atr_min"])
    )
    if cfg.get("trend_day_requires_green", True):
        trend_cond = trend_cond & is_green

    chop_cond = (
        (df["range_mult"] < cfg["chop_day_range_atr_max"])
        | (df["body_pct"] < cfg["chop_day_body_pct_max"])
    )

    df["day_type"] = "NEUTRAL"
    df.loc[trend_cond, "day_type"] = "TREND_BULL"
    df.loc[chop_cond, "day_type"] = "CHOP"
    # Trend takes priority over chop if both conditions met
    df.loc[trend_cond, "day_type"] = "TREND_BULL"

    return df


def analyze(tickers: list[str] | None = None,
            start: str | None = None,
            end: str | None = None) -> None:
    cfg = load_config()
    # Use run archive output dirs if env var is set, else fallback to default
    data_dir, tables_dir, charts_dir, summary_dir = resolve_output_dirs(STUDY_DIR)
    for d in [tables_dir, charts_dir, summary_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Discover tickers from available daily files
    csv_files = sorted(data_dir.glob("*_1D.csv"))
    if not csv_files:
        print("No daily CSV files found in outputs/data/. Run collect_data.py first.")
        return

    all_rows: list[pd.DataFrame] = []
    ticker_summaries: list[dict] = []

    for csv_path in csv_files:
        ticker = csv_path.stem.replace("_1D", "")
        if tickers and ticker not in tickers:
            continue

        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        # Ensure lowercase columns
        df.columns = [c.lower() for c in df.columns]

        if "close" not in df.columns:
            print(f"WARNING: {ticker} CSV missing 'close' column, skipping.")
            continue

        # Optional date filter
        if start:
            df = df[df.index >= start]
        if end:
            df = df[df.index <= end]

        if len(df) < cfg["sma_length"] + cfg["sma_slope_lookback"]:
            print(f"WARNING: {ticker} has insufficient data ({len(df)} rows), skipping.")
            continue

        df = classify_days(df, cfg)

        # Filter to uptrend days only
        uptrend_df = df[df["uptrend"]].copy()
        uptrend_df["ticker"] = ticker
        all_rows.append(uptrend_df)

        # Per-ticker summary
        n_up = len(uptrend_df)
        if n_up > 0:
            counts = uptrend_df["day_type"].value_counts()
            ticker_summaries.append({
                "ticker": ticker,
                "total_days": len(df),
                "uptrend_days": n_up,
                "trend_bull_n": int(counts.get("TREND_BULL", 0)),
                "chop_n": int(counts.get("CHOP", 0)),
                "neutral_n": int(counts.get("NEUTRAL", 0)),
                "trend_bull_pct": safe_divide(counts.get("TREND_BULL", 0), n_up) * 100,
                "chop_pct": safe_divide(counts.get("CHOP", 0), n_up) * 100,
                "neutral_pct": safe_divide(counts.get("NEUTRAL", 0), n_up) * 100,
            })
        else:
            ticker_summaries.append({
                "ticker": ticker,
                "total_days": len(df),
                "uptrend_days": 0,
                "trend_bull_n": 0, "chop_n": 0, "neutral_n": 0,
                "trend_bull_pct": 0, "chop_pct": 0, "neutral_pct": 0,
            })

    if not all_rows:
        print("No uptrend data found for any ticker.")
        return

    # Per-ticker table
    summary_df = pd.DataFrame(ticker_summaries)
    summary_df.to_csv(tables_dir / "trend_chop_by_ticker.csv", index=False)
    print(f"Saved: trend_chop_by_ticker.csv ({len(summary_df)} tickers)")

    # Aggregate table
    combined = pd.concat(all_rows, ignore_index=True)
    n_total = len(combined)
    agg_counts = combined["day_type"].value_counts()
    agg = {
        "uptrend_days": n_total,
        "trend_bull_n": int(agg_counts.get("TREND_BULL", 0)),
        "chop_n": int(agg_counts.get("CHOP", 0)),
        "neutral_n": int(agg_counts.get("NEUTRAL", 0)),
        "trend_bull_pct": safe_divide(agg_counts.get("TREND_BULL", 0), n_total) * 100,
        "chop_pct": safe_divide(agg_counts.get("CHOP", 0), n_total) * 100,
        "neutral_pct": safe_divide(agg_counts.get("NEUTRAL", 0), n_total) * 100,
    }
    agg_df = pd.DataFrame([agg])
    agg_df.to_csv(tables_dir / "trend_chop_aggregate.csv", index=False)
    print(f"Saved: trend_chop_aggregate.csv")

    # ── Chart ────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5))
    labels = ["TREND_BULL", "CHOP", "NEUTRAL"]
    vals = [agg.get("trend_bull_pct", 0), agg.get("chop_pct", 0), agg.get("neutral_pct", 0)]
    colors = ["#2ecc71", "#e74c3c", "#95a5a6"]
    ax.bar(labels, vals, color=colors, edgecolor="black", linewidth=0.5)
    ax.set_ylabel("% of Uptrend Days")
    ax.set_title("Trend vs Chop vs Neutral — Aggregate (Uptrend Regime)")
    ax.set_ylim(0, max(vals) * 1.25 if max(vals) > 0 else 100)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=10)
    plt.tight_layout()
    chart_path = charts_dir / "trend_chop_aggregate.png"
    fig.savefig(chart_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {chart_path.name}")

    # ── Markdown summary ─────────────────────────────────────
    md_lines = [
        "# Trend vs Chop — Uptrend Regime Summary",
        "",
        f"**Run date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Uptrend method:** {cfg['uptrend_regime_method']} "
        f"(close > SMA{cfg['sma_length']} AND SMA{cfg['sma_length']} rising over {cfg['sma_slope_lookback']} bars)",
        "",
        "## Aggregate",
        f"- Total uptrend-regime days analysed: **{n_total}**",
        f"- TREND_BULL days: **{agg['trend_bull_n']}** ({agg['trend_bull_pct']:.1f}%)",
        f"- CHOP days: **{agg['chop_n']}** ({agg['chop_pct']:.1f}%)",
        f"- NEUTRAL days: **{agg['neutral_n']}** ({agg['neutral_pct']:.1f}%)",
        "",
        "## Per Ticker",
    ]
    for row in ticker_summaries:
        md_lines.append(
            f"- **{row['ticker']}**: {row['uptrend_days']} uptrend days -- "
            f"Trend {row['trend_bull_pct']:.1f}%, Chop {row['chop_pct']:.1f}%, "
            f"Neutral {row['neutral_pct']:.1f}%"
        )
    md_lines.extend([
        "",
        "## Definitions (Locked)",
        f"- TREND_BULL: CLV >= {cfg['trend_day_clv_min']}, "
        f"Range/ATR >= {cfg['trend_day_range_atr_min']}"
        + (", close > open" if cfg.get("trend_day_requires_green") else ""),
        f"- CHOP: Range/ATR < {cfg['chop_day_range_atr_max']} "
        f"OR Body% < {cfg['chop_day_body_pct_max']}",
        "- NEUTRAL: all other uptrend days",
        "",
        "*No trade advice. Descriptive statistics only.*",
    ])
    (summary_dir / "trend_chop_summary.md").write_text(
        "\n".join(md_lines), encoding="utf-8"
    )
    print("Saved: trend_chop_summary.md")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    args = parser.parse_args()
    analyze(tickers=args.tickers, start=args.start, end=args.end)


if __name__ == "__main__":
    main()
