"""Base interface for data providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from ..config import Config


class ProviderBase(ABC):
    """Abstract provider — all concrete providers inherit from this."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg

    @abstractmethod
    def get_spot_price(self, ticker: str) -> float:
        """Return last trade / close for underlying."""
        ...

    @abstractmethod
    def get_option_contracts(
        self, ticker: str
    ) -> List[Dict[str, Any]]:
        """Return list of option contract dicts with at minimum:
        symbol, type, strike, expiration, open_interest.
        """
        ...
