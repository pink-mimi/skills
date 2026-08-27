from __future__ import annotations

import hashlib
import re


def hash_text(value):
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def choose_variant(candidates, rejected_hashes):
    rejected = set(rejected_hashes or [])
    for value in candidates:
        if hash_text(value) not in rejected:
            return value
    return candidates[-1]


def metric(value):
    return f"{int(value):,}" if value is not None else ""


def top_categories(payload, limit=3):
    labels = []
    for item in payload.get("items") or []:
        card = item.get("reader_card") or {}
        label = str(card.get("category_label") or item.get("category") or "").strip()
        if label and label not in labels:
            labels.append(label)
    generic = {"开源项目", "项目"}
    specific = [label for label in labels if label not in generic]
    if specific:
        return (specific + [label for label in labels if label in generic])[:limit]
    return labels[:limit]


def editorial_angles(payload, limit=3):
    editorial = payload.get("editorial") or {}
    angles = []
    for value in editorial.get("editorial_angles") or []:
        value = str(value).strip()
        if value and value not in angles:
            angles.append(value)
    if not angles:
        for item in payload.get("items") or []:
            edit = item.get("editorial") or {}
            value = str(edit.get("use_case") or "").strip()
            if value and value not in angles:
                angles.append(value)
    return angles[:limit]


def route_phrase(payload):
    angles = editorial_angles(payload)
    categories = top_categories(payload)
    sentence_like_angles = any(len(value) > 18 or value.endswith(("。", ".", "！", "？")) for value in angles)
    if categories and (len(categories) >= 2 or sentence_like_angles):
        return "、".join(categories[:5])
    if angles:
        return "；".join(angles)
    if categories:
        return "、".join(categories)
    return "AI 工具、开发者工具和数据监控"


def closing_detail(payload, observations):
    first = str((observations or [""])[0]).strip()
    single_project_markers = ("如果你", "它像是", "它是", "这个项目", "这个仓库")
    has_english_description = bool(re.search(r"[A-Za-z]{3,}\s+[A-Za-z]{3,}", first))
    if first and not has_english_description and not any(marker in first for marker in single_project_markers):
        return first
    routes = route_phrase(payload)
    return (
        f"这一期的线索落在{routes}上：有人在重做入口，有人在整理知识，"
        "也有人把复杂能力包成更顺手的工具。真正值得留下来的，不是今天涨了多少 Star，"
        "而是下次遇到同类问题时，它还能不能帮你少绕一段路。"
    )


def contains_cjk(value):
    return bool(re.search(r"[\u4e00-\u9fff]", str(value or "")))


def stale_official_english_fallback(value):
    text = str(value or "").strip()
    if not text.startswith("官方描述："):
        return False
    body = text.removeprefix("官方描述：").strip()
    return bool(body) and not contains_cjk(body)


def project_description(item):
    card = item.get("reader_card") or {}
    fallback = ""
    for value in (
        card.get("translated_description"),
        item.get("translated_description"),
        item.get("description"),
        card.get("summary"),
    ):
        text = str(value or "").strip()
        if not text:
            continue
        if stale_official_english_fallback(text):
            fallback = fallback or "项目官方描述需要发布前补充中文翻译。"
            continue
        if contains_cjk(text):
            return text
        fallback = fallback or text
    return fallback


def build_title(payload):
    options = (payload.get("editorial") or {}).get("title_options") or []
    if options:
        return str(options[0])
    return f"本周 GitHub 热门：{len(payload['items'])} 个正在变火的开源项目"


def build_opening_variants(payload):
    editorial = payload.get("editorial") or {}
    routes = route_phrase(payload)
    route_text = routes or editorial.get("weekly_theme") or "工具、资料和工作流"
    first = [
        f"这周的 GitHub 热榜有点像周末市集：{route_text}这些摊位挤在一起，有的摆出新工具，有的把老问题重新翻出来。",
        "热闹归热闹，真正值得停下来的，不是名字最响的项目，而是你一看 README 就能明白：它到底替我省了哪一步。",
        "这一期先按用途逛一圈：今晚能试的先拿走，值得系统看的记一笔，暂时用不上的留个坐标。",
    ]
    return [
        first,
        [
            f"本周开源雷达扫到一排刚开张的摊位：{route_text}这些路线依次亮出来，热闹但不需要全都带走。",
            "真正值得多看两眼的，是能把一个具体麻烦说清楚，并让你知道下一步该怎么试的项目。",
            "读的时候可以轻一点：今晚能试就试一下，值得系统看就留给周末，暂时用不上就收藏备用。",
        ],
        [
            "这一期 GitHub 热门不像一条整齐的主线，更像开发者把近期遇到的麻烦摆到同一张桌上。",
            f"{route_text}放在一起，不是因为它们相似，而是因为它们各自给出了一条可以继续追的路线。",
            "先逛一圈就好：眼前用得上的马上试，可能改变工作流的系统看，暂时离得远的留个坐标。",
        ],
    ]


def build_opening(payload):
    return build_opening_variants(payload)[0]


def image_label(item):
    mode = (item.get("_project_image") or {}).get("image_mode")
    return {
        "official_verified": "项目官方截图",
        "live_image2": "项目用途示意图",
    }.get(mode, "项目用途视觉")


def should_render_project_image(item):
    return (item.get("_project_image") or {}).get("image_mode") in {"official_verified", "live_image2"}


def build_project(item, index):
    card = item["reader_card"]
    edit = item["editorial"]
    metrics = card["metrics"]
    category = card.get("category_label") or item.get("category") or "开源项目"
    parts = []
    if metrics.get("language"):
        parts.append(str(metrics["language"]))
    if metrics.get("stars") is not None:
        parts.append(f"{metric(metrics['stars'])} Star")
    if metrics.get("weekly_stars") is not None:
        parts.append(f"本周 +{metric(metrics['weekly_stars'])}")
    if metrics.get("forks") is not None:
        parts.append(f"{metric(metrics['forks'])} Fork")
    tags = [category]
    if metrics.get("weekly_stars") is not None:
        tags.append(f"本周 +{metric(metrics['weekly_stars'])}")
    highlights = [str(value).strip() for value in card.get("highlights") or [] if str(value).strip()]
    lines = [
        "<!-- github-project:start -->",
        "",
        "---",
        "",
        f"## {index:02d} · {card.get('name') or item['repo']}",
        "",
        f"<!-- github-tags:{'|'.join(tags)} -->",
        "",
        f"> **一句话推荐**　{card.get('recommendation') or edit['use_case']}",
        "",
    ]
    if should_render_project_image(item):
        lines.extend([f"![{image_label(item)}](images/项目-{index:02d}.png)", ""])
    lines.extend([
        f"<!-- github-metrics:{'|'.join(parts)} -->",
        "",
        "**它是什么**",
        "",
        project_description(item),
        "",
        "**为什么值得看**",
        "",
        f"<!-- github-highlight-row:{'|'.join(highlights)} -->",
        "",
        f"**适合谁？**　{'、'.join(card.get('audience') or [])}",
        "",
        f"**项目地址：** [{item['official_url']}]({item['official_url']})",
        "",
        "<!-- github-project:end -->",
    ])
    return lines


def build_closing_variants(payload):
    categories = "、".join(top_categories(payload)) or "这些方向"
    first = [
        "## 最后，先问它离你有多近",
        "",
        f"这 {len(payload.get('items') or [])} 个项目落在{categories}这些方向上，不需要一次看完。比起全收藏，更实用的是先判断它解决的问题离你有多近。",
        "",
        "现在就会遇到的问题，可以今晚试一下，打开 README 看安装和示例，十分钟内判断它是不是你的工具。",
        "",
        "未来可能遇到的问题，值得系统看，也适合收藏备用到对应资料夹；等同类麻烦出现时，再回来翻这个坐标。",
        "",
        "与自己无关的问题，就让它继续留在热榜里发光。少一点收藏压力，也是一种效率。",
        "",
        "![结尾图](images/结尾图.png)",
    ]
    second = [
        "## 最后，别让收藏夹替你焦虑",
        "",
        f"{categories}这些方向都值得看，但不一定都值得今天安装。先问它和你的问题有多近。",
        "",
        "现在就会遇到的，今晚能试就试；能立刻省事的项目，不需要等到周末。",
        "",
        "未来可能遇到的，值得系统看，慢慢读 README、示例和限制条件。",
        "",
        "与自己无关的，收藏备用也可以，但别让它占用今天的注意力。",
        "",
        "![结尾图](images/结尾图.png)",
    ]
    third = [
        "## 最后，把热闹放回问题里",
        "",
        f"这一期的项目分别落在{categories}这些坐标上，适合用问题距离来判断先后顺序。",
        "",
        "现在就会遇到的，今晚能试就打开；哪怕只跑通一个示例，也比空收藏更有用。",
        "",
        "未来可能遇到的，留给需要补能力的时候系统看，也可以先收藏备用。",
        "",
        "与自己无关的，暂时放过它。热榜每天都很忙，你不用替每个项目安排归宿。",
        "",
        "![结尾图](images/结尾图.png)",
    ]
    return [first, second, third]


def build_closing(payload):
    return build_closing_variants(payload)[0]


def build_article(payload, history=None):
    title = build_title(payload)
    lines = [f"# {title}", "", "<!-- github-opening:start -->"]
    history = history or {}
    opening_variants = build_opening_variants(payload)
    opening_text = choose_variant(
        ["\n\n".join(value) for value in opening_variants],
        history.get("opening_hashes"),
    )
    for paragraph in opening_text.split("\n\n"):
        lines.extend([paragraph, ""])
    lines.append("<!-- github-opening:end -->")
    article_images = payload.get("_article_images") or []
    used_article_images = set()
    if article_images:
        used_article_images.add(0)
        lines.extend(["", f"![本周开源雷达](images/{article_images[0]['filename']})"])
    for index, item in enumerate(payload["items"], 1):
        lines.extend(build_project(item, index))
        if article_images and index in {4, 7}:
            image_index = 1 if index == 4 else 2
            if len(article_images) > image_index:
                used_article_images.add(image_index)
                lines.extend(["", f"![开源项目路线图](images/{article_images[image_index]['filename']})"])
    for image_index, image_record in enumerate(article_images):
        if image_index not in used_article_images:
            lines.extend(["", f"![开源项目路线图](images/{image_record['filename']})"])
    closing_variants = build_closing_variants(payload)
    closing_text = choose_variant(
        ["\n\n".join(value) for value in closing_variants],
        history.get("closing_hashes"),
    )
    lines.extend(["", "---", "", "<!-- github-closing:start -->", *closing_text.split("\n\n"), "<!-- github-closing:end -->"])
    summary = (
        f"从 GitHub 周榜前十中整理 {len(payload['items'])} 个项目，"
        "说明本周热度、实际用途、核心亮点和上手条件。"
    )
    return "\n".join(lines), title, summary


def article_section_hash(article, name):
    start = f"<!-- github-{name}:start -->"
    end = f"<!-- github-{name}:end -->"
    if start not in article or end not in article:
        return ""
    return hash_text(article.split(start, 1)[1].split(end, 1)[0])
