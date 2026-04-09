#!/usr/bin/env python3
"""
trend_chop_gap_quality — Data Collection
Fetches daily (and optionally intraday) bars for configured tickers.
Saves CSVs to outputs/data/ (or run archive folder if DATA_LAB_RUN_OUTPUT_DIR is set).
Writes run_log.txt to outputs/summary/.

Data source priority: Alpaca → yfinance fallback (with warning).
"""
from __future__ import annotations

import os
import sys
import time
import yaml
import argparse
from pathlib import Path
from datetime import datetime

STUDY_DIR = Path(__file__).resolve().parent
ROOT_DIR = STUDY_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "tools" / "studies"))

from run_id import resolve_output_dirs


def load_config() -> dict:
    with open(STUDY_DIR / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_tickers(cfg: dict, cli_tickers: list[str] | None = None) -> list[str]:
    """CLI override > tickers.txt > config default."""
    if cli_tickers:
        return cli_tickers
    tickers_file = STUDY_DIR / "tickers.txt"
    if tickers_file.exists():
        tickers = [
            line.strip()
            for line in tickers_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if tickers:
            return tickers
    return cfg.get("tickers_default", ["SPY"])


def resolve_end_date(cfg: dict, cli_end: str | None = None) -> str:
    if cli_end:
        return cli_end
    raw = cfg.get("end_date", "today")
    if raw == "today":
        return datetime.now().strftime("%Y-%m-%d")
    return raw


def _fetch_alpaca(ticker: str, start: str, end: str,
                  timeframe: str) -> "pd.DataFrame":
    """Try Alpaca via DataRouter (study_type='indicator' routes to Alpaca)."""
    from shared.data_router import DataRouter
    return DataRouter.get_price_data(
        ticker, start, end,
        timeframe="daily" if timeframe == "1Day" else "5min",
        source="alpaca",
        fallback=False,
        study_type="indicator",
    )


def _fetch_yfinance(ticker: str, start: str, end: str,
                    timeframe: str) -> "pd.DataFrame":
    """yfinance fallback — daily only (yfinance 5m limited to 60 days)."""
    import yfinance as yf
    import pandas as pd

    if timeframe != "1Day":
        # yfinance intraday 5m only goes back ~60 days
        df = yf.download(ticker, start=start, end=end,
                         interval="5m", progress=False, auto_adjust=True)
    else:
        df = yf.download(ticker, start=start, end=end,
                         progress=False, auto_adjust=True)
    if df.empty:
        raise RuntimeError(f"yfinance returned no data for {ticker}")

    # Normalise column names to lowercase
    df.columns = [str(c).lower() if isinstance(c, str) else str(c[0]).lower() for c in df.columns]
    # Handle MultiIndex columns from yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]).lower() for c in df.columns]
    return df


def _normalise_columns(df: "pd.DataFrame") -> "pd.DataFrame":
    """Ensure lowercase column names: open, high, low, close, volume."""
    import pandas as pd
    if isinstance(df.columns, pd.MultiIndex):
        # yfinance returns MultiIndex like (Price, Ticker) — take first level
        df.columns = [str(c[0]).lower() for c in df.columns]
    else:
        df.columns = [str(c).lower() for c in df.columns]
    return df


def collect(tickers: list[str] | None = None,
            start: str | None = None,
            end: str | None = None,
            use_intraday: bool | None = None) -> None:
    import pandas as pd

    cfg = load_config()
    tickers = resolve_tickers(cfg, tickers)
    start = start or cfg["start_date"]
    end = resolve_end_date(cfg, end)
    intraday = use_intraday if use_intraday is not None else cfg.get("use_intraday", False)

    # Use run archive output dirs if env var is set, else fallback to default
    out_data, _, _, summary_dir = resolve_output_dirs(STUDY_DIR)
    out_data.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    log_lines: list[str] = [
        "=== trend_chop_gap_quality — Data Collection Run Log ===",
        f"Timestamp : {datetime.now().isoformat()}",
        f"Tickers   : {tickers}",
        f"Date range: {start} to {end}",
        f"Daily TF  : {cfg.get('timeframe_daily', '1Day')}",
        f"Intraday  : {intraday}",
        "",
    ]

    daily_tf = cfg.get("timeframe_daily", "1Day")
    intraday_tf = cfg.get("timeframe_intraday", "5Min")

    for ticker in tickers:
        # ── Daily bars ───────────────────────────────────────
        source_used = "alpaca"
        try:
            df = _fetch_alpaca(ticker, start, end, daily_tf)
            df = _normalise_columns(df)
        except Exception as e_alp:
            source_used = "yfinance"
            warn = f"WARNING: Alpaca failed for {ticker} daily ({e_alp}). Falling back to yfinance."
            log_lines.append(warn)
            print(warn, file=sys.stderr)
            try:
                df = _fetch_yfinance(ticker, start, end, daily_tf)
                df = _normalise_columns(df)
            except Exception as e_yf:
                msg = f"ERROR: Both Alpaca and yfinance failed for {ticker} daily: {e_yf}"
                log_lines.append(msg)
                print(msg, file=sys.stderr)
                continue

        path = out_data / f"{ticker}_1D.csv"
        df.to_csv(path)
        msg = f"{ticker} daily ({source_used}): {len(df)} rows -> {path.name}"
        log_lines.append(msg)
        print(msg)

        # ── Intraday bars (optional) ─────────────────────────
        if intraday:
            intra_source = "alpaca"
            try:
                df_i = _fetch_alpaca(ticker, start, end, intraday_tf)
                df_i = _normalise_columns(df_i)
            except Exception as e_alp_i:
                intra_source = "yfinance"
                warn = (f"WARNING: Alpaca failed for {ticker} intraday ({e_alp_i}). "
                        f"Falling back to yfinance (limited to ~60 days).")
                log_lines.append(warn)
                print(warn, file=sys.stderr)
                try:
                    df_i = _fetch_yfinance(ticker, start, end, intraday_tf)
                    df_i = _normalise_columns(df_i)
                except Exception as e_yf_i:
                    msg = f"ERROR: Both sources failed for {ticker} intraday: {e_yf_i}"
                    log_lines.append(msg)
                    print(msg, file=sys.stderr)
                    continue

            ipath = out_data / f"{ticker}_5Min.csv"
            df_i.to_csv(ipath)
            msg = f"{ticker} intraday ({intra_source}): {len(df_i)} rows -> {ipath.name}"
            log_lines.append(msg)
            print(msg)

        # Small delay to be courteous to APIs
        time.sleep(0.25)

    # Write run log
    log_path = summary_dir / "run_log.txt"
    log_path.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"\nRun log: {log_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect data for trend_chop_gap_quality")
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--intraday", default=None)
    args = parser.parse_args()

    intraday = None
    if args.intraday is not None:
        intraday = args.intraday.lower() in ("true", "1", "yes")

    collect(
        tickers=args.tickers,
        start=args.start,
        end=args.end,
        use_intraday=intraday,
    )


if __name__ == "__main__":
    main()
