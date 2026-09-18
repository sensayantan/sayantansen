# Standalone Daybreak setup

Added 18-Sep-2026. The cloud workflow is checked in but **disabled by default**. The existing Codex schedule is unchanged.

## Executable research and summaries

`research.mjs` runs ten web-search passes (eight desks, markets, earnings) through OpenAI Responses web search. Each retrieval is followed by a separate structured extraction/summarization call restricted to supplied evidence and tool-returned source URLs. No portfolio data is supplied to the model.

`rankAndDeduplicate` sorts by **20 × human impact + 10 × significance + freshness bonus (0–10)**. Impact/significance are model-assessed 0–5 judgments, not measured facts. Impact ≥4 promotes a story into Top News. Repeated event IDs, canonical source URLs and headlines with ≥75% token overlap are removed. Top News has up to five stories; each other desk up to three. Publication dates outside 48 hours are dropped. Prior edition headlines are supplied to avoid unchanged announcements; this prompt safeguard does not guarantee semantic cross-day deduplication.

Source provenance and numeric-presence checks reduce unsupported additions; **they do not prove factual truth**. Search-cited URLs do not prove that whole articles were read. Casualty counts remain attributed and provisional. Earnings includes verified items found by search, not a certified exhaustive 500-company sweep. Raw responses, source lists, usage and ranking decisions stay in ignored `.daybreak-work/research-audit.json`, never committed or uploaded as artifacts.

## Configure credentials, privacy and spending

Repository Settings → Secrets and variables → Actions:

- Secret `OPENAI_API_KEY`: a dedicated API project key.
- Variable `DAYBREAK_OPENAI_MODEL`: an API model available to your account supporting Responses web search and structured outputs. No model is silently chosen.
- Secret `DAYBREAK_PORTFOLIO_SYMBOLS`: a JSON array of exactly 96 unique ticker strings, not the workbook or balances.
- Variable `DAYBREAK_CLOUD_ENABLED`: `true` enables cloud runs.
- Variable `DAYBREAK_API_PUBLISH_ENABLED`: leave unset during review; set `true` only to permit cloud publication.

**Privacy:** cloud execution requires storing ticker symbols in GitHub Secrets. Earlier Yahoo-only consent does not authorize us to provision this GitHub secret. We have not uploaded it. Decide whether this storage is acceptable before configuring it; otherwise use the local workbook and local execution. The cloud entry point removes the ticker secret from the research process environment; only Yahoo fetching uses it.

API usage is separate from the in-app subscription. Set project billing limits/alerts first. Each edition is bounded to 20 API requests, 4,000 output tokens/request and three web-tool calls/retrieval (30 maximum). No automatic retries. These bounds are **not a dollar spending cap**. Missing credentials/tickers are checked before paid research; failed research aborts rather than recycling old news.

## Review and activate

1. Configure credentials/model and, only if acceptable, the private GitHub ticker secret.
2. Enable `DAYBREAK_CLOUD_ENABLED`, leaving publication disabled.
3. Actions → Generate Daybreak → Run workflow with Publish unchecked. Review the HTML preview artifact. Private raw research/ticker files are never uploaded.
4. Set Pages source to **GitHub Actions** before publishing. This workflow explicitly deploys the tracked static site; bot `GITHUB_TOKEN` pushes do not trigger another workflow.
5. After live preview succeeds, disable the existing Codex automation to avoid duplicate editions, then enable `DAYBREAK_API_PUBLISH_ENABLED`.

The timer uses 17:00 and 18:00 UTC with a Pacific 10 AM Mon–Sat gate for DST, excluding Sunday. GitHub Actions may delay/miss runs: no exact-time guarantee. Repository rules must permit bot main commits and Pages deployment. Concurrent main changes stop safely rather than force-pushing. Generated HTML is checked in as latest + dated archive; latest.json stays static. Deployment is explicitly performed before live URL verification.

## Local use

Supply credentials securely in the environment, then:

```sh
node backend/daybreak/research.mjs --output .daybreak-work/edition.json
node backend/daybreak/run.mjs \
  --edition .daybreak-work/edition.json \
  --portfolio /path/to/local/SayantanStockCode.xlsx \
  --authorize-yahoo-portfolio
```

Review `.daybreak-work/preview/daybreak-latest.html` before adding `--publish`. Existing Codex research can still supply edition.json without an API key.

Tests: `node backend/daybreak/test.mjs` and `node --test backend/daybreak/research.test.mjs`. These use synthetic fixtures/mocked API responses, incur no paid calls and do not certify live API/model compatibility. Run a configured live preview before activation.

Implementation references: [OpenAI web search](https://developers.openai.com/api/docs/guides/tools-web-search), [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [GitHub Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages), and [scheduled workflow limitations](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).
