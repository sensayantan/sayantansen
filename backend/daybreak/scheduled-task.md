# Scheduled Daybreak task

The actual schedule remains in the Codex app, attached to the existing conversation. This file documents it; it does not register another scheduler.

The following is the intended repository-runner integration. The app update to enable it was blocked by safety review at check-in; the existing schedule remains unchanged until the exact recurring ticker-only egress and Git publishing workflow is approved. Do not mistake this file for a successfully applied app configuration.

- Automation ID: `publish-daybreak-news`
- Monday through Saturday, 10:00 AM Pacific (`America/Los_Angeles`); no Sunday run.
- Repository: `/Users/sayantan.sen/Documents/Codex/daybreak-publisher`
- Portfolio input: `/Users/sayantan.sen/Documents/Codex/2026-07-24/create-a-scheduled-task-called-weekday/SayantanStockCode.xlsx` (the retained local copy; the original Desktop file no longer exists)
- Runner: `backend/daybreak/run.mjs`

For each run, independently research every configured editorial region and sweep worldwide for major disasters and mass-casualty events. Put major verified events in Top News and remove cross-section duplicates by event. Include current authoritative market-strip sources, fresh technology reporting, sourced market analysis and newly verified S&P 500 earnings. Never turn a scheduled release into a reported result. Prepare `.daybreak-work/edition.json` using the real current date and actual source publication/verification timestamps, then run the repository pipeline with ticker-only Yahoo authorization and `--publish`.

Preserve the eight section headings in `config.json`, current design and site navigation. Do not publish yesterday's preview tomorrow: apply its layout but research tomorrow's content. Latest and dated archive must match; leave latest.json static. Report the deployed URL only after Pages verification, and clearly report failures. Do not stage source work files, private ticker lists or unrelated changes during routine publication.
