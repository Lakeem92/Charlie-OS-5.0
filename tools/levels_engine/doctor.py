#!/usr/bin/env python3
"""
Levels Engine — Doctor (one-command diagnostics).

Usage:
    python tools/levels_engine/doctor.py

Checks:
  1. Env file presence and variable loading
  2. Auth mode configuration (live vs paper for options & trading)
  3. Alpaca stocks data endpoint (authentication)
  4. Alpaca options snapshots endpoint (entitlement / OPRA)
  5. Alpaca options contracts metadata endpoint
  6. Prints targeted guidance for each failure mode
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import requests

# ── paths ────────────────────────────────────────────────────

_ENGINE_DIR = _SCRIPT_DIR                                  # tools/levels_engine/
_ROOT_DIR = _ENGINE_DIR.parent.parent                      # Data_Lab/
_LOCAL_ENV = _ENGINE_DIR / ".env"
_ROOT_ENV = _ROOT_DIR / ".env"
_PAPER_ENV = _ROOT_DIR / "shared" / "config" / "keys" / "paper.env"
_LIVE_ENV = _ROOT_DIR / "shared" / "config" / "keys" / "live.env"

_DATA_DIR = _ROOT_DIR / "data" / "levels"

# ── colours (works on Windows 10+ with ANSI) ────────────────

_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_RESET = "\033[0m"

def _ok(msg: str) -> str:
    return f"  {_GREEN}[OK]{_RESET}  {msg}"

def _warn(msg: str) -> str:
    return f"  {_YELLOW}[!!]{_RESET}  {msg}"

def _fail(msg: str) -> str:
    return f"  {_RED}[FAIL]{_RESET}  {msg}"

def _info(msg: str) -> str:
    return f"  {_CYAN}[--]{_RESET}  {msg}"


def _mask(val: str | None) -> str:
    """Show first 4 + last 4 chars, mask the middle."""
    if not val:
        return "(empty)"
    if len(val) <= 10:
        return val[:2] + "***" + val[-2:]
    return val[:4] + "…" + val[-4:] + f"  (len={len(val)})"


# ── env loading (mirrors config.py logic) ────────────────────

def _load_env_files() -> list[str]:
    """Load .env files in priority order. Return list of files loaded."""
    from dotenv import load_dotenv
    loaded: list[str] = []
    for path, label in [
        (_LOCAL_ENV, "tools/levels_engine/.env"),
        (_ROOT_ENV, "root .env"),
        (_PAPER_ENV, "shared/config/keys/paper.env"),
        (_LIVE_ENV, "shared/config/keys/live.env"),
    ]:
        if path.exists():
            load_dotenv(path, override=False)
            loaded.append(label)
    return loaded


def _strip_quotes(val: str | None) -> str | None:
    """Remove accidental wrapping quotes and whitespace from env values."""
    if val is None:
        return None
    val = val.strip()
    if len(val) >= 2:
        if (val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'"):
            val = val[1:-1].strip()
    return val if val else None


def _get_key(name: str, alt: str | None = None) -> str | None:
    """Get env var with quote-stripping and alternate name fallback."""
    val = _strip_quotes(os.getenv(name))
    if val:
        return val
    if alt:
        val = _strip_quotes(os.getenv(alt))
    return val


def _resolve_pair(mode: str) -> tuple[str | None, str | None]:
    """Resolve key+secret for a given auth mode (live / paper), with legacy fallback."""
    suffix = mode.upper()
    key = _get_key(f"ALPACA_API_KEY_{suffix}")
    secret = _get_key(f"ALPACA_API_SECRET_{suffix}")
    # Legacy single-key fallback
    if not key:
        key = _get_key("ALPACA_API_KEY", "APCA_API_KEY_ID")
    if not secret:
        secret = _get_key("ALPACA_API_SECRET", "APCA_API_SECRET_ACCESS_KEY")
    return key, secret


# ── HTTP checks ──────────────────────────────────────────────

def _check_endpoint(label: str, url: str, headers: dict, params: dict | None = None) -> tuple[int, str]:
    """
    Hit an endpoint, return (status_code, body_snippet).
    Retries once on 5xx.
    """
    for attempt in range(2):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            code = resp.status_code
            body = resp.text[:300]
            if code >= 500 and attempt == 0:
                continue
            return code, body
        except requests.exceptions.Timeout:
            return -1, "Request timed out (10s)"
        except requests.exceptions.ConnectionError as exc:
            return -2, f"Connection error: {exc}"
        except Exception as exc:
            return -99, f"Unexpected error: {exc}"
    return -99, "All retries exhausted"


def _interpret(code: int, body: str, context: str) -> str:
    """Return a human-readable line for the result."""
    if code == 200:
        return _ok(f"{context}: HTTP 200 — access confirmed")
    if code == 401:
        return _fail(
            f"{context}: HTTP 401 — authentication rejected.\n"
            f"         Keys not accepted. Ensure keys match the auth mode (live vs paper)\n"
            f"         and are not wrapped in quotes in .env."
        )
    if code == 403:
        return _fail(
            f"{context}: HTTP 403 — forbidden / entitlement issue.\n"
            f"         Your plan may not include this data.\n"
            f"         For options: you need OPRA market data subscription on your Alpaca account."
        )
    if code == 404:
        return _fail(
            f"{context}: HTTP 404 — endpoint not found.\n"
            f"         This is a URL construction bug, not an auth issue.\n"
            f"         Body: {body[:200]}"
        )
    if code == 429:
        return _warn(f"{context}: HTTP 429 — rate limited. Wait and retry.")
    if code == -1:
        return _fail(f"{context}: Timed out (10s). Check network connection.")
    if code == -2:
        return _fail(f"{context}: Connection error. Check network/firewall.")
    return _warn(f"{context}: HTTP {code}\n         Body: {body[:200]}")


# ── main ─────────────────────────────────────────────────────

def main() -> int:
    lines: list[str] = []  # for log file

    def out(msg: str = "") -> None:
        print(msg)
        lines.append(msg)

    out(f"\n{_BOLD}{'='*60}{_RESET}")
    out(f"{_BOLD}  LEVELS ENGINE — DOCTOR{_RESET}")
    out(f"{_BOLD}{'='*60}{_RESET}\n")

    # ── 1. Env file detection ────────────────────────────
    out(f"{_BOLD}1) Environment files{_RESET}")

    for path, label in [
        (_LOCAL_ENV, "tools/levels_engine/.env"),
        (_ROOT_ENV, "root .env"),
        (_PAPER_ENV, "shared/config/keys/paper.env"),
        (_LIVE_ENV, "shared/config/keys/live.env"),
    ]:
        if path.exists():
            out(_ok(f"{label} exists"))
        else:
            out(_info(f"{label} not found"))

    loaded = _load_env_files()
    if loaded:
        out(_ok(f"Loaded env from: {', '.join(loaded)}"))
    else:
        out(_fail("No .env files found anywhere!"))
        out(f"\n  Fix: copy .env.example → .env and fill in your keys:")
        out(f"    copy tools\\levels_engine\\.env.example tools\\levels_engine\\.env")
        _write_log(lines)
        return 1

    out("")

    # ── 2. Auth modes ────────────────────────────────────
    out(f"{_BOLD}2) Auth mode configuration{_RESET}")

    options_auth = _get_key("ALPACA_OPTIONS_AUTH") or "live"
    trading_auth = _get_key("ALPACA_TRADING_AUTH") or "paper"
    data_feed = _get_key("ALPACA_DATA_FEED") or "indicative"
    sec_agent = _get_key("SEC_USER_AGENT")

    out(_info(f"ALPACA_OPTIONS_AUTH = {options_auth}  ← used for options chain data"))
    out(_info(f"ALPACA_TRADING_AUTH = {trading_auth}  ← used for trading"))
    out(_info(f"ALPACA_DATA_FEED   = {data_feed}"))

    if sec_agent:
        out(_ok(f"SEC_USER_AGENT = {sec_agent}"))
    else:
        out(_warn("SEC_USER_AGENT not set (will use default — set yours for SEC compliance)"))

    out("")

    # ── 3. Key pairs ─────────────────────────────────────
    out(f"{_BOLD}3) Alpaca key pairs{_RESET}")

    opts_key, opts_secret = _resolve_pair(options_auth)
    trd_key, trd_secret = _resolve_pair(trading_auth)

    exit_early = False

    # Options key pair
    if opts_key:
        out(_ok(f"Options key  ({options_auth}) = {_mask(opts_key)}"))
    else:
        out(_fail(f"Options key ({options_auth}) MISSING — need ALPACA_API_KEY_{options_auth.upper()}"))
        exit_early = True

    if opts_secret:
        out(_ok(f"Options secret ({options_auth}) = {_mask(opts_secret)}"))
    else:
        out(_fail(f"Options secret ({options_auth}) MISSING — need ALPACA_API_SECRET_{options_auth.upper()}"))
        exit_early = True

    # Trading key pair (informational)
    if trd_key:
        out(_ok(f"Trading key  ({trading_auth}) = {_mask(trd_key)}"))
    else:
        out(_warn(f"Trading key ({trading_auth}) not set — trading disabled"))

    if exit_early:
        out(f"\n{_RED}  Cannot continue without options key pair.{_RESET}")
        out(f"  Fix: edit tools\\levels_engine\\.env and set ALPACA_API_KEY_{options_auth.upper()} / ALPACA_API_SECRET_{options_auth.upper()}")
        out(f"  Important: do NOT wrap values in quotes.\n")
        _write_log(lines)
        return 1

    out("")

    # ── 4. Alpaca connectivity checks ────────────────────
    out(f"{_BOLD}4) Alpaca data endpoint checks (using {options_auth} keys){_RESET}")

    headers = {
        "APCA-API-KEY-ID": opts_key,
        "APCA-API-SECRET-KEY": opts_secret,
        "Accept": "application/json",
    }

    # Check #1: Stocks latest quote (should be 200)
    stocks_url = "https://data.alpaca.markets/v2/stocks/SPY/quotes/latest"
    stocks_params = {"feed": "iex"}
    stocks_code, stocks_body = _check_endpoint("stocks", stocks_url, headers, stocks_params)
    out(_interpret(stocks_code, stocks_body, "Stocks data (SPY quote)"))

    # Check #2: Options snapshots by underlying (should be 200, NOT 404)
    opts_snap_url = "https://data.alpaca.markets/v1beta1/options/snapshots/SPY"
    opts_snap_params = {"feed": data_feed, "limit": "1"}
    opts_snap_code, opts_snap_body = _check_endpoint("options-snapshots", opts_snap_url, headers, opts_snap_params)
    out(_interpret(opts_snap_code, opts_snap_body, "Options snapshots (SPY)"))

    # Check #3: Options contracts metadata
    opts_contracts_url = "https://api.alpaca.markets/v2/options/contracts"
    opts_contracts_params = {"underlying_symbols": "SPY", "status": "active", "limit": "1"}
    opts_ctr_code, opts_ctr_body = _check_endpoint("options-contracts", opts_contracts_url, headers, opts_contracts_params)
    out(_interpret(opts_ctr_code, opts_ctr_body, "Options contracts (SPY)"))

    out("")

    # ── 5. Targeted guidance ─────────────────────────────
    out(f"{_BOLD}5) Diagnosis{_RESET}")

    all_ok = stocks_code == 200 and opts_snap_code == 200 and opts_ctr_code == 200

    if all_ok:
        out(_ok("All checks passed. Alpaca access is working."))
        out(f"  Run the pipeline:")
        out(f"    python tools\\levels_engine\\run_levels.py SPY TSLA NVDA\n")
    elif stocks_code == 401:
        out(_fail(f"Keys ({options_auth}) are rejected by Alpaca data API."))
        out(f"")
        out(f"  Checklist:")
        out(f"    1. Open tools\\levels_engine\\.env")
        out(f"    2. Confirm ALPACA_API_KEY_{options_auth.upper()} and ALPACA_API_SECRET_{options_auth.upper()} are correct")
        out(f"    3. No quotes around values:  ALPACA_API_KEY_LIVE=AKxyz...  (not \"AKxyz...\")")
        out(f"    4. No trailing spaces")
        out(f"    5. Confirm keys at https://app.alpaca.markets/")
        out(f"    6. Paper keys start with PK/SK; live keys start with AK")
        out(f"")
    elif stocks_code == 200 and (opts_snap_code in (401, 403) or opts_ctr_code in (401, 403)):
        out(_warn("Equities data WORKS but options data is BLOCKED."))
        out(f"")
        out(f"  This usually means:")
        out(f"    • Your Alpaca plan does not include options market data (OPRA)")
        out(f"    • You need an OPRA market data subscription")
        out(f"    • Or the options endpoint requires a different feed")
        out(f"")
        out(f"  Try:")
        out(f"    1. Check your Alpaca dashboard for data subscriptions")
        out(f"    2. Set ALPACA_DATA_FEED=indicative in .env (free tier)")
        out(f"    3. If on paid plan, try ALPACA_DATA_FEED=opra")
        out(f"    4. Run: python tools\\levels_engine\\run_levels.py SPY --skip-options")
        out(f"       (to at least get SEC levels while options access is sorted)")
        out(f"")
    elif opts_snap_code == 404 or opts_ctr_code == 404:
        out(_fail("One or more endpoints returned 404 — URL construction bug."))
        out(f"  Options snapshots URL: {opts_snap_url}")
        out(f"    Status: {opts_snap_code}  Body: {opts_snap_body[:150]}")
        out(f"  Options contracts URL: {opts_contracts_url}")
        out(f"    Status: {opts_ctr_code}  Body: {opts_ctr_body[:150]}")
        out(f"  This is NOT an auth issue — the endpoint path is wrong.")
        out(f"")
    else:
        out(_warn("Mixed results. See details above."))
        out(f"  stocks endpoint          → HTTP {stocks_code}")
        out(f"  options snapshots        → HTTP {opts_snap_code}")
        out(f"  options contracts        → HTTP {opts_ctr_code}")
        out(f"")

    _write_log(lines)
    return 0 if all_ok else 1


def _write_log(lines: list[str]) -> None:
    """Write doctor output to log file."""
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_dir = _DATA_DIR / today
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "doctor.log"
        # Strip ANSI codes for log file
        import re
        ansi_re = re.compile(r"\033\[[0-9;]*m")
        clean = [ansi_re.sub("", line) for line in lines]
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"Doctor run: {datetime.now(timezone.utc).isoformat()}\n")
            f.write("\n".join(clean))
            f.write("\n")
        print(f"  Log written to: {log_path}")
    except Exception:
        pass  # non-critical


if __name__ == "__main__":
    sys.exit(main())
