#!/usr/bin/env python3
"""
Template: Study Runner
Executes collect_data.py then analyze.py in sequence.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run study end-to-end")
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--intraday", default=None)
    args = parser.parse_args()

    scripts = ["collect_data.py", "analyze.py"]

    for script in scripts:
        script_path = STUDY_DIR / script
        if not script_path.exists():
            print(f"Skipping {script} (not found)")
            continue
        cmd = [sys.executable, str(script_path)]
        print(f"\n{'='*60}")
        print(f"Running: {script}")
        print(f"{'='*60}")
        result = subprocess.run(cmd, cwd=str(STUDY_DIR))
        if result.returncode != 0:
            print(f"ERROR: {script} exited with code {result.returncode}")
            sys.exit(result.returncode)

    print(f"\nAll outputs saved to: {STUDY_DIR / 'outputs'}")


if __name__ == "__main__":
    main()
