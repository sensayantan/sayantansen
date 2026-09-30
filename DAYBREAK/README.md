# Today's News — Daybreak

A researched morning news brief, published Monday to Saturday at 7:30 AM
Pacific as a standalone HTML page. The site's **Today's News** menu opens
the latest edition; an archive calendar opens any earlier one.

## Folder layout

| Path | What it is |
|---|---|
| `index.html` | The **Today's News** menu target. Reads `latest.json` without caching and forwards to the latest edition, with a cache-busting query. |
| `latest.json` | Static pointer, always `{"file":"daybreak-latest.html"}`. The pipeline checks it and never changes it. |
| `daybreak-latest.html` | Today's edition. Overwritten each morning. |
| `daybreak-YYYY-Mon-DD.html` | Dated copy of each edition, kept permanently. |
| `archive.html` + `archive.js` | The **Past editions** calendar. Only days with a file are selectable. |
| `archive-search.js` | Keyword search over every past story, above the calendar. Every word typed must start a word in a story's headline, summary, category or section (case- and accent-insensitive); results are newest first, dated, and link to the story's section in its edition. Runs in the browser, and only fetches its data once the reader starts typing. |
| `data/daybreak-index.json` | The list of editions that exist, which the calendar reads. Generated. |
| `data/daybreak-stories.json` | Every story from every dated edition (date, file, section, category, headline, summary), which the search filters. Generated; about 110 KB for the first 14 editions, growing roughly 8 KB per edition. |
| `patch_daybreak.py` | Re-applies this site's conventions to every edition after it lands (see below). |
| `pipeline/` | The code that researches, renders, validates and publishes an edition. |

Editions are a separate design system: each carries its own inline CSS from
`pipeline/template.html` and shares nothing with `assets/css/style.css`.
**Never hand-edit an edition** — the next morning's run overwrites it. Put
durable fixes in `patch_daybreak.py` or `pipeline/template.html`.

## How an edition reaches a reader

```
Codex app automation "publish-daybreak-news"  (Mon–Sat 7:30 AM Pacific,
   │  runs in the separate clone ~/Documents/Codex/daybreak-publisher)
   │  researches → .daybreak-work/edition.json + research-audit.json (private)
   ▼
DAYBREAK/pipeline/run.mjs --publish
   │  fast-forwards main, fetches prices, renders, validates
   │  commits ONLY DAYBREAK/daybreak-latest.html + the dated copy, pushes
   ▼
.github/workflows/render-content.yml   (triggers on DAYBREAK/**)
   │  python DAYBREAK/patch_daybreak.py
   │    rewrites links to the site's current page URLs
   │    adds the My Experiment nav link, the category bar, the archive
   │    link, the site footer and the "How this is made" note
   │    rebuilds DAYBREAK/data/daybreak-index.json and daybreak-stories.json
   │  commits the patched files with [skip ci]
   ▼
GitHub Pages  →  DAYBREAK/index.html → latest.json → daybreak-latest.html
```

Every step in `patch_daybreak.py` checks for its own marker first, so it is
idempotent and safe to re-run over every edition. It patches only edition
files (`daybreak-latest.html` and the dated ones), never this folder's own
`index.html` or `archive.html`.

### Where the pipeline used to live

The pipeline was in `backend/daybreak/` until the 2026-09-29 folder
reorganisation. Because the Codex automation's prompt called that path, and
`run.mjs` fast-forwards its clone partway through a run, `backend/daybreak`
was kept for one day as a symlink to `DAYBREAK/pipeline`. The automation's
prompt now calls `DAYBREAK/pipeline/` directly; the 2026-09-30 edition was
the first published that way, and the symlink was then removed.

### The optional cloud path

`pipeline/research.mjs` (API web retrieval, summary extraction, ranking and
deduplication), `pipeline/cloud.mjs` (standalone entry point) and
`.github/workflows/daybreak.yml` (a Mon–Sat cloud schedule with explicit
deploy and verification) can replace the Codex automation. That path is
**dormant**: its job only runs when the repository variable
`DAYBREAK_CLOUD_ENABLED` is `true`, which it is not. See
[cloud setup, safeguards and activation](pipeline/cloud-setup.md). The
sections below describe the Codex-driven path that publishes today.

## What runs where

Daybreak is a hybrid editorial and code pipeline. The Codex scheduled task does source-first internet research and prepares verified, structured inputs. Repository code fetches prices, calculates trends, renders a standalone HTML page, validates it and publishes it through Git. GitHub Pages serves the finished files; visitors do not make model or finance API calls.

```text
Codex app scheduled task (Mon–Sat, 7:30 AM America/Los_Angeles)
  → current research + event deduplication → private edition.json
  → run.mjs
       → read XLSX locally → ticker-only JSON
       → Yahoo prices → 7-day / 30-day changes
       → render.mjs + template.html → two identical HTML files
       → validate_html.py → scoped Git commit → origin/main
  → GitHub Pages deployment verification
  → DAYBREAK/index.html → static latest.json → daybreak-latest.html
```

The actual scheduler belongs to the Codex app. Its automation ID is `publish-daybreak-news`; it is attached to the existing conversation. There is no hidden Python scheduler, cron daemon or GitHub Actions news-generation job. `DAYBREAK/pipeline/run.mjs` is the checked-in executable pipeline called by that schedule, not a timer. `DAYBREAK/pipeline/scheduled-task.md` records the intended schedule and editorial instructions, but editing that document does not change the app automation.

Integration update, 17-Sep-2026: the user explicitly authorized transmitting only the 96 portfolio ticker symbols to Yahoo Finance and publishing generated HTML to GitHub main, now and on scheduled runs. The existing app automation was successfully updated to call this runner and use the retained workbook path. Offline tests and the public quote fetch passed at check-in. Each run must still validate its fresh inputs and verify its deployment; registration is not a guarantee of execution when local runtime, network, credentials or permissions are unavailable.

The app’s scheduled-task documentation is at [Scheduled tasks](https://learn.chatgpt.com/docs/automations?surface=app). Hosting, permission and runtime availability remain dependencies; the script cannot bypass permissions or guarantee a run if the local environment is unavailable.

## Repository components

| File | Responsibility |
| --- | --- |
| `DAYBREAK/pipeline/config.json` | Required section order, five market-strip labels and disclosed public tracking universe |
| `DAYBREAK/pipeline/editorial-sources.md` | Required publisher rosters and the read, cluster, rank, corroborate, translate, synthesize and carry-forward editorial workflow |
| `DAYBREAK/pipeline/audit.mjs` | Create and verify a private per-source research-audit manifest cryptographically bound to the exact edition |
| `DAYBREAK/pipeline/extract_portfolio.py` | Read first worksheet column A from XLSX using Python's standard library; emit ticker symbols only |
| `DAYBREAK/pipeline/fetch-prices.mjs` | Fetch Yahoo daily bars; preserve source dates and explicit errors |
| `DAYBREAK/pipeline/render.mjs` | Validate structured inputs and render one HTML string into latest/archive files |
| `DAYBREAK/pipeline/template.html` | Self-contained CSS, left-aligned masthead, red subheader, grey editorial sections, black/white markets and permanent navigation |
| `DAYBREAK/pipeline/validate_html.py` | Check balanced HTML, IDs, headings, market-table sizes, placeholders and matching checksums |
| `DAYBREAK/pipeline/run.mjs` | Orchestrate extraction, prices, rendering, validation, scoped Git publishing and Pages verification |
| `DAYBREAK/pipeline/test.mjs` | Offline synthetic tests; never publishes |
| `DAYBREAK/pipeline/edition.example.json` | Input shape only; deliberately not publishable |

No separate frontend framework/build is needed for this report. The renderer embeds the template CSS in each page. Existing site JS/CSS and About Me/Blogs are unchanged. Earlier scripts in the old Codex workspace were date-specific; they are not the new production entry point.

## Editorial input contract

The scheduled agent writes `.daybreak-work/edition.json` for the actual current Pacific date. It must also write `.daybreak-work/research-audit.json`: every roster URL has an actual check time, explicit status and article URLs, and every published citation appears in either a roster source's article list or the section's supplemental article list. The audit contains a SHA-256 digest of the canonical edition JSON. Rendering and publication refuse a missing, stale, incomplete or mismatched audit, preventing a newly styled page from silently reusing old research.

All ten configured editorial sections must exist, including the Bay Area desk immediately after Top US News. Section counts are editorial targets rather than publication minimums: the agent searches toward them, but may publish fewer verified stories. Configured maximums and the requirement that every included story cite at least two independent source domains remain hard gates; the pipeline never pads a section with weak or invented material. Story-count target shortfalls are not printed on the public page.

Before overwriting the working edition, the research command reads the prior `.daybreak-work/edition.json` when it is from an earlier date. Prior stories become search leads, not publishable content. For a below-target desk, the researcher checks those events for a material current-window development and must build any continuing story from newly retrieved, two-domain evidence. Unchanged recaps, copied summaries and inherited timestamps are rejected by instruction; the normal freshness and source validators still apply.

Each story contains `eventId`, `category`, `headline`, `summary`, `publishedAt`, and `sources`. Each source has `url`, `label`, and the actual `verifiedAt` timestamp. The agent opens/checks citations and uses the real publication time; it must not fabricate timestamps to pass validation. Example story shape:

```json
{
  "eventId": "stable-event-identifier",
  "category": "Country / topic",
  "headline": "Verified headline",
  "summary": "Concise attributed summary",
  "publishedAt": "actual source publication timestamp",
  "sources": [{"url":"https://publisher.example/article", "label":"Publisher", "verifiedAt":"actual verification timestamp"}]
}
```

Each of the five `metrics` requires a display `value`, its source observation date/time in `asOf`, and an authoritative `source` URL. Use `Source unavailable` explicitly when verification fails, never zero or an estimate. `marketAnalysis` and `marketAnalysisSources` hold sourced internals and mover analysis. `earnings.items` contains newly published results with `title`, `summary`, `officialUrl`, and `independentUrl`; scheduled earnings are not results. If none were verified, provide `earnings.emptyReason`.

`reviewComplete: true` means the agent completed significance ranking, citation verification and semantic event deduplication. Software rejects repeated event IDs, normalized headlines and exact source URLs, but cannot reliably detect every paraphrase or verify truth by itself. This is a guardrail, not a hallucination-proof system.

## Research and ranking

Search every region independently, plus a worldwide breaking-event sweep. Major earthquakes, floods, mass shootings, massacres, terrorism, accidents and humanitarian emergencies belong in Top News when their verified human impact and urgency warrant it. Nepal is searched within Asia-Pacific; there is no standalone disaster/Nepal desk.

Select Top News first. Do not repeat those events in any other editorial section. Regional desks are India & Asia-Pacific, the Middle East, Europe, Latin America including the Caribbean, Africa, and the US. Technology requires genuinely new reporting within the edition window. Health and Research prioritizes primary and peer-reviewed sources and always includes an autism-focused search covering research, care, access, education and clearly labeled human-interest stories. It distinguishes association from causation, preprints from peer review, animal or laboratory work from human evidence, and early research from clinical guidance. Local authoritative sources and independent wires support verification, especially casualty counts and disputed claims.

## Price methodology and privacy

The portfolio workbook remains local and is not added to this website repository. The retained copy is `/Users/sayantan.sen/Documents/Codex/2026-07-24/create-a-scheduled-task-called-weekday/SayantanStockCode.xlsx`; the original Desktop file no longer exists. Its extracted 96-symbol set was checked against the prior set and matches exactly. The extractor reads only column A ticker symbols from its first worksheet. It neither modifies the workbook nor exports account information, quantities, descriptions, balances or cost basis. The Yahoo fetcher accepts only symbols and sends only symbols in quote URLs. The user explicitly authorized this ticker transmission on 15-Sep-2026.

Prices use **unadjusted** daily-bar closes. Seven-day and one-month moves compare the latest available price with the nearest trading-day close on or before seven and 30 calendar days earlier. Today's daily bar may be intraday; mutual funds can have earlier NAV dates. Splits and distributions can affect unadjusted returns. The report labels observation dates and does not claim adjusted total returns.

Top gainers/losers contain five rows each within the disclosed 35-symbol universe, not the entire exchange. Increase/decrease tables have 10 slots each. If fewer stocks qualify, explicit unavailable slots preserve size without inventing stocks. Unavailable portfolio quotes are shown separately rather than silently dropped. The watch list contains every verified holding negative over both periods; review priority is not a buy/sell recommendation.

`.daybreak-work/` and the workbook filename are ignored by Git. Raw ticker lists, fetched data and editorial work files are not committed. **The generated report still includes portfolio watch-list symbols and prices and is publicly accessible on GitHub Pages**, as in the existing approved report. Do not add private balances or account data to it.

## Running locally

Dependencies: Node.js 20+ (built-in fetch), Python 3 and Git. No npm packages or OpenAI API key are required by these scripts. The recurring agent's research is supplied by Codex; moving autonomous research to your own server would require a separate research/model integration and its credentials/billing.

```bash
node DAYBREAK/pipeline/test.mjs

# After current verified edition.json has been prepared:
node DAYBREAK/pipeline/audit.mjs init \
  .daybreak-work/edition.json \
  .daybreak-work/research-audit.json
# Replace each skeleton status with the actual per-source result, then verify:
node DAYBREAK/pipeline/audit.mjs verify \
  .daybreak-work/edition.json \
  .daybreak-work/research-audit.json

node DAYBREAK/pipeline/run.mjs \
  --edition .daybreak-work/edition.json \
  --portfolio /absolute/path/to/SayantanStockCode.xlsx \
  --authorize-yahoo-portfolio

# Same pipeline with Git publication enabled:
node DAYBREAK/pipeline/run.mjs \
  --edition .daybreak-work/edition.json \
  --portfolio /absolute/path/to/SayantanStockCode.xlsx \
  --authorize-yahoo-portfolio \
  --publish
```

Without `--publish`, output stays under ignored `.daybreak-work/preview/`. Publication requires a clean `main` checkout, fetches origin and fast-forwards without overwriting unrelated work, rejects a stale edition or outdated source-verification timestamps, stages only the two generated HTML files, commits with the edition date and pushes. `latest.json` is checked but never changed. Existing dated archives remain untouched.

The publisher clone is `/Users/sayantan.sen/Documents/Codex/daybreak-publisher`. The other checkout under `Documents/ClaudeCode/sayantansen` does not automatically update: fetch/pull there when its worktree is safe. Both clones share the same GitHub repository.

## Failures and deployment

Validation failures stop before commit/push. Unavailable individual numeric fields are labelled; a failed whole workflow is not reported as success. A non-fast-forward sync or push error stops without force pushing. Generated/committed local files may remain for inspection after failure; do not reset them blindly. Pages deployment is verified separately from Git push, using a date-and-commit cache-busting URL and exact title check. If Pages stays old, report deployment pending/failure rather than claiming the edition is live.

Canonical public page: `https://sensayantan.github.io/sayantansen/DAYBREAK/daybreak-latest.html`.
