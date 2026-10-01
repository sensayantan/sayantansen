# Sayantan Blogs

Blog posts, written in the browser at `/admin` and published as static
pages. Fourteen posts today: thirteen migrated from the old Google Blogger
site, plus those written here since.

## Folder layout

| Path | What it is |
|---|---|
| `index.html` | The blog list page (menu: **Sayantan Blogs**). |
| `blogs.js` | Fetches `data/blogs.json` and draws one tile per post. |
| `content/<slug>.md` | The source of truth for each post: YAML front matter (title, date, tags, banner, layout, images, video, PDF) and a Markdown body. Written by the admin's **Blog Posts** collection. |
| `render_blogs.py` | Turns every `content/*.md` into a page under `posts/` and an entry in `data/blogs.json`. |
| `posts/<slug>.html` | One generated page per post. Never edit by hand. |
| `data/blogs.json` | Generated index of all posts, newest first, that the list page reads. |
| `comments.js` | Adds the giscus comment thread to each post page. |
| `images/<slug>/` | Each post's pictures, in its own folder so two posts' `IMG_1234.jpg` never overwrite each other. |
| `files/` | PDF attachments. |
| `migrate_blogger.py`, `backfill_admin_posts.py` | One-time scripts from the Blogger migration. Kept for the record; not part of the publishing flow. |
| `takeout/` | The raw Google Takeout export of the old blog. **Local only and gitignored** — it contains personal data (emails, followers, commenters), and everything committed here is public. |

## How a post gets published

```
/admin  "Blog Posts"  (Decap CMS, signed in through GitHub via oauth-proxy/)
   │  commits BLOG/content/<slug>.md, and any upload into BLOG/images/<slug>/
   ▼
.github/workflows/render-content.yml   (triggers on BLOG/**)
   │  python BLOG/render_blogs.py
   │    for each content/*.md:
   │      parse front matter + Markdown  →  BLOG/posts/<slug>.html
   │      excerpt, date, tile image      →  entry in BLOG/data/blogs.json
   │    posts whose .md was deleted lose their page and entry
   ▼
committed back to main with [skip ci]  →  GitHub Pages serves it
```

The list page is `index.html` + `blogs.js` reading `data/blogs.json`. Each
post page is fully static HTML — no script is needed to read it.

## Paths and the site base

The site is served from the root of `https://sensayantan.com/`. Image paths
are stored root-absolute (`/BLOG/images/<slug>/…`), and `render_blogs.py`
re-prefixes each path for where it is used (it also strips the pre-domain
`/sayantansen/` prefix, should an old path turn up):

- post pages sit two levels down, so root paths get `../../` (`POST_TO_ROOT`)
- `data/blogs.json` tile images are made relative to `BLOG/index.html`
  (`from_blog_index`)

A post's page chrome — header, nav, footer — is a template string inside
`render_blogs.py`, duplicated from the other pages. A change to the site
header or footer must be made there too, then the posts re-rendered.

## Comments

Comments are GitHub Discussions via [giscus](https://giscus.app): no server
or database. Leaving one needs a GitHub account. Threads are matched on the
page's **pathname**, so a post keeps its comments when retitled but not
when its slug or folder changes — which is why post URLs should now stay
put under `BLOG/posts/`. Moderation happens in the repo's Discussions tab.

## Old URLs

Before the site was reorganised, posts lived at `blogs/<slug>.html` and the
list at `blogs.html`. Those paths still exist as small redirect pages that
forward to the new location, keeping any `#anchor`, so links shared before
the move keep working.

## Run it locally

```
pip install -r requirements.txt
python BLOG/render_blogs.py
python3 -m http.server 8000      # from the repo folder
```

Open `http://localhost:8000/BLOG/`.

## When it breaks

- **A post published but isn't listed**: the render workflow did not run or
  failed; check the Actions tab, then `BLOG/data/blogs.json`.
- **Broken picture**: the path in the post's front matter or body must start
  with `/BLOG/images/<slug>/`.
- **Header or footer differs on posts**: the template in `render_blogs.py`
  was not updated alongside the other pages.
