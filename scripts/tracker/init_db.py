"""
Catalyst Tracker — Database Initializer
War Room v10.0 | Charlie OS 5.0

Run once to create the SQLite database. Safe to re-run — won't drop existing data.

Usage:
    python scripts/tracker/init_db.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "catalyst_tracker.db"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ── CATALYST LOG ────────────────────────────────────────────────────────────
    # One row per War Room analysis. Mirrors the §3 output format exactly.
    c.execute("""
    CREATE TABLE IF NOT EXISTS catalyst_log (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        logged_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        analysis_date       DATE NOT NULL,           -- date analysis was run

        -- Identity
        ticker              TEXT NOT NULL,
        company_name        TEXT,
        sector              TEXT,                    -- from §5 sector expertise
        lifecycle_stage     TEXT,                    -- STAGE 1/2/3/4 from §6

        -- Catalyst Classification (§7A, §7B)
        catalyst_type       INTEGER,                 -- 1-14
        catalyst_type_label TEXT,                    -- e.g. "EXISTENTIAL DE-RISKING"
        catalyst_engine     TEXT,                    -- F / M / N / F+M / F+N / ALL THREE
        narrative_tier      TEXT,                    -- TIER 1 / TIER 2 / TIER 3 (if narrative)

        -- Scoring Dimensions (§7C) — each 0-2
        score_realness      REAL,
        score_freshness     REAL,
        score_thesis_impact REAL,
        score_magnitude     REAL,
        score_stacking      REAL,

        -- Modifier and final score
        score_modifier      REAL DEFAULT 0,          -- ATM, float, narrative cap adjustments
        modifier_reason     TEXT,                    -- e.g. "ACTIVE ATM -1.5"
        score_total         REAL NOT NULL,           -- final 0-10

        -- Verdict fields (§3 template)
        conviction_tag      TEXT,                    -- HIGH / DEVELOPING / WEAK
        analyst_tier        TEXT,                    -- TIER 1-5 (if §8 catalyst)
        macro_context       TEXT,                    -- TAILWIND / HEADWIND / NEUTRAL
        the_one_variable    TEXT,                    -- single most important forward factor
        thesis_summary      TEXT,                    -- brief synthesis of the analysis
        catalyst_direction  TEXT,                    -- LONG / SHORT (direction of the catalyst)

        -- Earnings season tagging
        earnings_season     TEXT,                    -- e.g. "Q1-2026" for pattern grouping
        is_earnings         INTEGER DEFAULT 0        -- 1 if this was an earnings catalyst
    )
    """)

    # ── OUTCOMES ────────────────────────────────────────────────────────────────
    # Price follow-through for each logged catalyst.
    # Populated by log_outcome.py (manually or via auto-fetch).
    c.execute("""
    CREATE TABLE IF NOT EXISTS outcomes (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        catalyst_id         INTEGER NOT NULL REFERENCES catalyst_log(id),
        updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        -- Price checkpoints
        price_at_analysis   REAL,
        price_1d            REAL,
        price_3d            REAL,
        price_5d            REAL,
        price_10d           REAL,
        price_20d           REAL,

        -- Calculated returns (positive = moved in catalyst direction)
        return_1d           REAL,
        return_3d           REAL,
        return_5d            REAL,
        return_10d          REAL,
        return_20d          REAL,

        -- Qualitative outcome
        catalyst_resolved   TEXT,                    -- YES / NO / PARTIAL
        resolution_notes    TEXT                     -- what actually happened
    )
    """)

    # ── INDEXES ─────────────────────────────────────────────────────────────────
    c.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON catalyst_log(ticker)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_score ON catalyst_log(score_total)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_date ON catalyst_log(analysis_date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_type ON catalyst_log(catalyst_type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_earnings_season ON catalyst_log(earnings_season)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_outcome_catalyst ON outcomes(catalyst_id)")

    conn.commit()
    conn.close()
    print(f"Database initialized at: {DB_PATH}")


if __name__ == "__main__":
    init_db()
