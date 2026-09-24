# Scheduled Daybreak task

The actual schedule remains in the Codex app, attached to the existing conversation. This file documents it; it does not register another scheduler.

The existing app automation was successfully updated on 17-Sep-2026 to use this runner. The user explicitly authorized ticker-only Yahoo Finance transmission and generated HTML commits/pushes to GitHub main, now and on scheduled runs. The schedule remains Monday through Saturday at 10:00 AM Pacific. Runtime, network, credentials and validation remain execution dependencies.

- Automation ID: `publish-daybreak-news`
- Monday through Saturday, 10:00 AM Pacific (`America/Los_Angeles`); no Sunday run.
- Repository: `/Users/sayantan.sen/Documents/Codex/daybreak-publisher`
- Portfolio input: `/Users/sayantan.sen/Documents/Codex/2026-07-24/create-a-scheduled-task-called-weekday/SayantanStockCode.xlsx` (the retained local copy; the original Desktop file no longer exists)
- Runner: `backend/daybreak/run.mjs`

For each run, independently research every configured editorial region and sweep worldwide for major disasters and mass-casualty events. Put major verified events in Top News and remove cross-section duplicates by event. Include current authoritative market-strip sources, fresh technology reporting, sourced market analysis and newly verified S&P 500 earnings. Research Health and Research separately using peer-reviewed journals, primary studies, systematic reviews, clinical guidance and credible independent reporting. Always perform a dedicated autism spectrum disorder search for new research, healthcare access, support, education and clearly labeled inspirational human-interest stories. State study design and material limitations, distinguish association from causation, preprints from peer review, animal or laboratory work from human evidence, and early research from clinical guidance. Never provide diagnosis or treatment advice. Never turn a scheduled release into a reported result. Prepare `.daybreak-work/edition.json` using the real current date and actual source publication/verification timestamps, then run the repository pipeline with ticker-only Yahoo authorization and `--publish`.

Preserve the ten section headings in `config.json`, including Local US Bay-Area News immediately after Top US News, current design and site navigation. Enforce the configured story-count ranges and at least two independent source domains for every story. Use Google News for discovery only and cite original publishers. Do not publish yesterday's preview tomorrow: apply its layout but research tomorrow's content. Latest and dated archive must match; leave latest.json static. Report the deployed URL only after Pages verification, and clearly report failures. Do not stage source work files, private ticker lists or unrelated changes during routine publication.
