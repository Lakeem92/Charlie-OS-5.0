#!/usr/bin/env python3
"""
Template: Data Collection Script
Fetches price data for configured tickers and saves to outputs/data/.
"""
from __future__ import annotations

import sys
import yaml
from pathlib import Path
from datetime import datetime

STUDY_DIR = Path(__file__).resolve().parent
ROOT_DIR = STUDY_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from shared.data_router import DataRouter


def load_config() -> dict:
    with open(STUDY_DIR / "config.yaml", "r") as f:
        return yaml.safe_load(f)


def resolve_tickers(cfg: dict) -> list[str]:
    """Determine tickers from tickers.txt, CLI override, or config default."""
    tickers_file = STUDY_DIR / "tickers.txt"
    if tickers_file.exists():
        tickers = [
            line.strip()
            for line in tickers_file.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if tickers:
            return tickers
    return cfg.get("tickers_default", ["SPY"])


def collect(tickers: list[str] | None = None,
            start: str | None = None,
            end: str | None = None,
            use_intraday: bool | None = None) -> None:
    cfg = load_config()
    tickers = tickers or resolve_tickers(cfg)
    start = start or cfg["start_date"]
    end = end or (datetime.now().strftime("%Y-%m-%d") if cfg["end_date"] == "today" else cfg["end_date"])
    intraday = use_intraday if use_intraday is not None else cfg.get("use_intraday", False)

    out_data = STUDY_DIR / "outputs" / "data"
    out_data.mkdir(parents=True, exist_ok=True)
    summary_dir = STUDY_DIR / "outputs" / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    log_lines: list[str] = [
        f"=== Data Collection Run Log ===",
        f"Timestamp: {datetime.now().isoformat()}",
        f"Tickers: {tickers}",
        f"Date range: {start} to {end}",
        f"Timeframe daily: {cfg.get('timeframe_daily', '1Day')}",
        f"Use intraday: {intraday}",
        "",
    ]

    for ticker in tickers:
        try:
            df = DataRouter.get_price_data(
                ticker, start, end, timeframe="daily",
                source="alpaca", fallback=True, study_type="indicator"
            )
            path = out_data / f"{ticker}_1D.csv"
            df.to_csv(path)
            msg = f"{ticker} daily: {len(df)} rows saved -> {path.name}"
            log_lines.append(msg)
            print(msg)
        except Exception as e:
            msg = f"WARNING: {ticker} daily fetch failed: {e}"
            log_lines.append(msg)
            print(msg, file=sys.stderr)

    log_path = summary_dir / "run_log.txt"
    log_path.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"\nRun log written to {log_path}")


if __name__ == "__main__":
    collect()
