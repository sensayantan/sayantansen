# About Me

The site's landing page: an introduction, a professional journey, a personal
journey and a family section, each with its own photos. Everything a reader
sees on it is edited from the browser at `/admin`, not in code.

## Folder layout

| Path | What it is |
|---|---|
| `../index.html` | The page itself. It stays at the site root because it is the site's front door; moving it would add a redirect hop to every visit. |
| `content/about.yml` | The source of truth: the text of each section, in Markdown, and the photo list. Written by the admin's **About Me Page** entry. |
| `render_about.py` | Converts `about.yml` into `data/about.json`, turning each Markdown field into HTML. |
| `data/about.json` | What the page loads. Generated — never edit it by hand, the next render overwrites it. |
| `about.js` | Fetches `data/about.json` and fills the page's sections. |
| `images/` | The profile photos `about.yml` points at. |

## How it works

```
/admin  "About Me Page"  (Decap CMS, signed in through GitHub)
   │  commits AboutMe/content/about.yml straight to main
   ▼
.github/workflows/render-content.yml   (triggers on AboutMe/**)
   │  python AboutMe/render_about.py
   ▼
AboutMe/data/about.json   committed back to main with [skip ci]
   │
   ▼  GitHub Pages serves the new file
index.html  →  AboutMe/about.js  →  fetch("AboutMe/data/about.json", no-store)
               fills #about-intro, #profile-photos, #professional-journey,
               #personal-journey, #family-intro
```

The page's HTML is only a shell. Its words and photos arrive from the JSON
at load time, which is why an edit in the admin shows up without anyone
touching `index.html`.

`about.json` is fetched with `cache: "no-store"` because GitHub Pages' CDN
has repeatedly served a stale copy otherwise.

## Photos

Each photo in `about.yml` has an `image` path, an optional `caption` and an
`ai_generated` flag; a flagged photo is shown with an "AI Generated" badge. The admin
uploads into `AboutMe/images/` (its `media_folder` in `admin/config.yml`),
and paths are stored with the `/sayantansen/` base so the admin's own
preview resolves them.

## Run it locally

```
pip install -r requirements.txt
python AboutMe/render_about.py
python3 -m http.server 8000      # from the folder above the repo
```

Then open `http://localhost:8000/sayantansen/`. The page must be served,
not opened as a file: browsers block `fetch()` from `file://`.

## When it breaks

- **Old text after publishing**: check the render workflow ran and committed
  `AboutMe/data/about.json`; then hard-refresh.
- **Admin shows an error instead of the editor**: `admin/config.yml` is
  invalid. `admin/check_cms_config.py` runs in the render workflow to catch
  this before it ships.
- **A photo is missing**: its `image` path must start with
  `/sayantansen/AboutMe/images/`.
