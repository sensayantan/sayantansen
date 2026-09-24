#!/usr/bin/env python3
"""
Verifies every reference to assets/css/style.css and assets/js/*.js uses
the same ?v=N cache-buster. Run this after any change to either, before
committing — it exists because this exact mismatch has shipped as a real
bug more than once (see references/css-cache-busting.md).

CSS and JS share one counter on purpose. Two would be one more thing to
forget, and there is no benefit to versioning them separately here.

JS was unversioned until a cached autism.js kept serving an empty
ASK_ENDPOINT after the real one had shipped, leaving the page insisting the
search was "not connected" when it was. A stale stylesheet looks wrong; a
stale script makes a feature invisible.

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
PATTERN = re.compile(r"assets/(?:css/style\.css|js/[a-z-]+\.js)\?v=(\d+)")

# Any file that can reference the stylesheet or a script: top-level pages,
# every generated blog post, and the template that generates them.
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


UNVERSIONED = re.compile(r'(?:src|href)="(?:\.\./)?assets/(?:js/[a-z-]+\.js|css/style\.css)"')


def find_unversioned() -> dict[Path, int]:
    """A reference with no ?v= at all matches nothing above, so it would
    otherwise pass silently — which is how JS went unversioned for so long."""
    missing: dict[Path, int] = {}
    for pattern in CANDIDATE_GLOBS:
        for path in ROOT.glob(pattern):
            count = len(UNVERSIONED.findall(path.read_text(errors="ignore")))
            if count:
                missing[path] = count
    return missing


def main() -> int:
    unversioned = find_unversioned()
    if unversioned:
        print("MISSING — these reference an asset with no ?v= cache-buster at all:")
        for path, count in sorted(unversioned.items()):
            print(f"  {path.relative_to(ROOT)}: {count} reference(s)")
        return 1

    found = find_versions()
    if not found:
        print("No versioned asset references found — is this being run from the repo root context?")
        return 1

    all_versions = {v for versions in found.values() for v in versions}
    if len(all_versions) == 1:
        print(f"OK — every reference uses ?v={all_versions.pop()} ({len(found)} files checked).")
        return 0

    print("MISMATCH — not every file uses the same asset version:")
    for path, versions in sorted(found.items()):
        rel = path.relative_to(ROOT)
        print(f"  {rel}: {', '.join(sorted(set(versions)))}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
