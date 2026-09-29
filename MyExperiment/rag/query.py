"""
Retrieves the top-k most relevant documents for a question, using the
dense-embedding index built by build_index.py.

This is the "retrieval" half of RAG. It deliberately stops before the
"generation" half (feeding retrieved text to an LLM to write an answer),
so what comes back is the stored records themselves — real papers and
trials, each with a URL you can open and check.

The index and the model are loaded once per process and reused, and
search_many() embeds a whole list of questions in a single batch. That
matters now in a way it did not with TF-IDF: loading a neural model costs
a couple of seconds, so build_page_data.py would pay it eleven times over
if every call re-loaded.

Run manually:
    python3 query.py "is autism genetic"
    python3 query.py "how many kids get diagnosed with autism" --top-k 5
"""

from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / "index.pkl"

_index: dict | None = None
_model = None


def load_index() -> dict:
    global _index
    if _index is None:
        if not INDEX_PATH.exists():
            raise SystemExit("No index found — run build_index.py first.")
        with INDEX_PATH.open("rb") as f:
            _index = pickle.load(f)
        if "embeddings" not in _index:
            raise SystemExit(
                "index.pkl was built by the old TF-IDF script — rebuild it:\n"
                "  python3 build_index.py"
            )
    return _index


def load_model():
    """Loads the same model the index was built with, named inside index.pkl.

    Reading the name from the index rather than hardcoding it here is what
    stops a query being embedded by a different model than the documents —
    which produces plausible-looking scores that are entirely meaningless.
    """
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise SystemExit("sentence-transformers is not installed.\n  pip install -r requirements.txt")
        _model = SentenceTransformer(load_index()["model_name"])
    return _model


def search_many(questions: list[str], top_k: int) -> list[list[tuple[float, dict]]]:
    """Ranks the corpus against each question. One batch, one model load."""
    index = load_index()
    prefix = index.get("query_prefix", "")

    query_vecs = load_model().encode(
        [prefix + q for q in questions],
        normalize_embeddings=True,
    )

    # Both sides are unit-length, so this dot product *is* cosine similarity.
    scores = np.asarray(query_vecs, dtype=np.float32) @ index["embeddings"].T

    results = []
    for row in scores:
        top = np.argsort(-row)[:top_k]
        results.append([(float(row[i]), index["docs"][i]) for i in top])
    return results


def search(question: str, top_k: int) -> list[tuple[float, dict]]:
    return search_many([question], top_k)[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("question", help="The question to search the corpus for")
    parser.add_argument("--top-k", type=int, default=3, help="How many results to show (default: 3)")
    args = parser.parse_args()

    results = search(args.question, args.top_k)
    print(f'Query: "{args.question}"\n')

    for rank, (score, doc) in enumerate(results, start=1):
        date = doc.get("publication_date") or "undated"
        print(f"#{rank}  score={score:.3f}  [{doc['source']}]  {date}")
        print(f"    {doc['title']}")
        snippet = doc["text"][:220]
        print(f"    {snippet}{'...' if len(doc['text']) > 220 else ''}")
        print(f"    {doc['source_url']}")
        print()


if __name__ == "__main__":
    main()
