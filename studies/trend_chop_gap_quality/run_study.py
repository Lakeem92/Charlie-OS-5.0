#!/usr/bin/env python3
"""
trend_chop_gap_quality -- Study Runner

Orchestrates: collect_data -> analyze_trend_chop -> analyze_gapup_close_strength
              -> analyze_intraday_first_hour (if intraday enabled + data exists)
              -> analyze_forward_horizons (if horizons requested in spec)

Run Archive System:
    Each run creates a timestamped archive folder:
    outputs/runs/<RUN_ID>/{data,tables,charts,summary}/
    LATEST.txt points to the most recent run.

CLI usage:
    python run_study.py --tickers NVDA TSLA --start 2018-01-01 --end 2026-02-15 --intraday true
    python run_study.py --spec outputs/summary/run_spec.yaml
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import yaml
from pathlib import Path
from datetime import datetime

STUDY_DIR = Path(__file__).resolve().parent
ROOT_DIR = STUDY_DIR.parent.parent

# Import run_id utilities
sys.path.insert(0, str(ROOT_DIR / "tools" / "studies"))
from run_id import generate_run_id, create_run_folder


def load_config() -> dict:
    with open(STUDY_DIR / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_spec(spec_path: str | Path) -> dict:
    with open(spec_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _run_script(script_name: str, sub_args: list[str], env: dict | None = None) -> None:
    """Run a sub-script with shared args and environment."""
    script_path = STUDY_DIR / script_name
    if not script_path.exists():
        print(f"Skipping {script_name} (file not found)")
        return

    # Merge custom env with current environment
    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    cmd = [sys.executable, str(script_path)] + sub_args
    print(f"\n{'-'*60}")
    print(f"> {script_name}")
    print(f"  cmd: {' '.join(cmd)}")
    print(f"{'-'*60}")
    result = subprocess.run(cmd, cwd=str(STUDY_DIR), env=run_env)
    if result.returncode != 0:
        print(f"ERROR: {script_name} exited with code {result.returncode}")
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run trend_chop_gap_quality study end-to-end"
    )
    parser.add_argument("--tickers", nargs="*", default=None,
                        help="Override ticker list")
    parser.add_argument("--start", default=None,
                        help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default=None,
                        help="End date YYYY-MM-DD")
    parser.add_argument("--intraday", default=None,
                        help="Enable intraday analysis (true/false)")
    parser.add_argument("--spec", default=None,
                        help="Path to run_spec.yaml (overrides other args)")
    args = parser.parse_args()

    cfg = load_config()
    spec: dict | None = None

    # -- Resolve from spec if provided -----------------------------------
    if args.spec:
        spec = load_spec(args.spec)

        # Extract parameters from spec
        tickers = spec.get("tickers") or args.tickers
        date_range = spec.get("date_range", {})
        start = date_range.get("start") or args.start
        end = date_range.get("end") or args.end

        intraday_cfg = spec.get("intraday", {})
        use_intraday = intraday_cfg.get("enabled", False)

        outputs_cfg = spec.get("outputs", {})
        include_trend_chop = outputs_cfg.get("include_trend_chop_mix", True)
        include_gap = outputs_cfg.get("include_gap_close_strength", True)
        include_intraday_fh = outputs_cfg.get("include_intraday_first_hour", False)
        include_forward = outputs_cfg.get("include_forward_horizons", False)

    else:
        tickers = args.tickers
        start = args.start
        end = args.end
        use_intraday = cfg.get("use_intraday", False)
        if args.intraday is not None:
            use_intraday = args.intraday.lower() in ("true", "1", "yes")
        include_trend_chop = True
        include_gap = True
        include_intraday_fh = use_intraday
        include_forward = False

    # ========================================================================
    # RUN ARCHIVE: Generate run ID and create run folder
    # ========================================================================
    # Build effective spec for run_id generation (even if no --spec was passed)
    effective_spec = spec.copy() if spec else {}
    if tickers:
        effective_spec["tickers"] = list(tickers)
    if use_intraday:
        effective_spec.setdefault("intraday", {})["enabled"] = True

    run_id = generate_run_id(effective_spec)
    outputs_dir = STUDY_DIR / "outputs"
    run_folder = create_run_folder(outputs_dir, run_id)

    # Set environment variable for child scripts
    run_env = {"DATA_LAB_RUN_OUTPUT_DIR": str(run_folder)}

    print(f"\n{'='*60}")
    print(f"  RUN ARCHIVE: {run_folder.relative_to(STUDY_DIR)}")
    print(f"{'='*60}")

    # Write run_spec.yaml to run folder
    run_spec_path = run_folder / "summary" / "run_spec.yaml"
    effective_spec["_run_id"] = run_id
    effective_spec["_generated_at"] = datetime.now().isoformat()
    with open(run_spec_path, "w", encoding="utf-8") as f:
        yaml.dump(effective_spec, f, default_flow_style=False, sort_keys=False)

    # Also copy to top-level summary for backwards compatibility
    top_summary_dir = outputs_dir / "summary"
    top_summary_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(run_spec_path, top_summary_dir / "run_spec.yaml")

    # Initialize run log
    run_log_lines: list[str] = [
        f"=== Run Archive: {run_id} ===",
        f"Timestamp: {datetime.now().isoformat()}",
        f"Study: trend_chop_gap_quality",
        f"Tickers: {tickers or 'config default'}",
        f"Date range: {start or cfg['start_date']} to {end or cfg.get('end_date', 'today')}",
        f"Intraday: {use_intraday}",
        "",
    ]

    # -- Build shared CLI args for sub-scripts ---------------------------
    sub_args: list[str] = []
    if tickers:
        sub_args.extend(["--tickers"] + list(tickers))
    if start:
        sub_args.extend(["--start", start])
    if end:
        sub_args.extend(["--end", end])

    collect_args = sub_args[:]
    if use_intraday:
        collect_args.extend(["--intraday", "true"])
    elif args.intraday is not None:
        collect_args.extend(["--intraday", args.intraday])

    # -- Print header ----------------------------------------------------
    print(f"{'='*60}")
    print(f"STUDY: trend_chop_gap_quality")
    print(f"Tickers: {tickers or 'config default'}")
    print(f"Date range: {start or cfg['start_date']} to {end or cfg.get('end_date', 'today')}")
    print(f"Intraday: {use_intraday}")
    if spec:
        ev = spec.get("event", {})
        if ev.get("type"):
            ev_str = ev["type"]
            if ev.get("gap_bin_label"):
                ev_str += f" bin {ev['gap_bin_label']}"
            elif ev.get("gap_up_min") is not None:
                ev_str += f" >= {ev['gap_up_min']*100:.0f}%"
            print(f"Event: {ev_str}")
        fh = spec.get("forward_horizons", {})
        if fh.get("horizons"):
            print(f"Horizons: {fh['horizons']}")
    print(f"{'='*60}\n")

    # -- Step 1: Data collection -----------------------------------------
    _run_script("collect_data.py", collect_args, env=run_env)
    run_log_lines.append("Step 1: collect_data.py -- DONE")

    # -- Step 2: Trend/Chop analysis -------------------------------------
    if include_trend_chop:
        _run_script("analyze_trend_chop.py", sub_args, env=run_env)
        run_log_lines.append("Step 2: analyze_trend_chop.py -- DONE")
    else:
        print("Skipping analyze_trend_chop.py (not requested)")
        run_log_lines.append("Step 2: analyze_trend_chop.py -- SKIPPED")

    # -- Step 3: Gap-up close strength -----------------------------------
    if include_gap:
        _run_script("analyze_gapup_close_strength.py", sub_args, env=run_env)
        run_log_lines.append("Step 3: analyze_gapup_close_strength.py -- DONE")
    else:
        print("Skipping analyze_gapup_close_strength.py (not requested)")
        run_log_lines.append("Step 3: analyze_gapup_close_strength.py -- SKIPPED")

    # -- Step 4: Intraday first-hour -------------------------------------
    if include_intraday_fh and use_intraday:
        intraday_files = list((run_folder / "data").glob("*_5Min.csv"))
        if intraday_files:
            _run_script("analyze_intraday_first_hour.py", sub_args, env=run_env)
            run_log_lines.append("Step 4: analyze_intraday_first_hour.py -- DONE")
        else:
            print("Skipping analyze_intraday_first_hour.py (no intraday data files found)")
            run_log_lines.append("Step 4: analyze_intraday_first_hour.py -- SKIPPED (no data)")
    else:
        print("Skipping analyze_intraday_first_hour.py (not requested or intraday=false)")
        run_log_lines.append("Step 4: analyze_intraday_first_hour.py -- SKIPPED")

    # -- Step 5: Forward horizons ----------------------------------------
    if include_forward:
        _run_script("analyze_forward_horizons.py", sub_args, env=run_env)
        run_log_lines.append("Step 5: analyze_forward_horizons.py -- DONE")
    else:
        print("Skipping analyze_forward_horizons.py (not requested)")
        run_log_lines.append("Step 5: analyze_forward_horizons.py -- SKIPPED")

    # ========================================================================
    # Finalize run archive
    # ========================================================================
    run_log_lines.append("")
    run_log_lines.append(f"Run completed: {datetime.now().isoformat()}")
    run_log_lines.append("Exit: success")

    # Write run_log.txt to run folder
    run_log_path = run_folder / "summary" / "run_log.txt"
    run_log_path.write_text("\n".join(run_log_lines), encoding="utf-8")

    # Also append to top-level run_log for backwards compatibility
    top_log_path = top_summary_dir / "run_log.txt"
    with open(top_log_path, "a", encoding="utf-8") as f:
        f.write("\n\n" + "\n".join(run_log_lines))

    # Build manifest.json
    generated_files: list[str] = []
    for subdir in ["data", "tables", "charts", "summary"]:
        subdir_path = run_folder / subdir
        if subdir_path.exists():
            for file in subdir_path.iterdir():
                if file.is_file():
                    generated_files.append(f"{subdir}/{file.name}")

    manifest = {
        "run_id": run_id,
        "study_name": "trend_chop_gap_quality",
        "tickers": list(tickers) if tickers else cfg.get("tickers_default", []),
        "date_range": {
            "start": start or cfg.get("start_date"),
            "end": end or cfg.get("end_date", "today"),
        },
        "intraday_enabled": use_intraday,
        "generated_at": datetime.now().isoformat(),
        "files": sorted(generated_files),
    }

    manifest_path = run_folder / "summary" / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # ========================================================================
    # Copy key aggregates to top-level outputs for backwards compatibility
    # ========================================================================
    top_tables_dir = outputs_dir / "tables"
    top_charts_dir = outputs_dir / "charts"
    top_tables_dir.mkdir(parents=True, exist_ok=True)
    top_charts_dir.mkdir(parents=True, exist_ok=True)

    # Copy aggregate tables
    for pattern in ["*aggregate*.csv", "*summary*.csv"]:
        for f in (run_folder / "tables").glob(pattern):
            shutil.copy2(f, top_tables_dir / f.name)

    # Copy aggregate charts
    for pattern in ["*aggregate*.png", "*summary*.png", "*distribution*.png"]:
        for f in (run_folder / "charts").glob(pattern):
            shutil.copy2(f, top_charts_dir / f.name)

    # Copy summary markdown files
    for f in (run_folder / "summary").glob("*.md"):
        shutil.copy2(f, top_summary_dir / f.name)

    print(f"\n{'='*60}")
    print(f"STUDY COMPLETE: trend_chop_gap_quality")
    print(f"{'='*60}")
    print(f"  Run ID:      {run_id}")
    print(f"  Run folder:  {run_folder.relative_to(STUDY_DIR)}")
    print(f"  Latest:      outputs/LATEST.txt")
    print(f"{'='*60}")
    print(f"  Archive:")
    print(f"    data/    -- raw CSVs")
    print(f"    tables/  -- analysis results")
    print(f"    charts/  -- PNG charts")
    print(f"    summary/ -- run_spec.yaml, run_log.txt, manifest.json")
    print(f"{'='*60}")
    print(f"  Top-level (backwards compat): outputs/tables/, outputs/summary/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
