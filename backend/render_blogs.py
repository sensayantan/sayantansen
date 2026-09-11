"""
Renders admin-authored blog posts into static pages.

The Decap CMS admin at /admin writes Markdown files with YAML frontmatter
to content/blogs/*.md — one file per post, with fields for title, date,
tags, an image layout choice, uploaded images, an optional PDF, and the
body text. This script turns each of those into:

  - blogs/<slug>.html   a static page, same shape as the migrated
                        Blogger posts (backend/migrate_blogger.py)
  - an entry in data/blogs.json  used by blogs.html's tile grid

It only touches entries whose slug matches a file in content/blogs/ —
the migrated Blogger posts (and any others already in blogs.json) are
left untouched, so this is safe to run alongside that one-time script.

Run manually:
    python backend/render_blogs.py

In production this runs automatically via
.github/workflows/render-blogs.yml whenever content/blogs/** changes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import markdown as markdown_lib
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "blogs"
BLOGS_DIR = ROOT / "blogs"
DATA_PATH = ROOT / "data" / "blogs.json"
EXCERPT_LENGTH = 180


def parse_frontmatter(text: str) -> tuple[dict, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError("No YAML frontmatter found (expected a leading --- block)")
    front = yaml.safe_load(match.group(1)) or {}
    return front, match.group(2)


def strip_leading_slash(path: str) -> str:
    return path[1:] if path.startswith("/") else path


def render_gallery(images: list[dict]) -> str:
    figures = []
    for img in images:
        src = strip_leading_slash(img.get("image", ""))
        caption = img.get("caption") or ""
        cap_html = f"<figcaption>{caption}</figcaption>" if caption else ""
        figures.append(
            f'<figure class="blog-gallery-item"><img src="../{src}" alt="{caption}" loading="lazy">{cap_html}</figure>'
        )
    return f'<div class="blog-gallery">{"".join(figures)}</div>'


def render_images_block(images: list[dict], layout: str) -> str:
    if not images:
        return ""
    if layout == "hero":
        hero, rest = images[0], images[1:]
        src = strip_leading_slash(hero.get("image", ""))
        caption = hero.get("caption") or ""
        cap_html = f'<p class="blog-image-caption">{caption}</p>' if caption else ""
        html = f'<img class="blog-hero-image" src="../{src}" alt="{caption}">{cap_html}'
        if rest:
            html += render_gallery(rest)
        return html
    if layout == "gallery":
        return render_gallery(images)
    return ""  # "standard" layout: no dedicated image block


def render_attachment(path: str | None) -> str:
    if not path:
        return ""
    filename = path.rsplit("/", 1)[-1]
    href = "../" + strip_leading_slash(path)
    return f'<p class="blog-attachment"><a href="{href}">\U0001F4CE {filename}</a></p>'


def render_tags(tags: list[str]) -> str:
    if not tags:
        return ""
    chips = "".join(f'<span class="blog-tag">#{t}</span>' for t in tags)
    return f'<div class="blog-tags">{chips}</div>'


def make_excerpt(body_html: str, length: int = EXCERPT_LENGTH) -> str:
    text = re.sub(r"<[^>]+>", " ", body_html)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "…"


POST_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Sayantan Sen</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/css/style.css?v=4">
</head>
<body>

  <header class="site-header">
    <div class="container container-wide pillnav-row">
      <a href="../index.html" class="brand">Sayantan Sen</a>
      <button class="nav-toggle" id="nav-toggle" aria-label="Toggle menu" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
      <nav class="pillnav" id="nav-links">
        <a href="../index.html" class="pill">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 9.5 10 3l7 6.5"/><path d="M5 8.5V17h10V8.5"/></svg>
          About Me
        </a>
        <a href="../news.html" class="pill">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="4" width="14" height="12" rx="1"/><path d="M6 7.5h8M6 10.5h8M6 13.5h5"/></svg>
          Today's News
        </a>
        <a href="../blogs.html" class="pill active">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 16.5 4.7 13 14 3.7l2.3 2.3L7 15.3l-3.5.7Z"/></svg>
          Sayantan Blogs
        </a>
      </nav>
    </div>
  </header>

  <main class="container blog-post">
    <a class="blog-back-link" href="../blogs.html">&larr; All posts</a>
    <p class="blog-post-date">{date_display}</p>
    <h1 class="blog-post-title">{title}</h1>
    {tags_html}
    {images_html}
    <div class="blog-post-body">
{body_html}
    </div>
    {attachment_html}
  </main>

  <footer class="site-footer">
    <div class="container container-wide footer-row">
      <div class="footer-connect">
        <span class="footer-label">Connect</span>
        <a href="https://www.linkedin.com/" target="_blank" rel="noopener">LinkedIn</a>
        <a href="https://www.instagram.com/sen.sayantan1" target="_blank" rel="noopener">Instagram</a>
        <a href="https://www.facebook.com/" target="_blank" rel="noopener">Facebook</a>
        <a href="https://x.com/sensayantan" target="_blank" rel="noopener">X</a>
      </div>
      <p class="footer-copyright">&copy; <span id="year"></span> Sayantan Sen</p>
    </div>
  </footer>

  <script src="../assets/js/main.js"></script>
</body>
</html>
"""


def format_date(value) -> tuple[str, str]:
    """Returns (iso_string, display_string) from whatever Decap wrote —
    usually an ISO datetime string, but be tolerant of a plain date too."""
    text = str(value)
    date_part = text[:10]
    year, month, day = date_part.split("-")
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    display = f"{months[int(month) - 1]} {int(day)}, {year}"
    return text, display


def render_post(md_path: Path) -> dict:
    front, body_md = parse_frontmatter(md_path.read_text())
    slug = md_path.stem

    title = front.get("title") or "(untitled)"
    date_iso, date_display = format_date(front.get("date", ""))
    tags = front.get("tags") or []
    layout = front.get("layout") or "standard"
    images = front.get("images") or []
    attachment = front.get("attachment")

    body_html = markdown_lib.markdown(
        body_md.strip(), extensions=["tables", "fenced_code", "sane_lists"]
    )
    images_html = render_images_block(images, layout)
    tags_html = render_tags(tags)
    attachment_html = render_attachment(attachment)

    page_html = POST_PAGE_TEMPLATE.format(
        title=title,
        date_display=date_display,
        tags_html=tags_html,
        images_html=images_html,
        body_html=body_html,
        attachment_html=attachment_html,
    )
    BLOGS_DIR.mkdir(exist_ok=True)
    (BLOGS_DIR / f"{slug}.html").write_text(page_html)

    tile_image = None
    if images:
        tile_image = strip_leading_slash(images[0].get("image", "")) or None

    return {
        "slug": slug,
        "title": title,
        "date_iso": date_iso,
        "date_display": date_display,
        "excerpt": make_excerpt(body_html),
        "image": tile_image,
        "url": f"blogs/{slug}.html",
    }


def main() -> None:
    if not CONTENT_DIR.exists():
        print(f"No {CONTENT_DIR} directory yet — nothing to render.")
        return

    md_files = sorted(CONTENT_DIR.glob("*.md"))
    if not md_files:
        print(f"No posts found in {CONTENT_DIR}.")
        return

    rendered_slugs = set()
    new_entries = {}
    for md_path in md_files:
        entry = render_post(md_path)
        rendered_slugs.add(entry["slug"])
        new_entries[entry["slug"]] = entry
        print(f"Rendered {md_path.name} -> blogs/{entry['slug']}.html")

    existing = {"posts": []}
    if DATA_PATH.exists():
        existing = json.loads(DATA_PATH.read_text())

    kept = [p for p in existing.get("posts", []) if p["slug"] not in rendered_slugs]
    merged = kept + list(new_entries.values())
    merged.sort(key=lambda p: p["date_iso"], reverse=True)

    DATA_PATH.write_text(json.dumps({"posts": merged}, indent=2))
    print(f"Updated {DATA_PATH} ({len(merged)} posts total, {len(new_entries)} from content/blogs/)")


if __name__ == "__main__":
    main()
