"""
Central configuration for the Round Rock local-events tracker.

Nothing secret lives here. Credentials (SMTP login, recipient) are read from
environment variables / GitHub Actions secrets in notify.py.
"""

# ---------------------------------------------------------------------------
# Where you are / how far you'll travel
# ---------------------------------------------------------------------------
HOME_ZIP = "78665"          # your zip code
RADIUS_MILES = 20.0         # only keep events within this many miles
# Fallback centroid for 78665 if offline zip lookup fails (lat, lon).
HOME_LATLON_FALLBACK = (30.5599, -97.6189)

# ---------------------------------------------------------------------------
# Price rules
# ---------------------------------------------------------------------------
MAX_PRICE = 100.0           # keep free events + anything strictly under this
INCLUDE_UNKNOWN_PRICE = True  # keep events whose price we cannot determine

# ---------------------------------------------------------------------------
# How far ahead to look
# ---------------------------------------------------------------------------
LOOKAHEAD_DAYS = 21         # ignore events further out than this

# ---------------------------------------------------------------------------
# What counts as a "cultural" event you care about.
# An event is kept if it matches ANY keyword group below (in its title,
# description, or source category tags) AND is not a pure admin/government item.
# ---------------------------------------------------------------------------
INTEREST_KEYWORDS = {
    "music": [
        "music", "concert", "band", "live music", "dj", "symphony",
        "orchestra", "choir", "jazz", "blues", "acoustic", "open mic",
    ],
    "art": [
        "art", "gallery", "exhibit", "mural", "painting", "sculpture",
        "craft", "pottery", "ceramics", "drawing", "creates",
    ],
    "shopping": [
        "market", "vendor", "bazaar", "pop-up", "popup", "boutique",
        "makers", "handmade", "artisan", "shop local",
    ],
    "kids_toddler": [
        "kid", "kids", "child", "children", "toddler", "family",
        "story time", "storytime", "baby", "youth", "all ages",
        "family-friendly", "family friendly",
    ],
    "festivals": [
        "festival", "fest", "fair", "celebration", "parade", "fiesta",
        "carnival",
    ],
    "markets": [
        "farmers market", "farmers' market", "night market", "mainly art",
        "flea market", "craft fair",
    ],
}

# Events whose ONLY signal is one of these are dropped (government / admin).
EXCLUDE_KEYWORDS = [
    "commission meeting", "city council", "planning and zoning", "p&z",
    "work session", "public hearing", "board meeting", "agenda",
    "budget workshop", "canceled", "cancelled",
]

# Source category tags (from the city iCal CATEGORIES field) that are always
# considered cultural even if no keyword matched.
ALWAYS_KEEP_CATEGORIES = [
    "arts and culture", "music", "city events", "festival", "library",
    "parks and recreation",
]

# ---------------------------------------------------------------------------
# City of Round Rock iCal feeds (The Events Calendar / Tribe plugin).
# These are stable public .ics feeds - the most reliable source.
# ---------------------------------------------------------------------------
CITY_ICAL_FEEDS = [
    # Arts & Culture category feed
    "https://www.roundrocktexas.gov/?post_type=tribe_events&ical=1&eventDisplay=list&tribe_events_cat=arts",
    # General upcoming events feed (filtered later by keyword/category)
    "https://www.roundrocktexas.gov/events/list/?ical=1",
]

# ---------------------------------------------------------------------------
# Eventbrite discovery pages (best-effort HTML scrape - see sources/eventbrite.py).
# ---------------------------------------------------------------------------
EVENTBRITE_URLS = [
    "https://www.eventbrite.com/d/tx--round-rock/free--events--today/",
    "https://www.eventbrite.com/d/tx--round-rock/events--this-week/",
]

# ---------------------------------------------------------------------------
# Facebook page. NOTE: Facebook does not allow unauthenticated scraping and
# blocks server IPs. This source is OFF by default and ships as a documented
# stub (see sources/facebook.py and the README).
# ---------------------------------------------------------------------------
FACEBOOK_PAGE_URL = "https://www.facebook.com/RoundtheRockTX/"
ENABLE_FACEBOOK = False

# ---------------------------------------------------------------------------
# State file: tracks events already emailed so you don't get duplicates.
# Committed back to the repo by the GitHub Action.
# ---------------------------------------------------------------------------
SEEN_FILE = "seen.json"

# Only send an email when there is at least one NEW matching event.
NOTIFY_ONLY_ON_NEW = True

# A polite User-Agent for outbound requests.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
REQUEST_TIMEOUT = 25
