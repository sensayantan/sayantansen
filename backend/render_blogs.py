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
# The listing is one post per row now, so there is room for a longer
# excerpt than the old three-across grid allowed.
EXCERPT_LENGTH = 240


def parse_frontmatter(text: str) -> tuple[dict, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError("No YAML frontmatter found (expected a leading --- block)")
    front = yaml.safe_load(match.group(1)) or {}
    return front, match.group(2)


# This site is served from a GitHub Pages project path, not a domain root,
# so an absolute "/assets/..." would resolve one level too high. Decap's
# public_folder carries the base path so its own image previews resolve;
# everything rendered here strips it back off. Keeping it in one constant
# means a move to a custom domain touches exactly this line.
SITE_BASE = "/sayantansen/"


def strip_leading_slash(path: str) -> str:
    """A stored media path reduced to one relative to the site root.

    Tolerates every form Decap has written into content here: bare
    "assets/...", root-absolute "/assets/...", and base-prefixed
    "/sayantansen/assets/...". Older posts keep working untouched.
    """
    if not path:
        return path
    if path.startswith(("http://", "https://", "//")):
        return path
    if path.startswith(SITE_BASE):
        path = path[len(SITE_BASE):]
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


def render_banner(path: str | None, title: str) -> str:
    """The banner sits above the post title, separate from `images`.

    `images` and `layout` still control pictures *inside* the article; this
    is the one that also becomes the thumbnail in the blog list.
    """
    if not path:
        return ""
    src = "../" + strip_leading_slash(path)
    return f'<img class="blog-banner" src="{src}" alt="{title}">'


# Only these two, and only ever rebuilt from an extracted id — never by
# interpolating whatever was typed into an iframe src.
YOUTUBE_ID = re.compile(
    r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/|v/))([A-Za-z0-9_-]{6,})"
)
VIMEO_ID = re.compile(r"vimeo\.com/(?:video/)?(\d+)")


def render_video(url: str | None) -> str:
    """Embeds a YouTube or Vimeo link as a responsive player.

    Returns "" for anything it does not recognise rather than guessing, so
    a mistyped link shows nothing instead of a broken frame.
    """
    if not url:
        return ""

    match = YOUTUBE_ID.search(url)
    if match:
        src = f"https://www.youtube.com/embed/{match.group(1)}"
    else:
        match = VIMEO_ID.search(url)
        if not match:
            return ""
        src = f"https://player.vimeo.com/video/{match.group(1)}"

    return (
        '<div class="blog-video">'
        f'<iframe src="{src}" title="Video" loading="lazy" allowfullscreen '
        'allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
        'gyroscope; picture-in-picture" referrerpolicy="strict-origin-when-cross-origin">'
        "</iframe></div>"
    )


def render_attachment(path: str | None) -> str:
    """Links an uploaded file.

    An absolute URL is linked as-is. Prefixing "../" onto one produced
    hrefs like "../https://youtu.be/..." - which is how a video link pasted
    into this field became a broken relative path labelled with the video
    id as its filename.
    """
    if not path:
        return ""
    if path.startswith(("http://", "https://")):
        href = path
        label = path.split("://", 1)[1]
    else:
        href = "../" + strip_leading_slash(path)
        label = path.rsplit("/", 1)[-1]
    return f'<p class="blog-attachment"><a href="{href}">\U0001F4CE {label}</a></p>'


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
  <link rel="stylesheet" href="../assets/css/style.css?v=27">
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
        <a href="../autism.html" class="pill">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M7.5 3h5"/><path d="M9 3v5.5L4.5 16h11L11 8.5V3"/></svg>
          My Experiment
        </a>
      </nav>
    </div>
  </header>

  <main class="container blog-post">
    <a class="blog-back-link" href="../blogs.html">&larr; All posts</a>
    {banner_html}
    <p class="blog-post-date">{date_display}</p>
    <h1 class="blog-post-title">{title}</h1>
    {tags_html}
    {images_html}
    <div class="blog-post-body">
{body_html}
    </div>
    {video_html}
    {attachment_html}

    <section class="post-comments" id="comments">
      <h2 class="post-comments-title">Comments</h2>
      <p class="post-comments-note">
        Comments are GitHub Discussions on this site's repository, so leaving
        one needs a GitHub account.
      </p>
    </section>
  </main>

  <footer class="site-footer">
    <div class="container container-wide footer-row">
      <div class="footer-connect">
        <span class="footer-label">Connect</span>
        <a href="https://www.linkedin.com/in/sayantansenusa/" target="_blank" rel="noopener">LinkedIn</a>
        <a href="https://www.instagram.com/sen.sayantan1" target="_blank" rel="noopener">Instagram</a>
        <a href="https://www.facebook.com/sen.sayantan1" target="_blank" rel="noopener">Facebook</a>
        <a href="https://x.com/sensayantan" target="_blank" rel="noopener">X</a>
        <a href="https://substack.com/@sayantansen" target="_blank" rel="noopener">Substack</a>
      </div>
      <p class="footer-copyright">&copy; <span id="year"></span> Sayantan Sen</p>
    </div>
  </footer>

  <script src="../assets/js/main.js?v=27"></script>
  <script src="../assets/js/comments.js?v=27"></script>
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


def format_date_range(start, end) -> tuple[str, str]:
    """Display string for a post that covers a span of days.

    End date is optional, so a single-day post reads exactly as before. A
    range inside one month collapses the repeated month name, and one that
    crosses a year keeps both.
    """
    start_iso, start_display = format_date(start)
    if not end or not str(end).strip():
        return start_iso, start_display

    end_iso, end_display = format_date(end)
    if end_iso[:10] <= start_iso[:10]:
        # An end on or before the start is not a range; ignore it rather
        # than print something backwards.
        return start_iso, start_display

    s_year, s_month = start_iso[:4], start_iso[5:7]
    e_year, e_month = end_iso[:4], end_iso[5:7]
    if s_year == e_year and s_month == e_month:
        # "April 3–7, 2026"
        day = str(int(end_iso[8:10]))
        head = start_display.rsplit(",", 1)[0]
        return start_iso, f"{head}\u2013{day}, {s_year}"
    if s_year == e_year:
        # "April 3 – May 2, 2026"
        head = start_display.rsplit(",", 1)[0]
        tail = end_display.rsplit(",", 1)[0]
        return start_iso, f"{head} \u2013 {tail}, {s_year}"
    return start_iso, f"{start_display} \u2013 {end_display}"


def render_post(md_path: Path) -> dict:
    front, body_md = parse_frontmatter(md_path.read_text())
    slug = md_path.stem

    title = front.get("title") or "(untitled)"
    date_iso, date_display = format_date_range(front.get("date", ""), front.get("end_date"))
    tags = front.get("tags") or []
    layout = front.get("layout") or "standard"
    images = front.get("images") or []
    attachment = front.get("attachment")
    banner = front.get("banner")
    video = front.get("video")

    body_html = markdown_lib.markdown(
        body_md.strip(), extensions=["tables", "fenced_code", "sane_lists"]
    )
    banner_html = render_banner(banner, title)
    images_html = render_images_block(images, layout)
    tags_html = render_tags(tags)
    video_html = render_video(video)
    attachment_html = render_attachment(attachment)

    page_html = POST_PAGE_TEMPLATE.format(
        title=title,
        banner_html=banner_html,
        date_display=date_display,
        tags_html=tags_html,
        images_html=images_html,
        body_html=body_html,
        video_html=video_html,
        attachment_html=attachment_html,
    )
    BLOGS_DIR.mkdir(exist_ok=True)
    (BLOGS_DIR / f"{slug}.html").write_text(page_html)

    # The banner is the thumbnail when there is one. Falling back to the
    # first in-article image keeps the older posts, written before this field
    # existed, from losing their tile picture.
    tile_image = strip_leading_slash(banner) if banner else None
    if not tile_image and images:
        tile_image = strip_leading_slash(images[0].get("image", "")) or None

    return {
        "slug": slug,
        "title": title,
        "date_iso": date_iso,
        "date_display": date_display,
        "excerpt": make_excerpt(body_html),
        "image": tile_image,
        "url": f"blogs/{slug}.html",
        # Marks the entry as coming from content/blogs/. Entries without it
        # are the older Blogger imports, which exist only as rendered HTML
        # and must survive a rebuild. See main() for why that distinction
        # matters when a post is deleted.
        "source": "content",
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

    # Entries are merged rather than rebuilt because most posts here are
    # Blogger imports that exist only as rendered HTML, with no markdown to
    # render from. That merge also kept deleted posts forever: removing a
    # post in the CMS deletes its .md, and the stale entry and its HTML page
    # both stayed behind. Only entries this script wrote can be retired.
    kept, orphaned = [], []
    for post in existing.get("posts", []):
        if post["slug"] in rendered_slugs:
            continue  # re-rendered below, from the current markdown
        if post.get("source") == "content":
            orphaned.append(post["slug"])
        else:
            kept.append(post)

    for slug in orphaned:
        page = ROOT / "blogs" / f"{slug}.html"
        if page.exists():
            page.unlink()
        print(f"Removed deleted post {slug} (entry and blogs/{slug}.html)")

    merged = kept + list(new_entries.values())
    merged.sort(key=lambda p: p["date_iso"], reverse=True)

    DATA_PATH.write_text(json.dumps({"posts": merged}, indent=2))
    print(f"Updated {DATA_PATH} ({len(merged)} posts total, {len(new_entries)} from content/blogs/)")


if __name__ == "__main__":
    main()
