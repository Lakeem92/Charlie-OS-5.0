"""
Catalyst Tracker -- Pattern Analysis
War Room v10.0 | Charlie OS 5.0

Run this when you want to find patterns in your catalyst log.
Claude calls this when you ask questions like:
  "How did my high conviction calls perform this earnings season?"
  "Which catalyst types have the best 5-day follow-through?"
  "Show me all Type 1 catalysts from Q1-2026"

Usage:
    python scripts/tracker/query_patterns.py --report earnings_season --season Q1-2026
    python scripts/tracker/query_patterns.py --report by_type
    python scripts/tracker/query_patterns.py --report by_score_bucket
    python scripts/tracker/query_patterns.py --report by_engine
    python scripts/tracker/query_patterns.py --report recent --n 20
    python scripts/tracker/query_patterns.py --report ticker --ticker NVDA
    python scripts/tracker/query_patterns.py --report full_summary
"""

import argparse
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "catalyst_tracker.db"


def get_conn():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run init_db.py first.")
    return sqlite3.connect(DB_PATH)


def fmt_pct(val):
    if val is None:
        return "  n/a  "
    return f"{val:+6.2f}%"


def fmt_score(val):
    if val is None:
        return " - "
    return f"{val:.1f}"


def header(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


# ── REPORTS ─────────────────────────────────────────────────────────────────

def report_recent(n=20):
    conn = get_conn()
    rows = conn.execute(f"""
    SELECT cl.id, cl.analysis_date, cl.ticker, cl.score_total, cl.conviction_tag,
           cl.catalyst_type, cl.catalyst_engine,
           o.return_1d, o.return_3d, o.return_5d, o.return_10d, o.catalyst_resolved
    FROM catalyst_log cl
    LEFT JOIN outcomes o ON o.catalyst_id = cl.id
    ORDER BY cl.analysis_date DESC, cl.id DESC
    LIMIT {int(n)}
    """).fetchall()
    conn.close()

    header(f"RECENT {n} CATALYSTS")
    print(f"{'ID':>4}  {'Date':<11} {'Ticker':<7} {'Sc':>4}  {'Tag':<11} {'Eng':<10} {'1d':>7} {'3d':>7} {'5d':>7} {'10d':>7}  {'Resolved'}")
    print("-" * 90)
    for r in rows:
        print(f"{r[0]:>4}  {r[1]:<11} {r[2]:<7} {fmt_score(r[3]):>4}  {(r[4] or '-'):<11} {(r[6] or '-'):<10} "
              f"{fmt_pct(r[7])} {fmt_pct(r[8])} {fmt_pct(r[9])} {fmt_pct(r[10])}  {r[11] or 'pending'}")


def report_earnings_season(season=None):
    conn = get_conn()
    if season:
        rows = conn.execute("""
        SELECT cl.id, cl.analysis_date, cl.ticker, cl.score_total, cl.conviction_tag,
               cl.catalyst_type_label, cl.catalyst_engine,
               o.return_1d, o.return_3d, o.return_5d, o.return_10d, o.catalyst_resolved
        FROM catalyst_log cl
        LEFT JOIN outcomes o ON o.catalyst_id = cl.id
        WHERE cl.earnings_season = ? AND cl.is_earnings = 1
        ORDER BY cl.score_total DESC
        """, (season,)).fetchall()
        title = f"EARNINGS SEASON: {season}"
    else:
        latest = conn.execute(
            "SELECT earnings_season FROM catalyst_log WHERE is_earnings=1 ORDER BY analysis_date DESC LIMIT 1"
        ).fetchone()
        if not latest:
            print("No earnings catalysts logged yet.")
            conn.close()
            return
        season = latest[0]
        rows = conn.execute("""
        SELECT cl.id, cl.analysis_date, cl.ticker, cl.score_total, cl.conviction_tag,
               cl.catalyst_type_label, cl.catalyst_engine,
               o.return_1d, o.return_3d, o.return_5d, o.return_10d, o.catalyst_resolved
        FROM catalyst_log cl
        LEFT JOIN outcomes o ON o.catalyst_id = cl.id
        WHERE cl.earnings_season = ? AND cl.is_earnings = 1
        ORDER BY cl.score_total DESC
        """, (season,)).fetchall()
        title = f"EARNINGS SEASON: {season} (latest)"

    header(title)
    print(f"{'ID':>4}  {'Date':<11} {'Ticker':<7} {'Sc':>4}  {'Tag':<11} {'Type':<30} {'1d':>7} {'3d':>7} {'5d':>7} {'10d':>7}")
    print("-" * 100)
    for r in rows:
        type_label = (r[5] or "-")[:28]
        print(f"{r[0]:>4}  {r[1]:<11} {r[2]:<7} {fmt_score(r[3]):>4}  {(r[4] or '-'):<11} {type_label:<30} "
              f"{fmt_pct(r[7])} {fmt_pct(r[8])} {fmt_pct(r[9])} {fmt_pct(r[10])}")
    conn.close()


def report_by_type():
    conn = get_conn()
    rows = conn.execute("""
    SELECT cl.catalyst_type, cl.catalyst_type_label,
           COUNT(*) as n,
           AVG(cl.score_total) as avg_score,
           AVG(o.return_1d) as avg_1d,
           AVG(o.return_3d) as avg_3d,
           AVG(o.return_5d) as avg_5d,
           AVG(o.return_10d) as avg_10d,
           SUM(CASE WHEN o.return_5d > 0 THEN 1 ELSE 0 END) as wins_5d,
           SUM(CASE WHEN o.return_5d IS NOT NULL THEN 1 ELSE 0 END) as total_with_outcome
    FROM catalyst_log cl
    LEFT JOIN outcomes o ON o.catalyst_id = cl.id
    WHERE cl.catalyst_type IS NOT NULL
    GROUP BY cl.catalyst_type
    ORDER BY avg_5d DESC NULLS LAST
    """).fetchall()
    conn.close()

    header("PERFORMANCE BY CATALYST TYPE")
    print(f"{'Type':<4} {'Label':<32} {'N':>4}  {'AvgSc':>6}  {'1d avg':>7} {'3d avg':>7} {'5d avg':>7} {'10d avg':>8}  {'5d Win%':>8}")
    print("-" * 95)
    for r in rows:
        win_pct = f"{r[8]/r[9]*100:.0f}%" if r[9] and r[9] > 0 else "n/a"
        label = (r[1] or "-")[:30]
        print(f"{(r[0] or 0):>4} {label:<32} {r[2]:>4}  {fmt_score(r[3]):>6}  "
              f"{fmt_pct(r[4])} {fmt_pct(r[5])} {fmt_pct(r[6])} {fmt_pct(r[7])}  {win_pct:>8}")


def report_by_score_bucket():
    conn = get_conn()
    rows = conn.execute("""
    SELECT
        CASE
            WHEN score_total >= 8 THEN 'HIGH (8-10)'
            WHEN score_total >= 5 THEN 'DEVELOPING (5-7.9)'
            ELSE 'WEAK (1-4.9)'
        END as bucket,
        COUNT(*) as n,
        AVG(o.return_1d) as avg_1d,
        AVG(o.return_3d) as avg_3d,
        AVG(o.return_5d) as avg_5d,
        AVG(o.return_10d) as avg_10d,
        SUM(CASE WHEN o.return_5d > 0 THEN 1 ELSE 0 END) as wins_5d,
        SUM(CASE WHEN o.return_5d IS NOT NULL THEN 1 ELSE 0 END) as total_with_outcome
    FROM catalyst_log cl
    LEFT JOIN outcomes o ON o.catalyst_id = cl.id
    GROUP BY bucket
    ORDER BY MIN(score_total) DESC
    """).fetchall()
    conn.close()

    header("PERFORMANCE BY CONVICTION TIER")
    print(f"{'Tier':<24} {'N':>4}  {'1d avg':>7} {'3d avg':>7} {'5d avg':>7} {'10d avg':>8}  {'5d Win%':>8}")
    print("-" * 75)
    for r in rows:
        win_pct = f"{r[6]/r[7]*100:.0f}%" if r[7] and r[7] > 0 else "n/a"
        print(f"{r[0]:<24} {r[1]:>4}  {fmt_pct(r[2])} {fmt_pct(r[3])} {fmt_pct(r[4])} {fmt_pct(r[5])}  {win_pct:>8}")


def report_by_engine():
    conn = get_conn()
    rows = conn.execute("""
    SELECT cl.catalyst_engine,
           COUNT(*) as n,
           AVG(cl.score_total) as avg_score,
           AVG(o.return_1d) as avg_1d,
           AVG(o.return_3d) as avg_3d,
           AVG(o.return_5d) as avg_5d,
           AVG(o.return_10d) as avg_10d,
           SUM(CASE WHEN o.return_5d > 0 THEN 1 ELSE 0 END) as wins_5d,
           SUM(CASE WHEN o.return_5d IS NOT NULL THEN 1 ELSE 0 END) as total_with_outcome
    FROM catalyst_log cl
    LEFT JOIN outcomes o ON o.catalyst_id = cl.id
    WHERE cl.catalyst_engine IS NOT NULL
    GROUP BY cl.catalyst_engine
    ORDER BY avg_5d DESC NULLS LAST
    """).fetchall()
    conn.close()

    header("PERFORMANCE BY CATALYST ENGINE")
    print(f"{'Engine':<15} {'N':>4}  {'AvgSc':>6}  {'1d avg':>7} {'3d avg':>7} {'5d avg':>7} {'10d avg':>8}  {'5d Win%':>8}")
    print("-" * 80)
    for r in rows:
        win_pct = f"{r[7]/r[8]*100:.0f}%" if r[8] and r[8] > 0 else "n/a"
        print(f"{(r[0] or '-'):<15} {r[1]:>4}  {fmt_score(r[2]):>6}  "
              f"{fmt_pct(r[3])} {fmt_pct(r[4])} {fmt_pct(r[5])} {fmt_pct(r[6])}  {win_pct:>8}")


def report_ticker(ticker: str):
    conn = get_conn()
    rows = conn.execute("""
    SELECT cl.id, cl.analysis_date, cl.score_total, cl.conviction_tag,
           cl.catalyst_type_label, cl.catalyst_engine,
           cl.the_one_variable, cl.thesis_summary,
           o.return_1d, o.return_3d, o.return_5d, o.return_10d,
           o.catalyst_resolved, o.resolution_notes
    FROM catalyst_log cl
    LEFT JOIN outcomes o ON o.catalyst_id = cl.id
    WHERE cl.ticker = ?
    ORDER BY cl.analysis_date DESC
    """, (ticker.upper(),)).fetchall()
    conn.close()

    header(f"ALL ENTRIES: {ticker.upper()}")
    for r in rows:
        print(f"\nID #{r[0]} | {r[1]} | Score: {fmt_score(r[2])}/10 | {r[3] or '-'}")
        print(f"  Engine: {r[5] or '-'} | Type: {(r[4] or '-')[:40]}")
        if r[6]:
            print(f"  One Variable: {r[6]}")
        if r[7]:
            print(f"  Thesis: {r[7]}")
        print(f"  Returns -> 1d: {fmt_pct(r[8])} | 3d: {fmt_pct(r[9])} | 5d: {fmt_pct(r[10])} | 10d: {fmt_pct(r[11])}")
        if r[12]:
            print(f"  Resolved: {r[12]} - {r[13] or ''}")


def report_full_summary():
    conn = get_conn()

    total = conn.execute("SELECT COUNT(*) FROM catalyst_log").fetchone()[0]
    with_outcomes = conn.execute(
        "SELECT COUNT(DISTINCT catalyst_id) FROM outcomes WHERE return_5d IS NOT NULL"
    ).fetchone()[0]
    high = conn.execute("SELECT COUNT(*) FROM catalyst_log WHERE conviction_tag = 'HIGH'").fetchone()[0]
    developing = conn.execute("SELECT COUNT(*) FROM catalyst_log WHERE conviction_tag = 'DEVELOPING'").fetchone()[0]
    weak = conn.execute("SELECT COUNT(*) FROM catalyst_log WHERE conviction_tag = 'WEAK'").fetchone()[0]
    seasons = conn.execute(
        "SELECT DISTINCT earnings_season FROM catalyst_log WHERE earnings_season IS NOT NULL ORDER BY earnings_season"
    ).fetchall()
    conn.close()

    header("CATALYST TRACKER -- FULL SUMMARY")
    print(f"  Total catalysts logged   : {total}")
    print(f"  With 5-day outcomes      : {with_outcomes}")
    print(f"  HIGH conviction          : {high}")
    print(f"  DEVELOPING               : {developing}")
    print(f"  WEAK                     : {weak}")
    print(f"  Earnings seasons tracked : {', '.join(s[0] for s in seasons) or 'none yet'}")
    print()

    if with_outcomes > 0:
        report_by_score_bucket()
        report_by_engine()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query catalyst patterns")
    parser.add_argument("--report", type=str, required=True,
                        choices=["recent", "earnings_season", "by_type", "by_score_bucket",
                                 "by_engine", "ticker", "full_summary"],
                        help="Which report to run")
    parser.add_argument("--season", type=str, help="Earnings season (e.g. Q1-2026)")
    parser.add_argument("--ticker", type=str, help="Ticker symbol")
    parser.add_argument("--n", type=int, default=20, help="Number of rows for 'recent' report")
    args = parser.parse_args()

    if args.report == "recent":
        report_recent(args.n)
    elif args.report == "earnings_season":
        report_earnings_season(args.season)
    elif args.report == "by_type":
        report_by_type()
    elif args.report == "by_score_bucket":
        report_by_score_bucket()
    elif args.report == "by_engine":
        report_by_engine()
    elif args.report == "ticker":
        if not args.ticker:
            print("--ticker required for this report")
            exit(1)
        report_ticker(args.ticker)
    elif args.report == "full_summary":
        report_full_summary()
