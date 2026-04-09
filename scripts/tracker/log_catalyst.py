"""
Catalyst Tracker — Log Entry
War Room v10.0 | Charlie OS 5.0

Called automatically by Claude after every War Room analysis.
Lakeem never needs to touch this directly.

Usage (Claude calls this internally):
    python scripts/tracker/log_catalyst.py --json '{"ticker": "NVDA", ...}'

Or interactive:
    python scripts/tracker/log_catalyst.py --interactive
"""

import argparse
import json
import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "catalyst_tracker.db"

CATALYST_TYPES = {
    1:  "EXISTENTIAL DE-RISKING",
    2:  "TAM EXPANSION (SINGLE VERTICAL)",
    3:  "PLATFORM PLAYBOOK",
    4:  "NARRATIVE SHIFT",
    5:  "STRUCTURAL/MECHANICAL",
    6:  "DEFENSIVE",
    7:  "EXPECTATION RESET",
    8:  "MACRO CATALYST",
    9:  "IDENTITY RE-RATING",
    10: "NARRATIVE ACCELERATION",
    11: "COMPETITIVE MOAT EROSION",
    12: "CATALYST SEQUENCE PRIMER",
    13: "REGULATORY MOAT CREATION",
    14: "DILUTION TRAP",
    # Note: War Room uses 1-14; type 2A/2B mapped to 2/3 above
}

EARNINGS_SEASON_MAP = {
    1: "Q4",   # Jan reports = Q4 prior year
    2: "Q4",
    3: "Q4",
    4: "Q1",   # Apr reports = Q1
    5: "Q1",
    6: "Q1",
    7: "Q2",   # Jul reports = Q2
    8: "Q2",
    9: "Q2",
    10: "Q3",  # Oct reports = Q3
    11: "Q3",
    12: "Q3",
}


def get_earnings_season(analysis_date: date) -> str:
    quarter = EARNINGS_SEASON_MAP.get(analysis_date.month, "Q4")
    year = analysis_date.year
    # Q4 reports in Jan-Mar belong to the prior year's Q4
    if analysis_date.month in (1, 2, 3):
        year -= 1
    return f"{quarter}-{year}"


def log(data: dict) -> int:
    """Insert a catalyst entry. Returns the new row id."""
    if not DB_PATH.exists():
        from scripts.tracker.init_db import init_db
        init_db()

    today = data.get("analysis_date", str(date.today()))
    analysis_date = date.fromisoformat(today) if isinstance(today, str) else today

    # Auto-derive earnings season if not supplied
    earnings_season = data.get("earnings_season") or get_earnings_season(analysis_date)

    # Auto-derive conviction tag from score if not supplied
    score = float(data["score_total"])
    if not data.get("conviction_tag"):
        if score >= 8:
            conviction_tag = "HIGH"
        elif score >= 5:
            conviction_tag = "DEVELOPING"
        else:
            conviction_tag = "WEAK"
    else:
        conviction_tag = data["conviction_tag"]

    # Resolve catalyst type label
    ctype = data.get("catalyst_type")
    type_label = data.get("catalyst_type_label") or (CATALYST_TYPES.get(int(ctype)) if ctype else None)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    INSERT INTO catalyst_log (
        analysis_date, ticker, company_name, sector, lifecycle_stage,
        catalyst_type, catalyst_type_label, catalyst_engine, narrative_tier,
        score_realness, score_freshness, score_thesis_impact,
        score_magnitude, score_stacking, score_modifier, modifier_reason,
        score_total, conviction_tag, analyst_tier, macro_context,
        the_one_variable, thesis_summary, catalyst_direction,
        earnings_season, is_earnings
    ) VALUES (
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?,
        ?, ?
    )
    """, (
        str(analysis_date),
        data["ticker"].upper(),
        data.get("company_name"),
        data.get("sector"),
        data.get("lifecycle_stage"),

        ctype,
        type_label,
        data.get("catalyst_engine"),
        data.get("narrative_tier"),

        data.get("score_realness"),
        data.get("score_freshness"),
        data.get("score_thesis_impact"),
        data.get("score_magnitude"),
        data.get("score_stacking"),
        data.get("score_modifier", 0),
        data.get("modifier_reason"),

        score,
        conviction_tag,
        data.get("analyst_tier"),
        data.get("macro_context"),

        data.get("the_one_variable"),
        data.get("thesis_summary"),
        data.get("catalyst_direction"),

        earnings_season,
        int(data.get("is_earnings", False)),
    ))

    row_id = c.lastrowid
    conn.commit()
    conn.close()
    return row_id


def print_confirmation(row_id: int, data: dict):
    score = float(data["score_total"])
    tag = "[HIGH]" if score >= 8 else ("[DEVELOPING]" if score >= 5 else "[WEAK]")
    print(f"\n[OK] Logged -> ID #{row_id}")
    print(f"   {data['ticker'].upper()} | Score: {score}/10 | {tag}")
    print(f"   Engine: {data.get('catalyst_engine', '-')} | Type: {data.get('catalyst_type', '-')}")
    print(f"   DB: {DB_PATH}\n")


def interactive_mode():
    """Guided input for manual logging."""
    print("\n── WAR ROOM CATALYST LOG ──")
    data = {}
    data["ticker"] = input("Ticker: ").strip().upper()
    data["company_name"] = input("Company name (optional): ").strip() or None
    data["analysis_date"] = input(f"Analysis date [{date.today()}]: ").strip() or str(date.today())
    data["sector"] = input("Sector: ").strip() or None
    data["lifecycle_stage"] = input("Lifecycle stage (STAGE 1/2/3/4): ").strip() or None

    print("\nCatalyst Types: 1=Existential De-Risk 2=TAM Expansion 3=Platform Playbook")
    print("4=Narrative Shift 5=Structural/Mech 6=Defensive 7=Expectation Reset")
    print("8=Macro 9=Identity Re-Rating 10=Narrative Accel 11=Moat Erosion")
    print("12=Sequence Primer 13=Reg Moat Creation 14=Dilution Trap")
    ctype = input("Catalyst type (1-14): ").strip()
    data["catalyst_type"] = int(ctype) if ctype else None

    data["catalyst_engine"] = input("Engine (F / M / N / F+M / F+N / ALL THREE): ").strip() or None
    data["score_realness"] = float(input("Realness (0-2): ").strip())
    data["score_freshness"] = float(input("Freshness (0-2): ").strip())
    data["score_thesis_impact"] = float(input("Thesis Impact (0-2): ").strip())
    data["score_magnitude"] = float(input("Magnitude (0-2): ").strip())
    data["score_stacking"] = float(input("Stacking (0-2): ").strip())

    mod = input("Modifier (0 if none, negative number if penalty): ").strip()
    data["score_modifier"] = float(mod) if mod else 0
    if data["score_modifier"] != 0:
        data["modifier_reason"] = input("Modifier reason: ").strip()

    base = (data["score_realness"] + data["score_freshness"] + data["score_thesis_impact"]
            + data["score_magnitude"] + data["score_stacking"])
    data["score_total"] = max(0, round(base + data["score_modifier"], 1))
    print(f"  → Computed total: {data['score_total']}/10")
    confirm = input("Override total? (leave blank to accept): ").strip()
    if confirm:
        data["score_total"] = float(confirm)

    data["macro_context"] = input("Macro context (TAILWIND/HEADWIND/NEUTRAL): ").strip() or None
    data["the_one_variable"] = input("The One Variable: ").strip() or None
    data["thesis_summary"] = input("Thesis summary (1-2 sentences): ").strip() or None
    data["catalyst_direction"] = input("Catalyst direction (LONG/SHORT): ").strip().upper() or None
    data["is_earnings"] = input("Earnings catalyst? (y/n): ").strip().lower() == "y"

    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Log a War Room catalyst analysis")
    parser.add_argument("--json", type=str, help="JSON string with catalyst data")
    parser.add_argument("--interactive", action="store_true", help="Interactive input mode")
    args = parser.parse_args()

    if args.json:
        data = json.loads(args.json)
    elif args.interactive:
        data = interactive_mode()
    else:
        parser.print_help()
        exit(1)

    row_id = log(data)
    print_confirmation(row_id, data)
