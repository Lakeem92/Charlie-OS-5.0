#!/usr/bin/env python3
"""
Deterministic Natural-Language Parser for the Studies Infrastructure.

Converts a plain-English question into a canonical Study Run Spec (dict)
without any LLM inference.  Every rule is explicit and reproducible.

Usage (as library):
    from nl_parse import parse_query
    spec = parse_query("when NVDA gaps up 5%+ does it trend or chop and what's the win rate D5-D10")
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import yaml

TOOLS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TOOLS_DIR.parent.parent
REGISTRY_PATH = TOOLS_DIR / "studies_registry.yaml"

# ── Stopwords: common English words that look like tickers ───
_STOPWORDS = {
    "A", "I", "AM", "AN", "AS", "AT", "BE", "BY", "DO", "GO", "HE",
    "IF", "IN", "IS", "IT", "ME", "MY", "NO", "OF", "OK", "ON", "OR",
    "SO", "TO", "UP", "US", "WE", "AND", "ARE", "BUT", "CAN",
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
    "SIGMA", "DOES", "TREND", "RATE", "WHAT", "WHATS",
    "NEAR", "STRONG", "WEAK", "MIX", "PLUS",
    "MIN", "MAX", "AVG", "HOUR", "DAYS",
}

# ── Regex patterns ───────────────────────────────────────────
_TICKER_RE = re.compile(r"(?<!\w)\$?([A-Z]{1,5})(?!\w)")

# Gap-up patterns:  "gap up 5%", "gaps up 5%+", "gap >= 5%", "gap 5 percent", "gap up >=5%"
_GAP_UP_RE = re.compile(
    r"gap[s]?\s*(?:up|down)?\s*(?:>=?\s*)?(\d+(?:\.\d+)?)\s*%?\s*(?:\+|percent)?",
    re.IGNORECASE,
)

# Explicit gap bin: "3-5%", "5-8%", "12-20%"
_GAP_BIN_RE = re.compile(r"(\d+)\s*[-\u2013]\s*(\d+)\s*%", re.IGNORECASE)

# Horizon patterns: "D5", "D10", "D5-D10", "D1", "t+5", "t+10", "5-10 days"
_HORIZON_D_RE = re.compile(r"\bD\s*(\d+)", re.IGNORECASE)
_HORIZON_T_RE = re.compile(r"\bt\s*\+\s*(\d+)", re.IGNORECASE)
_HORIZON_RANGE_D_RE = re.compile(
    r"\bD\s*(\d+)\s*[-\u2013]\s*D?\s*(\d+)", re.IGNORECASE
)
_HORIZON_RANGE_DAYS_RE = re.compile(
    r"(\d+)\s*[-\u2013]\s*(\d+)\s*days?\s*(?:out)?", re.IGNORECASE
)
_NEXT_WEEK_RE = re.compile(r"\bnext\s+week\b", re.IGNORECASE)

# Date patterns: "2018-01-01", "from 2020", "since 2019"
_DATE_FULL_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_DATE_YEAR_RE = re.compile(r"\b(?:from|since|after)\s+(\d{4})\b", re.IGNORECASE)

# Intraday intent
_INTRADAY_KEYWORDS = [
    "first hour", "first-hour", "vwap", "opening range",
    "reclaim", "intraday", "5min", "5 min",
]

# Metric keywords
_WIN_RATE_RE = re.compile(r"win\s*rate|win[_\s]?pct|batting\s*avg", re.IGNORECASE)
_RETURN_RE = re.compile(r"return|avg\s*ret|median\s*ret", re.IGNORECASE)

# Study-relevant keyword sets for module selection
_TREND_CHOP_KEYWORDS = [
    "trend vs chop", "trend day", "chop day", "uptrend day mix",
    "trend or chop", "uptrend", "day mix", "day type",
]
_GAP_KEYWORDS = [
    "gap up", "gap down", "gaps up", "close strong", "close weak",
    "gap day", "close near high",
]
_INTRADAY_ANALYSIS_KEYWORDS = [
    "first hour", "failure score", "vwap hold", "signature",
    "opening range", "reclaim", "fade signature", "trend signature",
]


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

def parse_query(query: str) -> dict:
    """
    Parse a plain-English query into a canonical Study Run Spec dict.
    Deterministic: same input always produces the same output.
    """
    q = query.strip()
    q_lower = q.lower()

    # A) Ticker extraction
    tickers = _extract_tickers(q)

    # B) Event condition
    event = _extract_event(q_lower)

    # C) Horizons
    horizons_data = _extract_horizons(q_lower)

    # D) Metrics
    metrics = _extract_metrics(q_lower, horizons_data)

    # E) Intraday
    intraday_enabled = _detect_intraday(q_lower)

    # F) Date range
    date_range = _extract_dates(q_lower)

    # Module selection
    include_trend_chop = _has_any(q_lower, _TREND_CHOP_KEYWORDS)
    include_gap = _has_any(q_lower, _GAP_KEYWORDS)
    include_intraday_fh = intraday_enabled and _has_any(
        q_lower, _INTRADAY_ANALYSIS_KEYWORDS
    )
    include_horizons = bool(horizons_data["horizons"]) or bool(
        horizons_data["window"]
    )

    # If user asks "trend or chop" AND mentions gap, enable both
    if event.get("type") == "gap_up" and not include_gap:
        include_gap = True

    # If nothing specific matched, enable trend_chop + gap as defaults
    if not any([include_trend_chop, include_gap, include_intraday_fh, include_horizons]):
        include_trend_chop = True
        include_gap = True

    # Study match
    study_name = _match_study(q, include_horizons)

    spec = {
        "run_spec_version": "1.0",
        "query": q,
        "study": study_name,
        "tickers": tickers,
        "date_range": date_range,
        "event": event,
        "outputs": {
            "include_trend_chop_mix": include_trend_chop,
            "include_gap_close_strength": include_gap,
            "include_intraday_first_hour": include_intraday_fh,
            "include_forward_horizons": include_horizons,
        },
        "forward_horizons": horizons_data,
        "intraday": {"enabled": intraday_enabled},
    }
    return spec


# ─────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────

def _extract_tickers(query: str) -> list[str]:
    """Extract ALL-CAPS tokens 1-5 chars that look like tickers."""
    raw = _TICKER_RE.findall(query)
    seen: set[str] = set()
    tickers: list[str] = []
    for t in raw:
        t_upper = t.upper()
        if t_upper not in seen and t_upper not in _STOPWORDS:
            seen.add(t_upper)
            tickers.append(t_upper)
    return tickers


def _extract_event(q_lower: str) -> dict:
    """Parse gap-up/down event condition."""
    event: dict = {"type": None, "gap_up_min": None, "gap_bin_label": None}

    # Check explicit bin first: "3-5%"
    bin_match = _GAP_BIN_RE.search(q_lower)
    if bin_match:
        lo, hi = int(bin_match.group(1)), int(bin_match.group(2))
        event["type"] = "gap_up"
        event["gap_bin_label"] = f"{lo}-{hi}%"
        event["gap_up_min"] = lo / 100.0

    # Check general gap threshold: "gap up 5%+"
    gap_match = _GAP_UP_RE.search(q_lower)
    if gap_match:
        val = float(gap_match.group(1))
        event["type"] = "gap_up"
        if event["gap_up_min"] is None:
            event["gap_up_min"] = val / 100.0
        # If user said "5%+" and also mentioned a bin, keep the bin label
        # Otherwise clear bin label because it's a threshold, not a bin
        if event["gap_bin_label"] is None:
            event["gap_bin_label"] = None

    # If query mentions gap at all but no threshold parsed
    if event["type"] is None and ("gap up" in q_lower or "gaps up" in q_lower or "gap day" in q_lower):
        event["type"] = "gap_up"
        event["gap_up_min"] = 0.01  # default 1%

    return event


def _extract_horizons(q_lower: str) -> dict:
    """Parse forward-return horizons from query."""
    horizons: list[int] = []
    window: dict | None = None

    # D5-D10 or D5-10 style ranges
    range_match = _HORIZON_RANGE_D_RE.search(q_lower)
    if range_match:
        lo, hi = int(range_match.group(1)), int(range_match.group(2))
        window = {"start": lo, "end": hi}
        horizons.extend(range(lo, hi + 1))

    # "5-10 days out"
    if not range_match:
        days_match = _HORIZON_RANGE_DAYS_RE.search(q_lower)
        if days_match:
            lo, hi = int(days_match.group(1)), int(days_match.group(2))
            window = {"start": lo, "end": hi}
            horizons.extend(range(lo, hi + 1))

    # Individual D1, D5, D10 tokens (merge with existing)
    for m in _HORIZON_D_RE.finditer(q_lower):
        val = int(m.group(1))
        if val not in horizons:
            horizons.append(val)

    # t+5, t+10 tokens
    for m in _HORIZON_T_RE.finditer(q_lower):
        val = int(m.group(1))
        if val not in horizons:
            horizons.append(val)

    # "next week" -> D5-D10
    if _NEXT_WEEK_RE.search(q_lower) and not horizons:
        window = {"start": 5, "end": 10}
        horizons = list(range(5, 11))

    # Default when win rate / return requested but no horizon specified
    if not horizons and (
        _WIN_RATE_RE.search(q_lower) or _RETURN_RE.search(q_lower)
    ):
        horizons = [1, 2]

    horizons = sorted(set(horizons))

    # Metrics
    metrics = _extract_metrics(q_lower, {"horizons": horizons, "window": window})

    return {"horizons": horizons, "window": window, "metrics": metrics}


def _extract_metrics(q_lower: str, horizons_data: dict) -> list[str]:
    """Determine which metrics are requested."""
    metrics: list[str] = []
    if _WIN_RATE_RE.search(q_lower):
        metrics.append("win_rate_positive")
    if _RETURN_RE.search(q_lower):
        if "avg_return" not in metrics:
            metrics.append("avg_return")
        if "median_return" not in metrics:
            metrics.append("median_return")

    # If horizons exist but no explicit metric, default to all three
    if horizons_data.get("horizons") and not metrics:
        metrics = ["win_rate_positive", "avg_return", "median_return"]

    return metrics


def _detect_intraday(q_lower: str) -> bool:
    """Return True if query implies intraday analysis."""
    return any(kw in q_lower for kw in _INTRADAY_KEYWORDS)


def _extract_dates(q_lower: str) -> dict:
    """Parse start/end dates from query."""
    dates = {"start": None, "end": None}

    full_dates = _DATE_FULL_RE.findall(q_lower)
    if len(full_dates) >= 2:
        dates["start"] = full_dates[0]
        dates["end"] = full_dates[1]
    elif len(full_dates) == 1:
        dates["start"] = full_dates[0]

    if dates["start"] is None:
        year_match = _DATE_YEAR_RE.search(q_lower)
        if year_match:
            dates["start"] = f"{year_match.group(1)}-01-01"

    return dates


def _has_any(q_lower: str, keywords: list[str]) -> bool:
    """Check if any keyword is present in the query."""
    return any(kw in q_lower for kw in keywords)


def _match_study(query: str, include_horizons: bool) -> str:
    """Match query to a study using the registry."""
    if not REGISTRY_PATH.exists():
        return "trend_chop_gap_quality"  # fallback

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = yaml.safe_load(f)

    studies = registry.get("studies", {})
    if not studies:
        return "trend_chop_gap_quality"

    q_lower = query.lower()
    scored: list[tuple[int, str]] = []
    for name, cfg in studies.items():
        keywords = cfg.get("keywords", [])
        s = sum(1 for kw in keywords if kw.lower() in q_lower)
        scored.append((s, name))

    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored[0][1]


# ─────────────────────────────────────────────────────────────
# CLI for testing
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python nl_parse.py \"your question here\"")
        sys.exit(1)

    q = " ".join(sys.argv[1:])
    spec = parse_query(q)
    print(yaml.dump(spec, default_flow_style=False, sort_keys=False))
