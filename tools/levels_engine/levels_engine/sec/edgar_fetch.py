"""
SEC EDGAR fetcher.

Endpoints used:
  - https://efts.sec.gov/LATEST/search-index/companysearch/companysearch
  - https://data.sec.gov/submissions/CIK{cik}.json  (company filings index)
  - https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primary_doc}

All requests include the required SEC_USER_AGENT header.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from ..config import Config
from ..logger import get_logger
from ..utils.io import read_json_cache, write_json

log = get_logger("edgar_fetch")

# Filing types most likely to contain contractual price terms
_PREF_TYPES = {"8-K", "S-1", "S-3", "F-1", "F-3", "6-K",
               "424B1", "424B2", "424B3", "424B4", "424B5"}
_ALL_TYPES = _PREF_TYPES | {"DEF14A", "10-K", "10-Q", "SC 13D", "SC 13G"}

# SEC asks for ≤10 req/sec
_SEC_WAIT = 0.12


class EdgarFetcher:
    """Fetch recent SEC filings for a ticker."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self._headers = {
            "User-Agent": cfg.sec_user_agent,
            "Accept": "application/json",
        }
        self._cache = cfg.cache_dir

    # ── public ───────────────────────────────────────────

    def get_filings(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Return list of dicts:
          filing_type, filing_date, filing_url, document_url, document_text
        """
        cik = self._ticker_to_cik(ticker)
        if cik is None:
            log.warning("Could not resolve CIK for %s", ticker)
            return []

        filings_meta = self._fetch_filings_index(cik)
        if not filings_meta:
            log.info("%s: no filings in lookback window", ticker)
            return []

        results: List[Dict[str, Any]] = []
        for fm in filings_meta[: self.cfg.sec_max_filings]:
            doc_text = self._fetch_document(fm)
            if doc_text:
                fm["document_text"] = doc_text
                results.append(fm)
            time.sleep(_SEC_WAIT)

        log.info("%s: fetched %d filing documents (of %d indexed)",
                 ticker, len(results), len(filings_meta))
        return results

    # ── CIK resolution ───────────────────────────────────

    def _ticker_to_cik(self, ticker: str) -> Optional[str]:
        """Map ticker → zero-padded CIK string, with caching."""
        cache_path = self._cache / "company_tickers.json"
        mapping = read_json_cache(cache_path, max_age_hours=168)  # 7 days

        if mapping is None:
            mapping = self._download_company_tickers()
            if mapping:
                self._cache.mkdir(parents=True, exist_ok=True)
                write_json(mapping, cache_path)

        if not mapping:
            return None

        tk = ticker.upper()
        # SEC file is dict of {index: {cik_str, ticker, title}}
        for _idx, entry in mapping.items():
            if entry.get("ticker", "").upper() == tk:
                return str(entry["cik_str"]).zfill(10)
        return None

    def _download_company_tickers(self) -> Dict[str, Any]:
        url = "https://www.sec.gov/files/company_tickers.json"
        try:
            resp = requests.get(url, headers=self._headers, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            log.error("Failed to download company_tickers.json: %s", exc)
            return {}

    # ── filings index ────────────────────────────────────

    def _fetch_filings_index(self, cik: str) -> List[Dict[str, Any]]:
        """Get recent filings metadata from SEC submissions endpoint."""
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        try:
            time.sleep(_SEC_WAIT)
            resp = requests.get(url, headers=self._headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            log.error("Edgar filings index fetch failed: %s", exc)
            return []

        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.cfg.sec_lookback_days)).strftime("%Y-%m-%d")
        cik_num = cik.lstrip("0")

        results: List[Dict[str, Any]] = []
        for i in range(len(forms)):
            ftype = forms[i] if i < len(forms) else ""
            fdate = dates[i] if i < len(dates) else ""
            acc = accessions[i] if i < len(accessions) else ""
            pdoc = primary_docs[i] if i < len(primary_docs) else ""

            if fdate < cutoff:
                continue
            if ftype not in _ALL_TYPES:
                continue

            acc_clean = acc.replace("-", "")
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_clean}/{pdoc}"
            results.append({
                "filing_type": ftype,
                "filing_date": fdate,
                "filing_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={ftype}&dateb=&owner=include&count=10",
                "document_url": filing_url,
                "accession": acc,
            })

        # Sort preferred types first
        results.sort(key=lambda x: (0 if x["filing_type"] in _PREF_TYPES else 1, x["filing_date"]),
                     reverse=False)
        log.info("CIK %s: %d filings in lookback window", cik, len(results))
        return results

    # ── document fetch ───────────────────────────────────

    def _fetch_document(self, meta: Dict[str, Any]) -> Optional[str]:
        """Download the primary document text."""
        url = meta.get("document_url", "")
        if not url:
            return None
        try:
            time.sleep(_SEC_WAIT)
            resp = requests.get(url, headers=self._headers, timeout=30)
            resp.raise_for_status()
            # Limit text to 500KB to avoid memory issues with huge filings
            return resp.text[:500_000]
        except Exception as exc:
            log.warning("Failed to fetch %s: %s", url, exc)
            return None
