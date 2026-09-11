# OAuth proxy for /admin

GitHub Pages can't run server code, but logging into `/admin` (Decap CMS)
needs a server to safely exchange a GitHub login for an access token —
that exchange requires a client *secret*, which must never reach the
browser. This folder is that small server: a Cloudflare Worker
(`src/index.js`, routing to `src/auth.js` / `src/callback.js`) with a
static `public/` folder, deployed together as one app (generous free
tier, git-based deploys, no cost for a personal blog's login traffic).

## One-time setup

### 1. Create the Cloudflare Worker project

Cloudflare's dashboard changed mid-way through building this (twice) —
these steps reflect what's actually there now, not older docs.

1. Sign in at [dash.cloudflare.com](https://dash.cloudflare.com) (free account is fine).
2. In the left sidebar, click **Compute** (under "Build") to expand it, then click **Workers & Pages**.
3. Click **Create application** (top right) → **Import a repository** / connect to Git → pick this repo (`sensayantan/sayantansen`).
4. On the "Set up your application" screen:
   - **Project name**: anything, e.g. `sayantansen-oauth`
   - **Build command**: leave empty (nothing to build — plain JS, no bundler needed)
   - **Deploy command**: leave the default, `npx wrangler deploy`
   - Look for a **path / root directory** setting (may be under an "Advanced" toggle, or further down the form) and set it to `oauth-proxy` — this repo's wrangler config lives in that subfolder, not the repo root. If no such field exists in your version of this flow, tell me and we'll adjust (e.g. move the config to the repo root, or use a separate repo for the proxy).
5. Click **Deploy**. Once it finishes, note the URL Cloudflare gives you — something like `https://sayantansen-oauth.<your-account>.workers.dev`.

### 2. Register a GitHub OAuth App

1. GitHub → **Settings → Developer settings → OAuth Apps → New OAuth App**.
2. Fill in:
   - **Application name**: anything, e.g. "Sayantan Sen Blog Admin"
   - **Homepage URL**: `https://sensayantan.github.io/sayantansen/`
   - **Authorization callback URL**: `https://<your-worker-url>/api/callback` — must match your actual deployed URL from step 1 exactly, including `/api/callback` with no trailing slash.
3. Click **Register application**.
4. Click **Generate a new client secret** — copy both the **Client ID** and the **Client Secret** now (the secret is shown only once).

### 3. Give the proxy those credentials

Back in the Cloudflare project: **Settings → Variables and Secrets** → add:
- `GITHUB_CLIENT_ID` = the Client ID from step 2
- `GITHUB_CLIENT_SECRET` = the Client Secret from step 2 — add it as a **Secret**, not a plain text variable, so it's encrypted at rest.

Redeploy after saving (Cloudflare may prompt for this automatically).

### 4. Point the admin at this proxy

In `admin/config.yml`, set `backend.base_url` to your actual deployed URL from step 1 (it's currently a placeholder). Commit and push.

### 5. Test it

Visit `https://sensayantan.github.io/sayantansen/admin/` → click **Login with GitHub** → approve on GitHub's page → you should land back in the admin, logged in.

## How it works (the short version)

1. Clicking "Login with GitHub" opens a popup pointed at `/api/auth`, which redirects it to GitHub's own login/authorize page — the actual password entry happens on github.com, never on this site.
2. GitHub redirects the popup back to `/api/callback` with a one-time code.
3. `callback.js` exchanges that code for an access token — this step needs the client secret, which is why it must happen server-side, never in the browser.
4. The popup hands the token back to the main `/admin` window via `postMessage`, then closes. Decap stores the token and uses it to read/write files in the repo via the GitHub API from then on.

The `state` value generated in `auth.js` and checked in `callback.js` is a CSRF defense — it proves the callback we're processing was actually started by this browser, not planted by another site.

## Why this isn't Cloudflare Pages Functions

Earlier drafts of this proxy used Pages' file-based routing convention
(`functions/api/*.js`, auto-mapped to routes). Cloudflare's current
git-connected deploy flow builds everything as a single Worker instead —
one script (`src/index.js`) that routes requests itself, plus a static
`assets` directory declared in `wrangler.jsonc`, deployed via
`wrangler deploy`. Same end result, different plumbing.
