"""Shared Event model and small helpers used by every source."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Event:
    """A normalized event from any source."""

    title: str
    start: datetime                      # timezone-aware when possible
    source: str                          # "city" | "eventbrite" | "facebook"
    url: str = ""
    location: str = ""
    description: str = ""
    categories: list = field(default_factory=list)

    # Geo / price get filled in by the source or the filter step.
    lat: Optional[float] = None
    lon: Optional[float] = None
    zip_code: Optional[str] = None
    price: Optional[float] = None        # None = unknown, 0.0 = free
    is_free: Optional[bool] = None

    # Set during filtering.
    distance_mi: Optional[float] = None
    matched_interests: list = field(default_factory=list)

    @property
    def uid(self) -> str:
        """Stable id for dedup across runs."""
        if self.url:
            base = self.url.split("?")[0].rstrip("/")
        else:
            base = f"{self.title}|{self.start.date() if self.start else ''}"
        return hashlib.sha1(f"{self.source}:{base}".encode("utf-8")).hexdigest()[:16]

    def haystack(self) -> str:
        """Lower-cased blob used for keyword matching."""
        return " ".join(
            [self.title or "", self.description or "", " ".join(self.categories)]
        ).lower()


# --- small text helpers ----------------------------------------------------

_ZIP_RE = re.compile(r"\b(7\d{4})\b")           # Texas zips start with 7
_PRICE_RE = re.compile(r"\$\s?(\d{1,4}(?:\.\d{2})?)")


def extract_zip(text: str) -> Optional[str]:
    if not text:
        return None
    m = _ZIP_RE.search(text)
    return m.group(1) if m else None


def guess_price_from_text(text: str) -> Optional[float]:
    """Pull the lowest dollar amount mentioned, or 0.0 if it reads as free."""
    if not text:
        return None
    low = text.lower()
    if "free" in low and "$" not in text:
        return 0.0
    prices = [float(p) for p in _PRICE_RE.findall(text)]
    if prices:
        return min(prices)
    if "free" in low:
        return 0.0
    return None


def clean(text: str) -> str:
    """Collapse whitespace / unescape common iCal escapes."""
    if not text:
        return ""
    text = text.replace("\\n", " ").replace("\\,", ",").replace("\\;", ";")
    return re.sub(r"\s+", " ", text).strip()
