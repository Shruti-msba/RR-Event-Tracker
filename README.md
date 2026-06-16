# Local Events Tracker - Round Rock (78665)

A small, self-hosted tracker that emails you upcoming **free / under-$100 cultural
events** (music, art, shopping, toddler & family events, festivals, markets) happening
**within 20 miles of zip 78665**. It runs entirely on **GitHub Actions** on a daily
schedule - no server to maintain, no cost.

It checks three sources, filters by distance / price / interest, remembers what it has
already shown you, and emails a digest only when something **new** turns up.

```
fetch sources  ->  filter (date / distance / price / interest)  ->  diff vs seen.json  ->  email digest  ->  save state
```

---

## Sources & honest expectations

| Source | How it's read | Reliability |
|--------|---------------|-------------|
| **City of Round Rock** arts & events | Official public **iCal feeds** | Solid. This is the backbone. |
| **Eventbrite** (Round Rock, free/low-cost) | Best-effort scrape of embedded page data | Fragile. May be bot-blocked from CI or break if the page changes. Failures are non-fatal. |
| **Facebook** (Round the Rock) | **Disabled** - documented stub | Not possible to scrape unauthenticated; against Facebook's terms. See below. |

**About the Facebook source:** Facebook blocks unauthenticated access to Page content
and prohibits scraping, so a scraper would just hit a login wall. It ships off by default.
The reliable way to capture those events is to find the organizer's own calendar feed: if
"Round the Rock" (or any organizer you like) publishes a Google Calendar / `.ics` link, or
cross-posts to Eventbrite, add that feed to `CITY_ICAL_FEEDS` in `config.py` and it will be
picked up immediately using the same robust path as the city feed.

---

## One-time setup

### 1. Put this on your own GitHub account
Create a new repository (Private is fine) and upload these files, **or** fork/import this
project. The code must live in *your* account so the Action runs under your control.

### 2. Create a sending email + app password
Use a Gmail account (or any SMTP provider).

- Gmail: turn on 2-Step Verification, then create an **App Password**
  (Google Account -> Security -> App passwords). Use that 16-character password below,
  **not** your normal Gmail password.

### 3. Add repository secrets
In your repo: **Settings -> Secrets and variables -> Actions -> New repository secret.**
Add each of these:

| Secret | Example | Notes |
|--------|---------|-------|
| `SMTP_HOST` | `smtp.gmail.com` | |
| `SMTP_PORT` | `587` | |
| `SMTP_USER` | `you@gmail.com` | the sending account |
| `SMTP_PASS` | `your-16-char-app-password` | app password, kept secret |
| `EMAIL_TO`  | `you@gmail.com` | where digests go (comma-separate for several) |
| `EMAIL_FROM`| `Events Bot <you@gmail.com>` | optional |

The code only ever **reads** these from the environment. Nothing is written to the repo.

### 4. Enable Actions
Open the **Actions** tab and enable workflows if prompted. The schedule starts automatically;
you can also click **Run workflow** on the `local-events-tracker` workflow to test it now.

That's it. You'll get an email whenever new matching events appear.

---

## Customizing

Everything tweakable lives in `config.py`:

- `HOME_ZIP` / `RADIUS_MILES` - where you are and how far you'll travel.
- `MAX_PRICE` - the price ceiling (free always passes).
- `LOOKAHEAD_DAYS` - how far ahead to look.
- `INTEREST_KEYWORDS` - the categories you care about and the words that match them.
- `EXCLUDE_KEYWORDS` - things to drop (government meetings, canceled items, etc.).
- `CITY_ICAL_FEEDS` - **add any other `.ics` feed here** (libraries, other cities, organizer
  calendars). This is the easiest way to grow your coverage.
- `NOTIFY_ONLY_ON_NEW` - set `False` to get the full digest every run instead of only-when-new.

Change the schedule in `.github/workflows/check.yml` (the `cron` line - it's in **UTC**;
`0 13 * * *` is about 8 AM Central).

---

## Running locally

```bash
pip install -r requirements.txt

# see what it would send, without emailing or changing state:
python check.py --dry-run

# a real run (needs the SMTP_* environment variables set):
SMTP_USER=you@gmail.com SMTP_PASS=app-password EMAIL_TO=you@gmail.com python check.py
```

---

## How "no duplicates" works
`seen.json` stores the id of every event already emailed. Each run diffs the current matches
against it; only unseen events are flagged **NEW**, and the file is committed back to the repo
by the Action so the memory persists between runs. Delete `seen.json` (or reset it to `{}`) to
start fresh.

---

## Project layout

```
.
├── check.py                  # entry point: fetch -> filter -> diff -> email -> save
├── config.py                 # all your settings (zip, radius, price, feeds, keywords)
├── filters.py                # distance / price / interest / date filtering
├── notify.py                 # builds + sends the HTML email digest
├── requirements.txt
├── seen.json                 # state (events already emailed); committed by the Action
├── sources/
│   ├── base.py               # Event model + text/price helpers
│   ├── roundrock_city.py     # city iCal feeds (primary source)
│   ├── eventbrite.py         # best-effort Eventbrite scrape
│   └── facebook.py           # disabled stub (see notes above)
└── .github/workflows/check.yml
```

## A note on scraping
The city iCal feeds are public and meant to be subscribed to. Eventbrite and Facebook are
included on a best-effort / disabled basis respectively; if you rely on them heavily, prefer
official feeds or APIs and review each site's terms of use.
