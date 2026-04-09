"""
Catalyst Tracker — Log Outcome
War Room v10.0 | Charlie OS 5.0

Updates price follow-through for a previously logged catalyst.
Claude calls this when you say "log the outcome for [TICKER]" or
"update the outcome for ID #X".

Usage:
    python scripts/tracker/log_outcome.py --id 5 --json '{"price_at_analysis": 120.50, "price_1d": 124.00, ...}'
    python scripts/tracker/log_outcome.py --ticker NVDA  (updates most recent entry for NVDA)
    python scripts/tracker/log_outcome.py --list         (shows all entries pending outcomes)
"""

import argparse
import json
import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "catalyst_tracker.db"


def _calc_return(price_entry, price_exit, direction):
    """Return % move in catalyst direction. LONG = up is positive. SHORT = down is positive."""
    if not price_entry or not price_exit:
        return None
    raw = (price_exit - price_entry) / price_entry * 100
    return round(raw if direction != "SHORT" else -raw, 2)


def log_outcome(catalyst_id: int, data: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Fetch catalyst direction for return calculation
    row = c.execute(
        "SELECT catalyst_direction FROM catalyst_log WHERE id = ?", (catalyst_id,)
    ).fetchone()
    direction = row[0] if row else "LONG"

    p0 = data.get("price_at_analysis")
    p1 = data.get("price_1d")
    p3 = data.get("price_3d")
    p5 = data.get("price_5d")
    p10 = data.get("price_10d")
    p20 = data.get("price_20d")

    # Check if outcome row already exists
    existing = c.execute(
        "SELECT id FROM outcomes WHERE catalyst_id = ?", (catalyst_id,)
    ).fetchone()

    if existing:
        c.execute("""
        UPDATE outcomes SET
            updated_at          = CURRENT_TIMESTAMP,
            price_at_analysis   = COALESCE(?, price_at_analysis),
            price_1d            = COALESCE(?, price_1d),
            price_3d            = COALESCE(?, price_3d),
            price_5d            = COALESCE(?, price_5d),
            price_10d           = COALESCE(?, price_10d),
            price_20d           = COALESCE(?, price_20d),
            return_1d           = COALESCE(?, return_1d),
            return_3d           = COALESCE(?, return_3d),
            return_5d           = COALESCE(?, return_5d),
            return_10d          = COALESCE(?, return_10d),
            return_20d          = COALESCE(?, return_20d),
            catalyst_resolved   = COALESCE(?, catalyst_resolved),
            resolution_notes    = COALESCE(?, resolution_notes)
        WHERE catalyst_id = ?
        """, (
            p0, p1, p3, p5, p10, p20,
            _calc_return(p0, p1, direction),
            _calc_return(p0, p3, direction),
            _calc_return(p0, p5, direction),
            _calc_return(p0, p10, direction),
            _calc_return(p0, p20, direction),
            data.get("catalyst_resolved"),
            data.get("resolution_notes"),
            catalyst_id,
        ))
    else:
        c.execute("""
        INSERT INTO outcomes (
            catalyst_id, price_at_analysis, price_1d, price_3d, price_5d, price_10d, price_20d,
            return_1d, return_3d, return_5d, return_10d, return_20d,
            catalyst_resolved, resolution_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            catalyst_id, p0, p1, p3, p5, p10, p20,
            _calc_return(p0, p1, direction),
            _calc_return(p0, p3, direction),
            _calc_return(p0, p5, direction),
            _calc_return(p0, p10, direction),
            _calc_return(p0, p20, direction),
            data.get("catalyst_resolved"),
            data.get("resolution_notes"),
        ))

    conn.commit()
    conn.close()
    print(f"[OK] Outcome updated for catalyst ID #{catalyst_id}")
    if p0 and p5:
        r5 = _calc_return(p0, p5, direction)
        print(f"   5-day return (catalyst direction): {r5:+.2f}%")


def find_latest_id(ticker: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id FROM catalyst_log WHERE ticker = ? ORDER BY analysis_date DESC, id DESC LIMIT 1",
        (ticker.upper(),)
    ).fetchone()
    conn.close()
    if not row:
        raise ValueError(f"No catalyst log found for {ticker.upper()}")
    return row[0]


def list_pending():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
    SELECT cl.id, cl.analysis_date, cl.ticker, cl.score_total, cl.conviction_tag,
           o.price_at_analysis, o.return_5d
    FROM catalyst_log cl
    LEFT JOIN outcomes o ON o.catalyst_id = cl.id
    ORDER BY cl.analysis_date DESC
    LIMIT 50
    """).fetchall()
    conn.close()

    print(f"\n{'ID':>4}  {'Date':<12}  {'Ticker':<8}  {'Score':>5}  {'Tag':<12}  {'Entry':>8}  {'5d%':>7}")
    print("─" * 70)
    for r in rows:
        entry = f"${r[5]:.2f}" if r[5] else "pending"
        ret5 = f"{r[6]:+.2f}%" if r[6] is not None else "pending"
        print(f"{r[0]:>4}  {r[1]:<12}  {r[2]:<8}  {r[3]:>5.1f}  {(r[4] or '—'):<12}  {entry:>8}  {ret5:>7}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Log outcome for a catalyst entry")
    parser.add_argument("--id", type=int, help="Catalyst log ID")
    parser.add_argument("--ticker", type=str, help="Ticker (uses most recent entry)")
    parser.add_argument("--json", type=str, help="JSON with price/outcome data")
    parser.add_argument("--list", action="store_true", help="Show all logged catalysts")
    args = parser.parse_args()

    if args.list:
        list_pending()
    elif args.json:
        outcome_data = json.loads(args.json)
        catalyst_id = args.id or find_latest_id(args.ticker)
        log_outcome(catalyst_id, outcome_data)
    else:
        parser.print_help()
