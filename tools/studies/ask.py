#!/usr/bin/env python3
"""
ask.py -- The single English entrypoint for the Studies Infrastructure.

Lakeem speaks plain English. No flags, no CLI args beyond the question.

Usage:
    python tools/studies/ask.py "when NVDA gaps up 5%+ does it trend or chop and what's the win rate D5-D10"
    python tools/studies/ask.py "trend vs chop mix for TSLA in uptrends"
    python tools/studies/ask.py "gap up 3-5% close strong probability for META"
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import yaml
from pathlib import Path
from datetime import datetime

TOOLS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TOOLS_DIR.parent.parent

# Ensure tools/studies is on the path for nl_parse import
sys.path.insert(0, str(TOOLS_DIR))
from nl_parse import parse_query

REGISTRY_PATH = TOOLS_DIR / "studies_registry.yaml"


def _load_registry() -> dict:
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _print_header(spec: dict) -> None:
    """Print a human-friendly summary of what was parsed."""
    print()
    print("=" * 60)
    print("  STUDIES ENGINE -- Natural Language Router")
    print("=" * 60)
    print()
    print(f"  Query:    {spec['query']}")
    print(f"  Study:    {spec['study']}")
    print(f"  Tickers:  {', '.join(spec['tickers']) if spec['tickers'] else 'study defaults'}")

    # Event
    ev = spec.get("event", {})
    if ev.get("type"):
        ev_str = ev["type"]
        if ev.get("gap_bin_label"):
            ev_str += f" bin {ev['gap_bin_label']}"
        elif ev.get("gap_up_min") is not None:
            ev_str += f" >= {ev['gap_up_min']*100:.0f}%"
        print(f"  Event:    {ev_str}")
    else:
        print(f"  Event:    none (all days)")

    # Horizons
    fh = spec.get("forward_horizons", {})
    if fh.get("window"):
        w = fh["window"]
        print(f"  Forward:  D{w['start']}-D{w['end']}")
    if fh.get("horizons"):
        print(f"  Horizons: {fh['horizons']}")
    if fh.get("metrics"):
        print(f"  Metrics:  {', '.join(fh['metrics'])}")

    # Intraday
    intra = spec.get("intraday", {}).get("enabled", False)
    print(f"  Intraday: {'enabled' if intra else 'disabled'}")

    # Date range
    dr = spec.get("date_range", {})
    start_str = dr.get("start") or "config default"
    end_str = dr.get("end") or "today"
    print(f"  Dates:    {start_str} to {end_str}")

    # Modules
    outs = spec.get("outputs", {})
    modules = []
    if outs.get("include_trend_chop_mix"):
        modules.append("trend_chop")
    if outs.get("include_gap_close_strength"):
        modules.append("gap_close_strength")
    if outs.get("include_intraday_first_hour"):
        modules.append("intraday_first_hour")
    if outs.get("include_forward_horizons"):
        modules.append("forward_horizons")
    print(f"  Modules:  {', '.join(modules) if modules else 'all defaults'}")

    print()
    print("-" * 60)


def _resolve_entrypoint(spec: dict) -> Path:
    """Find the run_study.py for the matched study."""
    registry = _load_registry()
    studies = registry.get("studies", {})
    study_cfg = studies.get(spec["study"], {})
    entrypoint = study_cfg.get("entrypoint", "")
    if entrypoint:
        return ROOT_DIR / entrypoint
    # Fallback: try conventional path
    return ROOT_DIR / "studies" / spec["study"] / "run_study.py"


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python tools/studies/ask.py \"your question in plain English\"")
        print()
        print("Examples:")
        print('  python tools/studies/ask.py "when NVDA gaps up 5%+ does it trend or chop and what\'s the win rate D5-D10"')
        print('  python tools/studies/ask.py "trend vs chop mix for TSLA in uptrends"')
        print('  python tools/studies/ask.py "gap up 3-5% close strong probability for META"')
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    # A) Parse into spec
    spec = parse_query(query)

    # B) Print human-friendly summary
    _print_header(spec)

    # C) Write spec to a temp file and pass to study
    spec_dir = ROOT_DIR / "studies" / spec["study"] / "outputs" / "summary"
    spec_dir.mkdir(parents=True, exist_ok=True)

    spec_path = spec_dir / "run_spec.yaml"
    spec["_generated_at"] = datetime.now().isoformat()
    with open(spec_path, "w", encoding="utf-8") as f:
        yaml.dump(spec, f, default_flow_style=False, sort_keys=False)
    print(f"  Spec written to: {spec_path.relative_to(ROOT_DIR)}")
    print()

    # D) Run the study via --spec
    entrypoint = _resolve_entrypoint(spec)
    if not entrypoint.exists():
        print(f"ERROR: study entrypoint not found: {entrypoint}", file=sys.stderr)
        sys.exit(1)

    cmd = [sys.executable, str(entrypoint), "--spec", str(spec_path)]
    study_dir = entrypoint.parent

    print(f"  Running:  python {entrypoint.relative_to(ROOT_DIR)} --spec {spec_path.relative_to(ROOT_DIR)}")
    print("=" * 60)
    print()

    result = subprocess.run(cmd, cwd=str(study_dir))

    # E) Read LATEST.txt to find the run archive path
    outputs_dir = study_dir / "outputs"
    latest_file = outputs_dir / "LATEST.txt"
    run_archive_path = None
    if latest_file.exists():
        run_archive_path = latest_file.read_text(encoding="utf-8").strip()

    print()
    print("=" * 60)
    print(f"  DONE -- {spec['study']}")
    if run_archive_path:
        print(f"  Run archived at: {(study_dir / 'outputs' / run_archive_path).relative_to(ROOT_DIR)}")
        print(f"  Latest pointer:  {latest_file.relative_to(ROOT_DIR)}")
    print(f"  Top-level:       {outputs_dir.relative_to(ROOT_DIR)}")
    print("=" * 60)

    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
