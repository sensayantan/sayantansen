"""
Builds a TF-IDF retrieval index over corpus/seed_corpus.jsonl.

This is the "embeddings" step of a RAG pipeline, using TF-IDF vectors
instead of dense neural embeddings. TF-IDF was chosen for this experiment
specifically because this environment cannot reach huggingface.co to
download a real sentence-embedding model, and TF-IDF needs no network
access or paid API at all — it teaches the same downstream mechanics
(vectorize corpus, vectorize query, cosine similarity, rank by score).

Trade-off to know: TF-IDF matches on shared vocabulary, not meaning — it
won't connect "why does autism happen" to a document about "etiology" or
"genetic factors" unless those exact words overlap somewhere. Swapping in
real dense embeddings later (locally, once run somewhere HF Hub is
reachable, or via a paid embeddings API) is the natural upgrade and
wouldn't require changing query.py's retrieval logic at all — only how
`vectorizer.transform(...)` is computed.

Run manually:
    python3 build_index.py

Writes index.pkl (vectorizer + matrix + document metadata) alongside this
script. query.py loads that file — re-run this after editing the corpus.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parent
CORPUS_PATH = ROOT / "corpus" / "seed_corpus.jsonl"
INDEX_PATH = ROOT / "index.pkl"


def load_corpus() -> list[dict]:
    docs = []
    with CORPUS_PATH.open() as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    return docs


def main() -> None:
    docs = load_corpus()
    texts = [f"{d['title']}. {d['text']}" for d in docs]

    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(texts)

    with INDEX_PATH.open("wb") as f:
        pickle.dump({"vectorizer": vectorizer, "matrix": matrix, "docs": docs}, f)

    print(f"Indexed {len(docs)} documents -> {INDEX_PATH}")
    print(f"Vocabulary size: {len(vectorizer.vocabulary_)}")


if __name__ == "__main__":
    main()
