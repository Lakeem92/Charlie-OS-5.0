#!/usr/bin/env python3
"""
Data collection for Intraday EMA Cloud Pullback and 21 EMA Structural Failure Study.

Data source routing:
- US equities daily/intraday OHLCV: Alpaca via DataRouter (fallback handled by router)
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

STUDY_DIR = Path(__file__).resolve().parent
ROOT_DIR = STUDY_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR / "tools" / "studies"))

from shared.data_router import DataRouter
from shared.watchlist import get_watchlist
from run_id import resolve_output_dirs


def load_config() -> dict:
    with open(STUDY_DIR / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect daily + 5m data for EMA cloud study")
    parser.add_argument("--tickers", nargs="*", default=None, help="Ticker override")
    parser.add_argument("--start", default=None, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="End date YYYY-MM-DD")
    parser.add_argument("--intraday", default=None, help="Enable intraday fetch true/false")
    return parser.parse_args()


def resolve_tickers(cfg: dict, cli_tickers: list[str] | None) -> list[str]:
    if cli_tickers:
        return [t.upper() for t in cli_tickers]

    tickers_file = STUDY_DIR / "tickers.txt"
    if tickers_file.exists():
        file_tickers = [
            line.strip().upper()
            for line in tickers_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if file_tickers:
            return file_tickers

    default_cfg = cfg.get("tickers_default")
    if default_cfg:
        return [str(t).upper() for t in default_cfg]

    return get_watchlist()


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    rename_map = {
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "adj close": "adj_close",
        "adj_close": "adj_close",
    }
    kept = {}
    for col in out.columns:
        if col in rename_map:
            kept[col] = rename_map[col]
    out = out.rename(columns=kept)
    return out


def _save_df(df: pd.DataFrame, path: Path) -> None:
    to_save = df.copy()
    to_save.index.name = "timestamp"
    to_save.to_csv(path)


def _fetch_intraday_chunked(ticker: str, start: str, end: str, chunk_days: int = 30) -> pd.DataFrame:
    """Fetch 5-minute bars in chunks to avoid single-call row limits."""
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")

    frames: list[pd.DataFrame] = []
    cursor = start_dt
    while cursor <= end_dt:
        chunk_end = min(cursor + timedelta(days=chunk_days - 1), end_dt)
        chunk_df = DataRouter.get_price_data(
            ticker=ticker,
            start_date=cursor.strftime("%Y-%m-%d"),
            end_date=chunk_end.strftime("%Y-%m-%d"),
            timeframe="5min",
            study_type="returns",
        )
        if chunk_df is not None and not chunk_df.empty:
            frames.append(chunk_df)
        cursor = chunk_end + timedelta(days=1)

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, axis=0).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    return out


def collect(
    tickers: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
    use_intraday: bool | None = None,
) -> None:
    cfg = load_config()
    tickers = resolve_tickers(cfg, tickers)
    start = start or cfg["start_date"]
    end = end or (datetime.now().strftime("%Y-%m-%d") if cfg["end_date"] == "today" else cfg["end_date"])
    intraday = use_intraday if use_intraday is not None else cfg.get("use_intraday", False)

    print(f"Tickers: {len(tickers)} names")
    print(f"Date range: {start} to {end}")
    print(f"Intraday (5Min): {intraday}")

    data_dir, _, _, summary_dir = resolve_output_dirs(STUDY_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    log_lines: list[str] = [
        f"=== Data Collection Run Log ===",
        f"Timestamp: {datetime.now().isoformat()}",
        f"Tickers: {len(tickers)}",
        f"Date range: {start} to {end}",
        f"Timeframe daily: {cfg.get('timeframe_daily', '1Day')}",
        f"Timeframe intraday: {cfg.get('timeframe_intraday', '5Min') if intraday else 'disabled'}",
        "",
    ]

    manifest_rows: list[dict] = []

    for ticker in tickers:
        try:
            daily_df = DataRouter.get_price_data(
                ticker=ticker,
                start_date=start,
                end_date=end,
                timeframe="daily",
                study_type="returns",
            )
            daily_df = _normalize_ohlcv(daily_df)
            daily_path = data_dir / f"{ticker}_1D.csv"
            _save_df(daily_df, daily_path)
            msg = f"{ticker} daily: {len(daily_df)} rows saved -> {daily_path.name}"
            log_lines.append(msg)
            print(msg)
            manifest_rows.append(
                {
                    "ticker": ticker,
                    "dataset": "1D",
                    "rows": int(len(daily_df)),
                    "path": daily_path.name,
                    "status": "ok",
                }
            )
        except Exception as e:
            msg = f"WARNING: {ticker} daily fetch failed: {e}"
            log_lines.append(msg)
            print(msg, file=sys.stderr)
            manifest_rows.append(
                {
                    "ticker": ticker,
                    "dataset": "1D",
                    "rows": 0,
                    "path": "",
                    "status": f"error: {e}",
                }
            )
            continue

        if intraday:
            try:
                intraday_df = _fetch_intraday_chunked(ticker=ticker, start=start, end=end)
                intraday_df = _normalize_ohlcv(intraday_df)
                intraday_path = data_dir / f"{ticker}_5Min.csv"
                _save_df(intraday_df, intraday_path)
                msg = f"{ticker} 5min: {len(intraday_df)} rows saved -> {intraday_path.name}"
                log_lines.append(msg)
                print(msg)
                manifest_rows.append(
                    {
                        "ticker": ticker,
                        "dataset": "5Min",
                        "rows": int(len(intraday_df)),
                        "path": intraday_path.name,
                        "status": "ok",
                    }
                )
            except Exception as e:
                msg = f"WARNING: {ticker} 5min fetch failed: {e}"
                log_lines.append(msg)
                print(msg, file=sys.stderr)
                manifest_rows.append(
                    {
                        "ticker": ticker,
                        "dataset": "5Min",
                        "rows": 0,
                        "path": "",
                        "status": f"error: {e}",
                    }
                )

    log_path = summary_dir / "run_log_collect_data.txt"
    log_path.write_text("\n".join(log_lines), encoding="utf-8")

    manifest_df = pd.DataFrame(manifest_rows)
    manifest_df.to_csv(summary_dir / "data_manifest.csv", index=False)
    print(f"\nCollection log: {log_path}")
    print(f"Manifest: {summary_dir / 'data_manifest.csv'}")


if __name__ == "__main__":
    cli = parse_args()
    intraday_override = None
    if cli.intraday is not None:
        intraday_override = str(cli.intraday).lower() in ("true", "1", "yes")

    collect(
        tickers=cli.tickers,
        start=cli.start,
        end=cli.end,
        use_intraday=intraday_override,
    )
