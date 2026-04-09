"""
Levels Engine — Configuration loader.

Resolution order:
  1. tools/levels_engine/.env  (local override — MUST contain secrets)
  2. repo root .env             (fallback)
  3. Environment variables already set in the shell

Key layout (dual-key):
  ALPACA_API_KEY_LIVE   / ALPACA_API_SECRET_LIVE    → options chain (OPRA)
  ALPACA_API_KEY_PAPER  / ALPACA_API_SECRET_PAPER   → paper trading
  ALPACA_OPTIONS_AUTH   = live|paper  (which pair to use for data pulls)
  ALPACA_TRADING_AUTH   = live|paper  (which pair to use for trading)

Legacy single-key names (ALPACA_API_KEY / ALPACA_API_SECRET) are still
accepted as a fallback so old .env files keep working, but the dual-key
layout is preferred.
"""
from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field

from dotenv import load_dotenv

# --------------- .env resolution ---------------
_THIS_DIR = Path(__file__).resolve().parent.parent  # tools/levels_engine/
_ROOT_DIR = _THIS_DIR.parent.parent                 # Data_Lab/

_DEBUG = os.getenv("LEVELS_ENGINE_DEBUG", "0") == "1"

_local_env = _THIS_DIR / ".env"
_root_env = _ROOT_DIR / ".env"
_paper_env = _ROOT_DIR / "shared" / "config" / "keys" / "paper.env"
_live_env = _ROOT_DIR / "shared" / "config" / "keys" / "live.env"

for _path, _label in [
    (_local_env, "tools/levels_engine/.env"),
    (_root_env, "root .env"),
    (_paper_env, "shared/config/keys/paper.env"),
    (_live_env, "shared/config/keys/live.env"),
]:
    if _path.exists():
        load_dotenv(_path, override=False)
        if _DEBUG:
            print(f"[config] Loaded: {_label}")
    elif _DEBUG:
        print(f"[config] Not found: {_label}")

# --------------- helpers ---------------

def _strip_quotes(val: str | None) -> str | None:
    """Remove accidental wrapping quotes and surrounding whitespace."""
    if val is None:
        return None
    val = val.strip()
    if len(val) >= 2:
        if (val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'"):
            val = val[1:-1].strip()
    return val if val else None


def _env(key: str, default: str | None = None) -> str | None:
    raw = os.getenv(key)
    val = _strip_quotes(raw) if raw is not None else None
    if val is None and default is not None:
        val = default
    if _DEBUG and val:
        print(f"[config] {key} = {val[:4]}..." if len(val or "") > 8 else f"[config] {key} = {val}")
    return val


def _env_str(key: str, default: str) -> str:
    """Like _env but guarantees a non-None return."""
    return _env(key, default) or default


def _env_int(key: str, default: int) -> int:
    raw = _strip_quotes(os.getenv(key))
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _resolve_key_pair(mode: str) -> tuple[str, str]:
    """
    Return (api_key, api_secret) for the given auth mode ('live' or 'paper').

    Lookup priority:
      1. ALPACA_API_KEY_{MODE}  / ALPACA_API_SECRET_{MODE}
      2. Legacy ALPACA_API_KEY  / ALPACA_API_SECRET  (single-key fallback)
      3. APCA_ prefix variants  (Alpaca SDK naming)
    """
    suffix = mode.upper()  # LIVE or PAPER

    key = _strip_quotes(os.getenv(f"ALPACA_API_KEY_{suffix}"))
    secret = _strip_quotes(os.getenv(f"ALPACA_API_SECRET_{suffix}"))

    # Legacy single-key fallback
    if not key:
        key = _strip_quotes(os.getenv("ALPACA_API_KEY")) or _strip_quotes(os.getenv("APCA_API_KEY_ID"))
    if not secret:
        secret = _strip_quotes(os.getenv("ALPACA_API_SECRET")) or _strip_quotes(os.getenv("APCA_API_SECRET_ACCESS_KEY"))

    return (key or "", secret or "")


def _require_key_pair(mode: str, purpose: str) -> tuple[str, str]:
    """Like _resolve_key_pair but raises if either value is empty."""
    key, secret = _resolve_key_pair(mode)
    if not key or not secret:
        raise EnvironmentError(
            f"ALPACA_API_KEY_{mode.upper()} and ALPACA_API_SECRET_{mode.upper()} are required "
            f"for {purpose} (auth mode = {mode}).\n"
            f"  Fix: edit tools/levels_engine/.env and fill in the {mode} key pair.\n"
            f"  Run:  python tools/levels_engine/doctor.py   for full diagnostics."
        )
    return key, secret


# --------------- Config dataclass ---------------

@dataclass(frozen=True)
class Config:
    # Auth mode selectors
    alpaca_options_auth: str = field(default_factory=lambda: _env_str("ALPACA_OPTIONS_AUTH", "live"))
    alpaca_trading_auth: str = field(default_factory=lambda: _env_str("ALPACA_TRADING_AUTH", "paper"))
    alpaca_data_feed: str = field(default_factory=lambda: _env_str("ALPACA_DATA_FEED", "indicative"))

    # Resolved key pairs (populated from auth modes above)
    alpaca_api_key: str = field(default="")
    alpaca_api_secret: str = field(default="")

    # SEC / EDGAR
    sec_user_agent: str = field(
        default_factory=lambda: _env_str("SEC_USER_AGENT", "QuantLabLevelsEngine user@example.com")
    )
    sec_lookback_days: int = field(default_factory=lambda: _env_int("SEC_LOOKBACK_DAYS", 45))
    sec_max_filings: int = field(default_factory=lambda: _env_int("SEC_MAX_FILINGS", 20))

    # Paths
    data_dir: Path = field(default_factory=lambda: _ROOT_DIR / "data" / "levels")
    cache_dir: Path = field(default_factory=lambda: _THIS_DIR / ".cache")

    # Options defaults
    options_expiry_window_days: int = 60
    options_max_expirations: int = 8
    options_top_n: int = 10
    pin_balance_band: float = 0.25
    pin_oi_percentile: float = 70.0
    pin_max_results: int = 5
    vacuum_oi_percentile: float = 30.0
    vacuum_max_results: int = 5
    near_spot_pct: float = 5.0
    near_spot_max: int = 10

    # Arb extraction
    arb_confidence_threshold: float = 0.65

    def __post_init__(self) -> None:
        # Resolve the options key-pair based on auth mode (used for all data pulls)
        key, secret = _require_key_pair(self.alpaca_options_auth, "options chain data")
        # frozen dataclass — use object.__setattr__
        object.__setattr__(self, "alpaca_api_key", key)
        object.__setattr__(self, "alpaca_api_secret", secret)

    # ---------- header helpers ----------

    @staticmethod
    def get_alpaca_data_headers(auth_mode: str = "live") -> dict[str, str]:
        """Return HTTP headers dict for Alpaca data endpoints."""
        key, secret = _require_key_pair(auth_mode, "data endpoints")
        return {
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Accept": "application/json",
        }

    @staticmethod
    def get_alpaca_trading_headers(auth_mode: str = "paper") -> dict[str, str]:
        """Return HTTP headers dict for Alpaca trading endpoints."""
        key, secret = _require_key_pair(auth_mode, "trading endpoints")
        return {
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Accept": "application/json",
        }

    # ---------- URL helpers ----------

    @property
    def alpaca_base_url(self) -> str:
        if self.alpaca_trading_auth == "live":
            return "https://api.alpaca.markets"
        return "https://paper-api.alpaca.markets"

    @property
    def alpaca_data_url(self) -> str:
        return "https://data.alpaca.markets"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
