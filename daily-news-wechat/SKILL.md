---
name: daily-news-wechat
description: Use when users ask to collect daily news, summarize domestic or international events, create a verified Chinese news digest, generate a WeChat Official Account article, prepare yesterday's major events, or build a scheduled news review package.
---

# Daily News WeChat

## Overview

Create a review-first daily news package with explicit time boundaries, source traceability, diverse selection, WeChat-ready copy, covers, and HTML. Never invent timestamps or use weak items to fill a quota.

## Workflow

1. Read `assets/default-config.json`; copy it to the calling project only when customization is required.
2. Read `references/editorial-policy.md` before selecting or writing news.
3. Run `python scripts/run.py collect --output-root <project>` for deterministic RSS collection, or gather additional authoritative sources with available web tools.
4. Preserve full publication timestamps and time zones in JSON. Put unknown-time items into review; do not guess.
5. Run `python scripts/run.py build --output-root <project> [--custom extra.json]`.
6. Open `selected.json`, `needs-review.json`, and original links. Verify policy, disaster, public-safety, and important numeric claims against primary sources.
7. Improve `article.md` using `assets/article-template.md`: keep facts objective, explain ordinary-person impact, and add an actionable `小清提醒`.
8. Regenerate or update `wechat.html`, wide cover, square cover, titles, verification notes, and run report.
9. Run `python scripts/run.py verify --output-root <project>`. If status is `needs_review`, report the gap and do not claim publication readiness.

## Commands

| Command | Purpose |
|---|---|
| `collect` | Fetch configured RSS sources into `raw-news.json` |
| `build` | Filter, deduplicate, select, and render an audit package |
| `verify` | Check required artifacts and readiness status |
| `all` | Run all three commands in order |

Use `--run-at 2026-07-19T06:20:00+08:00` for reproducible runs. Use `--config <file>` to change the time window, regions, sources, limits, or themes.

## Required Editorial Gates

- Apply the left-closed, right-open configured window exactly.
- Select 5–8 items by default, cover at least four categories, and cap each category at two.
- Require official sources for policy, disaster, and public-safety claims.
- Timestamp dynamic figures with “截至……”. Do not reconcile conflicting figures by averaging.
- Keep source names and clickable article titles; never display raw URLs in published copy.
- Generate review materials only. Never publish or store WeChat secrets unless the user separately requests and authorizes it.

## Customization

- Change time and scope in `assets/default-config.json`.
- Enable `international` in `regions` and international sources in `sources` when requested.
- Add RSS sources without changing core code. Add a collector module only for non-RSS formats.
- Keep platform scheduling outside the core. Codex, Claude Code, cron, and Task Scheduler integrations must invoke the same Python commands.

## Common Mistakes

- Treating page update time as event time.
- Mixing publication timestamps without converting time zones.
- Counting multiple reports of one event as separate stories.
- Filling the minimum with old, promotional, or unverifiable content.
- Uploading a combined wide-and-square design as one WeChat cover.
- Claiming the package is ready when `verify` returns a nonzero exit code.
