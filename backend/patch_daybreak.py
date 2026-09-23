"""
Re-applies this site's conventions to each Daybreak edition.

DAYBREAK/*.html is generated outside this repo (Codex writes it and a
scheduled job commits it). It is a separate design system with its own
inline CSS, so nothing in assets/css/style.css reaches it — and every
hand-edit made to an edition is lost the next morning when a fresh one
lands. That is why the same fixes kept "rolling back".

This script is the durable version of those fixes. It reads each edition,
applies three changes, and writes it back:

  1. Adds the "My Experiment" link to the site nav, which the generator
     does not know about.
  2. Moves the category links out of the DAYBREAK masthead into their own
     bar underneath it. Inline in the masthead they wrap into the brand
     and the edition date and read as clutter.
  3. Inserts the short note explaining how the brief is produced.

Every step checks for its own marker first, so running this twice is a
no-op and running it on an already-patched archive changes nothing.

Run manually:
    python3 backend/patch_daybreak.py

In production this runs automatically via
.github/workflows/render-content.yml whenever DAYBREAK/** changes, which
is what makes the changes survive a new edition.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAYBREAK_DIR = ROOT / "DAYBREAK"
SITE = "https://sensayantan.github.io/sayantansen"

EXPERIMENT_LINK = (
    f'<a href="{SITE}/autism.html">'
    '<svg viewBox="0 0 20 20"><path d="M7.5 3h5M9 3v5.5L4.5 16h11L11 8.5V3"/></svg>'
    "My Experiment</a>"
)

METHOD_NOTE = (
    '<p class="dbMethod"><strong>How this is made</strong> — OpenAI Codex, on a '
    "standard monthly subscription rather than paid API calls, collects each day's "
    "stories against a fixed list of topics I follow, pulls them together through "
    "MCP, and writes a single static HTML page. A scheduled job commits that page "
    "to GitHub and this site renders it. The aim is a brief that costs nothing to "
    "run and reads <em>across</em> sources rather than through one: every outlet "
    "carries a slant, so the useful version of a story is the one assembled from "
    "several.</p>"
)

EXTRA_CSS = """
.dbCategoryBar{display:flex;flex-wrap:wrap;gap:8px 18px;padding:13px 5%;background:#f4f6fa;border-bottom:1px solid #d7dce5}
.dbCategoryBar a{font-size:11.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;text-decoration:none;color:#46587a;white-space:nowrap}
.dbCategoryBar a:hover,.dbCategoryBar a:focus{color:#2759bd;text-decoration:underline}
.dbMethod{margin:0;padding:11px 5% 13px;background:#fff;border-bottom:1px solid #e6eaf1;font-size:11px;line-height:1.65;color:#6b7a94}
.dbMethod strong{color:#46587a}
@media(max-width:850px){.dbCategoryBar{gap:7px 13px;padding:11px 5%}.dbCategoryBar a{font-size:11px}}
"""


def add_experiment_link(html: str) -> tuple[str, bool]:
    """Adds the nav item the generator doesn't know about."""
    if "autism.html" in html:
        return html, False
    # Append inside the site nav, after its last link.
    match = re.search(r'(<nav class="siteNav"[^>]*>.*?)(</nav>)', html, re.S)
    if not match:
        return html, False
    return html[: match.start()] + match.group(1) + EXPERIMENT_LINK + match.group(2) + html[match.end():], True


def move_category_links(html: str) -> tuple[str, bool]:
    """Lifts the category nav out of the masthead into a bar below it."""
    if 'class="dbCategoryBar"' in html:
        return html, False
    # The masthead is <header class="top">brand + nav + edition</header>.
    header = re.search(r'<header class="top">(.*?)</header>', html, re.S)
    if not header:
        return html, False
    inner = header.group(1)
    nav = re.search(r"<nav>(.*?)</nav>", inner, re.S)
    if not nav:
        return html, False

    stripped_header = '<header class="top">' + inner.replace(nav.group(0), "") + "</header>"
    bar = f'<nav class="dbCategoryBar" aria-label="News categories">{nav.group(1)}</nav>'
    return html[: header.start()] + stripped_header + bar + html[header.end():], True


def add_method_note(html: str) -> tuple[str, bool]:
    """Puts the note directly below the masthead (and its category bar)."""
    if 'class="dbMethod"' in html:
        return html, False
    # Anchor on the category bar this script just inserted, falling back to
    # the masthead itself. Anchoring on what we control rather than on what
    # follows it means a generator that reorders the page later still lands
    # the note in the right place — the Sep-10 edition has no <section
    # class="mast"> at all, and a stricter anchor silently skipped it.
    bar = re.search(r'<nav class="dbCategoryBar".*?</nav>', html, re.S)
    if bar:
        return html[: bar.end()] + METHOD_NOTE + html[bar.end():], True
    header = re.search(r'<header class="top">.*?</header>', html, re.S)
    if header:
        return html[: header.end()] + METHOD_NOTE + html[header.end():], True
    return html, False


def add_css(html: str) -> tuple[str, bool]:
    if ".dbCategoryBar{" in html:
        return html, False
    if "</style>" not in html:
        return html, False
    return html.replace("</style>", EXTRA_CSS + "</style>", 1), True


def patch(path: Path) -> list[str]:
    html = path.read_text()
    applied = []
    for name, fn in (
        ("css", add_css),
        ("experiment-link", add_experiment_link),
        ("category-bar", move_category_links),
        ("method-note", add_method_note),
    ):
        html, changed = fn(html)
        if changed:
            applied.append(name)
    if applied:
        path.write_text(html)
    return applied


def main() -> None:
    if not DAYBREAK_DIR.exists():
        print(f"No {DAYBREAK_DIR} — nothing to patch.")
        return

    files = sorted(DAYBREAK_DIR.glob("*.html"))
    if not files:
        print(f"No editions in {DAYBREAK_DIR}.")
        return

    touched = 0
    for path in files:
        applied = patch(path)
        if applied:
            touched += 1
            print(f"{path.name}: {', '.join(applied)}")
        else:
            print(f"{path.name}: already up to date")
    print(f"\nPatched {touched} of {len(files)} editions.")


if __name__ == "__main__":
    main()
