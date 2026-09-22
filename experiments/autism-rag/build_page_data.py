"""
Precomputes retrieval results for a fixed list of questions and writes
them to data/autism-faq.json, which autism.html displays.

Why precompute: the site is static (GitHub Pages), so there is no server to
embed a question when a visitor clicks. Because the page offers a fixed
dropdown rather than free-text input, running retrieval offline and shipping
the results as JSON gives identical output with no backend at all. Accepting
free-text questions is the step that forces a real backend.

The scores in that JSON are the real cosine similarities from the same index
query.py uses — nothing is hand-written or rounded up. Each result carries
the source_url of the actual paper or trial, so every claim on the page is
traceable to something a reader can open.

Run manually (after build_index.py):
    python3 build_index.py
    python3 build_page_data.py

Then commit the regenerated data/autism-faq.json — that file, not index.pkl,
is what the site actually serves.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from query import load_index, search_many

ROOT = Path(__file__).resolve().parent
SITE_ROOT = ROOT.parent.parent
OUTPUT_PATH = SITE_ROOT / "data" / "autism-faq.json"

TOP_K = 4
MAX_AUTHORS = 3

# Dense embeddings never score a pair at zero the way TF-IDF did, so a
# "score > 0" filter would let anything through. This floor drops results
# that rank top-k only because nothing better existed.
#
# TUNE THIS. The right value depends on the model and on the corpus, and it
# can only be set by reading real output: run query.py on a question the
# corpus genuinely cannot answer ("what is the capital of France"), see what
# the top score is, and set the floor just above it.
MIN_SCORE = 0.0

# Phrased the way someone might actually ask, not the way papers are titled —
# which is the point of switching to embeddings. With TF-IDF these failed
# whenever the asker's words and the document's words differed.
QUESTIONS = [
    "Is autism genetic?",
    "Do vaccines cause autism?",
    "How is autism prevalence changing over time?",
    "What screening tools are used for toddlers?",
    "How effective is parent-mediated early intervention?",
    "Why are more boys diagnosed with autism than girls?",
    "What do studies say about sleep problems in autistic children?",
    "Are there biomarkers for early autism diagnosis?",
    "What research exists on autistic adults?",
    "What clinical trials are studying autism therapies?",
    "How do autistic children experience sensory differences?",
]


def format_authors(authors: list[str]) -> str:
    if not authors:
        return ""
    if len(authors) <= MAX_AUTHORS:
        return ", ".join(authors)
    return ", ".join(authors[:MAX_AUTHORS]) + " et al."


def corpus_meta() -> dict:
    """Provenance for the page to display.

    The page reads this to describe its own corpus honestly: which model
    embedded it, how many documents, from where. Its presence is also how
    autism.html tells real sourced results apart from the old placeholder
    corpus, so the warning banner stays true to whatever is on the page.
    """
    index = load_index()
    counts: dict[str, int] = {}
    for doc in index["docs"]:
        counts[doc["source"]] = counts.get(doc["source"], 0) + 1
    return {
        "model": index["model_name"],
        "generated": date.today().isoformat(),
        "document_count": len(index["docs"]),
        "counts": counts,
    }


def main() -> None:
    all_results = search_many(QUESTIONS, TOP_K)

    entries = []
    for question, results in zip(QUESTIONS, all_results):
        entries.append({
            "question": question,
            "results": [
                {
                    "score": round(score, 3),
                    "title": doc["title"],
                    "text": doc["text"],
                    "source": doc["source"],
                    "source_url": doc["source_url"],
                    "publication_date": doc.get("publication_date", ""),
                    "authors": format_authors(doc.get("authors") or []),
                    "venue": doc.get("venue", ""),
                }
                for score, doc in results
                if score >= MIN_SCORE
            ],
        })

    payload = {"meta": corpus_meta(), "questions": entries}
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2))
    total = sum(len(e["results"]) for e in entries)
    print(f"Wrote {OUTPUT_PATH} ({len(entries)} questions, {total} results)")
    print("Commit that file to publish the change.")


if __name__ == "__main__":
    main()
