"""
Eventbrite source (BEST-EFFORT).

Eventbrite shut down its public search API, so this parses the JSON that the
discovery page embeds in `window.__SERVER_DATA__`. Two important caveats:

  1. Eventbrite frequently bot-walls datacenter IPs (GitHub Actions runners),
     so this may return 403/empty. That is expected and handled gracefully -
     the rest of the tracker keeps working.
  2. Page structure can change without notice. If the layout shifts, this
     parser may stop finding events until the selectors are updated.

If Eventbrite proves unreliable for you, the most robust alternative is to
subscribe to specific organizers' own iCal feeds and add them to
config.CITY_ICAL_FEEDS (they use the same .ics format).
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import List, Optional

import requests

import config
from sources.base import Event, clean

_SERVER_DATA_RE = re.compile(
    r"window\.__SERVER_DATA__\s*=\s*(\{.*?\});", re.DOTALL
)


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _events_from_blob(blob: dict) -> List[dict]:
    """Walk the embedded JSON looking for the search results list."""
    try:
        return blob["search_data"]["events"]["results"] or []
    except (KeyError, TypeError):
        pass
    # Fallback: scan for any list of dicts that look like events.
    found: List[dict] = []

    def walk(node):
        if isinstance(node, dict):
            if "name" in node and ("start_date" in node or "start" in node):
                found.append(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(blob)
    return found


def _one_url(url: str) -> List[Event]:
    resp = requests.get(
        url,
        headers={"User-Agent": config.USER_AGENT, "Accept": "text/html"},
        timeout=config.REQUEST_TIMEOUT,
    )
    if resp.status_code != 200:
        print(f"[eventbrite] {url} -> HTTP {resp.status_code} (likely bot wall)")
        return []

    m = _SERVER_DATA_RE.search(resp.text)
    if not m:
        print(f"[eventbrite] no embedded data found at {url}")
        return []
    try:
        blob = json.loads(m.group(1))
    except json.JSONDecodeError:
        print(f"[eventbrite] could not parse embedded JSON at {url}")
        return []

    out: List[Event] = []
    for raw in _events_from_blob(blob):
        name = raw.get("name")
        if isinstance(name, dict):
            name = name.get("text")
        name = clean(str(name or ""))
        if not name:
            continue

        start = raw.get("start_date") or (raw.get("start") or {}).get("local") \
            or (raw.get("start") or {}).get("utc")
        start_dt = _parse_dt(start) if isinstance(start, str) else None
        if start_dt is None:
            continue

        ev = Event(
            title=name,
            start=start_dt,
            source="eventbrite",
            url=raw.get("url") or raw.get("vanity_url") or "",
            description=clean(str((raw.get("summary") or raw.get("description") or ""))),
        )

        venue = raw.get("primary_venue") or raw.get("venue") or {}
        addr = (venue.get("address") or {}) if isinstance(venue, dict) else {}
        ev.location = clean(
            ", ".join(
                str(addr.get(k, ""))
                for k in ("localized_address_display", "city", "region", "postal_code")
                if addr.get(k)
            )
        )
        ev.zip_code = str(addr.get("postal_code")) if addr.get("postal_code") else None
        for latk, lonk in (("latitude", "longitude"),):
            try:
                ev.lat = float(addr.get(latk)) if addr.get(latk) else ev.lat
                ev.lon = float(addr.get(lonk)) if addr.get(lonk) else ev.lon
            except (TypeError, ValueError):
                pass

        # Price: Eventbrite marks free events and/or gives a min ticket price.
        if raw.get("is_free") is True:
            ev.price, ev.is_free = 0.0, True
        else:
            ta = raw.get("ticket_availability") or {}
            minp = (ta.get("minimum_ticket_price") or {}).get("major_value")
            if minp is not None:
                try:
                    ev.price = float(minp)
                    ev.is_free = ev.price == 0.0
                except (TypeError, ValueError):
                    pass
        out.append(ev)
    return out


def fetch() -> List[Event]:
    seen = {}
    for url in config.EVENTBRITE_URLS:
        try:
            for ev in _one_url(url):
                seen[ev.uid] = ev
        except Exception as exc:
            print(f"[eventbrite] failed: {url} -> {exc}")
    out = list(seen.values())
    print(f"[eventbrite] collected {len(out)} raw events")
    return out
