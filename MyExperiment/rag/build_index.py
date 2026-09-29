"""
Builds a dense-embedding retrieval index over everything in corpus/*.jsonl.

This replaces the earlier TF-IDF index. TF-IDF matched on shared vocabulary,
so "how many kids get diagnosed" failed to find the prevalence document —
the words didn't overlap. A sentence-embedding model maps text to a vector
by *meaning*, so wording no longer has to match.

The model runs locally on the CPU. Nothing is sent to a paid API; the model
file is downloaded once from Hugging Face (~130 MB) and cached in
~/.cache/huggingface afterwards.

On the model choice: all-MiniLM-L6-v2 is the usual first suggestion, but it
truncates input at 256 word-pieces — shorter than a typical PubMed abstract,
which would silently drop the tail of roughly half the corpus. bge-small-en
is the same size class and dimensionality with a 512-token window, which
covers a normal abstract whole. That also means no chunking step is needed
here; if full-text papers are added later, they will need one.

bge models expect a short instruction prefix on the *query* only, never on
the stored documents. That prefix is written into index.pkl so query.py
cannot drift out of sync with whatever model built the index.

Run manually (after fetching a corpus):
    python3 fetch_pubmed.py
    python3 fetch_trials.py
    python3 build_index.py

Writes index.pkl (model name, query prefix, embedding matrix, documents)
alongside this script. Re-run it after any change to corpus/.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
CORPUS_DIR = ROOT / "corpus"
INDEX_PATH = ROOT / "index.pkl"

MODEL_NAME = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
BATCH_SIZE = 64

REQUIRED_KEYS = {"id", "source", "title", "text", "source_url"}


def load_corpus() -> list[dict]:
    """Reads every corpus/*.jsonl file into one list of documents.

    Each fetch script owns its own file, so adding a source later means
    dropping in another .jsonl — no change here.
    """
    paths = sorted(CORPUS_DIR.glob("*.jsonl"))
    if not paths:
        raise SystemExit(
            f"No corpus files in {CORPUS_DIR}.\n"
            "Fetch some first:  python3 fetch_pubmed.py  &&  python3 fetch_trials.py"
        )

    docs: list[dict] = []
    seen_ids: set[str] = set()
    for path in paths:
        count = 0
        with path.open() as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                doc = json.loads(line)
                missing = REQUIRED_KEYS - set(doc)
                if missing:
                    raise SystemExit(f"{path.name}:{line_number} is missing {sorted(missing)}")
                if doc["id"] in seen_ids:
                    continue  # same record reachable from two searches
                seen_ids.add(doc["id"])
                docs.append(doc)
                count += 1
        print(f"  {path.name}: {count} documents")
    return docs


def embed(docs: list[dict]) -> tuple[np.ndarray, str]:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise SystemExit(
            "sentence-transformers is not installed.\n"
            "  pip install -r requirements.txt"
        )

    print(f"Loading {MODEL_NAME} (first run downloads ~130 MB, then it is cached)...")
    model = SentenceTransformer(MODEL_NAME)

    # Title first: it is the densest summary of what a record is about, and
    # carries real weight in the pooled vector.
    texts = [f"{d['title']}. {d['text']}" for d in docs]

    print(f"Embedding {len(texts)} documents on CPU — this takes a few minutes...")
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        # Unit-length vectors mean cosine similarity is a plain dot product,
        # so query.py needs no normalisation step of its own.
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    return np.asarray(embeddings, dtype=np.float32), MODEL_NAME


def main() -> None:
    docs = load_corpus()
    print(f"Loaded {len(docs)} unique documents\n")

    embeddings, model_name = embed(docs)

    with INDEX_PATH.open("wb") as f:
        pickle.dump(
            {
                "model_name": model_name,
                "query_prefix": QUERY_PREFIX,
                "embeddings": embeddings,
                "docs": docs,
            },
            f,
        )

    by_source: dict[str, int] = {}
    for doc in docs:
        by_source[doc["source"]] = by_source.get(doc["source"], 0) + 1

    print(f"\nIndexed {len(docs)} documents -> {INDEX_PATH}")
    print(f"Embedding matrix: {embeddings.shape[0]} x {embeddings.shape[1]} float32 "
          f"({embeddings.nbytes / 1_048_576:.1f} MB)")
    for source, count in sorted(by_source.items()):
        print(f"  {source}: {count}")
    print("\nNext: python3 query.py \"is autism genetic\"")


if __name__ == "__main__":
    main()
