#!/usr/bin/env python3
"""
First Hour 50%+ ATR to EMA Cloud Pullback Study Runner.

Creates versioned run archives under outputs/runs/<RUN_ID>/ and executes:
  1) collect_data.py  — cache-first data fetch (parent study reuse + incremental gap)
  2) analyze.py       — event detection + table generation

Usage:
  python run_study.py
  python run_study.py --tickers NVDA TSLA AAPL
  python run_study.py --start 2025-04-08 --end 2026-04-08
  python run_study.py --analysis-only            # skip data collection
  python run_study.py --disable-reuse            # force fresh data fetch
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

STUDY_DIR = Path(__file__).resolve().parent
ROOT_DIR = STUDY_DIR.parent.parent

sys.path.insert(0, str(ROOT_DIR / "tools" / "studies"))
from run_id import create_run_folder, generate_run_id  # type: ignore[import-not-found]


def load_config() -> dict:
    with open(STUDY_DIR / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _run_script(script_name: str, sub_args: list[str], env: dict | None = None) -> None:
    script_path = STUDY_DIR / script_name
    if not script_path.exists():
        print(f"Skipping {script_name} (not found)")
        return

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    cmd = [sys.executable, str(script_path)] + sub_args
    print(f"\n{'=' * 64}")
    print(f"Running: {script_name}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'=' * 64}")
    result = subprocess.run(cmd, cwd=str(STUDY_DIR), env=run_env)
    if result.returncode != 0:
        raise RuntimeError(f"{script_name} failed with exit code {result.returncode}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run first-hour ATR50+ to EMA cloud pullback study"
    )
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument(
        "--analysis-only", action="store_true", help="Skip data collection, run analysis only"
    )
    parser.add_argument(
        "--source-run-id", default=None, help="Override source study cache run ID"
    )
    parser.add_argument(
        "--disable-reuse", action="store_true", help="Disable cache reuse from parent study"
    )
    args = parser.parse_args()

    cfg = load_config()

    effective_spec: dict = {
        "study": cfg.get("study_name", "first_hour_atr50_ema_cloud_pullback"),
        "tickers": list(args.tickers) if args.tickers else [],
        "date_range": {
            "start": args.start or cfg.get("start_date", "2025-04-08"),
            "end": args.end or cfg.get("end_date", "today"),
        },
        "intraday": {"enabled": True},
        "event": {
            "type": "first_hour_atr50_cloud_pullback",
            "atr_threshold": float(cfg.get("atr_threshold", 0.50)),
            "trigger_max_bar": int(cfg.get("trigger_max_bar", 12)),
            "next_hour_bars": int(cfg.get("next_hour_bars", 12)),
        },
    }

    run_id = generate_run_id(effective_spec)
    outputs_dir = STUDY_DIR / "outputs"
    run_folder = create_run_folder(outputs_dir, run_id)

    run_env = {"DATA_LAB_RUN_OUTPUT_DIR": str(run_folder)}

    sub_args: list[str] = []
    if args.tickers:
        sub_args.extend(["--tickers", *args.tickers])
    if args.start:
        sub_args.extend(["--start", args.start])
    if args.end:
        sub_args.extend(["--end", args.end])
    if args.source_run_id:
        sub_args.extend(["--source-run-id", args.source_run_id])
    if args.disable_reuse:
        sub_args.append("--disable-reuse")

    run_log_lines = [
        f"=== Run Archive: {run_id} ===",
        f"Timestamp: {datetime.now().isoformat()}",
        f"Study: {effective_spec['study']}",
        f"Tickers: {effective_spec['tickers'] or 'watchlist'}",
        f"Date range: {effective_spec['date_range']['start']} to {effective_spec['date_range']['end']}",
        f"Reuse cache: {not args.disable_reuse}",
        f"Source run override: {args.source_run_id or 'none'}",
        "",
    ]

    summary_dir = run_folder / "summary"
    with open(summary_dir / "run_spec.yaml", "w", encoding="utf-8") as f:
        effective_spec["_run_id"] = run_id
        effective_spec["_generated_at"] = datetime.now().isoformat()
        yaml.dump(effective_spec, f, default_flow_style=False, sort_keys=False)

    try:
        if not args.analysis_only:
            _run_script("collect_data.py", sub_args, env=run_env)
            run_log_lines.append("Step 1: collect_data.py -- DONE")
        else:
            run_log_lines.append("Step 1: collect_data.py -- SKIPPED (analysis-only)")

        _run_script("analyze.py", sub_args, env=run_env)
        run_log_lines.append("Step 2: analyze.py -- DONE")
        run_log_lines.append("")
        run_log_lines.append("Exit: success")

    except Exception as exc:
        run_log_lines.append(f"Exit: failed ({exc})")
        (summary_dir / "run_log.txt").write_text("\n".join(run_log_lines), encoding="utf-8")
        raise

    (summary_dir / "run_log.txt").write_text("\n".join(run_log_lines), encoding="utf-8")

    print(f"\nRun complete:     {run_folder}")
    print(f"LATEST pointer:   {outputs_dir / 'LATEST.txt'}")
    print(f"Analysis summary: {run_folder / 'summary' / 'analysis_summary.txt'}")


if __name__ == "__main__":
    main()
