"""IO helpers — write JSON / CSV to output dirs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ..logger import get_logger

log = get_logger("io")


def write_json(data: Any, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    log.info("Wrote JSON → %s", path)
    return path


def write_csv(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    log.info("Wrote CSV  → %s (%d rows)", path, len(df))
    return path


def write_text(text: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    log.info("Wrote text → %s", path)
    return path


def read_json_cache(path: Path, max_age_hours: float = 168) -> Any | None:
    """Return cached JSON if file exists and is younger than max_age_hours."""
    if not path.exists():
        return None
    import time
    age_h = (time.time() - path.stat().st_mtime) / 3600
    if age_h > max_age_hours:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
