#!/usr/bin/env python3
"""
Pull every full-length video from the Upside Down Influencer YouTube channel
and write it to data/episodes.json so the site can be rebuilt with zero
manual work. YouTube Shorts and other short clips are filtered out by
duration, so only real episodes show up on the site.

Source of truth: YouTube Data API v3 (playlistItems on the channel's "uploads"
playlist, then videos.list for each video's duration). This needs a free API
key. See README.md for how to get one.

Usage:
    YOUTUBE_API_KEY=xxxxx python3 scripts/fetch_episodes.py

Env vars:
    YOUTUBE_API_KEY          required. A YouTube Data API v3 key.
    CHANNEL_ID                optional. Defaults to the Upside Down Influencer channel.
    EPISODE_MIN_DURATION_SECONDS
                               optional. Videos shorter than this are treated
                               as Shorts/clips and excluded. Defaults to 180
                               (3 minutes, YouTube's current max Shorts
                               length, so this safely excludes every Short
                               without risking cutting off a real episode).
"""
import json
import os
import re
import sys
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

API_BASE = "https://www.googleapis.com/youtube/v3"

# @upsidedowninfluencer
DEFAULT_CHANNEL_ID = "UCNNGiyZj4zeSSzVqwlv6PHQ"

# YouTube Shorts can be up to 3 minutes (180s) as of the current Shorts spec.
# Anything shorter than this is a Short or a repurposed clip, not an episode.
DEFAULT_MIN_DURATION_SECONDS = 180

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "episodes.json"

ISO8601_DURATION_RE = re.compile(
    r"P(?:(?P<days>\d+)D)?"
    r"T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?"
)


def parse_duration_seconds(iso_duration: str) -> int:
    """Parse an ISO 8601 duration like 'PT15M33S' into whole seconds."""
    match = ISO8601_DURATION_RE.match(iso_duration or "")
    if not match:
        return 0
    parts = match.groupdict()
    days = int(parts["days"] or 0)
    hours = int(parts["hours"] or 0)
    minutes = int(parts["minutes"] or 0)
    seconds = int(parts["seconds"] or 0)
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def uploads_playlist_id(channel_id: str) -> str:
    """The 'uploads' playlist for any channel is its ID with UC -> UU."""
    if channel_id.startswith("UC"):
        return "UU" + channel_id[2:]
    return channel_id


def api_get(path: str, params: dict) -> dict:
    url = f"{API_BASE}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"YouTube API error {e.code} on {path}: {body}", file=sys.stderr)
        raise


def best_thumbnail(thumbnails: dict) -> str:
    for size in ("maxres", "standard", "high", "medium", "default"):
        if size in thumbnails:
            return thumbnails[size]["url"]
    return ""


def fetch_all_episodes(api_key: str, channel_id: str) -> list:
    playlist_id = uploads_playlist_id(channel_id)
    episodes = []
    page_token = None

    while True:
        params = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": 50,
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        data = api_get("playlistItems", params)

        for item in data.get("items", []):
            snippet = item["snippet"]
            video_id = item["contentDetails"]["videoId"]
            # Skip private/deleted videos (YouTube returns a placeholder title)
            if snippet.get("title") in ("Private video", "Deleted video"):
                continue
            episodes.append({
                "video_id": video_id,
                "title": snippet.get("title", "").strip(),
                "description": snippet.get("description", "").strip(),
                "published_at": snippet.get("publishedAt", ""),
                "thumbnail": best_thumbnail(snippet.get("thumbnails", {})),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "embed_url": f"https://www.youtube.com/embed/{video_id}",
            })

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    # Newest first
    episodes.sort(key=lambda e: e["published_at"], reverse=True)
    return episodes


def attach_durations(api_key: str, episodes: list) -> None:
    """Fetch each video's duration via videos.list and set ep['duration_seconds']."""
    for batch in chunked(episodes, 50):
        ids = ",".join(ep["video_id"] for ep in batch)
        data = api_get("videos", {
            "part": "contentDetails",
            "id": ids,
            "key": api_key,
        })
        durations = {
            item["id"]: parse_duration_seconds(item["contentDetails"]["duration"])
            for item in data.get("items", [])
        }
        for ep in batch:
            ep["duration_seconds"] = durations.get(ep["video_id"], 0)


def filter_out_shorts(episodes: list, min_duration_seconds: int) -> list:
    kept = []
    for ep in episodes:
        if ep.get("duration_seconds", 0) < min_duration_seconds:
            print(
                f"Skipping short/clip ({ep['duration_seconds']}s): {ep['title']}",
                file=sys.stderr,
            )
            continue
        kept.append(ep)
    return kept


def main():
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    channel_id = os.environ.get("CHANNEL_ID", DEFAULT_CHANNEL_ID).strip()
    min_duration = int(os.environ.get(
        "EPISODE_MIN_DURATION_SECONDS", DEFAULT_MIN_DURATION_SECONDS
    ))

    if not api_key:
        print(
            "No YOUTUBE_API_KEY set. Leaving data/episodes.json untouched.\n"
            "See README.md for how to get a free key.",
            file=sys.stderr,
        )
        # Don't fail the build if the key isn't configured yet; the site
        # will just keep showing whatever episodes.json already has
        # (e.g. the sample data) until a key is added.
        sys.exit(0)

    episodes = fetch_all_episodes(api_key, channel_id)
    attach_durations(api_key, episodes)
    episodes = filter_out_shorts(episodes, min_duration)

    # duration_seconds was only needed for filtering, drop it from the
    # public data file to keep it tidy (not used by the templates).
    for ep in episodes:
        ep.pop("duration_seconds", None)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(episodes, indent=2), encoding="utf-8")
    print(f"Wrote {len(episodes)} episodes to {OUT_PATH}")


if __name__ == "__main__":
    main()
