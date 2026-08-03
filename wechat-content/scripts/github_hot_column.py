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


def project_description(item):
    card = item.get("reader_card") or {}
    return str(
        card.get("translated_description")
        or item.get("translated_description")
        or item.get("description")
        or card.get("summary")
        or ""
    ).strip()


def build_title(payload):
    options = (payload.get("editorial") or {}).get("title_options") or []
    if options:
        return str(options[0])
    return f"本周 GitHub 热门：{len(payload['items'])} 个正在变火的开源项目"


def build_opening_variants(payload):
    editorial = payload.get("editorial") or {}
    items = payload["items"]
    routes = route_phrase(payload)
    if editorial.get("opening_mode") == "theme" and editorial.get("theme_evidence"):
        first = [
            f"这周的 GitHub 热榜，不像一次技术秀，更像一张开发者压力清单：{routes or editorial.get('weekly_theme') or '工具、资料和工作流'}这几条路线同时冒头。",
            "Star 把它们推到眼前，但真正值得看的，是这些项目分别在替开发者省掉哪一段麻烦。",
            "往下看时，可以先问三个问题：哪个今晚能试，哪个值得慢慢学，哪个可能变成下一类工具入口。",
        ]
        return [
            first,
            [
                f"本周开源雷达扫到的不是单一风口，而是几条工作路线的重新排布：{routes or editorial.get('weekly_theme') or '工具、资料和工作流'}。",
                "有些项目在压缩信息噪音，有些在把复杂流程变成工具，还有些在替开发者补上一块长期缺口。",
                "热榜只是把它们照亮，真正的价值要看它们能不能在具体场景里少绕路。",
            ],
            [
                "这一期 GitHub 热门有个明显信号：开源正在从“给你一套代码”，继续往“替你压缩一段工作流”靠近。",
                f"{routes or editorial.get('weekly_theme') or '这些坐标'}被放在同一张榜上，不是因为它们相似，而是因为它们都在把某个麻烦变小。",
                "如果时间有限，别急着全收藏，先挑一个能试、一个能学、一个和当前工作最贴近的坐标。",
            ],
        ]
    first = [
        f"这周的 GitHub 热榜，不像一次技术秀，更像一张开发者压力清单：{routes}这几条路线同时冒头。",
        "Star 把它们推到眼前，但真正值得看的，是这些项目分别在替开发者省掉哪一段麻烦。",
        "往下看时，可以先问三个问题：哪个今晚能试，哪个值得慢慢学，哪个可能变成下一类工具入口。",
    ]
    return [
        first,
        [
            f"本周开源雷达扫到的不是单一风口，而是几条工作路线的重新排布：{routes}。",
            "有些项目在压缩信息噪音，有些在把复杂流程变成工具，还有些在替开发者补上一块长期缺口。",
            "热榜只是把它们照亮，真正的价值要看它们能不能在具体场景里少绕路。",
        ],
        [
            "这一期 GitHub 热门有个明显信号：开源正在从“给你一套代码”，继续往“替你压缩一段工作流”靠近。",
            f"{routes}被放在同一张榜上，不是因为它们相似，而是因为它们都在把某个麻烦变小。",
            "如果时间有限，别急着全收藏，先挑一个能试、一个能学、一个和当前工作最贴近的坐标。",
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
    editorial = payload.get("editorial") or {}
    observations = editorial.get("closing_observations") or []
    categories = "、".join(top_categories(payload)) or "这些方向"
    routes = route_phrase(payload)
    lead = (
        f"把这 {len(payload.get('items') or [])} 个项目放在一起看，共同变化不是 Star 同时上涨，"
        f"而是{routes}都在把一段工作流压短。"
    )
    detail = closing_detail(payload, observations)
    first = [
        "## 最后，热榜会刷新，问题不会",
        "",
        lead,
        "",
        detail,
        "",
        "如果只带走三个位置，可以先留一个马上试用的工具，再留一个能系统补课的资料，最后留一个和当前工作最接近的项目。这样收藏不是把链接埋起来，而是给下一次卡住时留一条路。",
        "",
        "> Star 会涨会跌，真正有用的项目，会在你需要时再次亮起来。",
        "",
        "![结尾图](images/结尾图.png)",
    ]
    second = [
        "## 最后，热榜会刷新，问题不会",
        "",
        f"本周突然升温的数字会慢慢回落，但{categories}背后的需求不会因此消失。",
        "",
        detail,
        "",
        "如果你只准备留下三个位置，可以先选一个马上试用，验证它是不是真的省事；再选一个系统补课，补一块长期会用到的能力；最后选一个和当前工作最接近的问题，让收藏夹不只是收藏夹。",
        "",
        "> 热榜记录速度，下一次打开时仍有用，才算真的留下来。",
        "",
        "![结尾图](images/结尾图.png)",
    ]
    third = [
        "## 最后，热榜会刷新，问题不会",
        "",
        f"把这些项目留在同一期，不是因为它们拥有相似的数字，而是因为它们分别落在{categories}这些坐标上。",
        "",
        detail,
        "",
        "时间有限时，不妨只挑三个：一个马上试用，一个系统补课，一个和当前工作最接近。这样热榜就不会只是一串数字，而会变成下周还能继续打开的线索。",
        "",
        "> 地图会更新，真正值得抵达的地方，会在你需要它时再次亮起来。",
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
