# pink-mimi Skills

Reusable Agent Skills maintained by `pink-mimi`.

## Skills

| Skill | Description |
|---|---|
| `daily-news-wechat` | Collects, filters, verifies, and formats a daily news review package for WeChat Official Accounts. |

## Install

```bash
npx skills add pink-mimi/skills --skill daily-news-wechat
```

Manual installation is also supported: copy `daily-news-wechat/` into an Agent Skills directory.

## Quick start

Invoke the skill naturally:

> Use `$daily-news-wechat` to prepare yesterday's major domestic news as a WeChat review package.

Or run the deterministic pipeline:

```bash
python daily-news-wechat/scripts/run.py all --output-root .
```

The default time window is Beijing time `[previous day 06:00, current day 06:00)`. The skill generates review materials only and does not publish to WeChat.

## License

MIT
