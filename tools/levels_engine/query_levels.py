#!/usr/bin/env python3
"""
Levels Engine — Natural Language Query Mode.

Produces a FORCED-ACTION MOMENTUM MAP (two lenses: front-week + closest monthly)
for 1–3 tickers.

Usage:
    python tools/levels_engine/query_levels.py TSLA
    python tools/levels_engine/query_levels.py TSLA NVDA SPY

Outputs:
    data/levels/YYYY-MM-DD/QUERY_REPORT_<TICKER>.md
    data/levels/YYYY-MM-DD/query_output_<TICKER>.json
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import date, datetime, timezone
from pathlib import Path

# Ensure package is importable when run as a script
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from levels_engine.config import Config
from levels_engine.logger import setup_logging, get_logger
from levels_engine.providers.alpaca_options import AlpacaOptionsProvider
from levels_engine.sec.edgar_fetch import EdgarFetcher
from levels_engine.sec.arb_extract import extract_arb_levels
from levels_engine.utils.dates import today_str, iso_utc, utcnow
from levels_engine.utils.io import write_json, write_text

from levels_engine.query_compute import (
    analyse_lens,
    build_paths,
    compute_verdict,
    load_arb_levels,
    select_lenses,
    staleness_label,
    _us_market_session,
)
from levels_engine.query_report import (
    build_query_json,
    render_query_md,
)

log = get_logger("query_cli")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Levels Engine — Natural Language Query (Forced-Action Momentum Map)",
    )
    p.add_argument("tickers", nargs="+", help="1–3 stock tickers (e.g. TSLA NVDA SPY)")
    p.add_argument("--skip-sec", action="store_true", help="Skip SEC EDGAR arb scan")
    p.add_argument("--summary", action="store_true",
                   help="Print compact desk snippet (walls + paths + arb) instead of full report")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    tickers = [t.upper().strip() for t in args.tickers[:3]]  # max 3

    # ── Config ───────────────────────────────────────────
    try:
        cfg = Config()
    except EnvironmentError as exc:
        print(f"\n❌ CONFIG ERROR: {exc}\n")
        print("Copy .env.example → .env and fill in your API keys.")
        return 1

    cfg.ensure_dirs()

    date_s = today_str()
    out_dir = cfg.data_dir / date_s
    out_dir.mkdir(parents=True, exist_ok=True)

    setup_logging(out_dir)
    log.info("Query Mode started for %s → %s", tickers, out_dir)

    today = date.fromisoformat(date_s)
    now_utc = utcnow()
    asof = iso_utc(now_utc)
    session = _us_market_session(now_utc)

    # ── Providers ────────────────────────────────────────
    alpaca = AlpacaOptionsProvider(cfg)
    edgar = EdgarFetcher(cfg) if not args.skip_sec else None

    summary_mode = args.summary
    success = 0

    for ticker in tickers:
        log.info("=" * 60)
        log.info("QUERY MODE — %s", ticker)
        log.info("=" * 60)

        try:
            result = _process_ticker(
                ticker, alpaca, edgar, cfg, today, asof, session, out_dir, date_s,
                summary=summary_mode,
            )
            if result:
                success += 1
        except Exception as exc:
            log.error("Query failed for %s: %s", ticker, exc)
            log.debug(traceback.format_exc())

    log.info("=" * 60)
    log.info("DONE — %d/%d tickers", success, len(tickers))
    log.info("=" * 60)

    return 0 if success else 1


def _process_ticker(
    ticker: str,
    alpaca: AlpacaOptionsProvider,
    edgar: EdgarFetcher | None,
    cfg: Config,
    today: date,
    asof: str,
    session: str,
    out_dir: Path,
    date_s: str,
    *,
    summary: bool = False,
) -> bool:
    """Process a single ticker in query mode.  Returns True on success."""

    # A) Spot price
    spot = alpaca.get_spot_price(ticker)
    log.info("%s spot = %.2f", ticker, spot)

    # B) Full chain (all expirations — we filter later by lens)
    contracts = alpaca.get_option_contracts(ticker)
    if not contracts:
        log.error("%s: no option contracts returned", ticker)
        return False

    # C) Lens selection
    front_exp, monthly_exp, monthly_proxy = select_lenses(contracts, today)
    log.info("%s lenses: front_week=%s  monthly=%s (proxy=%s)",
             ticker, front_exp, monthly_exp, monthly_proxy)

    if not front_exp and not monthly_exp:
        log.error("%s: could not determine any expiration lens", ticker)
        return False

    # D) Per-lens analysis
    lens_a = analyse_lens(contracts, spot, front_exp, cfg) if front_exp else {
        "expiration": "N/A", "levels": [], "iv_atm": None, "iv_near_median": None, "snapshot_date": None,
    }
    lens_b = analyse_lens(contracts, spot, monthly_exp, cfg) if monthly_exp else {
        "expiration": "N/A", "levels": [], "iv_atm": None, "iv_near_median": None, "snapshot_date": None,
    }

    staleness_a = staleness_label(lens_a.get("snapshot_date"), today)
    staleness_b = staleness_label(lens_b.get("snapshot_date"), today)

    # E) Arb / SEC levels
    arb_raw: list = []
    if edgar:
        try:
            filings = edgar.get_filings(ticker)
            arb_output = extract_arb_levels(ticker, filings, cfg)
            arb_raw = [lv.model_dump() if hasattr(lv, "model_dump") else lv
                       for lv in (arb_output.verified_levels + arb_output.candidates)]
        except Exception as exc:
            log.warning("SEC/arb extraction for %s: %s", ticker, exc)

    # Also try loading from today's existing run
    if not arb_raw:
        arb_raw = load_arb_levels(ticker, cfg.data_dir, date_s)

    # Inject arb levels into both lens level lists (tagged as ARB)
    for a in arb_raw:
        arb_entry = {
            "strike": a.get("level", 0),
            "type": "ARB LEVEL",
            "side": "above" if a.get("level", 0) >= spot else "below",
            "oi": 0,
            "volume": 0,
            "who_is_forced": "Non-options mechanical level; event/structure participants may defend/press around this price.",
            "breach": "If breached, structural participants may accelerate positioning around this price.",
            "rejection": "On rejection, structural participants may defend this price, especially near catalyst dates.",
        }
        lens_a["levels"].append(arb_entry)
        lens_b["levels"].append(arb_entry)

    # F) Paths
    paths_a = build_paths(lens_a.get("levels", []), spot)
    paths_b = build_paths(lens_b.get("levels", []), spot)

    # G) Verdict
    verdict = compute_verdict(
        lens_a.get("levels", []),
        lens_b.get("levels", []),
        spot,
    )

    # H) Diagnostics
    diag = {
        "total_contracts_fetched": len(contracts),
        "front_week_contracts": len([c for c in contracts if c.get("expiration") == front_exp]),
        "monthly_contracts": len([c for c in contracts if c.get("expiration") == monthly_exp]),
        "front_week_levels": len(lens_a.get("levels", [])),
        "monthly_levels": len(lens_b.get("levels", [])),
        "arb_levels_count": len(arb_raw),
        "iv_available": lens_a.get("iv_atm") is not None or lens_b.get("iv_atm") is not None,
    }

    # ── Write Markdown ───────────────────────────────────
    md = render_query_md(
        ticker=ticker,
        spot=spot,
        asof_utc=asof,
        session=session,
        lens_a=lens_a,
        lens_b=lens_b,
        monthly_proxy=monthly_proxy,
        staleness_a=staleness_a,
        staleness_b=staleness_b,
        arb_levels=arb_raw,
        arb_lookback_days=cfg.sec_lookback_days,
        paths_a=paths_a,
        paths_b=paths_b,
        verdict=verdict,
    )
    md_path = out_dir / f"QUERY_REPORT_{ticker}.md"
    write_text(md, md_path)

    # ── Write JSON ───────────────────────────────────────
    jdata = build_query_json(
        ticker=ticker,
        spot=spot,
        asof_utc=asof,
        session=session,
        lens_a=lens_a,
        lens_b=lens_b,
        monthly_proxy=monthly_proxy,
        staleness_a=staleness_a,
        staleness_b=staleness_b,
        arb_levels=arb_raw,
        paths_a=paths_a,
        paths_b=paths_b,
        verdict=verdict,
        diagnostics=diag,
    )
    json_path = out_dir / f"query_output_{ticker}.json"
    write_json(jdata, json_path)

    # ── Desk snippet (always built, used in --summary mode) ─
    snippet = _build_desk_snippet(
        ticker=ticker, spot=spot, asof=asof,
        lens_a=lens_a, lens_b=lens_b,
        monthly_proxy=monthly_proxy,
        paths_a=paths_a, paths_b=paths_b,
        arb_raw=arb_raw,
    )
    snippet_path = out_dir / f"DESK_SNIPPET_{ticker}.txt"
    write_text(snippet, snippet_path)

    # ── Print to console ─────────────────────────────────
    if summary:
        print(snippet)
    else:
        print(md)
    print(f"\n📄 Report:  {md_path}")
    print(f"📊 JSON:    {json_path}")
    print(f"📋 Snippet: {snippet_path}")

    return True


# ────────────────────────────────────────────────────────────
# DESK SNIPPET BUILDER
# ────────────────────────────────────────────────────────────

def _find_wall(levels: list, tag: str) -> dict | None:
    """Find the highest-OI level matching *tag* (CALL WALL or PUT WALL)."""
    candidates = [lv for lv in levels if lv.get("type") == tag and lv.get("oi", 0) > 0]
    if not candidates:
        return None
    return max(candidates, key=lambda lv: lv.get("oi", 0))


def _fmt_path(strikes: list, spot: float) -> str:
    if not strikes:
        return "none"
    nodes = [f"${spot:,.2f}"] + [f"${s:,.2f}" for s in strikes[:5]]
    return " -> ".join(nodes)


def _build_desk_snippet(
    *,
    ticker: str,
    spot: float,
    asof: str,
    lens_a: dict,
    lens_b: dict,
    monthly_proxy: bool,
    paths_a: dict,
    paths_b: dict,
    arb_raw: list,
) -> str:
    """Compact desk snippet — walls, paths, verified arb only."""
    lines: list[str] = []

    lines.append(f"{ticker} (as-of {asof}, spot ${spot:,.2f}):")

    # ── Front week ───────────────────────────────────────
    exp_a = lens_a.get("expiration", "N/A")
    lines.append(f"FRONT WEEK (EXP {exp_a}):")
    cw_a = _find_wall(lens_a.get("levels", []), "CALL WALL")
    pw_a = _find_wall(lens_a.get("levels", []), "PUT WALL")
    cw_a_s = f"${cw_a['strike']:,.2f} (OI {cw_a['oi']:,})" if cw_a else "none"
    pw_a_s = f"${pw_a['strike']:,.2f} (OI {pw_a['oi']:,})" if pw_a else "none"
    lines.append(f"  PUT WALL: {pw_a_s} | CALL WALL: {cw_a_s}")
    lines.append(f"  UPSIDE PATH: {_fmt_path(paths_a.get('upside', []), spot)}")
    lines.append(f"  DOWNSIDE PATH: {_fmt_path(paths_a.get('downside', []), spot)}")

    # ── Monthly ──────────────────────────────────────────
    exp_b = lens_b.get("expiration", "N/A")
    monthly_label = "MONTHLY PROXY" if monthly_proxy else f"EXP {exp_b}"
    lines.append(f"MONTHLY ({monthly_label}):")
    cw_b = _find_wall(lens_b.get("levels", []), "CALL WALL")
    pw_b = _find_wall(lens_b.get("levels", []), "PUT WALL")
    cw_b_s = f"${cw_b['strike']:,.2f} (OI {cw_b['oi']:,})" if cw_b else "none"
    pw_b_s = f"${pw_b['strike']:,.2f} (OI {pw_b['oi']:,})" if pw_b else "none"
    lines.append(f"  PUT WALL: {pw_b_s} | CALL WALL: {cw_b_s}")
    lines.append(f"  UPSIDE PATH: {_fmt_path(paths_b.get('upside', []), spot)}")
    lines.append(f"  DOWNSIDE PATH: {_fmt_path(paths_b.get('downside', []), spot)}")

    # ── Arb / contractual ────────────────────────────────
    verified = [a for a in arb_raw if a.get("document_url") or a.get("filing_url")]
    if verified:
        lines.append("ARB/CONTRACTUAL (VERIFIED):")
        for a in verified:
            level = a.get("level", 0)
            label = a.get("label", "")
            ftype = a.get("filing_type", "")
            fdate = a.get("filing_date", "")
            url = a.get("document_url") or a.get("filing_url") or ""
            lines.append(f"  - ${level:,.2f} ({label}) | Filing: {ftype} {fdate} | Source: {url}")
    else:
        lines.append("ARB/CONTRACTUAL (VERIFIED): NONE")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
