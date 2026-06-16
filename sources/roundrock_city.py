"""
City of Round Rock source.

Pulls one or more public iCal (.ics) feeds from the city's "The Events
Calendar" install. iCal is a stable, documented format, so this is the most
reliable of the three sources.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import requests
from icalendar import Calendar

import config
from sources.base import Event, clean, extract_zip, guess_price_from_text


def _to_dt(value) -> datetime:
    """icalendar gives date or datetime; normalize to aware datetime."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    # all-day date -> midnight UTC
    return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)


def _fetch_feed(url: str) -> List[Event]:
    resp = requests.get(
        url,
        headers={"User-Agent": config.USER_AGENT, "Accept": "text/calendar"},
        timeout=config.REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    cal = Calendar.from_ical(resp.content)

    events: List[Event] = []
    for comp in cal.walk("VEVENT"):
        title = clean(str(comp.get("summary", "")))
        if not title:
            continue
        dtstart = comp.get("dtstart")
        if dtstart is None:
            continue
        start = _to_dt(dtstart.dt)

        description = clean(str(comp.get("description", "")))
        location = clean(str(comp.get("location", "")))
        url_ = str(comp.get("url", "")) or ""

        cats = comp.get("categories")
        categories: List[str] = []
        if cats is not None:
            raw = getattr(cats, "cats", None) or cats
            try:
                categories = [str(c) for c in raw]
            except TypeError:
                categories = [str(cats)]

        ev = Event(
            title=title,
            start=start,
            source="city",
            url=url_,
            location=location,
            description=description,
            categories=categories,
        )

        # GEO coordinates if the feed provided them.
        geo = comp.get("geo")
        if geo is not None:
            try:
                ev.lat = float(geo.latitude)
                ev.lon = float(geo.longitude)
            except Exception:
                pass

        ev.zip_code = extract_zip(location) or extract_zip(description)
        ev.price = guess_price_from_text(f"{title} {description}")
        if ev.price is not None:
            ev.is_free = ev.price == 0.0

        events.append(ev)
    return events


def fetch() -> List[Event]:
    """Fetch + de-duplicate all configured city feeds."""
    seen = {}
    for url in config.CITY_ICAL_FEEDS:
        try:
            for ev in _fetch_feed(url):
                seen[ev.uid] = ev          # later feed wins; same uid == dup
        except Exception as exc:           # one bad feed shouldn't kill the run
            print(f"[city] feed failed: {url} -> {exc}")
    out = list(seen.values())
    print(f"[city] collected {len(out)} raw events")
    return out
