"""
Precomputes retrieval results for a fixed list of questions and writes
them to data/autism-faq.json, which autism.html displays.

Why precompute: the site is static (GitHub Pages), so there's no server
to run TF-IDF retrieval when a visitor clicks. Because the page offers a
fixed dropdown of questions rather than free-text input, running the
retrieval offline and shipping the results as JSON gives the identical
output with no backend at all.

The scores in that JSON are the real cosine-similarity scores from the
same index query.py uses — nothing is hand-written or rounded up.

Run manually (after build_index.py):
    python3 build_index.py
    python3 build_page_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

from query import search

ROOT = Path(__file__).resolve().parent
SITE_ROOT = ROOT.parent.parent
OUTPUT_PATH = SITE_ROOT / "data" / "autism-faq.json"
TOP_K = 3

# Phrased the way a parent might actually ask, not the way the corpus is
# worded — which is the point: it shows where keyword matching holds up
# and where it doesn't.
QUESTIONS = [
    "Is autism genetic?",
    "Do vaccines cause autism?",
    "How common is autism?",
    "At what age is autism usually diagnosed?",
    "What are the diagnostic criteria for autism?",
    "What screening tools are used to check for autism?",
    "Who can formally diagnose autism?",
    "What early intervention therapies are available?",
    "Is autism caused by parenting?",
    "Why are more boys diagnosed with autism than girls?",
    "Are autism and intellectual disability the same thing?",
]


def main() -> None:
    entries = []
    for question in QUESTIONS:
        results = search(question, TOP_K)
        entries.append(
            {
                "question": question,
                "results": [
                    {
                        "score": round(float(score), 3),
                        "title": doc["title"],
                        "category": doc["category"],
                        "text": doc["text"],
                        "source_note": doc["source_note"],
                    }
                    for score, doc in results
                    if score > 0
                ],
            }
        )

    OUTPUT_PATH.write_text(json.dumps({"questions": entries}, indent=2))
    print(f"Wrote {OUTPUT_PATH} ({len(entries)} questions)")


if __name__ == "__main__":
    main()
