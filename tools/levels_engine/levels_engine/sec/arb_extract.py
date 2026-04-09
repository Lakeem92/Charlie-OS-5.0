"""
ARB / Contractual decimal extractor from SEC filing text.

Purely mechanical — NO LLM/AI.  Regex patterns look for:
  - "$X.XX per share" near keywords (conversion, exercise, offering, etc.)
  - Captures context snippet, computes a mechanical confidence score.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from ..config import Config
from ..logger import get_logger
from ..schemas import ArbLevel, ArbLevelsOutput, ArbLevelsDiagnostics
from ..utils.dates import iso_utc, utcnow
from ..utils.text import strip_html, normalise_whitespace

log = get_logger("arb_extract")

# ── keyword families ─────────────────────────────────────────

_KEYWORDS: Dict[str, List[str]] = {
    "conversion":   ["conversion price", "convert", "convertible"],
    "exercise":     ["exercise price", "exercisable", "strike price"],
    "warrant":      ["warrant", "warrants"],
    "redemption":   ["redeem", "redemption price", "redeemable"],
    "offering":     ["offering price", "public offering", "per share offering"],
    "purchase":     ["purchase price"],
    "exchange":     ["exchange ratio"],
    "cap_floor":    ["cap", "floor", "ceiling"],
    "vwap":         ["vwap", "volume-weighted", "volume weighted"],
}

# Flattened keyword list for quick scanning
_ALL_KW = [kw for family in _KEYWORDS.values() for kw in family]

# ── price pattern ────────────────────────────────────────────
# Matches: $12.34  or  12.34 per share  or  USD 12.34
_PRICE_RE = re.compile(
    r"""
    (?:(?:US)?(?:\$|USD)\s*)       # optional currency marker
    (\d{1,6}(?:\.\d{1,6})?)       # digits with optional decimals
    |                              # OR
    (\d{1,6}\.\d{2,6})            # bare decimal (at least 2 decimal places)
    \s+per\s+share                 # must be followed by "per share"
    """,
    re.IGNORECASE | re.VERBOSE,
)

# "per share" nearby indicator
_PER_SHARE_RE = re.compile(r"per\s+share", re.IGNORECASE)


# ── public entry point ───────────────────────────────────────

def extract_arb_levels(
    ticker: str,
    filings: List[Dict[str, Any]],
    cfg: Config,
) -> ArbLevelsOutput:
    """
    Scan filing texts for contractual price levels.

    Parameters
    ----------
    ticker : str
    filings : list[dict] – each with keys:
        filing_type, filing_date, filing_url, document_url, document_text
    cfg : Config

    Returns
    -------
    ArbLevelsOutput
    """
    asof = iso_utc(utcnow())
    all_matches: List[ArbLevel] = []
    total_matches = 0

    for filing in filings:
        raw_text = filing.get("document_text", "")
        if not raw_text:
            continue

        plain = normalise_whitespace(strip_html(raw_text))
        matches = _scan_text(plain, filing, cfg)
        total_matches += len(matches)
        all_matches.extend(matches)

    # De-duplicate by (level, label)
    all_matches = _dedup(all_matches)
    log.info("%s: %d unique arb levels from %d filings (%d raw matches)",
             ticker, len(all_matches), len(filings), total_matches)

    # Split into verified vs candidates
    verified = [m for m in all_matches if m.confidence >= cfg.arb_confidence_threshold]
    candidates = [m for m in all_matches if m.confidence < cfg.arb_confidence_threshold]

    # Sort by confidence descending
    verified.sort(key=lambda x: x.confidence, reverse=True)
    candidates.sort(key=lambda x: x.confidence, reverse=True)

    return ArbLevelsOutput(
        ticker=ticker,
        asof_utc=asof,
        lookback_days=cfg.sec_lookback_days,
        verified_levels=verified,
        candidates=candidates,
        diagnostics=ArbLevelsDiagnostics(
            filings_scanned=len(filings),
            matches_found=total_matches,
        ),
    )


# ── internal scanning ────────────────────────────────────────

def _scan_text(text: str, filing: Dict[str, Any], cfg: Config) -> List[ArbLevel]:
    """Search text for keyword+price co-occurrences."""
    results: List[ArbLevel] = []
    text_lower = text.lower()

    for label, keywords in _KEYWORDS.items():
        for kw in keywords:
            # Find all keyword occurrences
            kw_lower = kw.lower()
            start = 0
            while True:
                idx = text_lower.find(kw_lower, start)
                if idx == -1:
                    break
                start = idx + 1

                # Search for prices within ±300 chars of keyword
                window_start = max(0, idx - 300)
                window_end = min(len(text), idx + len(kw) + 300)
                window = text[window_start:window_end]

                for m in _PRICE_RE.finditer(window):
                    price_str = m.group(1) or m.group(2)
                    if price_str is None:
                        continue
                    try:
                        price = float(price_str)
                    except ValueError:
                        continue
                    # Sanity: skip prices that are clearly not per-share
                    if price < 0.01 or price > 100_000:
                        continue

                    # Build context snippet (±120 chars around the price match in window)
                    snip_start = max(0, m.start() - 120)
                    snip_end = min(len(window), m.end() + 120)
                    snippet = window[snip_start:snip_end].strip()

                    confidence = _score(window, m, kw)

                    results.append(ArbLevel(
                        level=round(price, 6),
                        label=label,
                        context_snippet=snippet[:250],
                        filing_type=filing.get("filing_type", ""),
                        filing_date=filing.get("filing_date", ""),
                        filing_url=filing.get("filing_url", ""),
                        document_url=filing.get("document_url", ""),
                        confidence=round(confidence, 3),
                    ))
    return results


def _score(window: str, price_match: re.Match, keyword: str) -> float:
    """
    Mechanical confidence score (0–1).

    Components:
      +0.30  keyword is within 100 chars of price
      +0.25  "$" or "USD" present near the number
      +0.25  "per share" within 60 chars of the number
      +0.20  decimal has exactly 2 decimal places (typical share price)
    """
    score = 0.0

    # Keyword proximity
    kw_pos = window.lower().find(keyword.lower())
    price_pos = price_match.start()
    if kw_pos >= 0:
        dist = abs(kw_pos - price_pos)
        if dist <= 100:
            score += 0.30
        elif dist <= 200:
            score += 0.15

    # Currency symbol presence
    pre = window[max(0, price_match.start() - 5): price_match.start()]
    if "$" in pre or "usd" in pre.lower():
        score += 0.25

    # "per share" nearby
    after = window[price_match.end(): price_match.end() + 60]
    before = window[max(0, price_match.start() - 60): price_match.start()]
    if _PER_SHARE_RE.search(after) or _PER_SHARE_RE.search(before):
        score += 0.25

    # Decimal format (exactly N.NN)
    price_str = price_match.group(1) or price_match.group(2) or ""
    if "." in price_str:
        decimals = len(price_str.split(".")[1])
        if decimals == 2:
            score += 0.20
        elif decimals >= 3:
            score += 0.10

    return min(score, 1.0)


def _dedup(levels: List[ArbLevel]) -> List[ArbLevel]:
    """Keep highest-confidence entry per (level, label) pair."""
    best: Dict[Tuple[float, str], ArbLevel] = {}
    for lv in levels:
        key = (lv.level, lv.label)
        if key not in best or lv.confidence > best[key].confidence:
            best[key] = lv
    return list(best.values())
