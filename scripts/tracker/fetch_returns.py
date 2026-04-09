"""
Catalyst Tracker -- Auto Return Fetcher
War Room v10.0 | Charlie OS 5.0

Fetches historical prices from Tiingo and calculates forward returns
for logged catalysts. Only runs when explicitly called -- never automatic.

Claude calls this when Lakeem asks about forward returns, e.g.:
  "What are the forward returns for NVDA after earnings?"
  "How did my TSLA catalyst play out?"
  "Update the returns for everything from last week"

Usage:
    python scripts/tracker/fetch_returns.py --ticker NVDA
    python scripts/tracker/fetch_returns.py --all
    python scripts/tracker/fetch_returns.py --id 7
    python scripts/tracker/fetch_returns.py --pending   (shows what needs updating)
"""

import argparse
import sqlite3
import sys
import os
from datetime import date, timedelta
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DB_PATH = Path(__file__).parent.parent.parent / "data" / "catalyst_tracker.db"

# Return windows in calendar days (approximate -- Tiingo returns trading days only)
# We fetch a range and pick the closest available trading day
WINDOWS = {
    "1d":  1,
    "3d":  3,
    "5d":  5,
    "10d": 14,   # ~10 trading days
    "20d": 28,   # ~20 trading days
}


def get_conn():
    return sqlite3.connect(DB_PATH)


def fetch_prices_tiingo(ticker: str, start_date: str, end_date: str) -> dict:
    """
    Returns a dict of {date_str: close_price} for the given range.
    Uses the existing TiingoClient from shared/config/api_clients.py.
    """
    try:
        from shared.config.api_clients import TiingoClient
        client = TiingoClient()
        data = client.get_daily_prices(ticker, start_date=start_date, end_date=end_date)

        if not data or not isinstance(data, list):
            print(f"  [WARN] Tiingo returned no data for {ticker} ({start_date} to {end_date})")
            return {}

        price_map = {}
        for row in data:
            # Tiingo returns ISO date strings like "2026-04-09T00:00:00+00:00"
            day = str(row.get("date", ""))[:10]
            close = row.get("adjClose") or row.get("close")
            if day and close:
                price_map[day] = float(close)

        return price_map

    except Exception as e:
        print(f"  [ERROR] Tiingo fetch failed for {ticker}: {e}")
        return {}


def get_nth_trading_day_price(price_map: dict, from_date: date, n_calendar_days: int) -> tuple:
    """
    Find the closest available trading day price at/after from_date + n_calendar_days.
    Returns (price, actual_date_str) or (None, None).
    """
    target = from_date + timedelta(days=n_calendar_days)
    # Try target date and up to 4 days forward (skip weekends/holidays)
    for offset in range(5):
        check = target + timedelta(days=offset)
        check_str = check.strftime("%Y-%m-%d")
        if check_str in price_map:
            return price_map[check_str], check_str
    return None, None


def calc_return(price_entry, price_exit, direction):
    if not price_entry or not price_exit:
        return None
    raw = (price_exit - price_entry) / price_entry * 100
    return round(raw if direction != "SHORT" else -raw, 2)


def fetch_for_catalyst(catalyst_id: int, verbose=True) -> bool:
    """
    Fetch and store returns for a single catalyst. Returns True if updated.
    """
    conn = get_conn()
    row = conn.execute("""
        SELECT cl.id, cl.ticker, cl.analysis_date, cl.catalyst_direction,
               o.price_at_analysis, o.return_1d, o.return_3d, o.return_5d,
               o.return_10d, o.return_20d
        FROM catalyst_log cl
        LEFT JOIN outcomes o ON o.catalyst_id = cl.id
        WHERE cl.id = ?
    """, (catalyst_id,)).fetchone()
    conn.close()

    if not row:
        print(f"  [ERROR] Catalyst ID #{catalyst_id} not found.")
        return False

    cid, ticker, analysis_date_str, direction = row[0], row[1], row[2], row[3]
    price_entry = row[4]

    analysis_date = date.fromisoformat(analysis_date_str)
    today = date.today()

    # Fetch price range from analysis date through ~30 calendar days out
    end_date = min(today, analysis_date + timedelta(days=35))
    if analysis_date >= today:
        if verbose:
            print(f"  [SKIP] #{cid} {ticker} -- analysis date is today or future, no forward data yet.")
        return False

    if verbose:
        print(f"  Fetching prices for {ticker} ({analysis_date_str} to {end_date})...")

    price_map = fetch_prices_tiingo(ticker, analysis_date_str, str(end_date))
    if not price_map:
        return False

    # Entry price: use analysis_date price if not already set
    if not price_entry:
        price_entry, _ = get_nth_trading_day_price(price_map, analysis_date, 0)
        if not price_entry:
            # Try the day before (if analysis happened pre-market)
            prev = analysis_date - timedelta(days=1)
            price_entry = price_map.get(str(prev))

    if not price_entry:
        if verbose:
            print(f"  [WARN] Could not find entry price for {ticker} on {analysis_date_str}")
        return False

    # Calculate each return window
    results = {"price_at_analysis": price_entry}
    for window_name, cal_days in WINDOWS.items():
        price, actual_date = get_nth_trading_day_price(price_map, analysis_date, cal_days)
        if price:
            results[f"price_{window_name}"] = price
            results[f"return_{window_name}"] = calc_return(price_entry, price, direction or "LONG")
            if verbose:
                ret = results[f"return_{window_name}"]
                print(f"    {window_name:>4}: ${price:.2f} ({actual_date})  {ret:+.2f}%")
        else:
            if verbose:
                days_elapsed = (today - analysis_date).days
                if cal_days > days_elapsed:
                    print(f"    {window_name:>4}: not yet (need {cal_days} cal days, only {days_elapsed} elapsed)")

    # Write to outcomes table
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM outcomes WHERE catalyst_id = ?", (cid,)
    ).fetchone()

    if existing:
        sets = ", ".join(f"{k} = ?" for k in results)
        vals = list(results.values()) + [cid]
        conn.execute(f"UPDATE outcomes SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE catalyst_id = ?", vals)
    else:
        cols = ", ".join(results.keys())
        placeholders = ", ".join("?" for _ in results)
        vals = list(results.values())
        conn.execute(
            f"INSERT INTO outcomes (catalyst_id, {cols}) VALUES (?, {placeholders})",
            [cid] + vals
        )

    conn.commit()
    conn.close()
    return True


def fetch_for_ticker(ticker: str):
    conn = get_conn()
    rows = conn.execute("""
        SELECT id FROM catalyst_log WHERE ticker = ?
        ORDER BY analysis_date DESC
    """, (ticker.upper(),)).fetchall()
    conn.close()

    if not rows:
        print(f"No catalyst entries found for {ticker.upper()}.")
        return

    print(f"\nFetching returns for {ticker.upper()} ({len(rows)} entries)...")
    for (cid,) in rows:
        print(f"\n-- Catalyst ID #{cid} --")
        fetch_for_catalyst(cid)


def fetch_all_pending():
    conn = get_conn()
    rows = conn.execute("""
        SELECT cl.id FROM catalyst_log cl
        LEFT JOIN outcomes o ON o.catalyst_id = cl.id
        WHERE o.return_5d IS NULL
        AND cl.analysis_date < date('now')
        ORDER BY cl.analysis_date ASC
    """).fetchall()
    conn.close()

    if not rows:
        print("All logged catalysts already have 5-day return data.")
        return

    print(f"\nFetching returns for {len(rows)} pending catalysts...")
    updated = 0
    for (cid,) in rows:
        print(f"\n-- Catalyst ID #{cid} --")
        if fetch_for_catalyst(cid):
            updated += 1

    print(f"\nDone. Updated {updated}/{len(rows)} catalysts.")


def show_pending():
    conn = get_conn()
    rows = conn.execute("""
        SELECT cl.id, cl.analysis_date, cl.ticker, cl.score_total,
               cl.conviction_tag, o.return_5d
        FROM catalyst_log cl
        LEFT JOIN outcomes o ON o.catalyst_id = cl.id
        WHERE o.return_5d IS NULL
        ORDER BY cl.analysis_date DESC
    """).fetchall()
    conn.close()

    if not rows:
        print("No pending catalysts -- all have return data.")
        return

    print(f"\n{'ID':>4}  {'Date':<12}  {'Ticker':<8}  {'Score':>5}  {'Conviction'}")
    print("-" * 50)
    for r in rows:
        print(f"{r[0]:>4}  {r[1]:<12}  {r[2]:<8}  {r[3]:>5.1f}  {r[4] or '-'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch forward returns for logged catalysts")
    parser.add_argument("--ticker", type=str, help="Fetch returns for a specific ticker")
    parser.add_argument("--id",     type=int, help="Fetch returns for a specific catalyst ID")
    parser.add_argument("--all",    action="store_true", help="Fetch all pending catalysts")
    parser.add_argument("--pending",action="store_true", help="Show what needs return data")
    args = parser.parse_args()

    if args.pending:
        show_pending()
    elif args.ticker:
        fetch_for_ticker(args.ticker)
    elif args.id:
        print(f"\n-- Catalyst ID #{args.id} --")
        fetch_for_catalyst(args.id)
    elif args.all:
        fetch_all_pending()
    else:
        parser.print_help()
