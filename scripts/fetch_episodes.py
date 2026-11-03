#!/usr/bin/env python3
"""
Pull every video from the Upside Down Influencer YouTube channel and write it
to data/episodes.json so the site can be rebuilt with zero manual work.

Source of truth: YouTube Data API v3 (playlistItems on the channel's "uploads"
playlist). This needs a free API key — see README.md for how to get one.

Usage:
    YOUTUBE_API_KEY=xxxxx python3 scripts/fetch_episodes.py

Env vars:
    YOUTUBE_API_KEY   required. A YouTube Data API v3 key.
    CHANNEL_ID        optional. Defaults to the Upside Down Influencer channel.
"""
import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

API_BASE = "https://www.googleapis.com/youtube/v3"

# @upsidedowninfluencer
DEFAULT_CHANNEL_ID = "UCNNGiyZj4zeSSzVqwlv6PHQ"

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "episodes.json"


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


def main():
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    channel_id = os.environ.get("CHANNEL_ID", DEFAULT_CHANNEL_ID).strip()

    if not api_key:
        print(
            "No YOUTUBE_API_KEY set — leaving data/episodes.json untouched.\n"
            "See README.md for how to get a free key.",
            file=sys.stderr,
        )
        # Don't fail the build if the key isn't configured yet; the site
        # will just keep showing whatever episodes.json already has
        # (e.g. the sample data) until a key is added.
        sys.exit(0)

    episodes = fetch_all_episodes(api_key, channel_id)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(episodes, indent=2), encoding="utf-8")
    print(f"Wrote {len(episodes)} episodes to {OUT_PATH}")


if __name__ == "__main__":
    main()
