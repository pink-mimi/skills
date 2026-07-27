from __future__ import annotations


def metric(value):
    return f"{int(value):,}" if value is not None else ""


def build_title(payload):
    options = (payload.get("editorial") or {}).get("title_options") or []
    if options:
        return str(options[0])
    return f"这周突然走红的 {len(payload['items'])} 个开源项目"


def build_opening(payload):
    editorial = payload.get("editorial") or {}
    items = payload["items"]
    if editorial.get("opening_mode") == "theme" and editorial.get("theme_evidence"):
        evidence = editorial["theme_evidence"]
        names = "、".join(row["repo"] for row in evidence[:3])
        return [
            f"过去一周，{names} 等项目集中受到关注。它们共同指向一个变化："
            f"{editorial.get('weekly_theme') or '开发者正在把复杂技术变成可以实际使用的工具'}。",
            f"我们从本周突然走红的项目中挑出 {len(items)} 个。下面不只看 Star，"
            "还会说明它们为什么火、能解决什么问题，以及谁最值得收藏。",
            "热度负责把坐标点亮，真正值得抵达的，是那些能把问题说清楚、把工具做实的项目。",
        ]
    return [
        f"这一周值得关注的项目走向了几条不同路线："
        f"{'；'.join((editorial.get('editorial_angles') or [])[:3])}。",
        f"我们从本周突然走红的项目中挑出 {len(items)} 个，逐一说明它们为什么火、"
        "能解决什么问题，以及谁最值得收藏。",
        "项目之间未必共享同一个主题，但都提供了值得继续观察的新坐标。",
    ]


def image_label(item):
    mode = (item.get("_project_image") or {}).get("image_mode")
    return {
        "official_verified": "项目官方截图",
        "live_image2": "项目用途示意图",
    }.get(mode, "项目用途视觉")


def build_project(item, index):
    card = item["reader_card"]
    edit = item["editorial"]
    metrics = card["metrics"]
    parts = []
    if metrics.get("language"):
        parts.append(str(metrics["language"]))
    if metrics.get("stars") is not None:
        parts.append(f"{metric(metrics['stars'])} Star")
    if metrics.get("weekly_stars") is not None:
        parts.append(f"本周 +{metric(metrics['weekly_stars'])}")
    if metrics.get("forks") is not None:
        parts.append(f"{metric(metrics['forks'])} Fork")
    difficulty = card.get("difficulty") or {}
    return [
        "<!-- github-project:start -->",
        "",
        "---",
        "",
        f"## {index:02d} · {card.get('category_label') or item.get('category') or '开源项目'}",
        "",
        f"### {card.get('name') or item['repo']}",
        "",
        card.get("summary") or "",
        "",
        "**为什么这周火？**",
        "",
        edit["hot_reason"],
        "",
        edit["summary"],
        "",
        f"![{image_label(item)}](images/项目-{index:02d}.png)",
        "",
        f"<!-- github-metrics:{'|'.join(parts)} -->",
        "",
        f"> **一句话推荐**　{card.get('recommendation') or edit['use_case']}",
        "",
        *[f"- {value}" for value in card.get("highlights") or []],
        "",
        f"**适合谁？**　{'、'.join(card.get('audience') or [])}",
        "",
        f"**上手条件：**　{difficulty.get('note') or difficulty.get('label') or '以官方说明为准'}",
        "",
        f"**项目地址：** [{item['repo']}]({item['official_url']})",
        "",
        "<!-- github-project:end -->",
    ]


def build_closing(payload):
    editorial = payload.get("editorial") or {}
    observations = editorial.get("closing_observations") or []
    if editorial.get("opening_mode") == "theme":
        lead = (
            "把这一期的项目放在一起看，真正值得关注的不是数字同时上涨，"
            "而是开发者正在把技术整理成更容易学习、安装和使用的东西。"
        )
    else:
        lead = (
            "这一期没有一条可以概括所有项目的主线，但几条不同路线都在回答同一个问题："
            "怎样把技术变成真正可以使用的工具。"
        )
    detail = observations[0] if observations else "短期热度会变化，持续解决问题的能力更值得观察。"
    return [
        "## 最后留一个坐标",
        "",
        lead,
        "",
        detail,
        "",
        "Star 是一时的路标，能不能持续解决问题，才决定一个项目最终会走多远。",
        "",
        "> 不追每一个突然亮起的数字，只留下那些值得再次回来的位置。",
        "",
        "![结尾图](images/结尾图.png)",
    ]


def build_article(payload, history=None):
    title = build_title(payload)
    lines = [f"# {title}", ""]
    for paragraph in build_opening(payload):
        lines.extend([paragraph, ""])
    for index, item in enumerate(payload["items"], 1):
        lines.extend(build_project(item, index))
    lines.extend(["", "---", "", *build_closing(payload)])
    summary = (
        f"从过去七天突然走红的项目中精选 {len(payload['items'])} 个，"
        "说明本周热度、实际用途、核心亮点和上手条件。"
    )
    return "\n".join(lines), title, summary
