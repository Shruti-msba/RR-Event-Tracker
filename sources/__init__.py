"""Event sources. Each module exposes a fetch() -> List[Event]."""

from sources import roundrock_city, eventbrite, facebook

ALL_SOURCES = [roundrock_city, eventbrite, facebook]
