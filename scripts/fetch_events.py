#!/usr/bin/env python3
"""
Pull every live upcoming event from Eventbrite and write it to
data/events.json so the Events page updates itself with zero manual work
on the website side. Jessica manages events entirely in Eventbrite
(create, edit, cancel, see who's signed up). This script just mirrors
whatever's live there onto the website.

Source of truth: Eventbrite API v3 (an organization's events, expanded
with venue + description). Needs a free Eventbrite account + personal
token. See README.md for how to get one.

Usage:
    EVENTBRITE_TOKEN=xxxx EVENTBRITE_ORG_ID=xxxx python3 scripts/fetch_events.py
"""
import json
import os
import re
import sys
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

API_BASE = "https://www.eventbriteapi.com/v3"

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "events.json"


def api_get(path: str, token: str, params: dict | None = None) -> dict:
    params = params or {}
    url = f"{API_BASE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"Eventbrite API error {e.code} on {path}: {body}", file=sys.stderr)
        raise


def slugify(text: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or fallback


def human_date_range(start_iso: str, end_iso: str, timezone: str) -> str:
    try:
        from datetime import datetime
        start = datetime.fromisoformat(start_iso)
        end = datetime.fromisoformat(end_iso)
        same_day = start.date() == end.date()
        start_str = start.strftime("%B %-d, %Y · %-I:%M %p")
        if same_day:
            end_str = end.strftime("%-I:%M %p")
        else:
            end_str = end.strftime("%B %-d, %Y · %-I:%M %p")
        return f"{start_str} – {end_str} ({timezone})"
    except Exception:
        return start_iso


def fetch_events(token: str, org_id: str) -> list:
    events = []
    continuation = None

    while True:
        params = {
            "status": "live",
            "order_by": "start_asc",
            "expand": "venue,description",
        }
        if continuation:
            params["continuation"] = continuation

        data = api_get(f"/organizations/{org_id}/events/", token, params)

        for ev in data.get("events", []):
            ev_id = ev["id"]
            name = ev.get("name", {}).get("text", "").strip()
            summary = ev.get("summary", "") or ev.get("description", {}).get("text", "") or ""
            description_html = ""
            # Full HTML description needs its own call
            try:
                desc_data = api_get(f"/events/{ev_id}/description/", token)
                description_html = desc_data.get("description", "") or ""
            except Exception:
                description_html = f"<p>{summary}</p>"

            venue = ev.get("venue") or {}
            is_online = bool(ev.get("online_event"))
            if is_online:
                location_label = "Online"
                address = ""
            elif venue:
                city = (venue.get("address") or {}).get("city", "")
                region = (venue.get("address") or {}).get("region", "")
                location_label = ", ".join(p for p in (city, region) if p) or "In person"
                addr = venue.get("address") or {}
                address = ", ".join(
                    p for p in (
                        addr.get("address_1"),
                        addr.get("city"),
                        addr.get("region"),
                        addr.get("postal_code"),
                    ) if p
                )
            else:
                location_label = "In person"
                address = ""

            start = ev.get("start", {})
            end = ev.get("end", {})
            logo = ev.get("logo") or {}

            events.append({
                "id": ev_id,
                "slug": slugify(name, ev_id),
                "title": name,
                "summary": summary.strip(),
                "description_html": description_html,
                "is_online": is_online,
                "location_label": location_label,
                "address": address,
                "start_iso": start.get("utc", ""),
                "end_iso": end.get("utc", ""),
                "date_display": human_date_range(
                    start.get("local", ""), end.get("local", ""),
                    start.get("timezone", "")
                ),
                "image": logo.get("original", {}).get("url") or logo.get("url", ""),
                "eventbrite_url": ev.get("url", ""),
                "capacity_status": ev.get("status", ""),
            })

        pagination = data.get("pagination", {})
        if pagination.get("has_more_items"):
            continuation = pagination.get("continuation")
        else:
            break

    events.sort(key=lambda e: e["start_iso"])
    return events


def main():
    token = os.environ.get("EVENTBRITE_TOKEN", "").strip()
    org_id = os.environ.get("EVENTBRITE_ORG_ID", "").strip()

    if not token or not org_id:
        print(
            "No EVENTBRITE_TOKEN / EVENTBRITE_ORG_ID set. Leaving "
            "data/events.json untouched. See README.md for how to get these.",
            file=sys.stderr,
        )
        sys.exit(0)

    try:
        events = fetch_events(token, org_id)
    except Exception as exc:
        # Don't let a bad Eventbrite credential or a transient API problem
        # take down the whole site build. Episodes should still sync and
        # the site should still deploy; events.json just stays as it was
        # until this is fixed. The error above (printed by api_get) still
        # shows up in the Actions log so it's easy to spot and fix.
        print(
            f"Eventbrite sync failed ({exc}). Leaving data/events.json "
            "untouched and continuing.",
            file=sys.stderr,
        )
        sys.exit(0)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(events, indent=2), encoding="utf-8")
    print(f"Wrote {len(events)} event(s) to {OUT_PATH}")


if __name__ == "__main__":
    main()
