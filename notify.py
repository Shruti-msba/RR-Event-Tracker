"""
Email sender. Builds an HTML digest and sends it over SMTP.

Credentials come from environment variables (set as GitHub Actions secrets):
  SMTP_HOST   e.g. smtp.gmail.com
  SMTP_PORT   e.g. 587
  SMTP_USER   the sending account, e.g. you@gmail.com
  SMTP_PASS   an app password (NOT your normal password)
  EMAIL_TO    where the digest goes (defaults to SMTP_USER)
  EMAIL_FROM  optional friendly from (defaults to SMTP_USER)

This script never stores or prints credentials.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from typing import List

from sources.base import Event

# Note: user-facing message text uses "-" rather than the em dash on purpose.

_INTEREST_LABELS = {
    "music": "Music",
    "art": "Art",
    "shopping": "Shopping",
    "kids_toddler": "Kids / Toddler",
    "festivals": "Festivals",
    "markets": "Markets",
}


def _badge(interest: str) -> str:
    label = _INTEREST_LABELS.get(interest, interest.title())
    return (
        f'<span style="display:inline-block;background:#eef3ff;color:#2347a6;'
        f'border-radius:10px;padding:2px 8px;font-size:11px;margin:0 4px 4px 0;">'
        f"{escape(label)}</span>"
    )


def _price_text(ev: Event) -> str:
    if ev.is_free or ev.price == 0.0:
        return "Free"
    if ev.price is None:
        return "Price not listed"
    return f"From ${ev.price:.0f}"


def _distance_text(ev: Event) -> str:
    if ev.distance_mi is None:
        return "distance unknown"
    return f"{ev.distance_mi:g} mi away"


def _event_card(ev: Event, is_new: bool) -> str:
    when = ev.start.strftime("%a %b %-d, %-I:%M %p") if ev.start else "TBD"
    title = escape(ev.title)
    if ev.url:
        title = f'<a href="{escape(ev.url)}" style="color:#1a1a1a;text-decoration:none;">{title}</a>'
    new_tag = (
        '<span style="background:#1f9d55;color:#fff;border-radius:8px;'
        'padding:1px 7px;font-size:10px;margin-left:6px;">NEW</span>'
        if is_new
        else ""
    )
    badges = "".join(_badge(i) for i in ev.matched_interests)
    desc = escape((ev.description or "")[:180])
    if ev.description and len(ev.description) > 180:
        desc += "..."

    return f"""
    <div style="border:1px solid #e6e6e6;border-radius:10px;padding:14px 16px;margin:10px 0;">
      <div style="font-size:16px;font-weight:600;">{title}{new_tag}</div>
      <div style="color:#555;font-size:13px;margin:4px 0;">
        {escape(when)} &nbsp;•&nbsp; {_price_text(ev)} &nbsp;•&nbsp; {_distance_text(ev)}
      </div>
      <div style="color:#777;font-size:12px;margin-bottom:6px;">{escape(ev.location or "")}</div>
      <div style="margin:6px 0;">{badges}</div>
      <div style="color:#444;font-size:13px;">{desc}</div>
      <div style="font-size:11px;color:#999;margin-top:6px;">source: {escape(ev.source)}</div>
    </div>
    """


def build_html(events: List[Event], new_uids: set) -> str:
    today = datetime.now().strftime("%A, %B %-d")
    cards = "".join(_event_card(ev, ev.uid in new_uids) for ev in events)
    new_count = sum(1 for ev in events if ev.uid in new_uids)
    return f"""
    <div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:640px;margin:0 auto;">
      <h2 style="margin-bottom:2px;">Local events near 78665</h2>
      <div style="color:#666;font-size:13px;margin-bottom:14px;">
        {today} &nbsp;•&nbsp; {len(events)} upcoming &nbsp;•&nbsp; {new_count} new since last check
      </div>
      {cards}
      <div style="color:#aaa;font-size:11px;margin-top:18px;">
        Free + under-$100 cultural events within 20 miles. Sent by your GitHub Actions tracker.
      </div>
    </div>
    """


def send(events: List[Event], new_uids: set) -> None:
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    to_addr = os.environ.get("EMAIL_TO", user)
    from_addr = os.environ.get("EMAIL_FROM", user)

    if not user or not password:
        raise RuntimeError("SMTP_USER and SMTP_PASS must be set as secrets")

    new_count = len(new_uids)
    subject = f"{new_count} new local event(s) near you" if new_count else \
        f"{len(events)} upcoming local events near you"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(build_html(events, new_uids), "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls(context=context)
        server.login(user, password)
        server.sendmail(from_addr, [a.strip() for a in to_addr.split(",")], msg.as_string())
    print(f"[notify] sent digest to {to_addr} ({new_count} new)")
