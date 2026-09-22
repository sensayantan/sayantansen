# Autism RAG experiment — retrieval mechanics, phase 1

A learning experiment: the retrieval half of a RAG (retrieval-augmented
generation) pipeline, built over a small seed corpus about autism.

**What this is not yet:** a chatbot, a real knowledge base, or anything
user-facing. It's not wired into the site. The corpus is ~17 short,
illustrative documents written from general knowledge to test the
pipeline mechanics — not scraped or verified real-world data. Before any
of this becomes a real feature parents would use, the corpus needs to be
replaced with sourced, verified, current content (CDC ADDM reports, DSM-5
citations, primary research), and the generation half (turning retrieved
text into an actual answer) needs careful, cited, "not medical advice"
framing given the audience and stakes.

## Why TF-IDF instead of real embeddings

This environment can't reach huggingface.co, so downloading a real
sentence-embedding model wasn't an option here. TF-IDF (via scikit-learn)
needs no network access and no paid API, and it teaches the identical
downstream mechanics real embeddings use: vectorize the corpus, vectorize
the question, rank by cosine similarity. The limitation is real, though:
TF-IDF matches shared vocabulary, not meaning.

That limitation showed up immediately in testing — see below.

## Run it

```
cd experiments/autism-rag
python3 build_index.py          # rebuild after editing corpus/seed_corpus.jsonl
python3 query.py "is autism genetic"
python3 query.py "how many kids get diagnosed with autism" --top-k 5
```

## What testing actually showed

- `"is autism genetic"` and `"do vaccines cause autism"` both correctly
  surfaced the right document first, with a clear score gap over the
  next-best match.
- `"how many kids get diagnosed with autism"` — a natural way a parent
  might actually phrase the question — ranked the *actual* prevalence
  document **third**, behind two documents that happened to repeat
  "diagnosed"/"diagnosis" more densely. This is TF-IDF's core weakness in
  action: it can't tell that "how many kids get diagnosed" and "US autism
  prevalence" mean the same thing, only that they share fewer words than
  it expected.
- A question with no real match in the corpus (`"what is the capital of
  France"`) correctly returned nothing, rather than confidently returning
  a wrong document — worth confirming this holds for any future retrieval
  approach too.

## Next steps, in order

1. Grow the corpus with real, sourced content (CDC ADDM, DSM-5-TR,
   PubMed abstracts) instead of illustrative seed text.
2. Swap TF-IDF for real dense embeddings once run somewhere HF Hub is
   reachable (locally, or via a paid embeddings API) — `query.py`'s
   ranking logic (cosine similarity over vectors) doesn't need to change,
   only how the vectors themselves get computed.
3. Only after retrieval is trustworthy: add a generation step that feeds
   top-k retrieved chunks to an LLM to answer in plain language, with
   citations back to source documents and explicit "not medical advice"
   framing — given the audience (parents navigating a new diagnosis),
   ungrounded or uncited answers are a real harm risk, not just a quality
   issue.
