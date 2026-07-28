from __future__ import annotations

import hashlib


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


def build_title(payload):
    options = (payload.get("editorial") or {}).get("title_options") or []
    if options:
        return str(options[0])
    return f"本周 GitHub 热门：{len(payload['items'])} 个正在变火的开源项目"


def build_opening_variants(payload):
    editorial = payload.get("editorial") or {}
    items = payload["items"]
    if editorial.get("opening_mode") == "theme" and editorial.get("theme_evidence"):
        evidence = editorial["theme_evidence"]
        names = "、".join(row["repo"] for row in evidence[:3])
        first = [
            f"过去一周，{names} 等项目集中受到关注。它们共同指向一个变化："
            f"{editorial.get('weekly_theme') or '开发者正在把复杂技术变成可以实际使用的工具'}。",
            f"我们从本周突然走红的项目中挑出 {len(items)} 个。下面不只看 Star，"
            "还会说明它们为什么火、能解决什么问题，以及谁最值得收藏。",
            "热度负责把坐标点亮，真正值得抵达的，是那些能把问题说清楚、把工具做实的项目。",
        ]
        return [
            first,
            [
                f"本周突然升温的项目里，{names} 指向了同一条路线："
                f"{editorial.get('weekly_theme') or '把复杂技术做成真正可用的工具'}。",
                f"这期留下 {len(items)} 个坐标。除了热度，我们更关心它们解决什么问题、适合谁，以及上手需要什么。",
                "数字让项目被看见，持续解决问题的能力决定它能走多远。",
            ],
            [
                f"{names} 在同一周进入开发者视野，并不是偶然。"
                f"它们都在尝试{editorial.get('weekly_theme') or '降低复杂技术的使用门槛'}。",
                f"下面这 {len(items)} 个项目来自本周热度变化，也经过用途和维护核验。",
                "这是一张本周开源地图，也是一份可以按需收藏的工具清单。",
            ],
        ]
    first = [
        f"从 GitHub 周榜前 {len(items)} 个项目看，本周开源热度走向了几条不同路线。",
        f"这一周值得关注的项目走向了几条不同路线："
        f"{'；'.join((editorial.get('editorial_angles') or [])[:3])}。",
        "下面不展开审核过程，只保留读者最需要的部分：它是什么、数据如何、适合谁，以及是否值得继续打开看。",
        "热榜负责把项目推到眼前，真正决定要不要收藏的，还是它解决的问题是否刚好对你有用。",
    ]
    return [
        first,
        [
            f"本周突然升温的项目没有挤在同一条赛道："
            f"{'；'.join((editorial.get('editorial_angles') or [])[:3])}。",
            f"我们留下 {len(items)} 个不同方向的项目，分别看它们为什么火、能做什么，以及上手条件。",
            "方向不同并不妨碍它们成为本周值得保存的几个坐标。",
        ],
        [
            f"这周的开源热度沿着几条不同路线展开，共有 {len(items)} 个项目值得单独说明。",
            "它们没有被包装成一个虚假的共同趋势，而是按实际用途逐项介绍。",
            "先看问题，再看工具；先看是否适合自己，再决定要不要收藏。",
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
    return [
        "<!-- github-project:start -->",
        "",
        "---",
        "",
        f"## {index:02d} · {card.get('name') or item['repo']}",
        "",
        f"`{card.get('category_label') or item.get('category') or '开源项目'}`",
        "",
        f"**描述：** {card.get('summary') or edit.get('summary') or ''}",
        "",
        f"![{image_label(item)}](images/项目-{index:02d}.png)",
        "",
        f"<!-- github-metrics:{'|'.join(parts)} -->",
        "",
        f"> **一句话概况**　{card.get('recommendation') or edit['use_case']}",
        "",
        "**重点内容**",
        "",
        *[f"- {value}" for value in card.get("highlights") or []],
        "",
        f"**适合谁？**　{'、'.join(card.get('audience') or [])}",
        "",
        f"**项目地址：** [{item['official_url']}]({item['official_url']})",
        "",
        "<!-- github-project:end -->",
    ]


def build_closing_variants(payload):
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
    first = [
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
    second = [
        "## 最后留一个坐标",
        "",
        "本周突然升温的数字会慢慢回落，项目解决的问题却不会因此消失。",
        "",
        detail,
        "",
        "真正值得继续观察的，是它能否把一次关注变成持续维护，把一个想法变成可靠工具。",
        "",
        "> 热榜记录速度，时间检验价值。",
        "",
        "![结尾图](images/结尾图.png)",
    ]
    third = [
        "## 最后留一个坐标",
        "",
        "把这些项目留在同一期，不是因为它们拥有相似的数字，而是因为它们各自提供了一种解决问题的方法。",
        "",
        detail,
        "",
        "下一周会有新的项目出现，但清楚的问题、可靠的维护和真实的用途，始终比短暂排名更重要。",
        "",
        "> 地图会更新，值得抵达的标准不必每天改变。",
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
    for index, item in enumerate(payload["items"], 1):
        lines.extend(build_project(item, index))
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
