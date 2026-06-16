"""
Filter raw events down to the ones worth emailing:
  - happening from now up to LOOKAHEAD_DAYS out
  - within RADIUS_MILES of HOME_ZIP
  - free or priced under MAX_PRICE
  - matching at least one interest, and not a pure admin/government item
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import config
from sources.base import Event

# Offline zip -> lat/lon lookup (no network, no API key). Optional dependency.
try:
    import pgeocode

    _NOMI = pgeocode.Nominatim("us")
except Exception:                       # pragma: no cover
    _NOMI = None


def _zip_latlon(zip_code: str) -> Optional[Tuple[float, float]]:
    if not zip_code or _NOMI is None:
        return None
    try:
        rec = _NOMI.query_postal_code(zip_code)
        lat, lon = float(rec.latitude), float(rec.longitude)
        if math.isnan(lat) or math.isnan(lon):
            return None
        return lat, lon
    except Exception:
        return None


def home_latlon() -> Tuple[float, float]:
    return _zip_latlon(config.HOME_ZIP) or config.HOME_LATLON_FALLBACK


def _haversine_mi(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    r = 3958.8  # earth radius in miles
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _within_radius(ev: Event, home: Tuple[float, float]) -> bool:
    coords = None
    if ev.lat is not None and ev.lon is not None:
        coords = (ev.lat, ev.lon)
    elif ev.zip_code:
        coords = _zip_latlon(ev.zip_code)
    if coords is None:
        # Location unknown: keep it but flag (most city events are local).
        ev.distance_mi = None
        return True
    ev.distance_mi = round(_haversine_mi(home, coords), 1)
    return ev.distance_mi <= config.RADIUS_MILES


def _price_ok(ev: Event) -> bool:
    if ev.price is None:
        return config.INCLUDE_UNKNOWN_PRICE
    return ev.price < config.MAX_PRICE      # free (0.0) passes too


def _interests(ev: Event) -> List[str]:
    blob = ev.haystack()
    hits = []
    for interest, words in config.INTEREST_KEYWORDS.items():
        if any(w in blob for w in words):
            hits.append(interest)
    return hits


def _is_excluded(ev: Event) -> bool:
    blob = ev.haystack()
    if any(bad in blob for bad in config.EXCLUDE_KEYWORDS):
        # Still rescue it if it's clearly cultural by category.
        cat_blob = " ".join(ev.categories).lower()
        if any(c in cat_blob for c in config.ALWAYS_KEEP_CATEGORIES):
            return False
        return True
    return False


def _cultural(ev: Event) -> bool:
    if _is_excluded(ev):
        return False
    ev.matched_interests = _interests(ev)
    if ev.matched_interests:
        return True
    cat_blob = " ".join(ev.categories).lower()
    return any(c in cat_blob for c in config.ALWAYS_KEEP_CATEGORIES)


def apply_filters(events: List[Event]) -> List[Event]:
    home = home_latlon()
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=config.LOOKAHEAD_DAYS)

    kept: List[Event] = []
    for ev in events:
        start = ev.start
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if start < now - timedelta(hours=12):   # drop past events
            continue
        if start > horizon:
            continue
        if not _cultural(ev):
            continue
        if not _price_ok(ev):
            continue
        if not _within_radius(ev, home):
            continue
        kept.append(ev)

    kept.sort(key=lambda e: e.start)
    print(f"[filter] {len(kept)} events kept of {len(events)} raw")
    return kept
