# Project documentation

Sayantan Sen website Project Documentation: the record of the work behind the site and its Daybreak report, as epics,
stories (with acceptance criteria and assumptions) and a backlog of work
identified but not yet built. It is not a menu item; it lives at
`/sayantansen/ProjectDocs/` and asks for a GitHub sign-in before showing
anything.

## Folder layout

| Path | What it is |
|---|---|
| `index.html` | The page. |
| `projectdocs.js` | Sign-in gate, the epic/story view with filters, the backlog table, and the backlog editor. |
| `content/project-docs.yml` | The source of truth: document purpose, principles, epics → stories, backlog, definition of done, out of scope. Edited three ways (below). |
| `render_project_docs.py` | Converts the YAML into `data/project-docs.json`, rendering Markdown fields to HTML and tolerating statuses and backlog types it doesn't know. |
| `data/project-docs.json` | What the page loads. Generated — never edit it by hand. |

## How it works

```
three ways to edit ProjectDocs/content/project-docs.yml:
  · /admin "Project Documentation"     (Decap CMS)
  · this page's backlog editor         (GitHub REST API, same login token)
  · directly, by a person or a coding agent, through a pull request
        │  a commit to main
        ▼
.github/workflows/render-content.yml   (triggers on ProjectDocs/**)
        │  python ProjectDocs/render_project_docs.py
        ▼
ProjectDocs/data/project-docs.json  committed back with [skip ci]
        │
        ▼
index.html → projectdocs.js
   1. sign in through the oauth-proxy Worker (the same popup /admin uses);
      only the repository owner's GitHub login gets past the gate
   2. fetch data/project-docs.json (no-store) and render epics, stories
      and the backlog
   3. backlog edits: read the YAML through the GitHub contents API, change
      that one entry, and PUT it back with the file's sha, so a stale copy
      can never overwrite a newer one
```

## Things to know

- **The sign-in is a convenience, not a lock.** `data/project-docs.json` is
  an ordinary file on GitHub Pages and anyone who knows its URL can read it.
  Nothing in this document is sensitive, so that trade is deliberate (story
  7.5). Never put anything private in the YAML.
- **Quote YAML strings that contain `: `.** A plain list item such as
  `- It was wrong: the file…` parses as a mapping, not text, and renders as
  `{'…': …}`. Wrap such an item in double quotes.
- **Statuses** are `Done`, `In progress` or `Blocked`; backlog types are
  `Technical Debt`, `Feature Enhancement` or `Feature Development`. Anything
  else still renders, as a neutral chip.
- Everything is one project: every epic's `project` is "Sayantan Sen website Project Documentation". The page
  shows a heading per distinct `project` value, so a different value would
  split the page in two. Epics 1–7 are the website, 8–19 are the Daybreak
  report (titled "Daybreak — …"); add new epics with the next number.

## Run it locally

```
pip install -r requirements.txt
python ProjectDocs/render_project_docs.py
```
