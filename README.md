# sayantansen

Personal website — bio, blog, and a daily tech news feed. Built step by step
while learning web development.

## Status: Step 1 — vanilla site

Right now this is a plain HTML/CSS/JS site with no build tools, so it's easy
to preview and understand:

- `index.html` — the page content
- `assets/css/style.css` — styling
- `assets/js/main.js` — small bits of interactivity (mobile nav, footer year)

## Run it locally

Just open `index.html` in a browser, or serve it so relative links behave
like they will online:

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
2. Fill in real bio content and personal branding
3. Add a blog section (Markdown posts, no backend yet)
4. Add a Python backend (FastAPI) to generate a daily news feed
5. Rebuild the frontend in React, calling the Python API
6. Wire up Claude / OpenAI / Gemini API keys to power news summarization
7. Link the site from LinkedIn, Instagram, and Facebook profiles
