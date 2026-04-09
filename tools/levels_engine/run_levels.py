#!/usr/bin/env python3
"""
Levels Engine — CLI entry point.

Usage:
    python tools/levels_engine/run_levels.py TSLA NVDA
    python tools/levels_engine/run_levels.py SPY --window-days 45

Outputs are written to:
    data/levels/YYYY-MM-DD/
"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

# Ensure package is importable when run as a script
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from levels_engine.config import Config
from levels_engine.logger import setup_logging, get_logger
from levels_engine.providers.alpaca_options import AlpacaOptionsProvider
from levels_engine.compute_options_levels import compute_options_levels, build_strike_csv
from levels_engine.sec.edgar_fetch import EdgarFetcher
from levels_engine.sec.arb_extract import extract_arb_levels
from levels_engine.report_md import generate_report
from levels_engine.utils.dates import today_str
from levels_engine.utils.io import write_json, write_csv, write_text

log = get_logger("cli")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Levels Engine — deterministic key levels from options & SEC filings",
    )
    p.add_argument("tickers", nargs="+", help="One or more stock tickers (e.g. SPY TSLA)")
    p.add_argument("--window-days", type=int, default=None,
                   help="Override options expiry window (default: 60)")
    p.add_argument("--skip-sec", action="store_true",
                   help="Skip SEC EDGAR filing scan")
    p.add_argument("--skip-options", action="store_true",
                   help="Skip options chain fetch")
    p.add_argument("--doctor", action="store_true",
                   help="Run diagnostics (doctor.py) before the pipeline")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    tickers = [t.upper().strip() for t in args.tickers]

    # ── Doctor mode ──────────────────────────────────────
    if args.doctor:
        import subprocess
        doctor_path = Path(__file__).resolve().parent / "doctor.py"
        result = subprocess.run([sys.executable, str(doctor_path)])
        if result.returncode != 0:
            print("\nDoctor found issues. Fix them before running the pipeline.")
            return 1
        print("\nDoctor passed. Continuing to pipeline...\n")

    # ── Config ───────────────────────────────────────────
    try:
        cfg = Config()
    except EnvironmentError as exc:
        print(f"\n❌ CONFIG ERROR: {exc}\n")
        print("Copy .env.example → .env and fill in your API keys.")
        return 1

    if args.window_days:
        # Override via a new Config with the altered window
        cfg = Config(options_expiry_window_days=args.window_days)

    cfg.ensure_dirs()

    # ── Output directory ─────────────────────────────────
    date_str = today_str()
    out_dir = cfg.data_dir / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    setup_logging(out_dir)
    log.info("Levels Engine started for %s → %s", tickers, out_dir)

    # ── Providers ────────────────────────────────────────
    alpaca = AlpacaOptionsProvider(cfg) if not args.skip_options else None
    edgar = EdgarFetcher(cfg) if not args.skip_sec else None

    success_count = 0
    all_paths: list[str] = []

    for ticker in tickers:
        log.info("=" * 60)
        log.info("Processing %s", ticker)
        log.info("=" * 60)

        opts_output = None
        arb_output = None

        # ── A) Options levels ────────────────────────────
        if alpaca:
            try:
                spot = alpaca.get_spot_price(ticker)
                contracts = alpaca.get_option_contracts(ticker)
                opts_output = compute_options_levels(ticker, spot, contracts, cfg)

                # Write options JSON
                opts_path = out_dir / f"options_levels_{ticker}.json"
                write_json(opts_output.model_dump(), opts_path)
                all_paths.append(str(opts_path))

                # Write strike CSV
                csv_df = build_strike_csv(contracts)
                csv_path = out_dir / f"options_levels_{ticker}.csv"
                write_csv(csv_df, csv_path)
                opts_output.raw_csv_path = str(csv_path)
                all_paths.append(str(csv_path))

            except Exception as exc:
                _handle_provider_error(exc, "Options", ticker)
                log.debug(traceback.format_exc())

        # ── B) SEC arb levels ────────────────────────────
        if edgar:
            try:
                filings = edgar.get_filings(ticker)
                arb_output = extract_arb_levels(ticker, filings, cfg)

                arb_path = out_dir / f"arb_levels_{ticker}.json"
                write_json(arb_output.model_dump(), arb_path)
                all_paths.append(str(arb_path))

            except Exception as exc:
                log.error("SEC/arb extraction failed for %s: %s", ticker, exc)
                log.debug(traceback.format_exc())

        # ── C) Combined report ───────────────────────────
        if opts_output or arb_output:
            report = generate_report(opts_output, arb_output)
            rpt_path = out_dir / f"LEVELS_REPORT_{ticker}.md"
            write_text(report, rpt_path)
            all_paths.append(str(rpt_path))
            success_count += 1
        else:
            log.warning("%s: no data produced (both options and SEC failed)", ticker)

    # ── Summary ──────────────────────────────────────────
    log.info("=" * 60)
    log.info("DONE — %d/%d tickers processed", success_count, len(tickers))
    for p in all_paths:
        log.info("  → %s", p)
    log.info("=" * 60)

    if success_count == 0 and len(tickers) > 0:
        log.error("All tickers failed. Check API keys and connectivity.")
        log.error("Run:  python tools/levels_engine/doctor.py   for diagnostics.")
        return 2

    return 0


def _handle_provider_error(exc: Exception, stage: str, ticker: str) -> None:
    """Print actionable guidance for common HTTP errors."""
    msg = str(exc)
    log.error("%s fetch/compute failed for %s: %s", stage, ticker, exc)
    if "401" in msg:
        log.error(
            "  → 401 = authentication rejected. Your Alpaca keys may be wrong "
            "or not loaded into the environment."
        )
        log.error("  → Run:  python tools/levels_engine/doctor.py")
    elif "403" in msg:
        log.error(
            "  → 403 = forbidden. Your Alpaca plan may not include this data "
            "(e.g., options requires OPRA subscription)."
        )
        log.error("  → Run:  python tools/levels_engine/doctor.py")
    elif "429" in msg:
        log.error("  → 429 = rate limited. Wait a minute and retry.")


if __name__ == "__main__":
    sys.exit(main())
