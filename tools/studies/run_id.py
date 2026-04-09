#!/usr/bin/env python3
"""
run_id.py -- Deterministic Run ID Generator for the Studies Infrastructure.

Generates a unique, human-readable run identifier based on:
- Timestamp: local system time in YYYY-MM-DD_HHMM
- Tickers: joined with "-" (max 3 shown, else "MULTI")
- Key condition summary (gap threshold, horizons, etc.)
- Intraday flag suffix if enabled

Example:
    2026-02-15_0732_NVDA_gap5p_D5-10_intra

This module also provides utilities for:
- Creating run archive directories
- Managing LATEST.txt pointers
- Collision handling with suffix increments (_02, _03, etc.)

Usage:
    from run_id import generate_run_id, create_run_folder
    run_id = generate_run_id(spec)
    run_folder = create_run_folder(study_outputs_dir, run_id)
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Union


def generate_run_id(spec: dict) -> str:
    """
    Generate a deterministic RUN_ID from a study run spec.

    Components:
    - timestamp: YYYY-MM-DD_HHMM (local time)
    - tickers: joined with "-" (max 3, else "MULTI")
    - condition: gap threshold (gap5p) or window (D5-10) or horizons
    - intraday: "_intra" suffix if enabled

    Args:
        spec: The study run spec dictionary containing:
            - tickers: list of ticker symbols
            - event: dict with gap_up_min, type, etc.
            - forward_horizons: dict with window or horizons
            - intraday: dict with enabled flag

    Returns:
        A string like "2026-02-15_0732_NVDA_gap5p_D5-10_intra"
    """
    parts: list[str] = []

    # 1) Timestamp: YYYY-MM-DD_HHMM
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    parts.append(ts)

    # 2) Tickers
    tickers = spec.get("tickers") or []
    if not tickers:
        ticker_part = "ALL"
    elif len(tickers) <= 3:
        ticker_part = "-".join(tickers)
    else:
        ticker_part = "MULTI"
    parts.append(ticker_part)

    # 3) Condition summary
    condition_parts: list[str] = []

    # 3a) Gap threshold
    event = spec.get("event", {})
    gap_up_min = event.get("gap_up_min")
    if gap_up_min is not None:
        # Convert to percentage integer: 0.05 -> "gap5p"
        pct = int(gap_up_min * 100)
        condition_parts.append(f"gap{pct}p")

    # 3b) Forward horizons window or explicit horizons
    fh = spec.get("forward_horizons", {})
    window = fh.get("window")
    horizons = fh.get("horizons")

    if window:
        start = window.get("start", 1)
        end = window.get("end", 10)
        condition_parts.append(f"D{start}-{end}")
    elif horizons:
        # Truncate to reasonable length
        h_str = "-".join(str(h) for h in horizons[:4])
        if len(horizons) > 4:
            h_str += "+"
        condition_parts.append(f"D{h_str}")

    if condition_parts:
        parts.append("_".join(condition_parts))

    # 4) Intraday flag
    intraday_cfg = spec.get("intraday", {})
    if intraday_cfg.get("enabled", False):
        parts.append("intra")

    # Join all parts with underscore
    run_id = "_".join(parts)

    # Sanitize: remove any characters that are problematic for filenames
    run_id = re.sub(r'[<>:"/\\|?*]', '', run_id)

    return run_id


def _find_unique_folder(runs_dir: Path, run_id: str) -> Path:
    """
    Find a unique folder path, appending suffix if collision exists.

    If runs_dir/run_id exists, tries run_id_02, run_id_03, etc.

    Args:
        runs_dir: The runs/ directory path
        run_id: The base run ID

    Returns:
        Path to a folder that doesn't exist yet
    """
    candidate = runs_dir / run_id
    if not candidate.exists():
        return candidate

    # Collision: find next available suffix
    suffix = 2
    while True:
        suffixed_id = f"{run_id}_{suffix:02d}"
        candidate = runs_dir / suffixed_id
        if not candidate.exists():
            return candidate
        suffix += 1
        if suffix > 99:
            raise RuntimeError(f"Too many collisions for run_id: {run_id}")


def create_run_folder(study_outputs_dir: Union[str, Path], run_id: str) -> Path:
    """
    Create the run archive folder structure.

    Creates:
        outputs/runs/<RUN_ID>/
            data/
            tables/
            charts/
            summary/

    Also updates outputs/LATEST.txt with the relative path to the new run.

    Args:
        study_outputs_dir: Path to the study's outputs/ directory
        run_id: The generated run ID

    Returns:
        Path to the created run folder (outputs/runs/<RUN_ID>/)
    """
    outputs_dir = Path(study_outputs_dir)
    runs_dir = outputs_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    # Find unique folder (handle collisions)
    run_folder = _find_unique_folder(runs_dir, run_id)

    # Create subdirectories
    for subdir in ["data", "tables", "charts", "summary"]:
        (run_folder / subdir).mkdir(parents=True, exist_ok=True)

    # Update LATEST.txt
    latest_path = outputs_dir / "LATEST.txt"
    relative_run_path = run_folder.relative_to(outputs_dir)
    latest_path.write_text(f"{relative_run_path}/\n", encoding="utf-8")

    # Try to create symlink (may fail on Windows without admin privileges)
    symlink_path = outputs_dir / "latest"
    try:
        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()
        symlink_path.symlink_to(run_folder, target_is_directory=True)
    except OSError:
        # Symlink creation failed (common on Windows without developer mode)
        # Fall back silently to LATEST.txt only
        pass

    return run_folder


def get_run_output_dir() -> Path | None:
    """
    Get the run output directory from environment variable.

    Returns:
        Path to run output dir if DATA_LAB_RUN_OUTPUT_DIR is set, else None
    """
    env_val = os.environ.get("DATA_LAB_RUN_OUTPUT_DIR")
    if env_val:
        return Path(env_val)
    return None


def resolve_output_dirs(study_dir: Path) -> tuple[Path, Path, Path, Path]:
    """
    Resolve output directories, checking for run archive env var first.

    If DATA_LAB_RUN_OUTPUT_DIR is set, use that as base.
    Otherwise, use study_dir/outputs/ (backwards compatible).

    Args:
        study_dir: Path to the study directory

    Returns:
        Tuple of (data_dir, tables_dir, charts_dir, summary_dir)
    """
    run_output_dir = get_run_output_dir()

    if run_output_dir:
        base = run_output_dir
    else:
        base = study_dir / "outputs"

    return (
        base / "data",
        base / "tables",
        base / "charts",
        base / "summary",
    )


if __name__ == "__main__":
    # Quick test
    test_spec = {
        "tickers": ["NVDA"],
        "event": {"type": "gap_up", "gap_up_min": 0.05},
        "forward_horizons": {"window": {"start": 5, "end": 10}},
        "intraday": {"enabled": True},
    }
    print(f"Test run_id: {generate_run_id(test_spec)}")
