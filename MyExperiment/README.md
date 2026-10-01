# My Experiment — autism research search

A search over about 1,900 real research records — PubMed abstracts and
ClinicalTrials.gov trial records — that answers the questions families
actually ask about autism, and shows its working: every answer is a short
model-written summary on top of the ranked source records it was built
from, each linking to the real paper.

It is a **research search tool, not health information**. The page says so
before anything else, and nothing in the pipeline presents a result as
medical advice.

## Folder layout

| Path | What it is | Runs on |
|---|---|---|
| `index.html` | The page (menu: **My Experiment**). | the reader's browser |
| `autism.js` | Sends questions to the Worker, renders the summary and sources, falls back to stored results. | the reader's browser |
| `data/autism-faq.json` | Stored results for the prepared questions: ranked sources, no summary. The fallback when the Worker is unreachable. Generated. | served by GitHub Pages |
| `rag/` | The offline pipeline: fetch the corpus, embed it, build the page data and the Worker's index. Deep dive: [`rag/README.md`](rag/README.md). | your Mac, or GitHub Actions monthly |
| `worker/` | The Cloudflare Worker that answers questions live. Deep dive: [`worker/README.md`](worker/README.md). | Cloudflare |
| `worker/public/worker-index/` | `vectors.bin` + `docs.json`: the embedded corpus the Worker searches. Generated. | bundled into the Worker |

## Why there are three machines

GitHub Pages only serves files; it cannot run code. Answering a question
someone just typed means embedding it and ranking 1,900 vectors *at that
moment*, so that work needs a server — the Cloudflare Worker. Building the
corpus and its embeddings is slow, occasional work, so it runs offline and
its results are committed as files.

| Machine | Does | When |
|---|---|---|
| GitHub Actions (`refresh-corpus.yml`) or your Mac | fetch → embed → export | 1st of each month, or by hand |
| Cloudflare Worker `sayantansen-autism-search` | embed the question, rank, summarise | on every question |
| The reader's browser | ask, render, fall back | on every page view |

## Flow 1 — building the corpus (offline, monthly)

```
PubMed E-utilities ──▶ rag/fetch_pubmed.py  ──▶ rag/corpus/pubmed.jsonl   (~1,500)
ClinicalTrials.gov ──▶ rag/fetch_trials.py  ──▶ rag/corpus/trials.jsonl   (~400)
                                                         │
                     rag/build_index.py  (BAAI/bge-small-en-v1.5, 384-dim)
                                                         ▼
                                                   rag/index.pkl
                         ┌───────────────────────────────┼──────────────────────────┐
                         ▼                               ▼                          ▼
             rag/build_page_data.py          rag/export_worker_index.py     rag/calibrate.py
                         │                               │                  (logs score separation;
                         ▼                               ▼                   a record, not a gate)
             data/autism-faq.json          worker/public/worker-index/
                (committed)                        (committed)
```

`corpus/*.jsonl` and `index.pkl` are gitignored intermediates: rebuilt from
the two public APIs each time, thrown away afterwards. Both APIs are free,
need no key, and receive nothing but search terms.

`.github/workflows/refresh-corpus.yml` runs all of this on the 1st of each
month and commits the two outputs with `[skip ci]`. Because the Worker's
deployment is connected to this repository, committing a new
`worker-index/` redeploys the Worker with the new corpus — the page data
and the live search never drift apart.

## Flow 2 — answering a question (live)

```
reader picks a prepared question, or types one (max 300 chars)
   │
   ▼  autism.js  POST {question}
Worker /api/ask   (CORS: sensayantan.com, sensayantan.github.io + localhost; 20 / IP / minute)
   │  1. embed the question — Workers AI @cf/baai/bge-small-en-v1.5
   │     (must be the same model that built the index, or every score is noise;
   │      search.js refuses to run if docs.json names a different model)
   │  2. dot-product against 1,900 vectors held in memory; keep the top 4
   │     scoring ≥ 0.56 — no vector database, it is a 2.8 MB flat file
   │  3. nothing cleared the floor → return no answer; the model is never
   │     asked to answer from zero sources
   │  4. otherwise a text model (TEXT_MODEL in worker/wrangler.jsonc)
   │     summarises only those 4 records, citing them by number; if the
   │     summariser fails, the ranked sources are still returned without it
   ▼
{summary, results}  →  autism.js renders the summary + numbered sources
```

If the Worker fails, a **prepared** question falls back to its stored
entry in `data/autism-faq.json` — the same ranked sources, labelled as
stored, without a summary. A **typed** question has no fallback and shows
the error.

## Scores and thresholds

Two scoring scales appear, and they are not interchangeable:

| | Offline (sentence-transformers) | Live (Workers AI) |
|---|---|---|
| Relevance floor | `MIN_SCORE = 0.63` in `rag/build_page_data.py` | `MIN_SCORE = 0.56` in `worker/src/search.js` |
| "Strong match" | ≥ 0.80 | ≥ 0.735 |
| "Moderate match" | ≥ 0.72 | ≥ 0.655 |

Workers AI scores the same text about 0.065 lower than the local model
(0.742 vs 0.812 on "is autism genetic"), so the live bands are the offline
ones shifted by that offset. The offline numbers come from
`rag/calibrate.py`, measured on the first real corpus: off-topic questions
peaked at 0.586 and on-topic ones bottomed at 0.712, a clear gap for a
cutoff to sit in. The bands live in `SCORE_SCALES` in `autism.js`.

## What it deliberately does not do

- It is not MCP and not an agent: the browser POSTs JSON to an ordinary
  HTTP API.
- It does not rank papers by quality or check them against clinical
  consensus. A similarity score measures closeness to the question, not
  trustworthiness.
- It stores no questions and tracks no one. The rate limit uses a
  short-lived per-IP counter in Cloudflare's cache.
- It does not yet include CDC prevalence figures (there is no API; they
  would be hand-curated with citations) — a backlog item.

## Run it locally

```
cd MyExperiment/rag
pip install -r requirements.txt
python3 fetch_pubmed.py
python3 fetch_trials.py
python3 build_index.py
python3 query.py "is autism genetic"
python3 build_page_data.py
python3 export_worker_index.py
python3 test_parsers.py        # offline parser tests
```

Then serve the site (`python3 -m http.server 8000` from the repo folder)
and open `http://localhost:8000/MyExperiment/`.
Localhost is an allowed origin, so the live Worker answers there too.

## When it breaks

- **Only stored results, no summary**: the Worker is down or erroring.
  `GET https://sayantansen-autism-search.sen-sayantan.workers.dev/api/health`
  reports whether the index loaded and which text model is live. A retired
  Workers AI model is the usual cause: update `TEXT_MODEL` in
  `worker/wrangler.jsonc`.
- **Worker build fails after a push**: its Cloudflare build **root
  directory** must be `MyExperiment/worker`.
- **Live and stored results disagree wildly**: the Worker's embedding model
  no longer matches the one that built the index — see "Check the
  embeddings actually match" in [`worker/README.md`](worker/README.md).
