"""
Generates data/news.json for the "Today's News" page.

Not implemented yet — this is a placeholder for the AI content-generation
step. Once the detailed content prompt (what to fetch, which categories,
tone, sourcing rules) is defined, this script will:

  1. Call an LLM API (Claude or OpenAI, chosen by AI_PROVIDER below) to
     research/summarize the day's news for each category.
  2. Shape the result into the schema in data/news.json (see "sections"
     and "stats").
  3. Overwrite data/news.json so the frontend picks it up automatically.

Run manually for now:
    python backend/generate_news.py

Later this can be scheduled (e.g. a daily cron job or GitHub Action) to
regenerate the file every morning.
"""

import json
import os
from pathlib import Path

AI_PROVIDER = os.environ.get("AI_PROVIDER", "anthropic")  # "anthropic" or "openai"
NEWS_JSON_PATH = Path(__file__).resolve().parent.parent / "data" / "news.json"


def generate() -> dict:
    """TODO: call the chosen provider's API and build the news payload."""
    raise NotImplementedError("Content-generation logic not implemented yet.")


def main() -> None:
    data = generate()
    NEWS_JSON_PATH.write_text(json.dumps(data, indent=2))
    print(f"Wrote {NEWS_JSON_PATH}")


if __name__ == "__main__":
    main()
