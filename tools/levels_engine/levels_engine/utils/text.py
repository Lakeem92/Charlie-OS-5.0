"""Text helpers for SEC filing parsing."""
from __future__ import annotations

import re
from html.parser import HTMLParser
from io import StringIO


class _TagStripper(HTMLParser):
    """Simple HTML tag stripper."""

    def __init__(self):
        super().__init__()
        self.reset()
        self._fed: list[str] = []

    def handle_data(self, d: str) -> None:
        self._fed.append(d)

    def get_text(self) -> str:
        return "".join(self._fed)


def strip_html(html: str) -> str:
    """Remove HTML tags, return plain text."""
    s = _TagStripper()
    try:
        s.feed(html)
    except Exception:
        # Fallback: crude regex strip
        return re.sub(r"<[^>]+>", " ", html)
    return s.get_text()


def normalise_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
