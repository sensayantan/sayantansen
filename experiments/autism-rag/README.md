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

```
cd experiments/autism-rag
pip install -r requirements.txt

python3 fetch_pubmed.py          # -> corpus/pubmed.jsonl   (~1500 records)
python3 fetch_trials.py          # -> corpus/trials.jsonl   (~400 records)
python3 build_index.py           # -> index.pkl  (downloads the model once, ~130 MB)
python3 query.py "is autism genetic"
python3 build_page_data.py       # -> ../../data/autism-faq.json
```

Only `data/autism-faq.json` needs committing — that is what the site serves.
`index.pkl` is gitignored (derived, and a pickle is not a good repo artifact).

`python3 test_parsers.py` checks the XML and JSON parsing against fixtures
with no network access. Run it after touching either fetch script.

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

## Things to check when you first run it

- **Scores sit in a narrow, high band.** Unlike TF-IDF, dense embeddings
  rarely score anything near zero — unrelated text still lands around 0.6.
  Run `python3 query.py "what is the capital of France"` and see what the top
  score is. That number is your noise floor; set `MIN_SCORE` in
  `build_page_data.py` just above it, and re-check the bands in
  `scoreLabel()` in `assets/js/autism.js`. Both currently hold estimates.
- **The meaning-vs-words upgrade should be visible.** The question that
  failed under TF-IDF was "how many kids get diagnosed with autism", which
  ranked the actual prevalence document third. Semantically similar
  rephrasings should now rank together.

## Next steps, in order

1. Tune `MIN_SCORE` and the score bands against real output (above).
2. Hand-curate CDC ADDM prevalence figures with per-row citations.
3. Only after retrieval is trustworthy: add a generation step that feeds
   top-k retrieved records to an LLM to answer in plain language, with
   inline citations back to the source URLs and explicit "not medical
   advice" framing. Given the audience — parents navigating a new diagnosis
   — an ungrounded or uncited answer is a real harm, not a quality issue.
4. Free-text questions need a backend (GitHub Pages cannot embed a query at
   request time). Cloudflare Workers + Vectorize is the natural fit, since
   the OAuth proxy already runs there.
