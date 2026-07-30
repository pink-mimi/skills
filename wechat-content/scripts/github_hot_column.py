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


def top_categories(payload, limit=3):
    labels = []
    for item in payload.get("items") or []:
        card = item.get("reader_card") or {}
        label = str(card.get("category_label") or item.get("category") or "").strip()
        if label and label not in labels:
            labels.append(label)
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
    if first and not any(marker in first for marker in single_project_markers):
        return first
    return (
        f"这期更像一组分岔路：有人想更快理解世界，有人想把注意力重新安放好，"
        f"也有人在补 AI 学习、开发流程和具体业务工具里的短板。"
        f"先按自己的问题进入，通常比按 Star 数字从头看到尾更有收获。"
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
                f"换个角度看，本周突然升温的项目里，{names} 指向了同一条路线："
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
        "这一周的 GitHub 热榜有点分裂。",
        f"一边是 {route_phrase(payload)}，继续把“工具替人整理信息”往前推；"
        "另一边也在提醒我们，开源不只关心模型，也关心人怎么工作、东西怎么送达、问题怎么被拆开解决。",
        f"下面这 {len(items)} 个项目按 GitHub 周榜顺序整理。你不一定都要试，"
        "但可以从里面挑出几个值得收藏的位置：一个能马上试用的工具，一个适合系统学习的资料，"
        "或者一个和你当前工作最接近的项目。",
    ]
    return [
        first,
        [
            f"换个角度看，本周突然升温的项目没有挤在同一条赛道：{route_phrase(payload)}。",
            f"这 {len(items)} 个项目里，有的适合马上试用，有的适合系统学习，有的更像一枚提前出现的行业信号。",
            "先看它解决的问题，再看它是不是适合你；热榜只是入口，真正有用的东西要能留下来。",
        ],
        [
            f"这周的开源热度沿着几条不同路线展开：{route_phrase(payload)}。",
            f"我把前 {len(items)} 个项目按周榜顺序放在这里，不急着喊趋势，先看每个项目到底替谁解决了什么麻烦。",
            "如果只想快速浏览，重点看数据胶囊和一句话概况；如果准备收藏，再看重点内容和适合人群。",
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
        f"**描述：** {project_description(item)}",
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
    categories = "、".join(top_categories(payload)) or "这些方向"
    if editorial.get("opening_mode") == "theme":
        lead = f"把这一期的项目放在一起看，真正值得关注的不是数字同时上涨，而是{categories}这些需求正在被重新整理。"
    else:
        lead = f"这 {len(payload.get('items') or [])} 个项目里，最值得看的不只是 Star 数字，而是它们分别指向了几个真实需求：{route_phrase(payload)}。"
    detail = closing_detail(payload, observations)
    first = [
        "## 如果只收藏三个",
        "",
        lead,
        "",
        detail,
        "",
        "如果只收藏三个，我会优先看：",
        "",
        "- 一个能马上试用的工具；",
        "- 一个能系统学习的资料；",
        "- 一个和你当前工作最接近的项目。",
        "",
        "> 开源热榜每天都在变，但真正值得留下来的，通常是那些能让你下周还想再打开一次的东西。",
        "",
        "![结尾图](images/结尾图.png)",
    ]
    second = [
        "## 如果只收藏三个",
        "",
        "本周突然升温的数字会慢慢回落，但项目背后的需求不会因此消失。",
        "",
        detail,
        "",
        "如果你只准备留下三个位置，可以这样挑：先选一个马上试用，验证它是不是真的省事；再选一个系统学习，补一块长期会用到的能力；最后选一个最贴近当前工作的问题，让收藏夹不只是收藏夹。",
        "",
        "> 热榜记录速度，下一次打开时仍有用，才算真的留下来。",
        "",
        "![结尾图](images/结尾图.png)",
    ]
    third = [
        "## 如果只收藏三个",
        "",
        f"把这些项目留在同一期，不是因为它们拥有相似的数字，而是因为它们分别落在{categories}这些坐标上。",
        "",
        detail,
        "",
        "时间有限时，不妨只挑三个：一个马上试用，一个系统学习，一个最接近当前工作。这样热榜就不会只是一串数字，而会变成下周还能继续打开的线索。",
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
