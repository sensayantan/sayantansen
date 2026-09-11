"""
One-time migration: converts a Blogger Takeout export into this site's
blog format.

Reads the "feed.atom" file bundled inside a Blogger Takeout .zip (the
one under Blogger/Blogs/<blog name>/feed.atom — that feed mixes real
posts with comments and other entry types, so this filters to
type=POST, status=LIVE only), and produces:

  - data/blogs.json          index used by blogs.html for the tile grid
  - blogs/<slug>.html         one static page per post, full content

Run once:
    python backend/migrate_blogger.py migration/blogger-takeout.zip

Safe to re-run — it always regenerates both from scratch.
"""

from __future__ import annotations  # so `str | None` works on Python 3.9

import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
BLOGS_DIR = ROOT / "blogs"
DATA_PATH = ROOT / "data" / "blogs.json"

ATOM_NS = "{http://www.w3.org/2005/Atom}"
EXCERPT_LENGTH = 180


def local_tag(tag: str) -> str:
    return tag.split("}")[-1]


def find_feed_atom(zip_path: Path) -> bytes:
    with zipfile.ZipFile(zip_path) as z:
        candidates = [
            n for n in z.namelist() if n.endswith("feed.atom") and "/Blogs/" in n
        ]
        if not candidates:
            raise FileNotFoundError(
                "No Blogs feed.atom found inside the export. Expected a path "
                "like 'takeout/Blogger/Blogs/<blog name>/feed.atom'."
            )
        with z.open(candidates[0]) as f:
            return f.read()


def parse_posts(atom_bytes: bytes) -> list[dict]:
    root = ET.fromstring(atom_bytes)
    posts = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        fields = {}
        for child in entry:
            tag = local_tag(child.tag)
            if tag != "category":  # labels aren't used by any post in this export
                fields[tag] = child.text
        if fields.get("type") == "POST" and fields.get("status") == "LIVE":
            posts.append(fields)
    return posts


def extract_body(html_content: str) -> str:
    """Blogger post content is usually an HTML fragment, but at least one
    post here has a full <html><head>...<body> document pasted in — unwrap
    that case so we don't nest a document inside our own page."""
    if not html_content:
        return ""
    match = re.search(r"<body[^>]*>(.*)</body>", html_content, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else html_content.strip()


def slug_from_filename(filename: str | None, fallback: str) -> str:
    if filename:
        name = filename.rstrip("/").split("/")[-1]
        if name.endswith(".html"):
            name = name[:-5]
        if name:
            return name
    return fallback


def make_excerpt(html_content: str, length: int = EXCERPT_LENGTH) -> str:
    # Strip whole <style>/<script> blocks (content included), and real HTML
    # comments — Word-pasted content wraps metadata in <!--[if gte mso 9]>
    # ... <![endif]--> conditional comments, which a browser never renders
    # but a naive tag-strip would leak as visible text.
    text = re.sub(r"<!--.*?-->", " ", html_content or "", flags=re.DOTALL)
    text = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "…"


def first_image(html_content: str) -> str | None:
    """Returns the first usable image for the tile thumbnail, skipping any
    http:// (not https://) images entirely — GitHub Pages serves this site
    over https, and browsers block "mixed content" (loading an insecure
    http:// resource on a secure page), so an http image would always show
    as broken regardless of whether the source is even still online. Some
    old posts hotlinked images from third-party sites over http with no
    https alternative in the post; for those, no image is more honest than
    a permanently-broken one."""
    for match in re.finditer(r'<img[^>]+src="([^"]+)"', html_content or ""):
        url = match.group(1)
        if url.startswith("https://"):
            return url
    return None


def format_date(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return f"{dt.strftime('%B')} {dt.day}, {dt.year}"


POST_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Sayantan Sen</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/css/style.css">
</head>
<body>

  <header class="site-header">
    <div class="container pillnav-row">
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
    <div class="blog-post-body">
{body}
    </div>
  </main>

  <footer class="site-footer">
    <p class="container">&copy; <span id="year"></span> Sayantan Sen</p>
  </footer>

  <script src="../assets/js/main.js"></script>
</body>
</html>
"""


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python backend/migrate_blogger.py <path-to-takeout.zip>")
        sys.exit(1)

    zip_path = Path(sys.argv[1])
    atom_bytes = find_feed_atom(zip_path)
    posts = parse_posts(atom_bytes)
    print(f"Found {len(posts)} live posts in the export.")

    BLOGS_DIR.mkdir(exist_ok=True)
    index = []
    seen_slugs = set()

    for post in posts:
        body = extract_body(post.get("content"))
        fallback_slug = f"post-{post['id'].split('.')[-1]}" if post.get("id") else "post"
        slug = slug_from_filename(post.get("filename"), fallback_slug)
        if slug in seen_slugs:
            slug = f"{slug}-{post['id'].split('.')[-1][-6:]}"
        seen_slugs.add(slug)

        title = post.get("title") or "(untitled)"
        date_iso = post.get("published") or post.get("created")
        date_display = format_date(date_iso)

        page_html = POST_PAGE_TEMPLATE.format(
            title=title, date_display=date_display, body=body
        )
        (BLOGS_DIR / f"{slug}.html").write_text(page_html)

        index.append(
            {
                "slug": slug,
                "title": title,
                "date_iso": date_iso,
                "date_display": date_display,
                "excerpt": make_excerpt(body),
                "image": first_image(body),
                "url": f"blogs/{slug}.html",
            }
        )

    index.sort(key=lambda p: p["date_iso"], reverse=True)
    DATA_PATH.write_text(json.dumps({"posts": index}, indent=2))

    print(f"Wrote {len(index)} pages to {BLOGS_DIR}/")
    print(f"Wrote index to {DATA_PATH}")


if __name__ == "__main__":
    main()
