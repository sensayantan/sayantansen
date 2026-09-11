"""
Renders content/about.yml (edited via the Decap admin at /admin, under
"About Me Page") into data/about.json, which assets/js/about.js fetches
to populate index.html's three sections: About Me, My Family / My World,
and My Professional Journey.

Run manually:
    python backend/render_about.py

In production this runs automatically via
.github/workflows/render-content.yml whenever content/about.yml changes.
"""

from __future__ import annotations

import json
from pathlib import Path

import markdown as markdown_lib
import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = ROOT / "content" / "about.yml"
DATA_PATH = ROOT / "data" / "about.json"


def to_html(markdown_text: str) -> str:
    return markdown_lib.markdown((markdown_text or "").strip())


def main() -> None:
    data = yaml.safe_load(SOURCE_PATH.read_text()) or {}

    output = {
        "about_intro_html": to_html(data.get("about_intro", "")),
        "profile_photos": data.get("profile_photos") or [],
        "professional_journey_html": to_html(data.get("professional_journey", "")),
        "personal_journey_html": to_html(data.get("personal_journey", "")),
        "family_intro_html": to_html(data.get("family_intro", "")),
        "family_photos": data.get("family_photos") or [],
    }

    DATA_PATH.write_text(json.dumps(output, indent=2))
    print(f"Wrote {DATA_PATH}")


if __name__ == "__main__":
    main()
