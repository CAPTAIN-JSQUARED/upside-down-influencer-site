#!/usr/bin/env python3
"""
Static site builder for the Upside Down Influencer website.

Renders templates/*.html (Jinja2) using data/episodes.json into dist/,
and copies static/ alongside it. Run this after scripts/fetch_episodes.py
to pick up the latest YouTube episodes.

Usage:
    python3 build.py
"""
import json
import shutil
import re
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
DATA_PATH = ROOT / "data" / "episodes.json"
DIST_DIR = ROOT / "dist"

PAGES = ["index.html", "episodes.html", "about.html", "resources.html", "contact.html"]


def load_episodes():
    if not DATA_PATH.exists():
        return []
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    for ep in raw:
        # Human-friendly date for display
        try:
            dt = datetime.fromisoformat(ep["published_at"].replace("Z", "+00:00"))
            ep["published_display"] = dt.strftime("%B %-d, %Y")
        except Exception:
            ep["published_display"] = ""

        # Short description (first ~160 chars, cut at a word boundary)
        desc = re.sub(r"\s+", " ", ep.get("description", "")).strip()
        if len(desc) > 160:
            desc = desc[:160].rsplit(" ", 1)[0] + "…"
        ep["description_short"] = desc
    return raw


def build():
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    episodes = load_episodes()

    for page in PAGES:
        template = env.get_template(page)
        html = template.render(episodes=episodes)
        (DIST_DIR / page).write_text(html, encoding="utf-8")
        print(f"built {page}")

    # Also write index at root is already index.html; add a copy strategy
    shutil.copytree(STATIC_DIR, DIST_DIR / "static")

    # Custom domain for GitHub Pages: if a CNAME file exists at the repo
    # root, carry it into dist/ so Pages keeps the domain on every deploy.
    cname_src = ROOT / "CNAME"
    if cname_src.exists():
        shutil.copy(cname_src, DIST_DIR / "CNAME")
        print(f"included CNAME -> {cname_src.read_text().strip()}")

    print(f"\nDone. {len(episodes)} episode(s) in data/episodes.json.")
    print(f"Output: {DIST_DIR}")


if __name__ == "__main__":
    build()
