from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from collectors import collect, collect_custom
from core import BJT, NewsItem, deduplicate, item_dicts, load_config, normalize, partition, select_diverse, window_for, write_json
from render import THEMES, article_markdown, cover_png, cover_svg, markdown_to_html, theme_for

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = SKILL_ROOT / "assets" / "default-config.json"


def output_dir(root: Path, run_at: datetime) -> Path:
    return root / "daily-news" / run_at.astimezone(BJT).date().isoformat()


def command_collect(args, config, run_at):
    target = output_dir(args.output_root, run_at)
    rows, errors = collect(config)
    write_json(target / "raw-news.json", {"fetched_at": run_at.isoformat(), "items": rows, "errors": errors})
    print(target / "raw-news.json")


def read_raw(path: Path) -> tuple[list[dict], list[dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("items", []), payload.get("errors", [])


def command_build(args, config, run_at):
    target = output_dir(args.output_root, run_at)
    raw_path = args.input or target / "raw-news.json"
    rows, errors = read_raw(raw_path)
    if args.custom:
        rows.extend(collect_custom(args.custom))
    normalized = [normalize(row, run_at, config) for row in rows]
    merged = deduplicate(normalized)
    eligible, review = partition(merged, run_at, config)
    selected = select_diverse(eligible, config)
    start, end = window_for(run_at, config)
    categories = len({row.category for row in selected})
    status = "ready" if len(selected) >= config["selection"]["minimum"] and categories >= config["selection"]["minimum_categories"] else "needs_review"
    meta = {"status": status, "window_start": start.isoformat(), "window_end": end.isoformat(), "raw": len(rows), "eligible": len(eligible), "selected": len(selected), "categories": categories, "source_errors": errors}
    write_json(target / "candidates.json", {"meta": meta, "items": item_dicts(eligible)})
    write_json(target / "needs-review.json", item_dicts(review))
    write_json(target / "selected.json", {"meta": meta, "items": item_dicts(selected)})
    theme = theme_for(run_at, config["themes"])
    article = article_markdown(selected, start, end)
    (target / "article.md").write_text(article, encoding="utf-8")
    (target / "wechat.html").write_text(markdown_to_html(article, theme), encoding="utf-8")
    title = f"昨天，这{len(selected)}件大事值得关注"
    subtitle = f"{start:%m月%d日 %H:%M}—{end:%m月%d日 %H:%M}"
    (target / "cover-wide.svg").write_text(cover_svg(title, subtitle, theme, 900, 383), encoding="utf-8")
    (target / "cover-square.svg").write_text(cover_svg(title, subtitle, theme, 383, 383), encoding="utf-8")
    (target / "cover-wide.png").write_bytes(cover_png(theme, 900, 383))
    (target / "cover-square.png").write_bytes(cover_png(theme, 383, 383))
    (target / "titles.txt").write_text("\n".join([title, f"过去24小时，{len(selected)}条国内大事速览", f"早上好：这{len(selected)}件事与你有关"]), encoding="utf-8")
    notes = ["# 核验记录", "", "自动处理只完成时间窗、去重、评分和来源分级。发布前必须打开原文完成人工核验。", ""]
    notes.extend(f"- [ ] {item.source}：[《{item.title}》]({item.url})" for item in selected)
    (target / "verification-notes.md").write_text("\n".join(notes) + "\n", encoding="utf-8")
    (target / "run-report.md").write_text(f"# 运行报告\n\n- 状态：`{status}`\n- 入选：{len(selected)}\n- 类别：{categories}\n- 主题：{theme}\n- 来源错误：{len(errors)}\n", encoding="utf-8")
    print(target)


def command_verify(args, config, run_at) -> int:
    target = output_dir(args.output_root, run_at)
    required = ["selected.json", "article.md", "wechat.html", "cover-wide.svg", "cover-square.svg", "cover-wide.png", "cover-square.png", "titles.txt", "verification-notes.md", "run-report.md"]
    missing = [name for name in required if not (target / name).exists()]
    if missing:
        print("Missing: " + ", ".join(missing))
        return 1
    selected = json.loads((target / "selected.json").read_text(encoding="utf-8"))
    html_text = (target / "wechat.html").read_text(encoding="utf-8")
    errors = []
    if selected["meta"]["status"] != "ready": errors.append("status is needs_review")
    if re_search := __import__("re").search(r">https?://[^<]+<", html_text): errors.append(f"visible raw URL: {re_search.group(0)}")
    if errors:
        print("; ".join(errors))
        return 2
    print("OK")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Daily news to WeChat review package")
    parser.add_argument("command", choices=("collect", "build", "verify", "all"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=Path.cwd())
    parser.add_argument("--input", type=Path)
    parser.add_argument("--custom", type=Path)
    parser.add_argument("--run-at", help="ISO 8601 time; defaults to now in Asia/Shanghai")
    args = parser.parse_args()
    config = load_config(args.config)
    run_at = datetime.fromisoformat(args.run_at).astimezone(BJT) if args.run_at else datetime.now(BJT)
    if args.command in ("collect", "all"): command_collect(args, config, run_at)
    if args.command in ("build", "all"): command_build(args, config, run_at)
    if args.command in ("verify", "all"): raise SystemExit(command_verify(args, config, run_at))


if __name__ == "__main__":
    main()
