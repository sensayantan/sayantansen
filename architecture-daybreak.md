# Daybreak architecture

## What runs where

Daybreak is a hybrid editorial and code pipeline. The Codex scheduled task does source-first internet research and prepares verified, structured inputs. Repository code fetches prices, calculates trends, renders a standalone HTML page, validates it and publishes it through Git. GitHub Pages serves the finished files; visitors do not make model or finance API calls.

```text
Codex app scheduled task (Mon–Sat, 10:00 AM America/Los_Angeles)
  → current research + event deduplication → private edition.json
  → run.mjs
       → read XLSX locally → ticker-only JSON
       → Yahoo prices → 7-day / 30-day changes
       → render.mjs + template.html → two identical HTML files
       → validate_html.py → scoped Git commit → origin/main
  → GitHub Pages deployment verification
  → news.html → static latest.json → daybreak-latest.html
```

The actual scheduler belongs to the Codex app. Its automation ID is `publish-daybreak-news`; it is attached to the existing conversation. There is no hidden Python scheduler, cron daemon or GitHub Actions news-generation job. `backend/daybreak/run.mjs` is the checked-in executable pipeline called by that schedule, not a timer. `backend/daybreak/scheduled-task.md` records the intended schedule and editorial instructions, but editing that document does not change the app automation.

Integration status at code check-in: offline renderer/validation tests and the public 35-symbol fetch passed; local extraction matched all 96 prior symbols. Safety review blocked the new private-portfolio fetch test and the app update that would switch the existing task to this runner. The existing schedule and expanded regional search instructions remain in place, but the new runner is not yet wired into that automation. Explicit approval for recurring ticker-only Yahoo transmission plus report commits/pushes is required before retrying that integration. Do not treat this code commit as proof that tomorrow's full publication is guaranteed.

The app’s scheduled-task documentation is at [Scheduled tasks](https://learn.chatgpt.com/docs/automations?surface=app). Hosting, permission and runtime availability remain dependencies; the script cannot bypass permissions or guarantee a run if the local environment is unavailable.

## Repository components

| File | Responsibility |
| --- | --- |
| `backend/daybreak/config.json` | Required section order, five market-strip labels and disclosed public tracking universe |
| `backend/daybreak/extract_portfolio.py` | Read first worksheet column A from XLSX using Python's standard library; emit ticker symbols only |
| `backend/daybreak/fetch-prices.mjs` | Fetch Yahoo daily bars; preserve source dates and explicit errors |
| `backend/daybreak/render.mjs` | Validate structured inputs and render one HTML string into latest/archive files |
| `backend/daybreak/template.html` | Self-contained CSS, left-aligned masthead, red subheader, grey editorial sections, black/white markets and permanent navigation |
| `backend/daybreak/validate_html.py` | Check balanced HTML, IDs, headings, market-table sizes, placeholders and matching checksums |
| `backend/daybreak/run.mjs` | Orchestrate extraction, prices, rendering, validation, scoped Git publishing and Pages verification |
| `backend/daybreak/test.mjs` | Offline synthetic tests; never publishes |
| `backend/daybreak/edition.example.json` | Input shape only; deliberately not publishable |
| `DAYBREAK/latest.json` | Static pointer: `{"file":"daybreak-latest.html"}` |
| `news.html` | Existing frontend entry: reads the static pointer without caching and redirects to the report with cache busting |

No separate frontend framework/build is needed for this report. The renderer embeds the template CSS in each page. Existing site JS/CSS and About Me/Blogs are unchanged. Earlier scripts in the old Codex workspace were date-specific; they are not the new production entry point.

## Editorial input contract

The scheduled agent writes `.daybreak-work/edition.json` for the actual current Pacific date. All eight configured editorial sections must exist. Empty sections require an explicit reason rather than recycled news.

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

Select Top News first. Do not repeat those events in any other editorial section. Regional desks are India & Asia-Pacific, the Middle East, Europe, Latin America including the Caribbean, Africa, and the US. Technology requires genuinely new reporting within the edition window. Local authoritative sources and independent wires support verification, especially casualty counts and disputed claims.

## Price methodology and privacy

The portfolio workbook remains local and is not added to this website repository. The retained copy is `/Users/sayantan.sen/Documents/Codex/2026-07-24/create-a-scheduled-task-called-weekday/SayantanStockCode.xlsx`; the original Desktop file no longer exists. Its extracted 96-symbol set was checked against the prior set and matches exactly. The extractor reads only column A ticker symbols from its first worksheet. It neither modifies the workbook nor exports account information, quantities, descriptions, balances or cost basis. The Yahoo fetcher accepts only symbols and sends only symbols in quote URLs. The user explicitly authorized this ticker transmission on 15-Sep-2026.

Prices use **unadjusted** daily-bar closes. Seven-day and one-month moves compare the latest available price with the nearest trading-day close on or before seven and 30 calendar days earlier. Today's daily bar may be intraday; mutual funds can have earlier NAV dates. Splits and distributions can affect unadjusted returns. The report labels observation dates and does not claim adjusted total returns.

Top gainers/losers contain five rows each within the disclosed 35-symbol universe, not the entire exchange. Increase/decrease tables have 10 slots each. If fewer stocks qualify, explicit unavailable slots preserve size without inventing stocks. Unavailable portfolio quotes are shown separately rather than silently dropped. The watch list contains every verified holding negative over both periods; review priority is not a buy/sell recommendation.

`.daybreak-work/` and the workbook filename are ignored by Git. Raw ticker lists, fetched data and editorial work files are not committed. **The generated report still includes portfolio watch-list symbols and prices and is publicly accessible on GitHub Pages**, as in the existing approved report. Do not add private balances or account data to it.

## Running locally

Dependencies: Node.js 20+ (built-in fetch), Python 3 and Git. No npm packages or OpenAI API key are required by these scripts. The recurring agent's research is supplied by Codex; moving autonomous research to your own server would require a separate research/model integration and its credentials/billing.

```bash
node backend/daybreak/test.mjs

# After current verified edition.json has been prepared:
node backend/daybreak/run.mjs \
  --edition .daybreak-work/edition.json \
  --portfolio /absolute/path/to/SayantanStockCode.xlsx \
  --authorize-yahoo-portfolio

# Same pipeline with Git publication enabled:
node backend/daybreak/run.mjs \
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
