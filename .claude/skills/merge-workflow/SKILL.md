---
name: merge-workflow
description: How to branch, commit, open a PR, and merge changes into main on the sayantansen repo. Use when implementing a fix or feature that needs to ship, or when asked to merge, ship, or publish a code change.
---

This repo ships every change through its own branch and PR — never commit
directly to `main`, even for a one-line fix.

1. **Start from an up-to-date `main`.**
   `git checkout main && git pull origin main`, then branch from there.
   Skipping this is how stale-base PRs and avoidable conflicts happen.

2. **Name the branch by what it does**, matching existing patterns in this
   repo: `fix/<short-description>` for bug fixes, `feature/<short-description>`
   for new capability, `redesign/<short-description>` for visual/layout
   changes. One branch, one focused change — don't bundle an unrelated
   drive-by fix into a feature branch.

3. **Before pushing, verify locally, not just by reading the diff:**
   - Any visual/CSS/HTML change: serve it with `python3 -m http.server` and
     take a Playwright screenshot (desktop *and* mobile width) before
     claiming it works. This repo has shipped visual bugs that a screenshot
     would have caught immediately.
   - Any change to `content/*.yml` or the render pipeline: re-run the
     matching `backend/render_*.py` script and check the diff to `data/*.json`
     or `blogs/*.html` is exactly what's expected.
   - Any change to `assets/css/style.css`: bump the `?v=N` query string on
     *every* `<link rel="stylesheet" href="assets/css/style.css?v=N">`
     reference (`index.html`, `blogs.html`, `news.html`, and the template in
     `backend/render_blogs.py` — regenerate the blog posts after). Forgetting
     this is the single most repeated bug in this repo's history: the fix is
     correct in the file but browsers keep serving the stale cached CSS.

4. **Commit with a message that explains why, not just what** — end it with
   the attribution trailer this session's system prompt specifies
   (`Co-Authored-By:` / `Claude-Session:` lines), then
   `git push -u origin <branch>`.

5. **Open the PR** (see the `pr-description` skill for the body format).

6. **Before merging, check mergeable_state and any CI status** — this repo
   has no required checks configured today, but don't assume that stays
   true forever; check before merging blind.

7. **Merge with `merge_method: "merge"`** (this repo's consistent choice
   throughout its history — not squash, not rebase), using a commit title of
   the form `Merge pull request #N from sensayantan/<branch>`.

8. **Never force-push, rewrite history, or bypass this flow** without the
   user explicitly asking for it — including for trivial one-line fixes.
