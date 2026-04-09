"""
Levels Engine — Structured logging.

Writes to both console (rich if available, else plain) and a rotating
log file under the date-stamped output directory.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

_LOG_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FMT = "%Y-%m-%dT%H:%M:%S"

_configured = False


def setup_logging(log_dir: Path | None = None, level: int = logging.INFO) -> None:
    """Initialise root logger. Safe to call multiple times."""
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger("levels_engine")
    root.setLevel(level)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter(_LOG_FMT, datefmt=_DATE_FMT))
    root.addHandler(ch)

    # File handler (optional)
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "levels_engine.log", encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter(_LOG_FMT, datefmt=_DATE_FMT))
        root.addHandler(fh)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"levels_engine.{name}")
