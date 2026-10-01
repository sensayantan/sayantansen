# Privacy & contact

The site's privacy policy and its contact form, at
`https://sensayantan.com/Privacy/`, linked from every page's footer
("Privacy & contact") — including Daybreak editions, via
`DAYBREAK/patch_daybreak.py`.

## Folder layout

| Path | What it is |
|---|---|
| `index.html` | The privacy policy and the contact form. Plain HTML; update the "Last updated" date whenever the policy changes. |
| `contact.js` | Shows the form (or a "being set up" note), loads the Cloudflare Turnstile widget, and posts the form to the Worker. Holds two public values: the Worker endpoint and the Turnstile **site key**. |
| `worker/` | The `sayantansen-contact` Cloudflare Worker that verifies the Turnstile token and emails the message to the owner. |

## How a message reaches the owner

```
Privacy/index.html  →  contact.js
   1. reader fills in name, optional email, message
   2. Cloudflare Turnstile widget issues a one-time token ("human check")
   3. POST {name, email, message, turnstileToken} → worker /api/contact
        ▼
sayantansen-contact Worker
   · CORS: only sensayantan.com (and localhost for testing)
   · validates lengths; strips control characters from header values
   · verifies the token with Turnstile's siteverify (TURNSTILE_SECRET)
   · builds a plain-text email; Reply-To = the reader's address, if given
   · sends it with the SEND_EMAIL binding (Cloudflare Email Routing)
        ▼
the owner's inbox (CONTACT_TO, a destination address verified in Email Routing)
```

Nothing is stored anywhere along the way: no database, no log of messages.

## Where the secrets live

This repository is public, so neither secret is here:

| Setting | Where | What |
|---|---|---|
| `TURNSTILE_SECRET` | Worker → Settings → Variables and Secrets (secret) | Turnstile widget's secret key |
| `CONTACT_TO` | Worker → Settings → Variables and Secrets (secret) | the owner's Gmail, which must also be a **verified destination address** in Email Routing |
| `FROM_ADDRESS` | `worker/wrangler.jsonc` | `contact-form@sensayantan.com`; must be on the domain with Email Routing enabled |
| Turnstile **site key** | `contact.js` | public by design |

## One-time setup

1. **Email Routing:** Cloudflare → sensayantan.com → Email → Email Routing →
   enable, add the owner's Gmail under Destination addresses, click the
   verification link. Accept the MX/TXT records it adds (they do not affect
   the website).
2. **Turnstile:** Cloudflare → Turnstile → Add widget → hostnames
   `sensayantan.com` and `localhost`, mode Managed. The site key goes in
   `contact.js`; the secret key into the Worker (step 4).
3. **Worker:** Workers & Pages → Create application → Import a repository →
   `sensayantan/sayantansen`, project name `sayantansen-contact`, build
   command empty, deploy command `npx wrangler deploy`, **root directory
   `Privacy/worker`**.
4. **Secrets:** on the new Worker, Settings → Variables and Secrets → add
   `TURNSTILE_SECRET` and `CONTACT_TO` as secrets; redeploy.
5. Put the Worker's `…/api/contact` URL in `CONTACT_ENDPOINT` in `contact.js`.

`GET <worker>/api/health` reports whether all three pieces (secret, address,
email binding) are present, without revealing them.

## When it breaks

- **"The contact form is being set up"**: `CONTACT_ENDPOINT` or
  `TURNSTILE_SITE_KEY` in `contact.js` is empty.
- **"The human check didn't pass"**: the widget's hostname list is missing
  the page's domain, or `TURNSTILE_SECRET` belongs to a different widget.
- **"The message couldn't be sent"**: `CONTACT_TO` is not a verified
  destination address, or Email Routing is disabled for the domain.
