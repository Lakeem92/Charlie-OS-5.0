#!/usr/bin/env python3
"""
Analysis 3 — Intraday First-Hour Classifier

Only runs when intraday 5Min CSVs exist.  For each day:
- Computes VWAP, first-hour window, OR high/low
- Measures vwap_hold, or_break_time, pullback_depth, reclaim_count,
  firsthour_clv
- Computes Failure Score (0–5, locked rules)
- Classifies: TrendSignature / FadeSignature / ChopSignature

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

from utils import (
    atr, compute_daily_vwap, first_hour_window,
    or_break_time_minutes, pullback_depth, reclaim_count,
    clv as clv_series, safe_divide,
)
from run_id import resolve_output_dirs


def load_config() -> dict:
    with open(STUDY_DIR / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _filter_rth(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter to regular trading hours (9:30–16:00 ET) if timestamps are
    timezone-aware in US/Eastern, else keep all and print a warning.
    """
    idx = df.index
    if hasattr(idx, "tz") and idx.tz is not None:
        try:
            idx_et = idx.tz_convert("US/Eastern")
            mask = (idx_et.time >= pd.Timestamp("09:30").time()) & \
                   (idx_et.time <= pd.Timestamp("16:00").time())
            return df[mask]
        except Exception:
            pass  # fall through

    # If no TZ info, attempt to filter by time component
    if hasattr(idx, "time"):
        try:
            times = pd.Series([t.time() for t in idx], index=idx)
            mask = (times >= pd.Timestamp("09:30").time()) & \
                   (times <= pd.Timestamp("16:00").time())
            filtered = df[mask]
            if len(filtered) < len(df):
                return filtered
        except Exception:
            pass

    print("WARNING: Could not confirm exchange timezone. Keeping all bars.")
    return df


def _process_day(day_df: pd.DataFrame, vwap_series: pd.Series,
                 daily_atr: float, cfg: dict) -> dict | None:
    """Process a single day's intraday bars and return metrics dict."""
    if day_df.empty:
        return None

    or_min = cfg.get("intraday_or_minutes", 60)

    # First-hour window
    fh = first_hour_window(day_df, or_min)
    if fh.empty or len(fh) < 2:
        return None

    fh_vwap = vwap_series.reindex(fh.index)

    # OR high / low
    or_high = fh["high"].max()
    or_low = fh["low"].min()

    # VWAP hold: fraction of first-hour bars closing above VWAP
    above_vwap = fh["close"] > fh_vwap
    vwap_hold = safe_divide(above_vwap.sum(), len(fh))

    # OR break time
    break_time = or_break_time_minutes(day_df, or_high)

    # First-hour CLV
    fh_close = fh["close"].iloc[-1]
    fh_high = fh["high"].max()
    fh_low = fh["low"].min()
    fh_range = fh_high - fh_low
    fh_clv = safe_divide(fh_close - fh_low, fh_range)

    # Pullback depth
    pb_depth = pullback_depth(fh, or_high, or_low)

    # Reclaim count (first 2 hours = first hour × 2 bars-wise)
    two_hour_end = day_df.index[0] + pd.Timedelta(minutes=or_min * 2)
    two_hour_df = day_df.loc[:two_hour_end]
    two_hour_vwap = vwap_series.reindex(two_hour_df.index)
    rc = reclaim_count(two_hour_df["close"], two_hour_vwap)

    # Failure score (0–5)
    failure = 0
    if vwap_hold < 0.50:
        failure += 1
    if rc >= 2:
        failure += 1
    if fh_clv < 0.55:
        failure += 1
    if break_time > 40:
        failure += 1
    if pb_depth > 0.50:
        failure += 1

    # Signature classification
    if vwap_hold >= 0.80 and pb_depth <= 0.35 and fh_clv >= 0.75:
        signature = "TrendSignature"
    elif vwap_hold < 0.50 and rc >= 2 and fh_clv <= 0.55:
        signature = "FadeSignature"
    else:
        signature = "ChopSignature"

    return {
        "or_high": or_high,
        "or_low": or_low,
        "vwap_hold": round(vwap_hold, 4),
        "or_break_time_min": round(break_time, 1),
        "firsthour_clv": round(fh_clv, 4),
        "pullback_depth": round(pb_depth, 4),
        "reclaim_count": rc,
        "failure_score": failure,
        "signature": signature,
    }


def analyze(tickers: list[str] | None = None,
            start: str | None = None,
            end: str | None = None) -> None:
    cfg = load_config()
    # Use run archive output dirs if env var is set, else fallback to default
    data_dir, tables_dir, charts_dir, summary_dir = resolve_output_dirs(STUDY_DIR)
    for d in [tables_dir, charts_dir, summary_dir]:
        d.mkdir(parents=True, exist_ok=True)

    intraday_files = sorted(data_dir.glob("*_5Min.csv"))
    if not intraday_files:
        print("No intraday 5Min CSVs found. Skipping intraday analysis.")
        return

    all_day_rows: list[dict] = []
    ticker_summary_rows: list[dict] = []

    for csv_path in intraday_files:
        ticker = csv_path.stem.replace("_5Min", "")
        if tickers and ticker not in tickers:
            continue

        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        df.columns = [c.lower() for c in df.columns]
        if "close" not in df.columns or "volume" not in df.columns:
            print(f"WARNING: {ticker} intraday CSV missing required columns, skipping.")
            continue

        # RTH filter
        if cfg.get("rth_only", True):
            df = _filter_rth(df)

        if df.empty:
            continue

        if start:
            df = df[df.index >= start]
        if end:
            df = df[df.index <= end]

        # Load daily ATR for reference
        daily_path = data_dir / f"{ticker}_1D.csv"
        daily_atr_map: dict = {}
        if daily_path.exists():
            ddf = pd.read_csv(daily_path, index_col=0, parse_dates=True)
            ddf.columns = [c.lower() for c in ddf.columns]
            if "close" in ddf.columns:
                atr_s = atr(ddf["high"], ddf["low"], ddf["close"], cfg["atr_length"])
                for dt, val in atr_s.items():
                    if pd.notna(val):
                        daily_atr_map[dt.date() if hasattr(dt, "date") else dt] = val

        # Compute VWAP
        vwap_s = compute_daily_vwap(df)

        # Process each trading day
        dates = sorted(set(df.index.date))
        day_metrics: list[dict] = []

        for d in dates:
            day_mask = df.index.date == d
            day_df = df[day_mask]
            if len(day_df) < 4:  # need minimum bars
                continue

            daily_atr_val = daily_atr_map.get(d, np.nan)
            day_vwap = vwap_s.reindex(day_df.index)

            result = _process_day(day_df, day_vwap, daily_atr_val, cfg)
            if result is None:
                continue

            result["ticker"] = ticker
            result["date"] = str(d)
            all_day_rows.append(result)
            day_metrics.append(result)

        # Per-ticker summary
        if day_metrics:
            mdf = pd.DataFrame(day_metrics)
            sig_counts = mdf["signature"].value_counts()
            n = len(mdf)
            ticker_summary_rows.append({
                "ticker": ticker,
                "days_analysed": n,
                "trend_sig_n": int(sig_counts.get("TrendSignature", 0)),
                "fade_sig_n": int(sig_counts.get("FadeSignature", 0)),
                "chop_sig_n": int(sig_counts.get("ChopSignature", 0)),
                "trend_sig_pct": safe_divide(sig_counts.get("TrendSignature", 0), n) * 100,
                "fade_sig_pct": safe_divide(sig_counts.get("FadeSignature", 0), n) * 100,
                "chop_sig_pct": safe_divide(sig_counts.get("ChopSignature", 0), n) * 100,
                "avg_failure_score": round(mdf["failure_score"].mean(), 2),
            })

    if not all_day_rows:
        print("No intraday days processed.")
        return

    # ── Output tables ────────────────────────────────────────
    day_df_out = pd.DataFrame(all_day_rows)
    col_order = ["ticker", "date", "or_high", "or_low", "vwap_hold",
                 "or_break_time_min", "firsthour_clv", "pullback_depth",
                 "reclaim_count", "failure_score", "signature"]
    existing_cols = [c for c in col_order if c in day_df_out.columns]
    day_df_out = day_df_out[existing_cols]
    day_df_out.to_csv(tables_dir / "intraday_first_hour_by_day.csv", index=False)
    print(f"Saved: intraday_first_hour_by_day.csv ({len(day_df_out)} days)")

    ticker_sum_df = pd.DataFrame(ticker_summary_rows)
    ticker_sum_df.to_csv(tables_dir / "intraday_first_hour_summary_by_ticker.csv", index=False)
    print(f"Saved: intraday_first_hour_summary_by_ticker.csv")

    # Aggregate
    n_total = len(day_df_out)
    sig_total = day_df_out["signature"].value_counts()
    agg = {
        "days_analysed": n_total,
        "trend_sig_n": int(sig_total.get("TrendSignature", 0)),
        "fade_sig_n": int(sig_total.get("FadeSignature", 0)),
        "chop_sig_n": int(sig_total.get("ChopSignature", 0)),
        "trend_sig_pct": safe_divide(sig_total.get("TrendSignature", 0), n_total) * 100,
        "fade_sig_pct": safe_divide(sig_total.get("FadeSignature", 0), n_total) * 100,
        "chop_sig_pct": safe_divide(sig_total.get("ChopSignature", 0), n_total) * 100,
        "avg_failure_score": round(day_df_out["failure_score"].mean(), 2),
    }
    pd.DataFrame([agg]).to_csv(tables_dir / "intraday_first_hour_summary_aggregate.csv", index=False)
    print("Saved: intraday_first_hour_summary_aggregate.csv")

    # ── Chart: Signature distribution ────────────────────────
    fig, ax = plt.subplots(figsize=(7, 5))
    labels = ["TrendSignature", "FadeSignature", "ChopSignature"]
    vals = [agg.get("trend_sig_pct", 0), agg.get("fade_sig_pct", 0), agg.get("chop_sig_pct", 0)]
    colors = ["#2ecc71", "#e74c3c", "#f39c12"]
    ax.bar(labels, vals, color=colors, edgecolor="black", linewidth=0.5)
    ax.set_ylabel("% of Days")
    ax.set_title("Intraday Signature Distribution — Aggregate")
    ax.set_ylim(0, max(vals) * 1.3 if vals and max(vals) > 0 else 100)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=10)
    plt.tight_layout()
    chart_path = charts_dir / "intraday_signature_distribution.png"
    fig.savefig(chart_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {chart_path.name}")

    # ── Markdown summary ─────────────────────────────────────
    md = [
        "# Intraday First-Hour Classifier Summary",
        "",
        f"**Run date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**First-hour window:** {cfg.get('intraday_or_minutes', 60)} minutes",
        "",
        "## Aggregate",
        f"- Days analysed: **{n_total}**",
        f"- TrendSignature: **{agg['trend_sig_n']}** ({agg['trend_sig_pct']:.1f}%)",
        f"- FadeSignature: **{agg['fade_sig_n']}** ({agg['fade_sig_pct']:.1f}%)",
        f"- ChopSignature: **{agg['chop_sig_n']}** ({agg['chop_sig_pct']:.1f}%)",
        f"- Average failure score: **{agg['avg_failure_score']:.2f}** / 5",
        "",
        "## Per Ticker",
    ]
    for row in ticker_summary_rows:
        md.append(
            f"- **{row['ticker']}**: {row['days_analysed']} days — "
            f"Trend {row['trend_sig_pct']:.1f}%, Fade {row['fade_sig_pct']:.1f}%, "
            f"Chop {row['chop_sig_pct']:.1f}% — Avg FS: {row['avg_failure_score']:.2f}"
        )
    md.extend([
        "",
        "## Failure Score Rules (0–5, Locked)",
        "- +1 if vwap_hold < 0.50",
        "- +1 if reclaim_count >= 2",
        "- +1 if firsthour_clv < 0.55",
        "- +1 if or_break_time_minutes > 40",
        "- +1 if pullback_depth > 0.50",
        "",
        "## Signature Definitions (Locked)",
        "- **TrendSignature:** vwap_hold >= 0.80 AND pullback_depth <= 0.35 AND firsthour_clv >= 0.75",
        "- **FadeSignature:** vwap_hold < 0.50 AND reclaim_count >= 2 AND firsthour_clv <= 0.55",
        "- **ChopSignature:** all other days",
        "",
        "*No trade advice. Descriptive statistics only.*",
    ])
    (summary_dir / "intraday_first_hour_summary.md").write_text(
        "\n".join(md), encoding="utf-8"
    )
    print("Saved: intraday_first_hour_summary.md")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    args = parser.parse_args()
    analyze(tickers=args.tickers, start=args.start, end=args.end)


if __name__ == "__main__":
    main()
