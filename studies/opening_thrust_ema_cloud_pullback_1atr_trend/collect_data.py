#!/usr/bin/env python3
"""
Data collection for Opening Thrust to EMA Cloud Pullback Study.

Cache-first strategy:
- Reuse daily + 5-minute files from prior EMA cloud study run when available
- Fetch missing files only (Alpaca via DataRouter)
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yaml

import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

STUDY_DIR = Path(__file__).resolve().parent
ROOT_DIR = STUDY_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR / "tools" / "studies"))

from run_id import resolve_output_dirs  # type: ignore[import-not-found]
from shared.data_router import DataRouter
from shared.watchlist import get_watchlist


def load_config() -> dict:
    with open(STUDY_DIR / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect daily + 5m data with cache reuse")
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--source-run-id", default=None, help="Override source run ID for cache copy")
    parser.add_argument("--disable-reuse", action="store_true")
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
    return out


def _save_df(df: pd.DataFrame, path: Path) -> None:
    to_save = df.copy()
    to_save.index.name = "timestamp"
    to_save.to_csv(path)


def _fetch_intraday_chunked(ticker: str, start: str, end: str, chunk_days: int = 30) -> pd.DataFrame:
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


def _resolve_source_data_dir(cfg: dict, source_run_id_override: str | None) -> Path | None:
    reuse_cfg = cfg.get("reuse", {})
    if not reuse_cfg.get("enabled", True):
        return None

    source_study = reuse_cfg.get("source_study", "ema_cloud_pullback_21ema_failure")
    source_outputs = ROOT_DIR / "studies" / source_study / "outputs"
    if not source_outputs.exists():
        return None

    run_id = source_run_id_override
    if not run_id:
        configured = str(reuse_cfg.get("source_run_id", "auto"))
        if configured.lower() != "auto":
            run_id = configured

    if not run_id:
        latest_file = source_outputs / "LATEST.txt"
        if not latest_file.exists():
            return None
        rel = latest_file.read_text(encoding="utf-8").strip().replace("\\", "/").rstrip("/")
        if not rel:
            return None
        source_run_dir = source_outputs / rel
    else:
        source_run_dir = source_outputs / "runs" / run_id

    source_data = source_run_dir / "data"
    if source_data.exists():
        return source_data
    return None


def collect(
    tickers: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
    source_run_id: str | None = None,
    disable_reuse: bool = False,
) -> None:
    cfg = load_config()
    tickers = resolve_tickers(cfg, tickers)
    start = start or cfg["start_date"]
    end = end or (datetime.now().strftime("%Y-%m-%d") if cfg["end_date"] == "today" else cfg["end_date"])

    data_dir, _, _, summary_dir = resolve_output_dirs(STUDY_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    source_data_dir = None if disable_reuse else _resolve_source_data_dir(cfg, source_run_id)

    print(f"Tickers: {len(tickers)} names")
    print(f"Date range: {start} to {end}")
    print(f"Cache reuse enabled: {source_data_dir is not None}")
    if source_data_dir:
        print(f"Source data dir: {source_data_dir}")

    log_lines: list[str] = [
        "=== Data Collection Run Log ===",
        f"Timestamp: {datetime.now().isoformat()}",
        f"Tickers: {len(tickers)}",
        f"Date range: {start} to {end}",
        f"Cache reuse enabled: {source_data_dir is not None}",
        f"Source data dir: {source_data_dir if source_data_dir else 'none'}",
        "",
    ]

    manifest_rows: list[dict] = []

    for ticker in tickers:
        daily_path = data_dir / f"{ticker}_1D.csv"
        intraday_path = data_dir / f"{ticker}_5Min.csv"

        reused_daily = False
        reused_intraday = False

        if source_data_dir:
            src_daily = source_data_dir / f"{ticker}_1D.csv"
            src_intraday = source_data_dir / f"{ticker}_5Min.csv"
            if src_daily.exists() and not daily_path.exists():
                shutil.copy2(src_daily, daily_path)
                reused_daily = True
            if src_intraday.exists() and not intraday_path.exists():
                shutil.copy2(src_intraday, intraday_path)
                reused_intraday = True

        if reused_daily and reused_intraday:
            msg = f"{ticker}: reused 1D + 5Min from cache"
            print(msg)
            log_lines.append(msg)
            manifest_rows.append(
                {
                    "ticker": ticker,
                    "daily_status": "reused",
                    "intraday_status": "reused",
                    "daily_rows": pd.read_csv(daily_path).shape[0],
                    "intraday_rows": pd.read_csv(intraday_path).shape[0],
                }
            )
            continue

        daily_rows = 0
        intraday_rows = 0
        daily_status = "reused" if reused_daily else "missing"
        intraday_status = "reused" if reused_intraday else "missing"

        if not daily_path.exists():
            try:
                daily_df = DataRouter.get_price_data(
                    ticker=ticker,
                    start_date=start,
                    end_date=end,
                    timeframe="daily",
                    study_type="returns",
                )
                daily_df = _normalize_ohlcv(daily_df)
                _save_df(daily_df, daily_path)
                daily_rows = len(daily_df)
                daily_status = "fetched"
                msg = f"{ticker} daily: {daily_rows} rows saved -> {daily_path.name}"
                print(msg)
                log_lines.append(msg)
            except Exception as exc:
                daily_status = f"error: {exc}"
                msg = f"WARNING: {ticker} daily fetch failed: {exc}"
                print(msg, file=sys.stderr)
                log_lines.append(msg)
                manifest_rows.append(
                    {
                        "ticker": ticker,
                        "daily_status": daily_status,
                        "intraday_status": intraday_status,
                        "daily_rows": 0,
                        "intraday_rows": 0,
                    }
                )
                continue
        else:
            daily_rows = pd.read_csv(daily_path).shape[0]

        if not intraday_path.exists():
            try:
                intraday_df = _fetch_intraday_chunked(ticker=ticker, start=start, end=end)
                intraday_df = _normalize_ohlcv(intraday_df)
                _save_df(intraday_df, intraday_path)
                intraday_rows = len(intraday_df)
                intraday_status = "fetched"
                msg = f"{ticker} 5min: {intraday_rows} rows saved -> {intraday_path.name}"
                print(msg)
                log_lines.append(msg)
            except Exception as exc:
                intraday_status = f"error: {exc}"
                msg = f"WARNING: {ticker} 5min fetch failed: {exc}"
                print(msg, file=sys.stderr)
                log_lines.append(msg)
        else:
            intraday_rows = pd.read_csv(intraday_path).shape[0]

        manifest_rows.append(
            {
                "ticker": ticker,
                "daily_status": daily_status,
                "intraday_status": intraday_status,
                "daily_rows": int(daily_rows),
                "intraday_rows": int(intraday_rows),
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
    collect(
        tickers=cli.tickers,
        start=cli.start,
        end=cli.end,
        source_run_id=cli.source_run_id,
        disable_reuse=cli.disable_reuse,
    )
