# sayantansen

Personal website — bio, blog, and a daily tech news feed. Built step by step
while learning web development.

## Status: Step 2 — "Today's News" UI template

Still plain HTML/CSS/JS, no build tools. Now three pages sharing one nav:

- `index.html` — About Me
- `news.html` — Today's News (the "Daybreak" template)
- `blogs.html` — Sayantan Blogs (placeholder)
- `assets/css/style.css` — all styling (blue pill nav + Daybreak news template)
- `assets/js/main.js` — mobile nav toggle, footer year
- `assets/js/news.js` — fetches `data/news.json` and renders the news page
- `data/news.json` — the content shown on Today's News. Currently placeholder
  data; will be regenerated automatically once `backend/generate_news.py`
  is wired up to an AI API.
- `backend/` — Python side, not yet implemented. `generate_news.py` is a
  stub that will call Claude or OpenAI to research/summarize the day's
  news and write the result into `data/news.json`.

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
3. Write `backend/generate_news.py` — call Claude/OpenAI to research and summarize the day's news into `data/news.json`
4. Automate step 3 to run daily (e.g. scheduled GitHub Action)
5. Fill in real bio content and personal branding on About Me
6. Add an admin view for About Me and Sayantan Blogs (draft/edit/publish without touching code)
7. Rebuild the frontend in React once there's a real API/backend to talk to
8. Link the site from LinkedIn, Instagram, and Facebook profiles
