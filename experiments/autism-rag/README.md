# Autism RAG experiment — phase 2: real sources, real embeddings

The retrieval half of a RAG pipeline, built over autism research fetched
from public registries and indexed with a sentence-embedding model.

## What changed from phase 1

Phase 1 was a working pipeline over fake data. Two things were wrong with
it, and both are fixed here:

| | Phase 1 | Phase 2 |
|---|---|---|
| Corpus | 17 documents written from general knowledge — no URLs, nothing citable | Real PubMed abstracts + ClinicalTrials.gov records, each with a source URL |
| Vectors | TF-IDF (matches shared words) | `BAAI/bge-small-en-v1.5` (matches meaning) |

The first row is the one that mattered. The old corpus looked plausible and
was not verifiable — the prevalence figures in it were approximate
recollections, not readings from a CDC report. Every record now links to a
page you can open and check.

## How the whole thing fits together

Three different computers run code in this project, and it is worth being
precise about which does what, because the same Python runs in two of them.

| Where | Runs | When |
|---|---|---|
| Your Mac | the fetch / embed / export scripts | whenever you run them by hand |
| GitHub Actions | the exact same scripts | 1st of each month, unattended |
| Cloudflare Worker | `autism-search/` | every time a visitor types a question |

The first two are interchangeable — GitHub Actions is just a machine that
runs the scripts for you so you do not have to. The third is different in
kind, and the reason it exists is below.

### What is produced, and what is kept

```
fetch_pubmed.py  ──▶ corpus/pubmed.jsonl  ─┐
fetch_trials.py  ──▶ corpus/trials.jsonl  ─┴─▶ build_index.py ──▶ index.pkl
                                                                     │
                            ┌────────────────────────────────────────┴───────┐
                            ▼                                                ▼
                  build_page_data.py                            export_worker_index.py
                            │                                                │
                            ▼                                                ▼
                  data/autism-faq.json                   autism-search/public/worker-index/
                  (committed)                                         (committed)
```

Only the two bottom boxes are committed. `corpus/*.jsonl` and `index.pkl`
are gitignored **intermediates** — on a GitHub Actions run they are built
inside the runner and thrown away when it shuts down. Nothing is lost,
because they can always be rebuilt from the same two APIs.

So yes: `refresh-corpus.yml` does build `index.pkl` out of `pubmed.jsonl`
and `trials.jsonl`. But `index.pkl` is not the deliverable — it is a step on
the way to the two files that are, and it does not survive the run that made
it.

### Why a Cloudflare Worker is needed at all

GitHub Pages is a file server. It hands out `.html`, `.css`, `.js` and
`.json` exactly as they sit in the repo. It cannot run code.

That is fine for the prepared questions, because their answers were computed
in advance: `build_page_data.py` ran all eleven questions through the index
on a machine that *could* run Python, and wrote the results to
`data/autism-faq.json`. The browser just downloads that file. No server is
involved because no thinking happens at request time.

A question someone types cannot work that way, because nobody knew the
question in advance. The moment it is submitted, something has to:

1. turn that sentence into 384 numbers, which means running an embedding model
2. compare it against 1900 stored vectors
3. hand the best matches to a language model to summarise

None of that is a file that can be served. It is computation that has to
happen *when the request arrives*, on a computer that is awake and listening.
GitHub Pages has no such computer. Cloudflare Workers is one.

Cloudflare specifically, rather than any other host:

- it is free at this volume, and Workers AI covers both the embedding model
  and the summarising model on the free allowance
- the site already has a Worker (`oauth-proxy/`), so it is a familiar deploy
  rather than a new platform
- Workers do not sleep, so there is no 30-second cold start on the first
  question after a quiet night, which a free-tier container host would have

### Two paths a question can take

```
Prepared question (dropdown)
  browser ──▶ data/autism-faq.json  (a static file on GitHub Pages)
  no server, no cost, answer already computed

Typed question (free text)
  browser ──▶ Cloudflare Worker ──▶ Workers AI  (embed the question)
                               ──▶ vectors.bin  (rank 1900 documents)
                               ──▶ Workers AI  (summarise the top 4)
  computed live, per question
```

Both render into the same page. The dropdown keeps working whether or not
the Worker exists, which is why `ASK_ENDPOINT` in `assets/js/autism.js`
ships empty — an undeployed or broken Worker hides the text box instead of
breaking the page.

### This is not MCP

MCP (Model Context Protocol) is a way to hand tools to an AI assistant
during a conversation — it is how Claude Code reaches this GitHub repo, for
instance. Nothing in this project uses it.

The Worker is an ordinary HTTP API. The browser POSTs JSON to a URL and gets
JSON back, the same mechanism a weather widget or a login form uses. The
fetch scripts are ordinary HTTP clients against NCBI and ClinicalTrials.gov.
The distinction that matters: MCP is for an AI calling out to tools, and
every call here is regular software calling a regular web API.

## Where the data comes from

Two free public HTTP APIs. No account, no API key, no cost, nothing sent to
a paid service.

- **PubMed** (`fetch_pubmed.py`) — NLM's biomedical literature database, via
  the E-utilities API. Two calls: `esearch` returns PMIDs for a search term,
  `efetch` returns those records as XML. Abstracts only; full text lives in
  PMC under per-article licensing and is out of scope.
- **ClinicalTrials.gov** (`fetch_trials.py`) — the US trials registry, via
  its v2 JSON API. Trials matter alongside papers because they describe what
  is being *tried* rather than what was found, and each record names the
  institutions running it — the closest free source of real centre locations.

Not yet included: **CDC ADDM prevalence figures**. There is no clean API for
those — they are published as tables in MMWR surveillance summaries. The
honest path is hand-curating that small set of numbers with a citation per
row, which is a separate piece of work.

## Run it

Run these one line at a time. Note there are no trailing `#` comments
below, on purpose: zsh (the default macOS shell) does not treat `#` as a
comment when typed interactively, so a pasted `# ~1500 records` is read as
a tilde expansion and the command fails with "no such user or named
directory".

```
cd experiments/autism-rag
pip install -r requirements.txt
python3 fetch_pubmed.py
python3 fetch_trials.py
python3 build_index.py
python3 query.py "is autism genetic"
python3 build_page_data.py
python3 export_worker_index.py
```

What each step produces:

| Step | Writes | Notes |
|---|---|---|
| `fetch_pubmed.py` | `corpus/pubmed.jsonl` | ~1500 abstracts, a few minutes |
| `fetch_trials.py` | `corpus/trials.jsonl` | ~400 trial records |
| `build_index.py` | `index.pkl` | downloads the model once (~130 MB), then embeds on CPU |
| `build_page_data.py` | `../../data/autism-faq.json` | what the prepared-question dropdown serves |
| `export_worker_index.py` | `../../autism-search/public/worker-index/` | what the Worker serves free-text questions from |

Only `data/autism-faq.json` needs committing — that is what the site serves.
`index.pkl` and `corpus/*.jsonl` are both gitignored: they are derived, they
total several megabytes, and re-running the fetch reproduces them.

## Running it without a terminal

`.github/workflows/refresh-corpus.yml` does all of the above on the 1st of
each month, and commits the regenerated `data/autism-faq.json` back to
`main` with `[skip ci]` — the same pattern `render-content.yml` uses for
admin-published content. It can also be started by hand from the repo's
Actions tab (Run workflow).

Two things it does that a local run does not need:

- Installs the CPU-only PyTorch wheel first. The default Linux wheel is the
  CUDA build, ~2.5 GB, on a runner with no GPU.
- Caches `~/.cache/huggingface` under a key naming the model, so the ~130 MB
  download happens once rather than monthly, and switching models misses the
  cache instead of silently reusing the wrong weights.

It also runs `calibrate.py` and prints the result. That is not a gate — it
is a record, so that if the separation between on-topic and off-topic scores
ever collapses as the corpus shifts, the log shows it.

`python3 test_parsers.py` checks the XML and JSON parsing against fixtures
with no network access. Run it after touching either fetch script.

`python3 calibrate.py` measures where the score cutoff should sit — see
below.

## On the model choice

`all-MiniLM-L6-v2` is the usual first suggestion and is the wrong default
here: it truncates at 256 word-pieces, shorter than a typical PubMed
abstract, so the tail of roughly half the corpus would be silently dropped.
`bge-small-en-v1.5` is the same size class and dimensionality (384) with a
512-token window, which fits a normal abstract whole. That also means no
chunking step is needed — if full-text papers get added later, one will be.

bge expects a short instruction prefix on the query and none on the stored
documents. That prefix is written into `index.pkl` so `query.py` can never
embed a query with different settings than the documents were embedded with;
that mistake produces plausible scores that mean nothing.

## Calibrating the score threshold

Run `python3 calibrate.py`. It scores the questions the page asks alongside
deliberately unrelated ones and reports the gap, then suggests values for
`MIN_SCORE` in `build_page_data.py` and the bands in `scoreLabel()` in
`assets/js/autism.js`. Both currently hold estimates.

Spot-checking a single off-topic question is not enough, and it is worth
knowing why. A corpus about one narrow topic has a high floor: asking "what
is the capital of France" returns a trial run in Paris, and asking about
bicycle tyres returns a cycling-and-autism trial, both scoring around 0.50.
That is the model working — it found the closest thing that exists — but it
means one probe measures topical adjacency rather than the true floor.
calibrate.py uses several unrelated questions and takes the ceiling.

Measured on the first real corpus (~1900 documents, bge-small-en-v1.5):

| | score |
|---|---|
| Off-topic ceiling | 0.586 |
| On-topic floor | 0.712 |
| On-topic median | 0.802 |
| On-topic best | 0.874 |
| **Separation** | **+0.126** |

Those gave `MIN_SCORE = 0.63`, and score bands of 0.80 (strong) and 0.72
(moderate), which are what the code now holds. The separation is what
matters: with a clear gap, one cutoff genuinely divides signal from noise.
Under TF-IDF there was no such gap — the failing case in phase 1 was a
relevant document scoring *below* irrelevant ones.
- **The meaning-vs-words upgrade should be visible.** The question that
  failed under TF-IDF was "how many kids get diagnosed with autism", which
  ranked the actual prevalence document third. Semantically similar
  rephrasings should now rank together.

## Next steps, in order

1. Run `calibrate.py` and apply the thresholds it suggests (above).
2. Hand-curate CDC ADDM prevalence figures with per-row citations.
3. Only after retrieval is trustworthy: add a generation step that feeds
   top-k retrieved records to an LLM to answer in plain language, with
   inline citations back to the source URLs and explicit "not medical
   advice" framing. Given the audience — parents navigating a new diagnosis
   — an ungrounded or uncited answer is a real harm, not a quality issue.
4. ~~Free-text questions need a backend.~~ Built: see `autism-search/`.
   A Cloudflare Worker embeds the question with Workers AI, brute-forces it
   against the exported vectors, and has a language model summarise the top
   matches with citations. No vector database — at 1900 documents a flat
   file in the Worker is both faster and free.
