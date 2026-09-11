"""
One-time backfill: converts the 13 Blogger-migrated posts (currently
static-only HTML under blogs/, with no editable source) into
content/blogs/*.md, so they show up and become editable in /admin
alongside new posts.

This is an HTML -> Markdown conversion. Markdown is simpler than
arbitrary HTML, so the rendered result should be reviewed afterward —
re-run backend/render_blogs.py, then check blogs/<slug>.html. A few of
the more complex posts (heavy Word-paste formatting) may need manual
touch-up in the admin after this runs; that's expected, not a bug.

Run once:
    python backend/backfill_admin_posts.py
"""

from __future__ import annotations

import json
from pathlib import Path

from markdownify import markdownify

ROOT = Path(__file__).resolve().parent.parent
BLOGS_DIR = ROOT / "blogs"
CONTENT_DIR = ROOT / "content" / "blogs"
DATA_PATH = ROOT / "data" / "blogs.json"

# These exact strings bracket the body in every page migrate_blogger.py
# generated — reliable to split on since we control that template's
# output byte for byte, unlike generic HTML which would need a real
# parser to handle arbitrarily nested <div>s correctly.
START_MARKER = '<div class="blog-post-body">\n'
END_MARKER = "\n    </div>\n  </main>"


def extract_body_html(page_html: str) -> str:
    start = page_html.index(START_MARKER) + len(START_MARKER)
    end = page_html.rindex(END_MARKER)
    return page_html[start:end]


def to_frontmatter(title: str, date_iso: str, image: str | None) -> str:
    safe_title = title.replace('"', '\\"')
    # layout stays "standard" even when an image exists — the image is
    # already embedded inline in the body (that's how these posts were
    # originally authored), so it must NOT also render as a dedicated
    # hero/gallery block (that would show it twice). It's listed here
    # solely so render_blogs.py can use it as the tile-grid thumbnail.
    images_block = (
        f'images:\n  - image: "{image}"\n    caption: ""\n' if image else "images: []\n"
    )
    return (
        "---\n"
        f'title: "{safe_title}"\n'
        f"date: {date_iso}\n"
        "tags: []\n"
        "layout: standard\n"
        f"{images_block}"
        "---\n\n"
    )


def main() -> None:
    data = json.loads(DATA_PATH.read_text())
    CONTENT_DIR.mkdir(exist_ok=True)

    for post in data["posts"]:
        slug = post["slug"]
        html_path = BLOGS_DIR / f"{slug}.html"
        if not html_path.exists():
            print(f"Skipping {slug}: no {html_path}")
            continue

        page_html = html_path.read_text()
        body_html = extract_body_html(page_html)
        body_md = markdownify(body_html, heading_style="ATX").strip()

        frontmatter = to_frontmatter(post["title"], post["date_iso"], post.get("image"))
        (CONTENT_DIR / f"{slug}.md").write_text(frontmatter + body_md + "\n")
        print(f"Wrote content/blogs/{slug}.md")


if __name__ == "__main__":
    main()
