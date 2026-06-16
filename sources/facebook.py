"""
Facebook source - DISABLED by default.

Why this is a stub, not a scraper:

  * Facebook does not permit unauthenticated scraping of Pages, and it
    actively blocks requests from datacenter IPs like GitHub Actions runners.
    A scraper here would return a login wall, not events.
  * Automated scraping of Facebook violates its Terms of Service.

So this source intentionally returns nothing. Realistic ways to actually get
Round the Rock events into your tracker instead:

  1. Many community organizers cross-post to Eventbrite or have their own
     website with an iCal feed - add those feeds to config.CITY_ICAL_FEEDS.
  2. If "Round the Rock" publishes a public calendar (Google Calendar / ICS),
     add that .ics URL to config.CITY_ICAL_FEEDS - it will work immediately.
  3. Facebook's official Graph API can read a Page you manage or have a token
     for; wiring that up (with your own app + token in a secret) is the only
     ToS-compliant automated route, and is left as an optional extension.

To turn this on after wiring up a compliant method, set
config.ENABLE_FACEBOOK = True and implement fetch() below.
"""

from __future__ import annotations

from typing import List

import config
from sources.base import Event


def fetch() -> List[Event]:
    if not config.ENABLE_FACEBOOK:
        print("[facebook] disabled (see sources/facebook.py for why)")
        return []
    print("[facebook] enabled but no compliant fetch method implemented")
    return []
