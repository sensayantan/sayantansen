# Architecture

`https://sensayantan.github.io/sayantansen/` is a static site on GitHub
Pages: plain HTML, CSS and JavaScript, no framework, no build step, no
bundler. Everything a reader sees is a file in this repository. The few
things that need a running server — admin login and live autism search —
are two small Cloudflare Workers.

The repository is organised **one folder per menu item**. Each folder holds
its page, its script, its source content, its generator and its generated
data, plus a `README.md` explaining how that feature works end to end.

| Menu | Folder | What it is | Architecture |
|---|---|---|---|
| About Me | [`AboutMe/`](AboutMe/) (page: root `index.html`) | Bio, journeys, family, photos — edited in `/admin` | [AboutMe/README.md](AboutMe/README.md) |
| Today's News | [`DAYBREAK/`](DAYBREAK/) | A researched daily brief, Mon–Sat, plus an archive calendar | [DAYBREAK/README.md](DAYBREAK/README.md) |
| Sayantan Blogs | [`BLOG/`](BLOG/) | Blog posts written in `/admin`, rendered to static pages | [BLOG/README.md](BLOG/README.md) |
| My Experiment | [`MyExperiment/`](MyExperiment/) | Retrieval search over ~1,900 autism research records, with live summaries | [MyExperiment/README.md](MyExperiment/README.md) |

## The whole system

```
                        ┌──────────────── writers ────────────────┐
  Site owner in /admin  │  Codex automation (Mon–Sat 10 AM PT)     │  GitHub Actions cron (monthly)
  (Decap CMS)           │  researches + renders an edition         │  refresh-corpus.yml
        │               │                │                         │         │
  oauth-proxy Worker    │                │                         │         │
  (GitHub login)        │                │                         │         │
        │               └────────────────┼─────────────────────────┘         │
        ▼                                ▼                                   ▼
  AboutMe/content/            DAYBREAK/daybreak-*.html          MyExperiment/data/autism-faq.json
  BLOG/content/  + images     (commit + push to main)           MyExperiment/worker/public/worker-index/
  content/project-docs.yml                                      (commit to main)
        │                                │                                   │
        └───────────────┬────────────────┘                                   │
                        ▼                                                    │
        render-content.yml  (on push to AboutMe/, BLOG/, DAYBREAK/,          │
                             content/, admin/)                               │
          validate admin/config.yml · render About · render blog posts ·     │
          render project docs · patch Daybreak editions                      │
          → commit generated files back to main  [skip ci]                   │
                        │                                                    │
                        ▼                                                    ▼
                 GitHub Pages (serves main)                  autism-search Worker redeploys
                        │                                    (git-connected, Cloudflare)
                        ▼                                                    │
                  reader's browser  ──── POST /api/ask ─────────────────────▶┘
```

Three patterns repeat across every feature:

1. **Source → generator → generated file.** People and automations write
   *source* (Markdown/YAML in a `content/` folder, or a pipeline's inputs); a
   script turns it into what the site serves. Generated files are never
   hand-edited — the next run overwrites them. Fixes go in the generator.
2. **Commit-back with `[skip ci]`.** Workflows commit their output to `main`
   with `[skip ci]` so the commit does not re-trigger itself.
3. **Pages serve files; Workers run code.** GitHub Pages cannot execute
   anything, so anything that must happen *at request time* lives in a
   Cloudflare Worker.

## Shared pieces (outside the feature folders)

| Path | What it is |
|---|---|
| `index.html` | The About Me page and the site root. |
| `assets/css/style.css` | The one stylesheet for all site pages (Daybreak editions carry their own). |
| `assets/js/main.js` | Mobile nav toggle and footer year, on every page. |
| `admin/` | The Decap CMS editor at `/admin`. `config.yml` defines the About Me, Blog Posts and Project Documentation forms and where each writes. |
| `oauth-proxy/` | Cloudflare Worker that exchanges a GitHub login for a token, so `/admin` can commit. Holds the OAuth client secret; see its README. |
| `backend/` | Shared scripts: `check_cms_config.py` (catches an admin config that would take `/admin` down) and `render_project_docs.py`. |
| `projectdocs.html`, `content/project-docs.yml`, `data/project-docs.json` | The project documentation page: epics, stories and backlog. GitHub sign-in required to view. |
| `.github/workflows/` | `render-content.yml` (every content push), `refresh-corpus.yml` (monthly), `daybreak.yml` (dormant cloud Daybreak). |
| `ARCHITECTURE.md` | This file. |

### Navigation and page chrome

Every page carries the same header and footer, copy-pasted rather than
templated (there is no build step to include them): root `index.html`,
`projectdocs.html`, `BLOG/index.html`, `DAYBREAK/index.html`,
`DAYBREAK/archive.html`, `MyExperiment/index.html`, and the post template
inside `BLOG/render_blogs.py`. A change to the header or footer must be made
in all of them. Daybreak editions get their nav from
`DAYBREAK/pipeline/template.html` and `DAYBREAK/patch_daybreak.py`.

Every reference to the stylesheet or a script carries a shared `?v=N`
cache-buster; `.claude/skills/frontend-standards/scripts/check_css_version.py`
fails if any is missing or out of step.

## Redirects from the old layout

Before the folder reorganisation, pages lived at the root. These old URLs
are now small redirect pages that forward to the new location, keeping
any `?query` and `#anchor`:

| Old | New |
|---|---|
| `news.html` | `DAYBREAK/index.html` |
| `archive.html` | `DAYBREAK/archive.html` |
| `blogs.html` | `BLOG/index.html` |
| `blogs/<slug>.html` | `BLOG/posts/<slug>.html` |
| `autism.html` | `MyExperiment/index.html` |

`backend/daybreak` remains as a symlink to `DAYBREAK/pipeline` until the
Codex automation's prompt is updated to the new path (see
[DAYBREAK/README.md](DAYBREAK/README.md)).

## Privacy rule

Everything committed here is publicly served by GitHub Pages, whether or
not a page links to it. Personal data — contact details, followers,
commenters, and any future reader data such as comments or reactions —
never goes in this repository. Raw exports (e.g. `BLOG/takeout/`) stay
local and gitignored; reader data belongs in a Worker's own storage.

## External services

| Service | Used for | Cost |
|---|---|---|
| GitHub Pages | hosting | free |
| GitHub Actions | rendering, monthly corpus refresh | free tier |
| GitHub Discussions + giscus | blog comments | free |
| Cloudflare Workers + Workers AI | admin login; autism search embedding and summaries | free tier |
| PubMed E-utilities, ClinicalTrials.gov | the autism corpus | free, no key |
| Yahoo Finance | Daybreak market data (ticker symbols only) | free |
| Codex app | Daybreak research and publishing | existing subscription |
