#!/usr/bin/env python3
"""
Verifies every stylesheet reference to assets/css/style.css uses the same
?v=N cache-buster. Run this after any change to style.css, before
committing — it exists because this exact mismatch has shipped as a real
bug more than once (see references/css-cache-busting.md).

Usage:
    python3 .claude/skills/frontend-standards/scripts/check_css_version.py

Exits 0 and prints the single version in use if everything matches.
Exits 1 and lists every mismatched file:version pair otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PATTERN = re.compile(r"assets/css/style\.css\?v=(\d+)")

# Any file that can reference the stylesheet: top-level pages, every
# generated blog post, and the template that generates them.
CANDIDATE_GLOBS = ["*.html", "blogs/*.html", "backend/render_blogs.py"]


def find_versions() -> dict[Path, list[str]]:
    found: dict[Path, list[str]] = {}
    for pattern in CANDIDATE_GLOBS:
        for path in ROOT.glob(pattern):
            text = path.read_text(errors="ignore")
            matches = PATTERN.findall(text)
            if matches:
                found[path] = matches
    return found


def main() -> int:
    found = find_versions()
    if not found:
        print("No style.css?v=N references found — is this being run from the repo root context?")
        return 1

    all_versions = {v for versions in found.values() for v in versions}
    if len(all_versions) == 1:
        print(f"OK — every reference uses ?v={all_versions.pop()} ({len(found)} files checked).")
        return 0

    print("MISMATCH — not every file uses the same CSS version:")
    for path, versions in sorted(found.items()):
        rel = path.relative_to(ROOT)
        print(f"  {rel}: {', '.join(sorted(set(versions)))}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
