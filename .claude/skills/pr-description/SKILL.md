---
name: pr-description
description: Writes pull request descriptions for the sayantansen repo. Use when opening a PR, writing a PR description, or summarizing a branch's changes for a pull request.
allowed-tools: Read, Grep, Glob, Bash
model: haiku
---

`allowed-tools` is restricted to read-only tools plus `Bash` (needed for
`git diff`/`git log`) — writing a PR description should never edit code,
so this skill can't accidentally do it even if asked to. `model: haiku` is
set because summarizing an already-made diff into a fixed template is a
low-reasoning, templated task — cheaper and faster than the default model
without a quality tradeoff worth paying for here. If PR descriptions ever
start reading as shallow or missing nuance, that's the first thing to
revert.

Before writing anything, run `git diff main...HEAD` and `git log main..HEAD --oneline`
to see everything the branch actually changed — never guess from memory.

Write the PR body in this format, matching how every PR on this repo has been
written so far:

## Summary
- Bullet points of what changed, one per logical change, not per file
- Name the actual file(s) touched when it clarifies what changed
- If this fixes a bug, say what was actually broken and why — not just what
  the fix does (e.g. "the CSS cache-buster was never bumped after PR #21,
  so browsers kept serving the old stylesheet" beats "updated style.css")
- If a change touches shared chrome (site-header, site-footer, or the blog
  post template in `render_blogs.py`), call out every place it was applied —
  this repo has several near-duplicate copies of that markup and it's easy
  to miss one

## Verification
- State what was actually checked, not just "should work": local rendering
  with `python3 -m http.server`, a Playwright screenshot for anything visual,
  re-running the relevant `render_*.py` script and diffing the output
- For a bug fix, show the before/after or explain what confirmed the root cause

## Test plan
- A short checklist of what to verify after merge (e.g. "hard-refresh and
  confirm X", "click through Y") — phrase as unchecked boxes: `- [ ] ...`

End with the standard attribution footer:

```
🤖 Generated with [Claude Code](https://claude.com/claude-code)

<session URL, if this was written by Claude Code>
```

Keep it factual and specific — avoid vague filler like "improves the user
experience" or "makes the code cleaner." Say what changed and why it needed
to change.
