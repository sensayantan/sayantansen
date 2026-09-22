"""
Retrieves the top-k most relevant documents for a question, using the
index built by build_index.py. This is the "retrieval" half of RAG —
it deliberately stops before the "generation" half (feeding retrieved
text to an LLM to write an answer), so you can inspect what gets
retrieved and why before trusting anything built on top of it.

Run manually:
    python3 query.py "why does autism happen"
    python3 query.py "how common is autism" --top-k 5
"""

from __future__ import annotations

import argparse
import pickle
from pathlib import Path

from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / "index.pkl"


def load_index() -> dict:
    if not INDEX_PATH.exists():
        raise SystemExit("No index found — run build_index.py first.")
    with INDEX_PATH.open("rb") as f:
        return pickle.load(f)


def search(question: str, top_k: int) -> list[tuple[float, dict]]:
    index = load_index()
    query_vec = index["vectorizer"].transform([question])
    scores = cosine_similarity(query_vec, index["matrix"])[0]

    ranked = sorted(zip(scores, index["docs"]), key=lambda x: x[0], reverse=True)
    return ranked[:top_k]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", help="The question to search the corpus for")
    parser.add_argument("--top-k", type=int, default=3, help="How many results to show (default: 3)")
    args = parser.parse_args()

    results = search(args.question, args.top_k)

    print(f'Query: "{args.question}"\n')
    if not results or results[0][0] == 0.0:
        print("No matching documents — try different wording (TF-IDF needs shared vocabulary, not just related meaning).")
        return

    for rank, (score, doc) in enumerate(results, start=1):
        print(f"#{rank}  score={score:.3f}  [{doc['category']}]  {doc['title']}")
        print(f"    {doc['text'][:200]}{'...' if len(doc['text']) > 200 else ''}")
        print(f"    source: {doc['source_note']}")
        print()


if __name__ == "__main__":
    main()
