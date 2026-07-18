# Platform integration

The core is platform-neutral: `SKILL.md`, JSON configuration, Python scripts, Markdown, HTML, and SVG.

## Codex

Install the skill, invoke `$daily-news-wechat`, or schedule `scripts/run.py` from a local automation. Keep scheduling prompts outside core scripts.

## Claude Code compatibility

Install the same skill directory in a supported skills location. Validate discovery and invocation against the Claude Code version in use. Do not fork core data formats; adapters should invoke the same commands.

## Other schedulers

Use cron or Windows Task Scheduler to invoke `python scripts/run.py all --output-root <project>`. Live collection requires network access; deterministic tests do not.
