"""
Alpaca Options provider.

Uses Alpaca Market-Data v2 endpoints:
  - GET /v2/stocks/{symbol}/snapshot         → spot price
  - GET /v1beta1/options/snapshots/{ticker}  → full chain (primary)
  - GET /v1beta1/options/contracts           → contract metadata (fallback)
  - GET /v1beta1/options/snapshots           → OI, volume, IV (batch by symbol)

Rate limiting:  simple retry with back-off.
Pagination:     follows `next_page_token`.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

from ..config import Config
from ..logger import get_logger
from .provider_base import ProviderBase

log = get_logger("alpaca_options")

_MAX_RETRIES = 3
_RETRY_WAIT = 2  # seconds


class AlpacaOptionsProvider(ProviderBase):
    """Fetch option contracts + OI from Alpaca.

    Uses the auth mode from Config.alpaca_options_auth (default: live)
    so that options chain / OPRA endpoints get live credentials.
    """

    def __init__(self, cfg: Config) -> None:
        super().__init__(cfg)
        # Options chain always uses the options-auth key pair
        self._headers = cfg.get_alpaca_data_headers(auth_mode=cfg.alpaca_options_auth)
        self._data_base = cfg.alpaca_data_url
        log.info(
            "AlpacaOptionsProvider using auth_mode=%s  data_feed=%s",
            cfg.alpaca_options_auth,
            cfg.alpaca_data_feed,
        )

    # ── helpers ──────────────────────────────────────────

    def _get(self, url: str, params: Dict[str, Any] | None = None) -> Any:
        """GET with retries.  Reports 404s with full URL + body snippet."""
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = requests.get(url, headers=self._headers, params=params, timeout=30)
                if resp.status_code == 429:
                    wait = _RETRY_WAIT * attempt
                    log.warning("Rate-limited (429). Waiting %ds…", wait)
                    time.sleep(wait)
                    continue
                if resp.status_code == 404:
                    log.error(
                        "404 NOT FOUND — URL: %s  params=%s\n  Body: %s",
                        resp.url, params, resp.text[:300],
                    )
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as exc:
                if attempt == _MAX_RETRIES:
                    log.error("Request failed after %d retries: %s", _MAX_RETRIES, exc)
                    raise
                time.sleep(_RETRY_WAIT * attempt)
        return {}

    def _paginate(self, url: str, params: Dict[str, Any], key: str) -> List[Dict]:
        """Follow next_page_token and collect all items under `key`."""
        all_items: List[Dict] = []
        while True:
            data = self._get(url, params)
            items = data.get(key) or data.get("option_contracts") or []

            # Handle dict-of-dicts (snapshots endpoint returns {symbol: {...}})
            if isinstance(items, dict):
                all_items.extend(items.values() if items else [])
            else:
                all_items.extend(items)

            token = data.get("next_page_token")
            if not token:
                break
            params["page_token"] = token
        return all_items

    # ── public API ───────────────────────────────────────

    def get_spot_price(self, ticker: str) -> float:
        """Last trade price from Alpaca stock snapshot."""
        url = f"{self._data_base}/v2/stocks/{ticker}/snapshot"
        params: Dict[str, str] = {}
        if self.cfg.alpaca_data_feed:
            params["feed"] = "iex"  # use iex for stock snapshot (free tier)
        data = self._get(url, params)
        # snapshot → latestTrade → p (price)
        lt = data.get("latestTrade") or {}
        price = lt.get("p", 0.0)
        if not price:
            # fallback to latest bar close
            bar = data.get("dailyBar") or data.get("minuteBar") or {}
            price = bar.get("c", 0.0)
        if not price:
            raise ValueError(f"Cannot determine spot price for {ticker}")
        log.info("%s spot = %.2f", ticker, price)
        return float(price)

    def get_option_contracts(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Fetch option chain via the snapshots/{underlying} endpoint.

        This uses the same endpoint pattern as the existing LabAlpacaClient:
          GET /v1beta1/options/snapshots/{underlying}?feed=indicative

        Returns list of dicts with keys:
          symbol, type, strike, expiration, open_interest, volume, iv
        """
        merged = self._fetch_chain_via_snapshots(ticker)
        if not merged:
            # Fallback: try the contracts + individual snapshots approach
            log.info("%s: snapshots-by-underlying empty, falling back to contracts endpoint", ticker)
            merged = self._fetch_chain_via_contracts(ticker)

        if not merged:
            log.warning("No option contracts returned for %s", ticker)
        else:
            log.info("%s → %d option contracts with data", ticker, len(merged))
        return merged

    # ── private helpers ──────────────────────────────────

    def _parse_symbol(self, sym: str) -> Dict[str, Any]:
        """
        Parse OCC option symbol like SPY260220C00590000 into components.
        Format: ROOT(variable) + YYMMDD + C/P + strike*1000 (8 digits)
        """
        import re
        m = re.match(r'^([A-Z]+)(\d{6})([CP])(\d{8})$', sym)
        if not m:
            return {}
        root, date_str, cp, strike_str = m.groups()
        year = 2000 + int(date_str[:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        exp = f"{year:04d}-{month:02d}-{day:02d}"
        strike = int(strike_str) / 1000.0
        return {
            "root": root,
            "expiration": exp,
            "type": "call" if cp == "C" else "put",
            "strike": strike,
        }

    def _fetch_chain_via_snapshots(self, ticker: str) -> List[Dict[str, Any]]:
        """
        GET /v1beta1/options/snapshots/{underlying}
        Returns all contract snapshots for the underlying in one call.

        Then enriches with OI from /v2/options/contracts (broker API) because
        the indicative feed snapshots do not include openInterest.
        """
        url = f"{self._data_base}/v1beta1/options/snapshots/{ticker}"
        feed = self.cfg.alpaca_data_feed or "indicative"
        params: Dict[str, Any] = {"feed": feed, "limit": 1000}

        all_snaps: Dict[str, Dict] = {}
        while True:
            data = self._get(url, params)
            snapshots = data.get("snapshots") or {}
            if isinstance(snapshots, dict):
                all_snaps.update(snapshots)
            token = data.get("next_page_token")
            if not token:
                break
            params["page_token"] = token

        log.info("%s snapshots (raw) = %d", ticker, len(all_snaps))
        if not all_snaps:
            return []

        # Fetch OI from contracts endpoint (works on indicative/free tier)
        oi_map = self._fetch_contracts_oi(ticker)

        # Parse symbols and build result
        now = datetime.now(timezone.utc)
        exp_limit = (now + timedelta(days=self.cfg.options_expiry_window_days)).strftime("%Y-%m-%d")
        exp_start = now.strftime("%Y-%m-%d")

        merged: List[Dict[str, Any]] = []
        for sym, snap in all_snaps.items():
            parsed = self._parse_symbol(sym)
            if not parsed:
                continue
            exp = parsed["expiration"]
            if exp < exp_start or exp > exp_limit:
                continue
            greeks = snap.get("greeks") or {}

            # OI: prefer contracts endpoint, fallback to snapshot field
            oi_info = oi_map.get(sym, {})
            oi = int(oi_info.get("open_interest", 0) or snap.get("openInterest", 0) or 0)
            oi_date = oi_info.get("open_interest_date", "")

            # Volume: prefer snapshot field, fallback to dailyBar.v
            vol = int(snap.get("dailyVolume", 0) or 0)
            if not vol:
                bar = snap.get("dailyBar") or {}
                vol = int(bar.get("v", 0) or 0)

            # IV: prefer snapshot field, fallback to greeks
            iv = float(snap.get("impliedVolatility", 0) or greeks.get("iv", 0) or 0)

            merged.append({
                "symbol": sym,
                "type": parsed["type"][:1],  # c / p
                "strike": parsed["strike"],
                "expiration": exp,
                "open_interest": oi,
                "open_interest_date": oi_date,
                "volume": vol,
                "iv": iv,
            })

        # Limit to first N expirations
        expirations = sorted(set(c["expiration"] for c in merged))
        kept_exp = set(expirations[: self.cfg.options_max_expirations])
        filtered = [c for c in merged if c["expiration"] in kept_exp]
        log.info("%s contracts (filtered to %d expirations) = %d",
                 ticker, len(kept_exp), len(filtered))
        return filtered

    def _fetch_contracts_oi(self, ticker: str) -> Dict[str, Dict[str, Any]]:
        """
        Fetch OI data from /v2/options/contracts (broker API).
        Returns {symbol: {"open_interest": int, "open_interest_date": str}}.
        The indicative-feed snapshots do NOT contain openInterest,
        so this is the only reliable OI source for free-tier accounts.
        """
        contracts = self._fetch_contracts_list(ticker)
        oi_map: Dict[str, Dict[str, Any]] = {}
        for c in contracts:
            sym = c.get("symbol", "")
            oi = int(c.get("open_interest", 0) or 0)
            oi_date = c.get("open_interest_date", "")
            if sym:
                oi_map[sym] = {"open_interest": oi, "open_interest_date": oi_date}
        log.info("%s OI enrichment: %d contracts with OI data", ticker, len(oi_map))
        return oi_map

    def _fetch_chain_via_contracts(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Fallback: GET /v1beta1/options/contracts then merge snapshots.
        Used if the snapshot-by-underlying endpoint returns empty.
        """
        contracts = self._fetch_contracts_list(ticker)
        if not contracts:
            return []

        symbols = [c["symbol"] for c in contracts]
        snapshots = self._fetch_snapshots_batch(symbols)
        snap_map = {s.get("symbol", ""): s for s in snapshots}

        merged: List[Dict[str, Any]] = []
        for c in contracts:
            sym = c["symbol"]
            snap = snap_map.get(sym, {})
            greeks = snap.get("greeks") or {}

            # OI from contracts endpoint directly
            oi = int(c.get("open_interest", 0) or 0)
            oi_date = c.get("open_interest_date", "")

            # Volume: prefer snapshot field, fallback to dailyBar.v
            vol = int(snap.get("dailyVolume", 0) or 0)
            if not vol:
                bar = snap.get("dailyBar") or {}
                vol = int(bar.get("v", 0) or 0)

            # IV: prefer snapshot field, fallback to greeks
            iv = float(snap.get("impliedVolatility", 0) or greeks.get("iv", 0) or 0)

            merged.append({
                "symbol": sym,
                "type": c.get("type", "").lower()[:1],
                "strike": float(c.get("strike_price", 0)),
                "expiration": c.get("expiration_date", ""),
                "open_interest": oi,
                "open_interest_date": oi_date,
                "volume": vol,
                "iv": iv,
            })
        return merged

    def _fetch_contracts_list(self, ticker: str) -> List[Dict]:
        """GET /v2/options/contracts with expiration window filter."""
        url = "https://api.alpaca.markets/v2/options/contracts"
        now = datetime.now(timezone.utc)
        exp_start = now.strftime("%Y-%m-%d")
        exp_end = (now + timedelta(days=self.cfg.options_expiry_window_days)).strftime("%Y-%m-%d")
        params: Dict[str, Any] = {
            "underlying_symbols": ticker,
            "expiration_date_gte": exp_start,
            "expiration_date_lte": exp_end,
            "status": "active",
            "limit": 1000,
        }
        if self.cfg.alpaca_data_feed and self.cfg.alpaca_data_feed != "indicative":
            params["feed"] = self.cfg.alpaca_data_feed

        try:
            raw = self._paginate(url, params, "option_contracts")
        except Exception as exc:
            log.warning("Contracts endpoint failed: %s — using snapshots only", exc)
            return []

        log.info("%s contracts (raw) = %d", ticker, len(raw))
        expirations = sorted(set(c.get("expiration_date", "") for c in raw))
        kept_exp = set(expirations[: self.cfg.options_max_expirations])
        filtered = [c for c in raw if c.get("expiration_date", "") in kept_exp]
        log.info("%s contracts (filtered to %d expirations) = %d",
                 ticker, len(kept_exp), len(filtered))
        return filtered

    def _fetch_snapshots_batch(self, symbols: List[str]) -> List[Dict]:
        """GET /v1beta1/options/snapshots in batches (API limit ~100 per call)."""
        url = f"{self._data_base}/v1beta1/options/snapshots"
        batch_size = 100
        all_snaps: List[Dict] = []
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i: i + batch_size]
            params: Dict[str, Any] = {
                "symbols": ",".join(batch),
                "limit": batch_size,
            }
            if self.cfg.alpaca_data_feed and self.cfg.alpaca_data_feed != "indicative":
                params["feed"] = self.cfg.alpaca_data_feed
            data = self._get(url, params)
            snapshots = data.get("snapshots") or {}
            if isinstance(snapshots, dict):
                for sym, snap_data in snapshots.items():
                    snap_data["symbol"] = sym
                    all_snaps.append(snap_data)
            elif isinstance(snapshots, list):
                all_snaps.extend(snapshots)
            if i + batch_size < len(symbols):
                time.sleep(0.3)
        log.info("Fetched %d option snapshots", len(all_snaps))
        return all_snaps
