# OAuth proxy for /admin

GitHub Pages can't run server code, but logging into `/admin` (Decap CMS)
needs a server to safely exchange a GitHub login for an access token —
that exchange requires a client *secret*, which must never reach the
browser. This folder is that small server: two functions
(`functions/api/auth.js`, `functions/api/callback.js`), deployed on
Cloudflare Pages (generous free tier, git-based deploys, no cost for a
personal blog's login traffic).

## One-time setup

### 1. Create the Cloudflare Pages project

1. Sign in at [dash.cloudflare.com](https://dash.cloudflare.com) (free account is fine).
2. In the left sidebar, click **Compute** (under "Build") to expand it, then click **Workers & Pages**.
   (Cloudflare's dashboard nests it here now — it's no longer a top-level sidebar item.)
3. Click **Create application** (top right).
4. Choose **Pages**, then **Connect to Git** → pick this repo (`sensayantan/sayantansen`).
5. Configure the build:
   - **Root directory**: `oauth-proxy`
   - **Framework preset**: None
   - **Build command**: (leave empty)
   - **Build output directory**: `public`
6. Click **Save and Deploy**. Once it finishes, note the URL Cloudflare gives you — something like `https://sayantansen-oauth.pages.dev`.

### 2. Register a GitHub OAuth App

1. GitHub → **Settings → Developer settings → OAuth Apps → New OAuth App**.
2. Fill in:
   - **Application name**: anything, e.g. "Sayantan Sen Blog Admin"
   - **Homepage URL**: `https://sensayantan.github.io/sayantansen/`
   - **Authorization callback URL**: `https://<your-pages-url>/api/callback` — must match your actual Cloudflare Pages URL from step 1 exactly, including `/api/callback` with no trailing slash.
3. Click **Register application**.
4. Click **Generate a new client secret** — copy both the **Client ID** and the **Client Secret** now (the secret is shown only once).

### 3. Give the proxy those credentials

Back in the Cloudflare Pages project: **Settings → Environment variables** → add, for the Production environment:
- `GITHUB_CLIENT_ID` = the Client ID from step 2
- `GITHUB_CLIENT_SECRET` = the Client Secret from step 2 (mark it "Encrypt"/secret if offered)

Trigger a new deployment (Cloudflare usually does this automatically after saving env vars; otherwise use "Retry deployment").

### 4. Point the admin at this proxy

In `admin/config.yml`, set `backend.base_url` to your actual Cloudflare Pages URL from step 1 (it's currently a placeholder). Commit and push.

### 5. Test it

Visit `https://sensayantan.github.io/sayantansen/admin/` → click **Login with GitHub** → approve on GitHub's page → you should land back in the admin, logged in.

## How it works (the short version)

1. Clicking "Login with GitHub" opens a popup pointed at `/api/auth`, which redirects it to GitHub's own login/authorize page — the actual password entry happens on github.com, never on this site.
2. GitHub redirects the popup back to `/api/callback` with a one-time code.
3. `callback.js` exchanges that code for an access token — this step needs the client secret, which is why it must happen server-side, never in the browser.
4. The popup hands the token back to the main `/admin` window via `postMessage`, then closes. Decap stores the token and uses it to read/write files in the repo via the GitHub API from then on.

The `state` value generated in `auth.js` and checked in `callback.js` is a CSRF defense — it proves the callback we're processing was actually started by this browser, not planted by another site.
