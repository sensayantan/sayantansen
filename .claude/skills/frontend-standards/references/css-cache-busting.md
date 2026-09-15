# Why the CSS cache-buster keeps breaking, and the full checklist

GitHub Pages serves `assets/css/style.css` with caching headers generous
enough that browsers (and GitHub's own CDN) can keep serving a stale copy
for minutes after the file changes on the server — long enough that a
correct CSS fix can look like it "didn't work" to whoever's testing it.

This has actually happened on this site more than once: PR #20 introduced
the `?v=N` query-string fix, and PRs #21–23 each changed `style.css` again
without remembering to bump the number, silently re-breaking the same
thing. The fix is trivial; remembering to do it every time is the hard
part. That's what `scripts/check_css_version.py` is for — run it instead
of relying on memory.

## Every place the version string lives

- `index.html`
- `blogs.html`
- `news.html`
- `backend/render_blogs.py` (the `POST_PAGE_TEMPLATE` string — bump this,
  then re-run `python3 backend/render_blogs.py` so every generated post
  under `blogs/*.html` picks it up)

## The actual workflow

1. Change `assets/css/style.css`.
2. Bump every `?v=N` above to `N+1`.
3. Re-run `python3 backend/render_blogs.py`.
4. Run `python3 .claude/skills/frontend-standards/scripts/check_css_version.py`
   — it exits non-zero and lists exactly which file is out of step if you
   missed one.
5. Only then commit.
