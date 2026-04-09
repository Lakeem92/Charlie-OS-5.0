"""
Levels Engine — Pydantic v2 schemas for JSON outputs.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Options levels ──────────────────────────────────────────

class StrikeLevel(BaseModel):
    strike: float
    call_oi: int = 0
    put_oi: int = 0
    total_oi: int = 0


class PinCandidate(BaseModel):
    strike: float
    total_oi: int
    balance: float = Field(
        description="abs(call-put)/(call+put+1); lower = more balanced"
    )


class VacuumWindow(BaseModel):
    low_strike: float
    high_strike: float
    avg_oi: float
    distance_from_spot: float


class OptionsLevelsDiagnostics(BaseModel):
    contracts_count: int = 0
    expirations_count: int = 0
    missing_oi_count: int = 0


class OptionsLevelsOutput(BaseModel):
    ticker: str
    spot: float
    asof_utc: str
    window_days: int
    expirations_considered: int
    call_wall: Optional[StrikeLevel] = None
    put_wall: Optional[StrikeLevel] = None
    top_call_clusters: List[StrikeLevel] = Field(default_factory=list)
    top_put_clusters: List[StrikeLevel] = Field(default_factory=list)
    pin_candidates: List[PinCandidate] = Field(default_factory=list)
    vacuum_windows: List[VacuumWindow] = Field(default_factory=list)
    near_spot_levels: List[StrikeLevel] = Field(default_factory=list)
    diagnostics: OptionsLevelsDiagnostics = Field(
        default_factory=OptionsLevelsDiagnostics
    )
    raw_csv_path: Optional[str] = None


# ── SEC / Arb levels ───────────────────────────────────────

class ArbLevel(BaseModel):
    level: float
    label: str
    context_snippet: str = ""
    filing_type: str = ""
    filing_date: str = ""
    filing_url: str = ""
    document_url: str = ""
    confidence: float = 0.0


class ArbLevelsDiagnostics(BaseModel):
    filings_scanned: int = 0
    matches_found: int = 0


class ArbLevelsOutput(BaseModel):
    ticker: str
    asof_utc: str
    lookback_days: int
    verified_levels: List[ArbLevel] = Field(default_factory=list)
    candidates: List[ArbLevel] = Field(default_factory=list)
    diagnostics: ArbLevelsDiagnostics = Field(
        default_factory=ArbLevelsDiagnostics
    )
