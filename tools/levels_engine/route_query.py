#!/usr/bin/env python3
"""
Lightweight natural-language router for the Levels Engine.

Detects intent keywords and tickers from a raw user query,
then delegates to query_levels.py --summary.

Usage:
    python tools/levels_engine/route_query.py "what are the key levels on TSLA?"
    python tools/levels_engine/route_query.py "call wall and put wall for NVDA SPY"
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# ── Intent keywords (lower-case) ────────────────────────────
_INTENT_KEYWORDS = [
    "key levels",
    "call wall",
    "put wall",
    "forced-action map",
    "options levels",
    "walls",
    "oi levels",
    "gamma levels",
]

# ── Ticker regex: 1–5 uppercase alpha, optional $ prefix ────
_TICKER_RE = re.compile(r"(?<!\w)\$?([A-Z]{1,5})(?!\w)")

# Common English words that look like tickers but aren't
_STOPWORDS = {
    "A", "I", "AM", "AN", "AS", "AT", "BE", "BY", "DO", "GO", "HE",
    "IF", "IN", "IS", "IT", "ME", "MY", "NO", "OF", "OK", "ON", "OR",
    "OUR", "SO", "TO", "UP", "US", "WE", "AND", "ARE", "BUT", "CAN",
    "DID", "FOR", "GET", "GOT", "HAS", "HAD", "HER", "HIM", "HIS",
    "HOW", "ITS", "KEY", "LET", "MAY", "NOT", "NOW", "OLD", "ONE",
    "OUR", "OUT", "OWN", "RAN", "RUN", "SAT", "SAY", "SET", "SHE",
    "THE", "TOO", "TWO", "USE", "WAS", "WAY", "WHO", "WHY", "WIN",
    "WON", "YET", "YOU", "ALL", "ANY", "BIG", "DAY", "NEW", "PUT",
    "SEE", "SAW", "TOP", "TRY", "ASK", "BACK", "BEEN", "BEST",
    "BOTH", "CALL", "COME", "DOWN", "EACH", "EVEN", "FIND", "FIRST",
    "FROM", "GIVE", "GOOD", "HAVE", "HERE", "HIGH", "INTO", "JUST",
    "KEEP", "KNOW", "LAST", "LIKE", "LONG", "LOOK", "MADE", "MAKE",
    "MANY", "MORE", "MOST", "MUCH", "MUST", "NAME", "NEXT", "ONLY",
    "OPEN", "OVER", "PART", "SAME", "SHOW", "SIDE", "SOME", "SUCH",
    "TAKE", "TELL", "THAN", "THAT", "THEM", "THEN", "THEY", "THIS",
    "TIME", "UPON", "VERY", "WANT", "WEEK", "WELL", "WENT", "WERE",
    "WHAT", "WHEN", "WILL", "WITH", "WORD", "WORK", "YEAR", "YOUR",
    "ABOUT", "AFTER", "BASED", "BEING", "BELOW", "CLOSE", "COULD",
    "EVERY", "FRONT", "GOING", "GREAT", "LEVEL", "MONTH", "OTHER",
    "RIGHT", "SHALL", "SINCE", "STILL", "THEIR", "THERE", "THESE",
    "THINK", "THOSE", "THREE", "TODAY", "UNDER", "UNTIL", "WATCH",
    "WHICH", "WHILE", "WOULD", "SHOULD", "WHERE", "STOCK", "PRICE",
    "PATH", "ABOVE", "GAMMA", "DELTA", "THETA", "ALPHA", "BETA",
    "SIGMA",
}


def detect_intent(query: str) -> bool:
    """Return True if the query matches any intent keyword."""
    q_lower = query.lower()
    return any(kw in q_lower for kw in _INTENT_KEYWORDS)


def extract_tickers(query: str) -> list[str]:
    """Extract up to 3 unique ticker candidates from the query."""
    # Find all uppercase token matches (or $-prefixed)
    raw = _TICKER_RE.findall(query.upper())
    seen: set[str] = set()
    tickers: list[str] = []
    for t in raw:
        if t not in seen and t not in _STOPWORDS:
            seen.add(t)
            tickers.append(t)
            if len(tickers) == 3:
                break
    return tickers


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python route_query.py \"<natural language query>\"")
        return 1

    query = " ".join(sys.argv[1:])

    if not detect_intent(query):
        print("Not an options-levels request. No action taken.")
        return 0

    tickers = extract_tickers(query)
    if not tickers:
        print("No ticker detected. Include 1-3 tickers like TSLA, NVDA, SPY.")
        return 0

    # Build and run query_levels.py --summary
    script = Path(__file__).resolve().parent / "query_levels.py"
    cmd = [sys.executable, str(script)] + tickers + ["--summary"]

    result = subprocess.run(cmd, cwd=str(script.parent.parent.parent))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
