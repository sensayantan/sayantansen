# sayantansen

Personal website — bio, blog, and a daily tech news feed. Built step by step
while learning web development.

## Status: Step 3 — news generator backend (7 of 8 sections working)

Frontend is plain HTML/CSS/JS, no build tools. Three pages sharing one nav:

- `index.html` — About Me
- `news.html` — Today's News (the "Daybreak" template)
- `blogs.html` — Sayantan Blogs (placeholder)
- `assets/css/style.css` — all styling (blue pill nav + Daybreak news template)
- `assets/js/main.js` — mobile nav toggle, footer year
- `assets/js/news.js` — fetches `data/news.json` and renders the news page
- `data/news.json` — the content shown on Today's News. Currently placeholder
  data — see below to generate a real edition.

Backend (Python), in `backend/`:

- `config.py` — defines the 7 AI-researched sections (Top News, US News,
  World News, India News, Technology & Innovation, AI Model & Product
  Updates, Sports) — their labels and preferred sources
- `claude_news.py` — calls Claude with the web search tool for one section,
  parses the response into stories with real source citations
- `state.py` — tracks the last successful run so each edition only
  searches for news since then (falls back to 3 days for the first run)
- `generate_news.py` — orchestrates all sections and writes `data/news.json`
- `requirements.txt`, `.env.example` — dependencies and API key template

**Money/Markets is not yet wired up.** Stock prices and index levels need a
real market-data API (for accurate, timestamped numbers) rather than AI
web-search synthesis — building that is a separate phase once a data
provider is chosen.

### Generate a real edition

```
cd backend
pip install -r requirements.txt
cp .env.example .env   # then fill in ANTHROPIC_API_KEY
python generate_news.py
```

This calls the Claude API (costs apply — web search is $10 per 1,000
searches plus normal token costs) and overwrites `data/news.json`. Refresh
`news.html` (served, not opened directly — see "Run it locally" below) to
see the real edition.

### Still to come

- Money/Markets section (needs a market-data API)
- Automatic daily scheduling (GitHub Actions cron)
- Auto-deploy (commit + push `data/news.json` after each run)

## Run it locally

`index.html` and `blogs.html` can be opened directly as files. `news.html`
needs to be served over HTTP (browsers block `fetch()` of local files), so
from the project folder run:

```
python3 -m http.server 8000
```

Then visit `http://localhost:8000`.

## Publish it (GitHub Pages)

1. On GitHub, go to the repo's **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to "Deploy from a branch".
3. Pick the `main` branch and `/ (root)` folder, then save.
4. GitHub will give you a URL like `https://<username>.github.io/sayantansen/`
   within a minute or two.

## Roadmap

1. ✅ Vanilla HTML/CSS/JS site with placeholder content
2. ✅ "Today's News" UI template (blue pill nav, Daybreak-style layout, driven by `data/news.json`)
3. ✅ `backend/generate_news.py` — Claude + web search researches and writes 7 of 8 sections
4. Money/Markets section (needs a market-data API — decision pending)
5. Automate news generation to run daily (scheduled GitHub Action)
6. Auto-deploy: commit + push `data/news.json` after each generated edition
7. Fill in real bio content and personal branding on About Me
8. Add an admin view for About Me and Sayantan Blogs (draft/edit/publish without touching code)
9. Rebuild the frontend in React once there's a real API/backend to talk to
10. Link the site from LinkedIn, Instagram, and Facebook profiles
