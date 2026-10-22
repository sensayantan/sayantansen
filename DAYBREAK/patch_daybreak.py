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
  3. Adds the "Archive" link to that bar, which is how a reader reaches
     an older edition.
  4. Inserts the short note explaining how the brief is produced.

Before those, it rewrites links to the site's pages from the old
sensayantan.github.io/sayantansen address to sensayantan.com, and from their
pre-move root URLs (news.html, blogs.html, autism.html, archive.html) to the
feature folders they now live in, so older editions and a generator still
using the old template link straight to the right page.

It also writes DAYBREAK/data/daybreak-index.json, the list of editions that
exist, which DAYBREAK/archive.html reads to decide which calendar days are
selectable, and DAYBREAK/data/daybreak-stories.json, every story from every
dated edition, which the archive's search box filters.

Every step checks for its own marker first, so running this twice is a
no-op and running it on an already-patched archive changes nothing.

Run manually:
    python3 DAYBREAK/patch_daybreak.py

In production this runs automatically via
.github/workflows/render-content.yml whenever DAYBREAK/** changes, which
is what makes the changes survive a new edition.
"""

from __future__ import annotations

import datetime as dt
import html as html_lib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAYBREAK_DIR = ROOT / "DAYBREAK"
INDEX_PATH = DAYBREAK_DIR / "data" / "daybreak-index.json"
STORIES_PATH = DAYBREAK_DIR / "data" / "daybreak-stories.json"
SITE = "https://sensayantan.com"
# Where the site lived before the custom domain. GitHub Pages redirects it to
# SITE, but editions should link straight to the domain rather than through a
# hop, so update_site_links rewrites it.
OLD_SITE = "https://sensayantan.github.io/sayantansen"

# daybreak-2026-Sep-24.html -> 2026-09-24. Editions are named with an
# abbreviated month, which does not sort or compare as a date, so the
# archive index converts them once here rather than in the browser.
EDITION_RE = re.compile(r"^daybreak-(\d{4})-([A-Z][a-z]{2})-(\d{2})\.html$")

# Sits in the masthead beside the edition date, not in the category bar.
# In the bar it was the 12th of 12 links and read as another news section
# rather than a control, which is why it went unnoticed.
# chrome=off strips the site header and footer on the archive page, which a
# pop-up has no use for. target=_blank means it still opens in a new tab with
# JavaScript off; the injected script upgrades that to a sized window and can
# then tell when the browser blocked it.
ARCHIVE_LINK = (
    f'<a class="dbArchiveLink" href="{SITE}/DAYBREAK/archive.html?chrome=off"'
    ' target="_blank" rel="noopener">'
    '<svg viewBox="0 0 20 20" aria-hidden="true">'
    '<rect x="3" y="4" width="14" height="4" rx="1"/>'
    '<path d="M4.5 8.5V16h11V8.5M8 11.5h4"/></svg>'
    "Past editions</a>"
)

BARE_START = "/*site-bare-start*/"
BARE_END = "/*site-bare-end*/"

# Must be the first thing in <head>: set from the body-end script instead,
# the header and footer would paint and then be pulled away.
BARE_SCRIPT = (
    "<script>" + BARE_START
    + 'if(location.search.indexOf("chrome=")>-1)'
    + 'document.documentElement.className+=" is-bare";'
    + BARE_END + "</script>"
)

# The generator labels each category with the section's full title. Eleven of
# those will not fit one row at any readable size — they total roughly 1450px
# of text against about 1200px of bar — so the bar carries a short menu label
# and the section heading keeps the full name.
CATEGORY_LABELS = {
    "Top News": "Top News",
    "Top US News": "US",
    "Local US Bay-Area News": "Bay Area",
    "Top India & Asia-Pacific News": "India & APAC",
    "Top India &amp; Asia-Pacific News": "India &amp; APAC",
    "Top News from the Middle-East": "Middle East",
    "Top News from Europe": "Europe",
    "Top News from Latin America": "Latin America",
    "Top News from Africa": "Africa",
    "Technology & AI": "Tech & AI",
    "Technology &amp; AI": "Tech &amp; AI",
    "Health and Research": "Health",
    "Markets": "Markets",
}

POPUP_START = "/*site-popup-start*/"
POPUP_END = "/*site-popup-end*/"

# A pop-up blocker is silent: window.open just returns null, and without this
# the pill would look broken. The notice offers a plain link, which is a
# normal user-initiated navigation and is not blocked.
POPUP_SCRIPT = (
    "<script>" + POPUP_START + """
// The generator's .siteHeader is itself position:sticky at top:0, so the
// category bar has to pin below it rather than on top of it. Its height
// changes with width (it stacks on a narrow screen) and is zero in the
// pop-up, where the header is hidden — so measure it instead of guessing.
(function(){
  var header=document.querySelector(".siteHeader");
  function offset(){
    var h=header?Math.round(header.getBoundingClientRect().height):0;
    document.documentElement.style.setProperty("--dbStickyTop",h+"px");
  }
  offset();
  window.addEventListener("resize",offset);
  window.addEventListener("load",offset);
})();
(function(){
  var link=document.querySelector(".dbArchiveLink");
  if(!link)return;
  // Already inside the pop-up: going back to the archive should reuse this
  // window, not try to open a second one on top of it.
  if(document.documentElement.classList.contains("is-bare")){
    link.target="";
    return;
  }
  var notice=null;
  link.addEventListener("click",function(e){
    e.preventDefault();
    if(notice){notice.remove();notice=null;}
    var w=null;
    try{
      w=window.open(link.href,"daybreakArchive",
        "width=720,height=780,menubar=no,toolbar=no,location=no,resizable=yes,scrollbars=yes");
    }catch(err){w=null;}
    // A blocked pop-up is null, already closed, or has no usable closed flag.
    if(!w||w.closed||typeof w.closed=="undefined"){
      notice=document.createElement("div");
      notice.className="dbPopupBlocked";
      notice.setAttribute("role","alert");
      notice.innerHTML='Your browser blocked the pop-up. '+
        '<a href="'+link.href+'" target="_blank" rel="noopener">Open past editions in a new tab</a>';
      (document.querySelector(".dbCategoryBar")||document.body).insertAdjacentElement("afterend",notice);
      return;
    }
    try{w.focus();}catch(err){}
  });
})();
""" + POPUP_END + "</script>"
)

# The site footer the rest of the site carries. The generator emits only a
# one-line "Daybreak - date - Generated" footer, and the Daybreak pages are
# a separate design system, so the site footer has never reached them.
FOOTER_LINKS = [
    ("https://www.linkedin.com/in/sayantansenusa/", "LinkedIn"),
    ("https://www.instagram.com/sen.sayantan1", "Instagram"),
    ("https://www.facebook.com/sen.sayantan1", "Facebook"),
    ("https://x.com/sensayantan", "X"),
    ("https://substack.com/@sayantansen", "Substack"),
]
SITE_FOOTER = (
    '<footer class="dbSiteFooter"><div class="dbSiteFooterRow">'
    '<div class="dbSiteFooterLinks"><span class="dbSiteFooterLabel">Connect</span>'
    + "".join(
        f'<a href="{href}" target="_blank" rel="noopener">{label}</a>'
        for href, label in FOOTER_LINKS
    )
    + f'</div><p class="dbSiteFooterCopy">&copy; 2026 Sayantan Sen · <a href="{SITE}/Privacy/index.html">Privacy &amp; contact</a></p>'
    "</div></footer>"
)

EXPERIMENT_LINK = (
    f'<a href="{SITE}/MyExperiment/index.html">'
    '<svg viewBox="0 0 20 20"><path d="M7.5 3h5M9 3v5.5L4.5 16h11L11 8.5V3"/></svg>'
    "My Experiment</a>"
)

METHOD_NOTE = (
    '<p class="dbMethod"><strong>How this is made</strong> — OpenAI Codex, on a '
    "standard monthly subscription rather than paid API calls. It works from a "
    "fixed list of topics I follow, gathers the day's stories, summarises them, "
    "and writes a single static HTML page. A scheduled job commits that page to "
    "GitHub and this site renders it. The aim is a brief that costs nothing to run "
    "and reads <em>across</em> sources rather than through one: every outlet "
    "carries a slant, so the most useful version of a story is the one assembled "
    "from several.</p>"
)

CSS_START = "/*site-patch-start*/"
CSS_END = "/*site-patch-end*/"

EXTRA_CSS = CSS_START + """
/* Sticks to the top so a reader can jump between sections without scrolling
   back up. One row: nowrap plus overflow-x, so a narrow window scrolls the
   menu sideways rather than stacking it into two or three rows. */
.dbCategoryBar{position:sticky;top:var(--dbStickyTop,76px);z-index:40;display:flex;flex-wrap:nowrap;overflow-x:auto;
  gap:0;padding:0 5%;background:#163172;border-bottom:1px solid #0f2454;
  -webkit-overflow-scrolling:touch;scrollbar-width:none}
.dbCategoryBar::-webkit-scrollbar{display:none}
.dbCategoryBar a{flex:0 0 auto;padding:11px 14px;font-size:10.5px;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;text-decoration:none;color:#c3d3f2;white-space:nowrap;
  border-bottom:2px solid transparent}
/* A divider between items so eleven short labels read as separate menu
   entries rather than one run-on line. */
.dbCategoryBar a+a{box-shadow:inset 1px 0 0 rgba(255,255,255,.14)}
.dbCategoryBar a:hover,.dbCategoryBar a:focus{color:#fff;background:#1d3f8a;border-bottom-color:#8fb4ff}
/* Anchor jumps otherwise land underneath the pinned bar. */
.section,[id^="s"]{scroll-margin-top:calc(var(--dbStickyTop,76px) + 46px)}
html{scroll-behavior:smooth}
.dbMethod{margin:0;padding:11px 5% 13px;background:#fff;border-bottom:1px solid #e6eaf1;font-size:11px;line-height:1.65;color:#6b7a94}
.dbMethod strong{color:#46587a}
/* The generator styles its own site header white, with its own padding and
   its own blue. Every other page uses the navy pill nav, so clicking
   "Today's News" made the header jump. These match it: same navy, same
   accent, same type, and left/right padding reproducing the .container-wide
   box (1480px, centred, 1.25rem gutter) the rest of the site uses. */
.siteHeader{background:#163172;border-bottom:1px solid rgba(255,255,255,.12);
  /* min-height:76px from the generator made this header 4px taller than
     every other page's, which is visible as a jump when navigating. The
     1rem padding reproduces .pillnav-row and lands on the same height. */
  min-height:0;padding-top:1rem;padding-bottom:1rem;
  padding-left:max(1.25rem,calc((100% - 1480px) / 2 + 1.25rem));
  padding-right:max(1.25rem,calc((100% - 1480px) / 2 + 1.25rem))}
.siteName{color:#fff;font-size:1.1rem;font-weight:700}
/* The generator centres this nav with margin:auto and balances it with a
   118px spacer. Every other page pushes it to the right edge instead, so
   centring it here moved every link sideways on navigation. */
.siteNav{gap:.4rem;margin:0 0 0 auto}
.siteSpacer{display:none}
/* line-height too: the site's body sets 1.6, and without it these links
   come out 6px shorter, which is exactly how much the header was off. */
.siteNav a{gap:.45rem;padding:.55rem 1rem;font-size:.85rem;font-weight:600;line-height:1.6;color:rgba(255,255,255,.75)}
.siteNav svg{width:16px;height:16px;flex-shrink:0}
.siteNav a:hover,.siteNav a:focus{background:rgba(255,255,255,.12);color:#fff}
.siteNav a.active,.siteNav a.active:hover{background:#2451b3;color:#fff}
/* margin-left:auto pushes the whole group to the right edge; the generator
   put that on .edition, which now sits inside this group and so no longer
   reaches the header. */
.dbMasthead-tools{display:flex;align-items:center;gap:16px;margin-left:auto}
.dbMasthead-tools .edition{margin-left:0}
/* Pop-up view: no site nav and no site footer. The generator's
   "Daybreak - date - Generated" line stays, since it is content. */
.is-bare .siteHeader,.is-bare .dbSiteFooter{display:none}
.is-bare .dbCategoryBar{top:0}
html.is-bare body{padding-bottom:0}
.dbPopupBlocked{margin:0;padding:10px 5%;background:#fff4d6;border-bottom:1px solid #e8d391;font-size:12px;color:#6b5312}
.dbPopupBlocked a{color:#8a5a00;font-weight:700}
.dbArchiveLink{display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border:1px solid #c9d2e2;border-radius:999px;background:#fff;font-size:11.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;text-decoration:none;color:#2759bd;white-space:nowrap}
.dbArchiveLink svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:1.6}
.dbArchiveLink:hover,.dbArchiveLink:focus{background:#2759bd;border-color:#2759bd;color:#fff}
/* Fixed, matching the site footer on every other page. The generator's own
   one-line footer stays in the flow above it; body padding keeps the last
   of the page clear of this bar. */
body{padding-bottom:64px}
.dbSiteFooter{position:fixed;left:0;right:0;bottom:0;z-index:50;background:#163172;color:#fff;padding:14px 5%;font-size:13px}
.dbSiteFooterRow{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px 20px}
.dbSiteFooterLinks{display:flex;align-items:center;flex-wrap:wrap;gap:20px}
.dbSiteFooterLabel{font-weight:700}
.dbSiteFooter a{color:#fff;text-decoration:none}
.dbSiteFooter a:hover,.dbSiteFooter a:focus{text-decoration:underline}
.dbSiteFooterCopy{margin:0;color:#fff}
@media(max-width:850px){.dbCategoryBar{padding:0 5%}
.siteHeader{flex-direction:row;align-items:center;gap:12px}
.siteNav{width:auto;margin:0 0 0 auto}.dbCategoryBar a{padding:10px 11px;font-size:10px}
.dbMasthead-tools{gap:10px}.dbArchiveLink{padding:5px 10px;font-size:11px}
/* Three stacked rows at this width, measured, so the clearance matches. */
body{padding-bottom:132px}
.dbSiteFooterRow{justify-content:flex-start;gap:4px 16px}.dbSiteFooterLinks{gap:16px}
/* The market strip drops to two columns here. Plain 1fr columns cannot
   shrink below their longest word, so a long value such as "-0.2% intraday"
   in the 30px figure pushed the strip past the screen and the whole page
   scrolled sideways. minmax(0,1fr) lets the columns shrink; the text wraps. */
.indexStrip{grid-template-columns:repeat(2,minmax(0,1fr))}
.metric{padding:18px 16px;overflow-wrap:anywhere}.metric strong{font-size:24px}}
""" + CSS_END


# Each page moved into its menu's folder. The old root URLs still redirect,
# but an edition should link straight to the page rather than through a hop.
MOVED_PAGES = {
    f"{SITE}/news.html": f"{SITE}/DAYBREAK/index.html",
    f"{SITE}/blogs.html": f"{SITE}/BLOG/index.html",
    f"{SITE}/autism.html": f"{SITE}/MyExperiment/index.html",
    f"{SITE}/archive.html": f"{SITE}/DAYBREAK/archive.html",
}


def update_site_links(html: str) -> tuple[str, bool]:
    """Points links at the site's current domain and feature-folder URLs."""
    updated = html.replace(f'"{OLD_SITE}/', f'"{SITE}/').replace(f'"{OLD_SITE}"', f'"{SITE}/"')
    for old, new in MOVED_PAGES.items():
        updated = updated.replace(f'"{old}"', f'"{new}"').replace(f'"{old}?', f'"{new}?')
    return updated, updated != html


def add_experiment_link(html: str) -> tuple[str, bool]:
    """Adds the nav item the generator doesn't know about."""
    if "MyExperiment/index.html" in html:
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


def add_archive_link(html: str) -> tuple[str, bool]:
    """Puts the archive link in the masthead, beside the edition date.

    An earlier version appended it to the category bar, where it was the
    last of twelve links and looked like one more news section. In the
    masthead it reads as what it is: a way out of today's edition.
    """
    # Clear the old placement so an already-patched edition moves the link
    # rather than ending up with two.
    stale = re.search(r'<a class="dbArchiveLink".*?</a>', html, re.S)
    if stale:
        if stale.group(0) == ARCHIVE_LINK and 'class="dbMasthead-tools"' in html:
            return html, False
        # Older placement or older markup: strip it, and unwrap the tools div
        # so the block below rebuilds it in the current order.
        html = html[: stale.start()] + html[stale.end():]
        html = re.sub(r'<div class="dbMasthead-tools">(.*?)</div>', r"\1", html, count=1, flags=re.S)

    # The masthead is <header class="top">brand + edition</header> by the
    # time move_category_links has run.
    edition = re.search(r'<div class="edition">.*?</div>', html, re.S)
    if not edition:
        return html, False
    # Date first, pill last, so the pill lands hard against the right edge.
    tools = (
        '<div class="dbMasthead-tools">'
        + edition.group(0)
        + ARCHIVE_LINK
        + "</div>"
    )
    return html[: edition.start()] + tools + html[edition.end():], True


def add_bare_mode(html: str) -> tuple[str, bool]:
    """Lets an edition render without site chrome when opened in the pop-up.

    The archive pop-up passes chrome=off through to the edition it opens, so
    the whole pop-up reads as one chrome-less surface instead of the archive
    losing its header and the edition getting it back.
    """
    existing = re.search(
        re.escape("<script>" + BARE_START) + ".*?" + re.escape(BARE_END + "</script>"),
        html,
        re.S,
    )
    if existing:
        if existing.group(0) == BARE_SCRIPT:
            return html, False
        return html[: existing.start()] + BARE_SCRIPT + html[existing.end():], True
    head = re.search(r"<head[^>]*>", html)
    if not head:
        return html, False
    return html[: head.end()] + BARE_SCRIPT + html[head.end():], True


def add_popup_script(html: str) -> tuple[str, bool]:
    """Opens the archive in a sized window, and says so when that is blocked.

    Replaces an existing block rather than skipping it, so edits to
    POPUP_SCRIPT reach editions patched by an earlier version.
    """
    existing = re.search(
        re.escape("<script>" + POPUP_START) + ".*?" + re.escape(POPUP_END + "</script>"),
        html,
        re.S,
    )
    if existing:
        if existing.group(0) == POPUP_SCRIPT:
            return html, False
        return html[: existing.start()] + POPUP_SCRIPT + html[existing.end():], True
    if "</body>" not in html:
        return html, False
    return html.replace("</body>", POPUP_SCRIPT + "</body>", 1), True


def shorten_category_labels(html: str) -> tuple[str, bool]:
    """Swaps each category label for its short form, keeping the full one as
    the link's title so hovering still explains it.

    Idempotent because the short labels are not themselves keys in the map.
    """
    bar = re.search(r'(<nav class="dbCategoryBar"[^>]*>)(.*?)(</nav>)', html, re.S)
    if not bar:
        return html, False

    changed = False

    def relabel(match: re.Match[str]) -> str:
        nonlocal changed
        opening, text = match.group(1), match.group(2)
        short = CATEGORY_LABELS.get(text.strip())
        if not short or short == text.strip():
            return match.group(0)
        changed = True
        if "title=" not in opening:
            opening = opening[:-1] + f' title="{text.strip()}">'
        return opening + short + "</a>"

    inner = re.sub(r'(<a\b[^>]*>)([^<]+)</a>', relabel, bar.group(2))
    if not changed:
        return html, False
    replaced = bar.group(1) + inner + bar.group(3)
    return html[: bar.start()] + replaced + html[bar.end():], True


def add_site_footer(html: str) -> tuple[str, bool]:
    """Adds the site footer, fixed to the bottom as on every other page.

    The generator's own footer carries the generation timestamp and stays
    where it is, in the flow; this one is chrome and sits below it.
    """
    # An edition hand-edited before this script existed carries its own copy
    # of the site footer, with the LinkedIn and Facebook URLs that were later
    # corrected and no Substack link. Replace it rather than adding a second
    # one beside it — daybreak-2026-Sep-10.html showed two stacked footers.
    stale = re.search(r'<footer><div class="footer-connect">.*?</footer>', html, re.S)
    if stale:
        html = html[: stale.start()] + html[stale.end():]
    current = re.search(r'<footer class="dbSiteFooter">.*?</footer>', html, re.S)
    if current:
        # Replace rather than skip, so a change to SITE_FOOTER (such as the
        # Privacy & contact link) reaches editions patched by an earlier run.
        if current.group(0) == SITE_FOOTER:
            return html, bool(stale)
        return html[: current.start()] + SITE_FOOTER + html[current.end():], True
    if "</body>" not in html:
        return html, False
    return html.replace("</body>", SITE_FOOTER + "</body>", 1), True


def edition_date(name: str) -> dt.date | None:
    """The calendar date an edition filename stands for, or None."""
    m = EDITION_RE.match(name)
    if not m:
        return None
    year, month, day = m.groups()
    try:
        return dt.datetime.strptime(f"{year}-{month}-{day}", "%Y-%b-%d").date()
    except ValueError:
        return None


def write_index(files: list[Path]) -> bool:
    """Writes the archive index the calendar reads.

    The calendar greys out every day with no edition. Deriving that from a
    weekday rule would be wrong: Daybreak skips Sundays, but it has also
    missed ordinary weekdays, and those days would offer a link to a file
    that does not exist. So the index lists exactly the files present.
    """
    editions = []
    for path in files:
        date = edition_date(path.name)
        if date:
            editions.append({"date": date.isoformat(), "file": path.name})
    editions.sort(key=lambda e: e["date"])

    index = {
        "editions": editions,
        "first": editions[0]["date"] if editions else None,
        "last": editions[-1]["date"] if editions else None,
    }
    payload = json.dumps(index, indent=2) + "\n"
    # Rewriting an identical file on every run would add an empty commit to
    # the render workflow, so only write when something actually changed.
    if INDEX_PATH.exists() and INDEX_PATH.read_text() == payload:
        return False
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(payload)
    return True


SECTION_RE = re.compile(
    r'<section class="section" id="(s\d+)">.*?<h2>(.*?)</h2>(.*?)</section>', re.S
)
STORY_RE = re.compile(
    r'<article class="story">.*?<small>(.*?)</small>\s*<h3>(.*?)</h3>\s*<p>(.*?)</p>', re.S
)


def plain(fragment: str) -> str:
    """Tag-free, entity-decoded, whitespace-collapsed text."""
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def stories_in(path: Path) -> list[dict]:
    """The news stories in one edition, in page order.

    Only <article class="story"> blocks count: earnings items and market
    rows share the <h3> tag but are not stories a reader searches for. Every
    edition since the first uses this markup, so no fallback is needed.
    """
    html = path.read_text()
    found = []
    for section_id, title, body in SECTION_RE.findall(html):
        for category, headline, summary in STORY_RE.findall(body):
            found.append({
                "section": plain(title),
                "anchor": section_id,
                "category": plain(category),
                "headline": plain(headline),
                "summary": plain(summary),
            })
    return found


def write_story_index(files: list[Path]) -> bool:
    """Writes the searchable list of every story in every dated edition.

    daybreak-latest.html is skipped: it is a byte-identical copy of today's
    dated edition, and indexing both would list each of today's stories
    twice. Newest edition first, stories in page order, so results read in
    the order a reader would meet them.
    """
    stories = []
    for path in files:
        date = edition_date(path.name)
        if not date:
            continue
        for story in stories_in(path):
            stories.append({"date": date.isoformat(), "file": path.name, **story})
    stories.sort(key=lambda s: s["date"], reverse=True)  # stable: keeps page order
    payload = json.dumps({"stories": stories}, ensure_ascii=False, separators=(",", ":")) + "\n"
    if STORIES_PATH.exists() and STORIES_PATH.read_text() == payload:
        return False
    STORIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORIES_PATH.write_text(payload)
    return True


def add_method_note(html: str) -> tuple[str, bool]:
    """Puts the note directly below the masthead (and its category bar).

    Replaces an existing note rather than skipping it. The note's wording is
    ours, not the generator's, so editing METHOD_NOTE above and re-running
    has to update every edition — a plain "already present, skip" would
    silently leave old text on every page already patched.
    """
    existing = re.search(r'<p class="dbMethod">.*?</p>', html, re.S)
    if existing:
        if existing.group(0) == METHOD_NOTE:
            return html, False
        return html[: existing.start()] + METHOD_NOTE + html[existing.end():], True
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
    """Injects our styles, replacing a previous injection if there is one.

    Delimited by markers for the same reason the note is matched and
    replaced: tweaking EXTRA_CSS must reach editions that were patched by an
    earlier version of this script.
    """
    existing = re.search(re.escape(CSS_START) + ".*?" + re.escape(CSS_END), html, re.S)
    if existing:
        if existing.group(0) == EXTRA_CSS:
            return html, False
        return html[: existing.start()] + EXTRA_CSS + html[existing.end():], True
    if "</style>" not in html:
        return html, False
    return html.replace("</style>", EXTRA_CSS + "</style>", 1), True


def patch(path: Path) -> list[str]:
    html = path.read_text()
    applied = []
    for name, fn in (
        ("site-links", update_site_links),
        ("css", add_css),
        ("experiment-link", add_experiment_link),
        ("category-bar", move_category_links),
        ("archive-link", add_archive_link),
        ("short-categories", shorten_category_labels),
        ("site-footer", add_site_footer),
        ("bare-mode", add_bare_mode),
        ("popup-script", add_popup_script),
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

    # DAYBREAK/ also holds this site's own index.html and archive.html, which
    # are not editions and must never be patched as one.
    files = sorted(
        p for p in DAYBREAK_DIR.glob("*.html")
        if p.name == "daybreak-latest.html" or EDITION_RE.match(p.name)
    )
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
    if write_index(files):
        print(f"\nWrote {INDEX_PATH.relative_to(ROOT)}")
    else:
        print(f"\n{INDEX_PATH.relative_to(ROOT)}: already up to date")
    if write_story_index(files):
        print(f"Wrote {STORIES_PATH.relative_to(ROOT)}")
    else:
        print(f"{STORIES_PATH.relative_to(ROOT)}: already up to date")
    print(f"Patched {touched} of {len(files)} editions.")


if __name__ == "__main__":
    main()
