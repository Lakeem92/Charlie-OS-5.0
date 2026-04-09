"""
Human-readable Markdown report generator.
"""
from __future__ import annotations

from typing import Optional

from .schemas import ArbLevelsOutput, OptionsLevelsOutput


def generate_report(
    opts: Optional[OptionsLevelsOutput],
    arb: Optional[ArbLevelsOutput],
) -> str:
    """Produce a combined Markdown report for one ticker."""
    parts: list[str] = []

    ticker = (opts.ticker if opts else arb.ticker if arb else "UNKNOWN")
    parts.append(f"# LEVELS REPORT — {ticker}")
    parts.append("")

    # ── 1. Snapshot ──────────────────────────────────────
    parts.append("## 1) Snapshot")
    if opts:
        parts.append(f"- **Ticker:** {opts.ticker}")
        parts.append(f"- **Spot:** ${opts.spot:,.2f}")
        parts.append(f"- **As-of (UTC):** {opts.asof_utc}")
        parts.append(f"- **Window:** {opts.window_days} days, "
                     f"{opts.expirations_considered} expirations")
        parts.append("")

        if opts.call_wall:
            parts.append(f"- **CALL WALL:** ${opts.call_wall.strike:,.2f}  "
                         f"(OI: {opts.call_wall.call_oi:,})")
        else:
            parts.append("- **CALL WALL:** N/A")

        if opts.put_wall:
            parts.append(f"- **PUT WALL:** ${opts.put_wall.strike:,.2f}  "
                         f"(OI: {opts.put_wall.put_oi:,})")
        else:
            parts.append("- **PUT WALL:** N/A")
        parts.append("")

        # Pin candidates
        if opts.pin_candidates:
            parts.append("### Pin / Magnet Candidates")
            parts.append("| Strike | Total OI | Balance |")
            parts.append("|-------:|---------:|--------:|")
            for p in opts.pin_candidates[:5]:
                parts.append(f"| ${p.strike:,.2f} | {p.total_oi:,} | {p.balance:.4f} |")
            parts.append("")

        # Vacuum windows
        if opts.vacuum_windows:
            parts.append("### Vacuum Windows (low-OI gaps near spot)")
            parts.append("| Low | High | Avg OI | Distance |")
            parts.append("|----:|-----:|-------:|---------:|")
            for v in opts.vacuum_windows[:5]:
                parts.append(f"| ${v.low_strike:,.2f} | ${v.high_strike:,.2f} "
                             f"| {v.avg_oi:,.1f} | {v.distance_from_spot:,.2f} |")
            parts.append("")
    else:
        parts.append("_Options data unavailable._")
        parts.append("")

    # ── 2. Options Ladder ────────────────────────────────
    parts.append("## 2) Options Ladder")
    if opts:
        # Top calls
        if opts.top_call_clusters:
            parts.append("### Top Call OI Strikes")
            parts.append("| Strike | Call OI | Put OI | Total OI |")
            parts.append("|-------:|--------:|-------:|---------:|")
            for s in opts.top_call_clusters[:10]:
                parts.append(f"| ${s.strike:,.2f} | {s.call_oi:,} | {s.put_oi:,} | {s.total_oi:,} |")
            parts.append("")

        # Top puts
        if opts.top_put_clusters:
            parts.append("### Top Put OI Strikes")
            parts.append("| Strike | Call OI | Put OI | Total OI |")
            parts.append("|-------:|--------:|-------:|---------:|")
            for s in opts.top_put_clusters[:10]:
                parts.append(f"| ${s.strike:,.2f} | {s.call_oi:,} | {s.put_oi:,} | {s.total_oi:,} |")
            parts.append("")

        # Near-spot
        if opts.near_spot_levels:
            parts.append("### Near-Spot High OI Strikes")
            parts.append("| Strike | Call OI | Put OI | Total OI |")
            parts.append("|-------:|--------:|-------:|---------:|")
            for s in opts.near_spot_levels[:10]:
                parts.append(f"| ${s.strike:,.2f} | {s.call_oi:,} | {s.put_oi:,} | {s.total_oi:,} |")
            parts.append("")
    else:
        parts.append("_Options data unavailable._")
        parts.append("")

    # ── 3. Contractual / Arb Levels ─────────────────────
    parts.append("## 3) Contractual / Arb Levels (SEC EDGAR)")
    if arb and (arb.verified_levels or arb.candidates):
        if arb.verified_levels:
            parts.append("### Verified Levels")
            parts.append("| Level | Type | Filing | Date | Confidence | Snippet |")
            parts.append("|------:|------|--------|------|------------|---------|")
            for lv in arb.verified_levels:
                snip = lv.context_snippet[:80].replace("|", "\\|")
                url = f"[link]({lv.document_url})" if lv.document_url else ""
                parts.append(f"| ${lv.level:,.2f} | {lv.label} | {lv.filing_type} | "
                             f"{lv.filing_date} | {lv.confidence:.2f} | {snip} {url} |")
            parts.append("")

        if arb.candidates:
            parts.append("### Candidate Levels (below confidence threshold)")
            parts.append("| Level | Type | Filing | Date | Confidence |")
            parts.append("|------:|------|--------|------|------------|")
            for lv in arb.candidates[:15]:
                parts.append(f"| ${lv.level:,.2f} | {lv.label} | {lv.filing_type} "
                             f"| {lv.filing_date} | {lv.confidence:.2f} |")
            parts.append("")
    else:
        lookback = arb.lookback_days if arb else "N/A"
        parts.append(f"_No verified contractual levels found in last {lookback} days._")
        parts.append("")

    # ── 4. Diagnostics ──────────────────────────────────
    parts.append("## 4) Diagnostics")
    if opts:
        d = opts.diagnostics
        parts.append(f"- Contracts pulled: **{d.contracts_count:,}**")
        parts.append(f"- Expirations: **{d.expirations_count}**")
        parts.append(f"- Missing OI (set to 0): **{d.missing_oi_count:,}**")
    if arb:
        da = arb.diagnostics
        parts.append(f"- Filings scanned: **{da.filings_scanned}**")
        parts.append(f"- Raw price matches: **{da.matches_found}**")
    parts.append("")
    parts.append("---")
    parts.append(f"_Generated by Levels Engine v0.1.0_")
    parts.append("")

    return "\n".join(parts)
