"""
Measures where the score threshold should sit, instead of guessing it.

Dense embeddings do not score unrelated text near zero the way TF-IDF did,
so "score > 0" is not a usable filter. But the right cutoff cannot be read
off the model card either — it depends on this corpus. A corpus about one
narrow topic has a high floor, because even an irrelevant question retrieves
*something* topical.

So this measures it. It runs the questions the page actually asks, plus a
set of deliberately unrelated ones, and reports the gap between them:

  - off-topic ceiling : the best score an irrelevant question can reach.
                        Anything at or below this is indistinguishable from
                        having found nothing.
  - on-topic floor    : the worst score a question the corpus *can* answer
                        gets. A real cutoff has to sit below this.

If those two overlap, no single threshold separates signal from noise, and
the corpus needs to grow rather than the threshold needing tuning.

Run manually (after build_index.py):
    python3 calibrate.py
"""

from __future__ import annotations

import statistics

from build_page_data import QUESTIONS
from query import search_many

# Chosen to share no vocabulary *and* no subject matter with autism
# research — including the physical-activity and geography overlaps that
# made earlier spot-checks read higher than they should have.
OFF_TOPIC = [
    "how do I replace a bicycle tyre",
    "what is the capital of France",
    "best recipe for chocolate cake",
    "how does a diesel engine work",
    "who won the 1983 cricket world cup",
    "what is the exchange rate for the yen",
]


def top_scores(questions: list[str]) -> list[float]:
    return [results[0][0] if results else 0.0 for results in search_many(questions, 1)]


def report(label: str, questions: list[str], scores: list[float]) -> None:
    print(f"\n{label}")
    print("-" * len(label))
    for question, score in sorted(zip(questions, scores), key=lambda pair: -pair[1]):
        print(f"  {score:.3f}  {question}")


def main() -> None:
    on_scores = top_scores(QUESTIONS)
    off_scores = top_scores(OFF_TOPIC)

    report("On-topic (what the page asks)", QUESTIONS, on_scores)
    report("Off-topic (nothing in the corpus answers these)", OFF_TOPIC, off_scores)

    off_ceiling = max(off_scores)
    on_floor = min(on_scores)
    gap = on_floor - off_ceiling

    print("\nSummary")
    print("-------")
    print(f"  off-topic ceiling : {off_ceiling:.3f}  (max of {len(off_scores)})")
    print(f"  on-topic floor    : {on_floor:.3f}  (min of {len(on_scores)})")
    print(f"  on-topic median   : {statistics.median(on_scores):.3f}")
    print(f"  on-topic best     : {max(on_scores):.3f}")
    print(f"  separation        : {gap:+.3f}")

    print("\nSuggested settings")
    print("------------------")
    if gap <= 0:
        print("  The bands overlap — an irrelevant question scores as well as a")
        print("  relevant one. No threshold fixes that; the corpus needs more")
        print("  documents, or the questions need to match what it actually covers.")
        return

    # Sit the cutoff in the gap, nearer the noise side so a genuinely weak
    # but real match is shown rather than silently dropped.
    min_score = off_ceiling + gap * 0.35
    strong = statistics.median(on_scores)
    moderate = min_score + (strong - min_score) / 2

    print(f"  build_page_data.py   MIN_SCORE = {min_score:.2f}")
    print(f"  autism.js            strong match  >= {strong:.2f}")
    print(f"                       moderate      >= {moderate:.2f}")
    print("                       weak          below that")


if __name__ == "__main__":
    main()
