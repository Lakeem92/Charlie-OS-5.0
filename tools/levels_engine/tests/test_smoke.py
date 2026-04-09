"""
Smoke tests for the Levels Engine.

Default: offline (mocked data).
Set RUN_LIVE=1 to run a live smoke test against SPY (requires API keys).

Usage:
    cd tools/levels_engine
    python -m pytest tests/ -v
    RUN_LIVE=1 python -m pytest tests/ -v -k live
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure package is importable
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ── Fixtures ─────────────────────────────────────────────────

MOCK_CONTRACTS = [
    {"symbol": "SPY250221C00590000", "type": "call", "strike": 590.0,
     "expiration": "2025-02-21", "open_interest": 45000, "volume": 1200, "iv": 0.15},
    {"symbol": "SPY250221P00590000", "type": "put", "strike": 590.0,
     "expiration": "2025-02-21", "open_interest": 42000, "volume": 900, "iv": 0.16},
    {"symbol": "SPY250221C00600000", "type": "call", "strike": 600.0,
     "expiration": "2025-02-21", "open_interest": 80000, "volume": 3500, "iv": 0.14},
    {"symbol": "SPY250221P00600000", "type": "put", "strike": 600.0,
     "expiration": "2025-02-21", "open_interest": 15000, "volume": 800, "iv": 0.17},
    {"symbol": "SPY250221C00610000", "type": "call", "strike": 610.0,
     "expiration": "2025-02-21", "open_interest": 25000, "volume": 600, "iv": 0.18},
    {"symbol": "SPY250221P00610000", "type": "put", "strike": 610.0,
     "expiration": "2025-02-21", "open_interest": 60000, "volume": 2100, "iv": 0.19},
    {"symbol": "SPY250221C00580000", "type": "call", "strike": 580.0,
     "expiration": "2025-02-21", "open_interest": 5000, "volume": 100, "iv": 0.20},
    {"symbol": "SPY250221P00580000", "type": "put", "strike": 580.0,
     "expiration": "2025-02-21", "open_interest": 3000, "volume": 50, "iv": 0.21},
    {"symbol": "SPY250221C00620000", "type": "call", "strike": 620.0,
     "expiration": "2025-02-21", "open_interest": 2000, "volume": 40, "iv": 0.22},
    {"symbol": "SPY250221P00620000", "type": "put", "strike": 620.0,
     "expiration": "2025-02-21", "open_interest": 1000, "volume": 20, "iv": 0.23},
]

MOCK_FILING_TEXT = """
<html><body>
<p>The Company has entered into a convertible note with a conversion price of $595.00 per share.
The warrants are exercisable at an exercise price of $610.50 per share, subject to adjustment.
The offering price of the shares was determined to be $588.25 per share pursuant to the
underwriting agreement dated January 15, 2025.</p>
<p>Redemption price: $600.00 per share. VWAP floor: $575.00.</p>
</body></html>
"""


# ── Mock Config ──────────────────────────────────────────────

def _mock_config():
    """Return a Config-like object without requiring env vars."""
    from levels_engine.config import Config
    from dataclasses import fields

    # Build with all defaults by patching required env vars
    with patch.dict(os.environ, {
        "ALPACA_API_KEY": "test-key",
        "ALPACA_API_SECRET": "test-secret",
        "SEC_USER_AGENT": "TestAgent test@test.com",
    }):
        return Config()


# ── Options compute tests ────────────────────────────────────

class TestOptionsCompute:
    """Test deterministic options level computation with mock data."""

    def setup_method(self):
        self.cfg = _mock_config()

    def test_compute_returns_output(self):
        from levels_engine.compute_options_levels import compute_options_levels
        result = compute_options_levels("SPY", 598.0, MOCK_CONTRACTS, self.cfg)
        assert result.ticker == "SPY"
        assert result.spot == 598.0
        assert result.call_wall is not None
        assert result.put_wall is not None

    def test_call_wall_is_max_call_oi(self):
        from levels_engine.compute_options_levels import compute_options_levels
        result = compute_options_levels("SPY", 598.0, MOCK_CONTRACTS, self.cfg)
        # Strike 600 has 80000 call OI — should be the call wall
        assert result.call_wall.strike == 600.0
        assert result.call_wall.call_oi == 80000

    def test_put_wall_is_max_put_oi(self):
        from levels_engine.compute_options_levels import compute_options_levels
        result = compute_options_levels("SPY", 598.0, MOCK_CONTRACTS, self.cfg)
        # Strike 610 has 60000 put OI — should be the put wall
        assert result.put_wall.strike == 610.0
        assert result.put_wall.put_oi == 60000

    def test_top_clusters_populated(self):
        from levels_engine.compute_options_levels import compute_options_levels
        result = compute_options_levels("SPY", 598.0, MOCK_CONTRACTS, self.cfg)
        assert len(result.top_call_clusters) > 0
        assert len(result.top_put_clusters) > 0

    def test_empty_contracts(self):
        from levels_engine.compute_options_levels import compute_options_levels
        result = compute_options_levels("SPY", 598.0, [], self.cfg)
        assert result.call_wall is None
        assert result.put_wall is None
        assert result.diagnostics.contracts_count == 0

    def test_near_spot_filters_by_pct(self):
        from levels_engine.compute_options_levels import compute_options_levels
        result = compute_options_levels("SPY", 598.0, MOCK_CONTRACTS, self.cfg)
        for lv in result.near_spot_levels:
            assert abs(lv.strike - 598.0) / 598.0 <= self.cfg.near_spot_pct / 100

    def test_build_strike_csv(self):
        from levels_engine.compute_options_levels import build_strike_csv
        df = build_strike_csv(MOCK_CONTRACTS)
        assert "strike" in df.columns
        assert "call_oi" in df.columns
        assert "put_oi" in df.columns
        assert len(df) > 0

    def test_pin_candidates_balance(self):
        from levels_engine.compute_options_levels import compute_options_levels
        result = compute_options_levels("SPY", 598.0, MOCK_CONTRACTS, self.cfg)
        for pin in result.pin_candidates:
            assert pin.balance <= self.cfg.pin_balance_band


# ── Arb extraction tests ────────────────────────────────────

class TestArbExtract:
    """Test regex-based contractual level extraction."""

    def setup_method(self):
        self.cfg = _mock_config()

    def test_extracts_levels_from_filing(self):
        from levels_engine.sec.arb_extract import extract_arb_levels
        filings = [{
            "filing_type": "8-K",
            "filing_date": "2025-01-20",
            "filing_url": "https://sec.gov/test",
            "document_url": "https://sec.gov/test/doc.htm",
            "document_text": MOCK_FILING_TEXT,
        }]
        result = extract_arb_levels("SPY", filings, self.cfg)
        assert result.diagnostics.filings_scanned == 1
        all_levels = result.verified_levels + result.candidates
        assert len(all_levels) > 0

    def test_finds_conversion_price(self):
        from levels_engine.sec.arb_extract import extract_arb_levels
        filings = [{
            "filing_type": "8-K",
            "filing_date": "2025-01-20",
            "filing_url": "",
            "document_url": "",
            "document_text": MOCK_FILING_TEXT,
        }]
        result = extract_arb_levels("SPY", filings, self.cfg)
        all_levels = result.verified_levels + result.candidates
        price_values = [lv.level for lv in all_levels]
        assert 595.0 in price_values, f"Expected 595.0 in {price_values}"

    def test_empty_filings(self):
        from levels_engine.sec.arb_extract import extract_arb_levels
        result = extract_arb_levels("SPY", [], self.cfg)
        assert result.verified_levels == []
        assert result.candidates == []
        assert result.diagnostics.filings_scanned == 0

    def test_no_crash_on_garbage_html(self):
        from levels_engine.sec.arb_extract import extract_arb_levels
        filings = [{
            "filing_type": "8-K",
            "filing_date": "2025-01-20",
            "filing_url": "", "document_url": "",
            "document_text": "<html><<<<broken>>>></html>",
        }]
        result = extract_arb_levels("SPY", filings, self.cfg)
        assert result is not None


# ── Schema tests ─────────────────────────────────────────────

class TestSchemas:
    def test_options_output_serialises(self):
        from levels_engine.schemas import OptionsLevelsOutput
        out = OptionsLevelsOutput(ticker="TEST", spot=100.0, asof_utc="2025-01-01T00:00:00Z",
                                  window_days=60, expirations_considered=5)
        d = out.model_dump()
        assert d["ticker"] == "TEST"
        assert isinstance(json.dumps(d), str)

    def test_arb_output_serialises(self):
        from levels_engine.schemas import ArbLevelsOutput
        out = ArbLevelsOutput(ticker="TEST", asof_utc="2025-01-01T00:00:00Z", lookback_days=45)
        d = out.model_dump()
        assert d["ticker"] == "TEST"


# ── Report generation test ───────────────────────────────────

class TestReport:
    def test_report_generates_markdown(self):
        from levels_engine.schemas import OptionsLevelsOutput, ArbLevelsOutput
        from levels_engine.report_md import generate_report
        opts = OptionsLevelsOutput(ticker="TEST", spot=100.0,
                                   asof_utc="2025-01-01T00:00:00Z",
                                   window_days=60, expirations_considered=3)
        arb = ArbLevelsOutput(ticker="TEST", asof_utc="2025-01-01T00:00:00Z",
                              lookback_days=45)
        md = generate_report(opts, arb)
        assert "# LEVELS REPORT" in md
        assert "TEST" in md


# ── Live smoke test (opt-in) ────────────────────────────────

@pytest.mark.skipif(
    os.getenv("RUN_LIVE", "0") != "1",
    reason="Set RUN_LIVE=1 to run live smoke test"
)
class TestLiveSmoke:
    def test_spy_full_pipeline(self, tmp_path):
        """Full pipeline against SPY with real API calls."""
        from levels_engine.config import Config
        cfg = Config()
        cfg.ensure_dirs()

        from levels_engine.providers.alpaca_options import AlpacaOptionsProvider
        from levels_engine.compute_options_levels import compute_options_levels
        from levels_engine.sec.edgar_fetch import EdgarFetcher
        from levels_engine.sec.arb_extract import extract_arb_levels
        from levels_engine.report_md import generate_report

        provider = AlpacaOptionsProvider(cfg)
        spot = provider.get_spot_price("SPY")
        assert spot > 0

        contracts = provider.get_option_contracts("SPY")
        assert len(contracts) > 0

        opts = compute_options_levels("SPY", spot, contracts, cfg)
        assert opts.call_wall is not None

        edgar = EdgarFetcher(cfg)
        filings = edgar.get_filings("SPY")
        arb = extract_arb_levels("SPY", filings, cfg)

        report = generate_report(opts, arb)
        assert "LEVELS REPORT" in report
