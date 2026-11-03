# The Upside Down Influencer — website

A simple, fast website for the podcast. The big thing it does differently from
the old site: the **Episodes** page and the homepage's "Latest episodes"
section update themselves automatically, straight from Jessica's YouTube
channel (@upsidedowninfluencer). Nobody has to log in anywhere and manually
add a new episode — ever.

## How it works

- `scripts/fetch_episodes.py` asks YouTube for every video on the channel
  (title, description, thumbnail, publish date) and saves it to
  `data/episodes.json`.
- `build.py` turns the templates in `templates/` plus `data/episodes.json`
  into plain HTML files in `dist/` — that `dist/` folder is the entire
  website, ready to host anywhere.
- `.github/workflows/deploy.yml` runs both of those automatically every
  2 hours (and whenever you push a change), then publishes `dist/` to GitHub
  Pages. That's the "zero manual work" part — new YouTube uploads show up on
  the site within a couple hours with nobody touching anything.

Clicking an episode thumbnail opens that video in an embedded YouTube player
right on the page (a lightbox), so visitors can watch without leaving the site.

## One-time setup (about 20 minutes)

### 1. Get a free YouTube Data API key

1. Go to https://console.cloud.google.com/ and sign in with the Google
   account tied to the YouTube channel (or any Google account — it doesn't
   need to own the channel, the channel's videos are public).
2. Create a new project (top dropdown → "New Project"), any name is fine.
3. In the search bar, search for **"YouTube Data API v3"** and click **Enable**.
4. Go to **APIs & Services → Credentials → Create Credentials → API key**.
5. Copy the key. (Optional but recommended: click "Restrict key" and limit it
   to the YouTube Data API v3, so it can't be used for anything else.)

This is free — the quota is 10,000 units/day, and checking for new episodes
every 2 hours uses only a handful of units.

### 2. Put the code on GitHub

1. Create a free GitHub account if you don't have one: https://github.com/signup
2. Create a new repository (e.g. `upside-down-influencer-site`) — Public or
   Private both work with GitHub Pages.
3. Upload everything in this folder to that repository (drag-and-drop on
   github.com works fine for a one-time upload, or use `git push` if you're
   comfortable with git).

### 3. Add the YouTube API key as a secret

1. In the repo, go to **Settings → Secrets and variables → Actions**.
2. Click **New repository secret**.
3. Name: `YOUTUBE_API_KEY`. Value: the key from step 1. Save.

### 4. Turn on GitHub Pages

1. In the repo, go to **Settings → Pages**.
2. Under "Build and deployment", set **Source** to **GitHub Actions**.
3. Go to the **Actions** tab and run the "Sync episodes & deploy" workflow
   once manually (there's a "Run workflow" button) to kick things off.
4. After it finishes (1–2 minutes), your site is live at
   `https://<your-github-username>.github.io/<repo-name>/`.

### 5. Point your existing domain at it

The `CNAME` file in this repo already contains `upsidedowninfluencer.com`.
To make that domain actually point here:

1. In the repo, **Settings → Pages → Custom domain**, enter
   `upsidedowninfluencer.com` (should already show up from the CNAME file —
   just confirm it) and save.
2. At your domain registrar (wherever `upsidedowninfluencer.com` is managed —
   check your Squarespace account or wherever you bought the domain), add
   these DNS records:
   - An `A` record for the root domain pointing to GitHub Pages' IPs:
     `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - A `CNAME` record for `www` pointing to `<your-github-username>.github.io`
3. DNS changes can take a few minutes to a day to fully propagate. GitHub
   will show a green checkmark on the Pages settings page once it's verified
   and auto-issues HTTPS for you.

**Until you do this step**, the site works fine at its `github.io` address —
there's no rush, and nothing breaks on the old site until you're ready to
switch the DNS over.

## Updating content that isn't episodes

Everything else (About page copy, Resources cards, nav links, colors, fonts)
is plain HTML/CSS in `templates/` and `static/css/style.css` — edit the text,
commit, push, and the next workflow run (or your manual push) rebuilds and
redeploys automatically. No build tools or frameworks to install beyond
Python + the one `jinja2` package.

- **Colors/fonts**: all defined as CSS variables at the top of
  `static/css/style.css` (`--ink`, `--cream`, `--amber`, `--font-display`,
  `--font-body`). Change those and the whole site re-skins.
- **Nav / footer links**: in `templates/base.html`.
- **Newsletter signup form**: in `templates/index.html` (`#subscribe`
  section) — currently a placeholder form. Point its `action` at your email
  provider's signup endpoint (Mailchimp, ConvertKit, Buttondown, etc. all
  have a simple form-action URL for this).
- **Contact form**: in `templates/contact.html` — same idea; wire it up to
  something like Formspree or Netlify Forms so submissions actually reach an
  inbox.
- **Social links**: currently placeholders (`#`) in `templates/base.html`
  footer — drop in the real Instagram/TikTok/Facebook URLs.

## Running it locally (optional, for previewing changes)

```bash
pip install jinja2
python3 build.py          # uses whatever is in data/episodes.json
python3 -m http.server --directory dist 8000
# open http://localhost:8000
```

To pull real episodes locally before pushing:

```bash
export YOUTUBE_API_KEY=your-key-here
python3 scripts/fetch_episodes.py
python3 build.py
```

## What's placeholder right now

- The 3 sample episodes in `data/episodes.json` are fake — they'll be
  overwritten by real data the first time the workflow runs with a valid
  `YOUTUBE_API_KEY` secret.
- Resources cards, About page photo, and social links are structural
  placeholders carried over from the old site's sections — swap in real
  content whenever you're ready.
- Audio-platform badges (Apple/Spotify/iHeart) link to the show's main page
  on each platform rather than per-episode, since there's no automatic way to
  match a YouTube upload to its Buzzsprout/Spotify episode without manual
  mapping. If that matters, Buzzsprout's own RSS feed could be pulled in the
  same automated way later to add per-episode audio links.
