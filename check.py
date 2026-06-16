"""
Entry point. Run by GitHub Actions on a schedule (or locally / on demand).

Flow:
  1. fetch raw events from every enabled source
  2. filter by date window, distance, price, and interest
  3. compare against seen.json to find what's NEW
  4. email a digest (only if there's something new, by default)
  5. update seen.json so the Action can commit it

Usage:
  python check.py            # normal run
  python check.py --dry-run  # fetch + filter + print, no email, no state write
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Dict, List

import config
import notify
from filters import apply_filters
from sources import ALL_SOURCES
from sources.base import Event


def load_seen() -> Dict[str, str]:
    if not os.path.exists(config.SEEN_FILE):
        return {}
    try:
        with open(config.SEEN_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}


def save_seen(seen: Dict[str, str]) -> None:
    with open(config.SEEN_FILE, "w", encoding="utf-8") as fh:
        json.dump(seen, fh, indent=2, sort_keys=True)


def collect() -> List[Event]:
    raw: List[Event] = []
    for src in ALL_SOURCES:
        try:
            raw.extend(src.fetch())
        except Exception as exc:
            print(f"[collect] source {src.__name__} failed: {exc}")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="print results, send no email, write no state")
    args = parser.parse_args()

    events = apply_filters(collect())

    seen = load_seen()
    new_uids = {ev.uid for ev in events if ev.uid not in seen}

    print(f"[main] {len(events)} matching events, {len(new_uids)} new")
    for ev in events:
        flag = "NEW " if ev.uid in new_uids else "    "
        when = ev.start.strftime("%Y-%m-%d %H:%M") if ev.start else "?"
        print(f"  {flag}{when}  {ev.title}  ({ev.source})")

    if args.dry_run:
        print("[main] dry run - no email, no state change")
        return 0

    if not events:
        print("[main] nothing matched; not sending")
        return 0

    if config.NOTIFY_ONLY_ON_NEW and not new_uids:
        print("[main] no new events since last run; not sending")
        return 0

    notify.send(events, new_uids)

    # Record everything we just surfaced so we don't repeat it next time.
    now = datetime.now(timezone.utc).isoformat()
    for ev in events:
        seen.setdefault(ev.uid, now)
    save_seen(seen)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
