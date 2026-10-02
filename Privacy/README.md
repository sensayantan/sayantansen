# Privacy & contact

The site's privacy policy and its contact form, at
`https://sensayantan.com/Privacy/`, linked as **"Privacy & contact"** from
every page's footer — including the blog post template and every Daybreak
edition (added by `DAYBREAK/patch_daybreak.py`).

Built 2026-10-01 as step 2 of the plan agreed on 2026-09-30
(1 domain → 2 privacy page → 3 analytics → 4 social-sign-in comments).

## Folder layout

| Path | What it is |
|---|---|
| `index.html` | The privacy policy and the contact form. Plain HTML; update the "Last updated" date whenever the policy changes. |
| `contact.js` | Shows the form (or a "being set up" note), loads the Cloudflare Turnstile widget, posts the form to the Worker, and shows the Worker's reason code in brackets when something fails. Holds two public values: the Worker endpoint and the Turnstile **site key**. |
| `worker/` | The `sayantansen-contact` Cloudflare Worker that verifies the Turnstile token and emails the message to the owner. |

## What the page says

A plain-language policy describing what the site actually does, written
from the code rather than from a template:

| Section | What it states |
|---|---|
| The short version | Personal site; no ads, nothing sold or shared; no cookies of its own; no analytics today; never asks for or stores a password; contact messages are emailed, not stored. |
| When you visit | GitHub Pages hosts the site (GitHub sees request details under its privacy statement); Cloudflare manages the domain and DNS; Google Fonts receives visitors' IP address and browser details when fonts load. No analytics — and if visitor counts are added, they will be counts only, no IPs or cookies, and the page will say so first. |
| Comments on blog posts | Today's comments use giscus: public GitHub Discussions, signing in on GitHub's own page. The planned Google/Facebook/X/GitHub comments will be described — name, profile picture, provider user ID, time, comment, where kept, how to delete — before they go live. |
| My Experiment's search | Questions go to a Cloudflare service and an AI model on Cloudflare; not stored; counted per IP address for one minute only, to prevent overload. |
| The contact form | Name, optional email and message are emailed to the owner via Cloudflare; nothing stored on the site; Cloudflare Turnstile checks for bots under Cloudflare's policy; messages deleted on request. |
| Admin and project pages | For the owner only; sign-in on GitHub; the project docs keep it in the tab, the `/admin` editor in the browser until logout. |
| Links to other sites | Daybreak's sources, research papers and social profiles have their own policies. |
| Your requests | Access or deletion requests and questions go through the form; the date at the top changes whenever the page does. |

When analytics (step 3) or the new comments (step 4) ship, the matching
section here must be updated **before** they go live, with a new date.

## How a message reaches the owner

```
Privacy/index.html  →  contact.js
   1. reader fills in name, optional email, message
   2. Cloudflare Turnstile widget issues a one-time token ("human check")
   3. POST {name, email, message, turnstileToken} → worker /api/contact
        ▼
sayantansen-contact Worker
   · CORS: only sensayantan.com (and localhost:8000 for testing)
   · validates lengths; strips control characters from header values,
     so a name cannot inject extra email headers
   · verifies the token with Turnstile's siteverify (TURNSTILE_SECRET);
     on failure returns Turnstile's error code as "reason"
   · builds a plain-text email; Reply-To = the reader's address, if given
   · sends it with the SEND_EMAIL binding (Cloudflare Email Routing);
     on failure returns Email Routing's reason, with addresses masked
        ▼
the owner's inbox (CONTACT_TO, a verified Email Routing destination address)
```

Nothing is stored anywhere along the way: no database, no log of messages.

## Where the settings live

This repository is public, so neither secret is here:

| Setting | Where | What |
|---|---|---|
| `TURNSTILE_SECRET` | Worker → Settings → Variables and Secrets, type **Secret** | the Turnstile widget's secret key |
| `CONTACT_TO` | Worker → Settings → Variables and Secrets, type **Secret** | the owner's Gmail; must also be a **verified destination address** in Email Routing |
| `FROM_ADDRESS` | `worker/wrangler.jsonc` | `contact-form@sensayantan.com`; must be on the domain with Email Routing enabled |
| `SITE_ORIGINS` | `worker/wrangler.jsonc` | pages allowed to post to the form |
| `keep_vars: true` | `worker/wrangler.jsonc` | keeps dashboard-set variables across deploys (see the setup record) |
| Turnstile **site key** | `contact.js` | `0x4AAAAAAFLbmJJ930ofF5vj` — public by design |

`GET https://sayantansen-contact.sen-sayantan.workers.dev/api/health`
reports, without revealing any value:

```json
{"ok": true, "turnstileSecret": true, "turnstileSecretValid": true,
 "contactTo": true, "emailBinding": true}
```

`turnstileSecretValid` is checked live: the Worker asks Turnstile to verify a
dummy token, and a wrong secret comes back as `invalid-input-secret`.
`ok` does **not** prove delivery — only a real test message does, because
an unverified destination address passes every check above and still
fails at send time.

## Setup record (2026-10-01)

What was done in the Cloudflare dashboard, in order, including what went
wrong and how it was fixed. Repeat these steps if the setup ever has to be
rebuilt.

### 1. Email Routing — enabled, destination added late

- **sensayantan.com → Email → Email Routing → enable.** Cloudflare added the
  mail DNS records itself: MX `route1/2/3.mx.cloudflare.net`, SPF
  `v=spf1 include:_spf.mx.cloudflare.net ~all`, and a DKIM record. They do
  not affect the website's A/AAAA records.
- **Destination addresses → add the owner's Gmail → click the verification
  link Cloudflare emails → status Verified.** This was skipped at first: the
  list showed *"No destination addresses found"*, so every send failed with
  "The message couldn't be sent". No routing rule is needed — the form only
  sends mail.

### 2. Turnstile — recreated after a duplicate

- Turnstile is an **account-level** tool, not inside the domain's menu:
  `https://dash.cloudflare.com/?to=/:account/turnstile`, or search
  "Turnstile" (Cmd+K).
- **Add widget manually** (not "Set up with Spin"): name
  `sensayantan contact`, hostnames `sensayantan.com` and `localhost`, mode
  **Managed**, pre-clearance **No**. The confirmation screen shows the
  **Site Key** (public, goes in `contact.js`) and the **Secret Key** (goes in
  the Worker only).
- The first attempt left **two** widgets with the same name, and the Worker
  held a secret matching neither (health showed
  `turnstileSecretValid: false`; the form said "The human check didn't
  pass"). Both were deleted and one widget recreated; its site key replaced
  the old one in `contact.js` (#91).
- The yellow banner *"Siteverify isn't being called"* appears until the
  Worker has verified real tokens; it clears on its own.

### 3. The Worker — root directory

- **Workers & Pages → Create application → Import a repository →
  `sensayantan/sayantansen`**: project name `sayantansen-contact`, build
  command empty, deploy command `npx wrangler deploy`, **root directory
  `Privacy/worker`**.
- The first build failed with *"Asset too large … .git/objects/pack/…
  32.2 MiB"*: the root directory had not been set, so Wrangler treated the
  whole repository as static files. Setting it to `Privacy/worker` (Settings
  → Build) and retrying fixed it.
- Like the other two Workers, it is git-connected: **every push to `main`
  redeploys it.**

### 4. Secrets — Text vs Secret

- **Settings → Variables and Secrets → + Add**, choosing **Type: Secret**
  (the dropdown defaults to Text) for `TURNSTILE_SECRET` and `CONTACT_TO`,
  then **Deploy**.
- `CONTACT_TO` was saved as **Text** more than once, and each push to `main`
  silently deleted it: a deploy replaces plain-text variables with the
  config's `vars`. The form then said "The contact form is not set up yet".
  `keep_vars: true` (#92) now keeps dashboard values across deploys; Secrets
  were never affected.
- A saved Secret cannot be viewed or edited in place ("encrypted Secret …
  rotate this secret"): delete it and add it again with the new value.

### Changes shipped along the way

| PR | What |
|---|---|
| #88 | The page, the form, the Worker, the footer link everywhere |
| #89 | Worker endpoint and first site key in `contact.js` |
| #90 | Turnstile error codes shown on failure; `turnstileSecretValid` in health; secret trimmed |
| #91 | Site key of the recreated widget |
| #92 | `keep_vars: true`, so dashboard variables survive deploys |
| #93 | Email Routing's send error shown on failure, addresses masked |

## When it breaks

The form shows a reason in brackets after its message:

| Form says | Cause | Fix |
|---|---|---|
| "The contact form is being set up" | `CONTACT_ENDPOINT` or `TURNSTILE_SITE_KEY` empty in `contact.js` | fill them in, bump the cache version |
| "The contact form is not set up yet." | a Worker setting is missing — health shows which | re-add it as a **Secret** and Deploy |
| "The human check didn't pass (invalid-input-secret)" | `TURNSTILE_SECRET` is wrong — e.g. the site key, or another widget's secret | copy the widget's Secret Key (rotate if hidden), replace the Secret |
| "… (timeout-or-duplicate)" | page left open over 5 minutes, or token reused | reload the page and resend |
| "… (missing-token)" | widget didn't load — page hostname not listed on the widget | add the hostname to the widget |
| "The message couldn't be sent (… not a verified address …)" | no verified destination address in Email Routing | add the Gmail under Destination addresses and verify it |
