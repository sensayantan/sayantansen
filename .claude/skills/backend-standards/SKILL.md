---
name: backend-standards
description: Backend coding standards for the sayantansen repo's Python scripts (backend/*.py) and the render/publish pipeline. Use when writing or editing anything under backend/, .github/workflows/render-content.yml, or admin/config.yml.
---

The backend is a set of small, independent Python scripts under `backend/` —
not a framework, not a long-running service. Keep additions in that spirit:
a script that does one job and exits, not a new service to operate.

## The render_*.py pattern

`render_about.py` and `render_blogs.py` follow the same shape — copy it for
any new content type:

1. Read source content from `content/` (YAML front matter + Markdown, edited
   via the Decap CMS admin at `/admin`).
2. Convert Markdown to HTML with the `markdown` library — don't hand-roll
   Markdown parsing.
3. Write the result to `data/*.json` (for JS-rendered pages) or generate
   static `.html` files directly (for blog posts), matching whichever the
   consuming page already expects.
4. Start the script with a module docstring explaining what it reads, what
   it writes, and how it's triggered in production (usually: automatically,
   via `.github/workflows/render-content.yml` on a push touching
   `content/**`) — someone reading the file cold should not have to guess.

Run the relevant script locally and diff its output before trusting a
change to it; don't rely on the GitHub Action alone to validate.

## Config and secrets

- Runtime configuration (model names, search limits, provider choice) lives
  in `backend/config.py`, not scattered across scripts.
- Real secrets (API keys) belong in `.env`, which is gitignored — never
  commit one, and never hardcode a key as a fallback default in code.
  `.env.example` documents which variables are needed without real values.
- The OAuth proxy's secrets (`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`) live
  in Cloudflare's own dashboard (Workers & Pages → Settings → Variables and
  Secrets), never in this repo — `oauth-proxy/src/*.js` only reads them from
  `env` at runtime.

## GitHub Actions

- `.github/workflows/render-content.yml` re-runs the render scripts and
  commits the output back to `main` on every push touching `content/**`,
  using `git commit -m "... [skip ci]"` to avoid re-triggering itself.
  Follow that same pattern (`[skip ci]`) for any new workflow that commits
  generated output back to the repo.
- Prefer extending this single workflow over adding a new one, unless the
  new automation runs on a genuinely different trigger (e.g. a schedule
  rather than a content push).

## Dependencies

Add new Python dependencies to `backend/requirements.txt`, pinned loosely
(no dependency has an exact-version pin today — match that unless a specific
version is required to avoid a known bug).
