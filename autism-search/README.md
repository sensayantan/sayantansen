# Autism search Worker

GitHub Pages serves files; it cannot run code. The prepared questions on
`/autism.html` work anyway because their answers are computed offline and
shipped as JSON. A question someone types has to be embedded *at that
moment*, which needs a server. This folder is that server.

It is deliberately a **separate Worker** from `oauth-proxy/`, not extra
routes on it. That one holds GitHub client secrets and guards admin login;
this one is a public, unauthenticated endpoint that spends AI inference on
whatever a stranger types. Neither should be able to take the other down.

For how this fits with the offline pipeline — which machine runs what, which
files are intermediates, and why the prepared questions need no server at
all — see **How the whole thing fits together** in
[`experiments/autism-rag/README.md`](../experiments/autism-rag/README.md).

This is a plain HTTP API, not MCP. The browser POSTs JSON to a URL and gets
JSON back.

## What it does

```
POST /api/ask   {"question": "..."}
  -> embed the question with Workers AI (same model that built the index)
  -> dot-product it against 1900 stored vectors, keep the best 4
  -> hand those 4 records to a language model to summarise, with citations
  -> return the summary and the records

GET /api/health   confirms the index loaded and scores a sample query
```

There is no vector database. 1900 vectors × 384 dimensions is 2.8 MB —
small enough to hold in memory and brute-force in well under a millisecond.
A managed vector DB earns its keep at a scale this corpus is nowhere near,
and would add a paid dependency to something that currently costs nothing.

## Two model names you may have to change

`src/search.js` and `src/answer.js` each name a Workers AI model:

| Where | Name | Value |
|---|---|---|
| `src/search.js` | `EMBEDDING_MODEL` | `@cf/baai/bge-small-en-v1.5` |
| `wrangler.jsonc` (`vars`) | `TEXT_MODEL` | set this from the current catalogue |

The text model lives in config rather than code because Cloudflare retires
these on a schedule. The first value used here resolved to
`@cf/meta/infire-llama-3.1-8b-instruct`, which had been deprecated on
2026-05-30 — the ask endpoint returned `5028: ... was deprecated`. Check the
current catalogue, paste the id into `wrangler.jsonc`, redeploy.
`GET /api/health` reports the value the live deployment is using, so a wrong
name is visible without having to trigger a failed ask.

**These were written without being able to check Cloudflare's current model
catalogue** — developers.cloudflare.com is unreachable from the environment
this was built in. Check both against your account's Workers AI model list
before deploying. If a name is wrong, the constant is the only thing to
change.

The embedding model is the one that matters. It **must** be the same model
that built `index.pkl` (`BAAI/bge-small-en-v1.5`), or queries land in a
different vector space than the documents and every score is meaningless
while still looking like a plausible number. `search.js` compares the name
recorded in `docs.json` and refuses to run if they disagree — but that only
catches a wrong *name*, not two models that share a name and differ in
weights. The compatibility check below catches that.

## Setup

### 1. Export the index

```
cd experiments/autism-rag
python3 export_worker_index.py
```

Writes `autism-search/public/worker-index/vectors.bin` and `docs.json`.
Both must be committed — deployment is git-connected, so the Worker gets
them from the repo.

### 2. Create the Worker

Same flow as `oauth-proxy/`, with a different root directory:

1. [dash.cloudflare.com](https://dash.cloudflare.com) → **Compute** → **Workers & Pages**
2. **Create application** → **Import a repository** → pick `sensayantan/sayantansen`
3. On the setup screen:
   - **Project name**: `sayantansen-autism-search`
   - **Build command**: leave empty (plain JS, nothing to build)
   - **Deploy command**: default, `npx wrangler deploy`
   - **Root directory**: `autism-search` — this is the field that is easy to
     miss and the reason a deploy fails with "no wrangler config found"
4. **Deploy**, then note the URL, e.g.
   `https://sayantansen-autism-search.<account>.workers.dev`

The Workers AI binding is declared in `wrangler.jsonc`, so it is created on
deploy — there is nothing to click. If the dashboard asks you to enable
Workers AI on the account first, do that and redeploy.

### 3. Check it loaded

```
curl https://<your-worker-url>/api/health
```

Expect `{"ok":true,"sample_score":0.xxx}`. If `ok` is false the message says
what failed — almost always a missing `worker-index/` (step 1 not committed)
or a wrong model name.

### 4. Check the embeddings actually match

This is the step worth not skipping. Locally:

```
cd experiments/autism-rag
python3 query.py "is autism genetic"
```

Then the same question through the Worker:

```
curl -X POST https://<your-worker-url>/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"is autism genetic"}'
```

**The top-ranked paper should be the same, with a similar score.** If the
rankings are unrelated, Workers AI's `bge-small-en-v1.5` is not producing
the same vectors as the local one, and the whole thing is returning
confident nonsense. Stop and tell me if that happens — the fix is to embed
the corpus with Workers AI too, so both sides use one model.

### 5. Switch the box on

In `assets/js/autism.js`, set:

```js
const ASK_ENDPOINT = "https://<your-worker-url>/api/ask";
```

Commit and push. Until it is set the free-text box stays hidden and the
prepared-question dropdown works as before, so a half-finished deploy never
breaks the page.

## Keeping the index in sync

`.github/workflows/refresh-corpus.yml` re-exports these files each month and
commits them alongside `data/autism-faq.json`. Without that the page data
would be refreshed monthly while the Worker answered from a frozen corpus —
a silent drift that would be hard to notice.

The cost is repo size: `vectors.bin` is binary, so git stores a full 2.8 MB
copy per refresh rather than a delta — roughly 35 MB of history per year. If
that becomes a problem, move the two files to Cloudflare R2 and fetch them
in `loadIndex()` instead.

## Limits and abuse

- Questions are capped at 300 characters.
- CORS allows only `sensayantan.github.io` and localhost.
- 20 questions per IP per minute. This uses the Cache API, which is
  per-colocation rather than global, so it is a soft limit — enough to stop
  a stuck loop or a casual scraper from burning the daily Workers AI
  allowance, not enough to stop someone who is trying.
- If retrieval finds nothing above the relevance floor, the language model
  is never called. Asking a model to answer from no sources is asking it to
  invent one.
