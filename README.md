# sayantansen

Sayantan Sen's personal website — https://sensayantan.com/

(Before 2026-09-30 it lived at `sensayantan.github.io/sayantansen/`; GitHub
Pages redirects every old link there to the same page here.)

A static site on GitHub Pages: plain HTML, CSS and JavaScript, no build
step. Four sections, one folder each:

| Menu | Folder | How it works |
|---|---|---|
| About Me | `AboutMe/` (page: `index.html`) | [AboutMe/README.md](AboutMe/README.md) |
| Today's News | `DAYBREAK/` | [DAYBREAK/README.md](DAYBREAK/README.md) |
| Sayantan Blogs | `BLOG/` | [BLOG/README.md](BLOG/README.md) |
| My Experiment | `MyExperiment/` | [MyExperiment/README.md](MyExperiment/README.md) |

The project documentation (epics, stories, backlog) lives in `ProjectDocs/`
— see [ProjectDocs/README.md](ProjectDocs/README.md).

**Start with [ARCHITECTURE.md](ARCHITECTURE.md)** for how the pieces fit
together: what writes content, what renders it, what serves it, and the two
Cloudflare Workers behind admin login and live search.

## Editing content

About Me and blog posts are edited in the browser at
[`/admin`](https://sensayantan.com/admin/) (Decap CMS,
GitHub sign-in). Publishing commits straight to `main`; a GitHub Action
renders the pages within a minute. Admin login needs the Worker in
[`oauth-proxy/`](oauth-proxy/README.md).

## Run it locally

Pages load their content with `fetch()`, which browsers block for
`file://`, so serve the site. It is published at the root of its domain,
so serve this repository's folder itself:

```
python3 -m http.server 8000
```

Then open `http://localhost:8000/`.

To regenerate content after editing source files:

```
pip install -r requirements.txt
python AboutMe/render_about.py
python BLOG/render_blogs.py
python ProjectDocs/render_project_docs.py
python DAYBREAK/patch_daybreak.py
```

## Publishing

GitHub Pages serves the `main` branch from the repository root
(**Settings → Pages → Deploy from a branch → `main` / root**). Changes
reach `main` through a branch and pull request.
