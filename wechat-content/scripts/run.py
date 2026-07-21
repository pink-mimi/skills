from __future__ import annotations

import argparse
import json
import struct
from datetime import datetime
from pathlib import Path

from rendering import build_article, build_html, render_images
from news_visuals import choose_news_visual, valid_live_pair

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_VERSION = "2.1.0"
NEWS_REQUIRED_FIELDS = ("what_happened", "why_it_matters", "reader_action", "editor_note", "keywords")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def choose_theme(content_type: str, requested: str, config: dict, run_at: datetime) -> str:
    names = config["themes"][content_type]
    if requested != "auto":
        if requested not in names:
            raise SystemExit(f"主题 {requested} 不适用于 {content_type}")
        return requested
    return names[run_at.date().toordinal() // 7 % len(names)]


def output(root: Path, payload: dict) -> Path:
    date = payload["package_id"][-10:]
    return root / "wechat" / payload["content_type"] / date


def png_size(path: Path):
    data = path.read_bytes()
    return struct.unpack(">II", data[16:24]) if data[:8] == b"\x89PNG\r\n\x1a\n" else None


def title_options(content_type: str, title: str, count: int) -> list[str]:
    if content_type == "daily-news":
        return [title, f"未完地图｜{title}", f"昨天，这 {count} 件事值得关注", f"昨日坐标：{count} 个正在发生的变化", f"别只看热搜，昨天更值得留意的是这些事"]
    return [title, f"未完地图｜{title}", f"本周开源坐标：{count} 个值得收藏的项目", f"GitHub 本周观察：这 {count} 个项目解决了什么", f"从热榜到实用：本周值得打开的 {count} 个项目"]


def enforce_content_quality(payload: dict) -> dict:
    payload=dict(payload); payload["items"]=[dict(item) for item in payload.get("items",[])]
    if payload.get("content_type")=="daily-news":
        incomplete=[item for item in payload["items"] if any(not item.get(field) for field in NEWS_REQUIRED_FIELDS)]
        if incomplete:
            payload["status"]="needs_review"
            payload["risks"]=list(payload.get("risks") or [])+[f"{len(incomplete)} 条新闻缺少发布级解释字段"]
    return payload


def verify(out: Path, payload: dict) -> None:
    errors = []
    for name in ("公众号成稿.md", "微信版.html", "备选标题.txt", "公众号摘要.txt", "运行报告.md", "render-manifest.json"):
        if not (out / name).exists():
            errors.append(f"缺少 {name}")
    for name, size in (("合并封面.png", (1283, 383)), ("横版封面.png", (900, 383)), ("方形封面.png", (383, 383))):
        path = out / "images" / name
        if not path.exists() or png_size(path) != size:
            errors.append(f"图片异常 {name}")
    if payload["content_type"] == "daily-news":
        path=out/"images"/"新闻一日脉络.png"
        if not path.exists() or png_size(path)!=(1200,675): errors.append("图片异常 新闻一日脉络.png")
    else:
        for index in range(1, len(payload["items"]) + 1):
            path = out / "images" / f"项目-{index:02d}.png"
            if not path.exists() or png_size(path) != (1200, 675): errors.append(f"图片异常 {path.name}")
    page = (out / "微信版.html").read_text(encoding="utf-8") if (out / "微信版.html").exists() else ""
    for token in ('id="copy-wechat"', 'id="wechat-content"', "ClipboardItem", "data:image/png;base64,"):
        if token not in page:
            errors.append(f"HTML 缺少 {token}")
    if 'src="images/' in page:
        errors.append("复制区域仍依赖本地图片路径")
    if errors:
        raise SystemExit("；".join(errors))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "verify", "all"))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=ROOT / "assets/default-config.json")
    parser.add_argument("--theme", default="auto")
    parser.add_argument("--image-input-dir", type=Path)
    args = parser.parse_args()
    payload, config = load(args.input), load(args.config)
    if payload.get("schema_version") != 1 or payload.get("content_type") not in ("daily-news", "github-hot"):
        raise SystemExit("不支持的标准内容包")
    payload=enforce_content_quality(payload)
    run_at = datetime.fromisoformat(payload["run_at"])
    out = output(args.output_root, payload)
    theme = choose_theme(payload["content_type"], args.theme, config, run_at)
    visual = None
    if payload["content_type"] == "daily-news":
        visual = choose_news_visual(run_at, config, ROOT / "assets")
        if valid_live_pair(args.image_input_dir, int(config["images"]["maximum_bytes"])):
            visual.update(image_mode="live_image2", cover_path=args.image_input_dir / "cover.png", overview_path=args.image_input_dir / "overview.png", fallback_reason="")
        else:
            if args.image_input_dir:
                visual["fallback_reason"] = "live_image_invalid"
            visual["image_mode"] = "weekday_fallback"
    if args.command in ("build", "all"):
        article, title, summary = build_article(payload)
        cover_title=(payload.get("editorial") or {}).get("cover_title") or (f"昨天，这 {len(payload['items'])} 件事值得关注" if payload["content_type"]=="daily-news" else title)
        image_mode = render_images(out / "images", payload, theme, cover_title, visual)
        write(out / "公众号成稿.md", article)
        write(out / "微信版.html", build_html(article, out / "images", payload, theme, visual))
        write(out / "备选标题.txt", "\n".join(title_options(payload["content_type"], title, len(payload["items"]))))
        write(out / "公众号摘要.txt", summary)
        manifest = {"schema_version": 1, "content_template": payload["content_type"], "template_version": TEMPLATE_VERSION, "theme": theme, "theme_version": "2.0.0", "image_mode": image_mode, "input_status":payload["status"], "source_package": payload["package_id"]}
        if visual:
            manifest.update({"visual_variant":visual["name"],"color_theme":visual["palette_name"],"asset_version":config["news_visuals"]["version"],"fallback_reason":visual["fallback_reason"]})
        write(out / "render-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        visual_report = "" if not visual else f"\n- visual_variant: `{visual['name']}`\n- color_theme: `{visual['palette_name']}`\n- asset_version: `{config['news_visuals']['version']}`\n- fallback_reason: `{visual['fallback_reason']}`"
        write(out / "运行报告.md", f"# 运行报告\n\n- content_type: `{payload['content_type']}`\n- input_status: `{payload['status']}`\n- content_template: `{payload['content_type']}@{TEMPLATE_VERSION}`\n- theme: `{theme}@2.0.0`\n- image_mode: `{image_mode}`{visual_report}\n- 发布：仅生成审核包，未上传、未发布。")
    if args.command in ("verify", "all"):
        verify(out, payload)
        print("OK")


if __name__ == "__main__":
    main()
