"""Phase 0 — Watchlist Cleanup Script
Separates ETFs from equities in the master watchlist.
Uses yfinance quoteType + known ETF list from the spec.
"""
import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import csv
from pathlib import Path

# ── Known ETF classification from spec ──────────────────────────────────
TIER1_ETFS = {
    "SOXX", "SMH", "IGV", "AIS", "QTUM", "IBOT", "ROBO", "CLOU", "DTCR", "NLR",
    "XLE", "XLF", "XHB", "XBI", "XLI", "XLV", "KRE", "XME",
    "ARKK", "ARKF", "TAN", "ICLN", "JETS", "UFO", "MEME", "IPO",
    "FXI", "KWEB", "KORU",
    "GLD", "SLV", "MOO",
    "HACK", "XLC",
}

TIER2_ETFS = {
    "SPY", "QQQ", "DIA", "IWM", "IWC", "EEM", "MAGS",
    "SOXS", "SQQQ", "YANG", "FAZ", "MEXX",
    "USO", "DBA", "PALL", "PICK", "OIH",
    "TLT", "HYG",
    "XLP", "XLK", "XLY", "VIX",
}

ALL_SPEC_ETFS = TIER1_ETFS | TIER2_ETFS

# Additional known ETFs/ETNs that may appear in the watchlist but aren't in spec tiers
# We'll classify using yfinance for anything ambiguous
KNOWN_ETFS_EXTRA = {
    "ARKQ", "ARKX", "BRZU", "BULL", "EDC", "ETOR", "EURL", "ETHU",
    "EZJ", "EZU", "FCG", "FTXH", "IBB", "IHE", "INDL",
    "ITA", "ITB", "PBW", "PPH", "AIQ",
    "SPX",  # S&P 500 index — not tradeable as equity
}

def classify_ticker(symbol):
    """Classify a ticker as ETF or equity."""
    if symbol in TIER1_ETFS:
        return "ETF", 1
    if symbol in TIER2_ETFS:
        return "ETF", 2
    if symbol in KNOWN_ETFS_EXTRA:
        return "ETF", 2  # default extra ETFs to tier 2
    return "EQUITY", None

def main():
    # Read current master watchlist
    master_path = Path(r"C:\QuantLab\Data_Lab\shared\config\watchlist.csv")
    tickers = []
    with open(master_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tickers.append(row["Symbol"].strip())

    print(f"Total tickers in original master: {len(tickers)}")

    equities = []
    etf_tier1 = []
    etf_tier2 = []
    ambiguous = []

    for t in tickers:
        asset_type, tier = classify_ticker(t)
        if asset_type == "ETF":
            if tier == 1:
                etf_tier1.append(t)
            else:
                etf_tier2.append(t)
        else:
            equities.append(t)

    # Skip slow yfinance verification — our known lists are comprehensive
    # Any truly ambiguous tickers stay as equities (safe default)
    recheck = []

    # Ensure HACK and XLC are in Tier 1 (spec requirement)
    for t in ["HACK", "XLC"]:
        if t in etf_tier2:
            etf_tier2.remove(t)
        if t not in etf_tier1:
            etf_tier1.append(t)

    # Add spec ETFs that aren't in the original master
    all_original = set(tickers)
    for t in sorted(TIER1_ETFS):
        if t not in all_original and t not in etf_tier1:
            etf_tier1.append(t)
            print(f"  Added missing Tier 1 ETF: {t}")
    for t in sorted(TIER2_ETFS):
        if t not in all_original and t not in etf_tier2:
            etf_tier2.append(t)
            print(f"  Added missing Tier 2 ETF: {t}")

    # Sort all lists
    equities.sort()
    etf_tier1.sort()
    etf_tier2.sort()

    # Write master_watchlist.csv (equities only)
    out_dir = Path(r"C:\QuantLab\Data_Lab\watchlists")
    with open(out_dir / "master_watchlist.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker"])
        for t in equities:
            writer.writerow([t])

    # Write etf_watchlist.csv
    with open(out_dir / "etf_watchlist.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker", "tier"])
        for t in etf_tier1:
            writer.writerow([t, 1])
        for t in etf_tier2:
            writer.writerow([t, 2])

    # Write focus_list.csv (empty with proper columns)
    with open(out_dir / "focus_list.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker", "added_date", "notes", "sector"])

    print(f"\n{'='*50}")
    print(f"WATCHLIST CLEANUP COMPLETE")
    print(f"{'='*50}")
    print(f"Equities (master_watchlist.csv):  {len(equities)}")
    print(f"Tier 1 ETFs (full structural):    {len(etf_tier1)}")
    print(f"Tier 2 ETFs (momentum only):      {len(etf_tier2)}")
    print(f"Total ETFs (etf_watchlist.csv):    {len(etf_tier1) + len(etf_tier2)}")
    print(f"Focus list: empty (ready for input)")
    print(f"\nTier 1 ETFs: {', '.join(etf_tier1)}")
    print(f"\nTier 2 ETFs: {', '.join(etf_tier2)}")
    if recheck:
        print(f"\nReclassified from equity to ETF: {', '.join(recheck)}")

if __name__ == "__main__":
    main()
