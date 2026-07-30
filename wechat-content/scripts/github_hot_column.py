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
    return (
        "这期更像一组分岔路：有人在重做协作入口，有人在把复杂信息压成看板，"
        "也有人继续打磨 AI 编程、学习资料和工程审查工具。"
        "真正值得留下来的，不是今天涨了多少 Star，而是下周遇到具体问题时，"
        "它还能不能帮你少绕一段路。"
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
        routes = route_phrase(payload)
        first = [
            f"这一周的 GitHub 热榜，有点像把开发者最近的焦虑摊在桌面上：信息太多、工具太散、AI 能力又更新得太快。",
            f"{names} 先亮了起来，但它们不是同一种答案，而是几条不同路线同时冒头：{routes or editorial.get('weekly_theme') or '复杂技术怎样变成普通开发者也能立刻试用的工具'}。",
            "所以这篇不按“谁 Star 多”来凑热闹。每个项目只看几件事：它原本想解决什么、这周为什么被看见、谁真的可能用得上。",
            "你不用一次收藏 10 个。能从里面挑出一个马上试、一个留着学、一个继续观察，这期热榜就不算白看。",
        ]
        return [
            first,
            [
                f"换个角度看，本周突然升温的项目里，{names} 只是最先被看见的几个坐标。",
                f"往下看会发现几条路线交错在一起：{routes or editorial.get('weekly_theme') or '工具、资料和工作流都在重新长出入口'}。",
                "这篇更像一张筛选清单：先看官方描述，再看一句话概况和适合人群，最后决定它该进收藏夹，还是只做一次路过的信号。",
            ],
            [
                f"{names} 在同一周进入开发者视野，并不是偶然，但它们也不是同一种答案。",
                f"这一期更像几条支线同时亮灯：{routes or editorial.get('weekly_theme') or '有人做工具，有人整理知识，有人改造工作流'}。",
                f"下面这 {len(items)} 个项目按 GitHub 周榜顺序整理。先别急着被数字带走，看看它们各自把哪类麻烦变小了一点。",
            ],
        ]
    first = [
        "这一周的 GitHub 热榜有点分裂，但也因此更值得看：它不是单一趋势的合影，更像一组真实需求的现场。",
        f"本周开源雷达扫到几条不同路线：{route_phrase(payload)}。"
        "有人在重做协作入口，有人在压缩信息噪音，也有人继续把 AI 编程和工程工具往可用处推。",
        f"下面这 {len(items)} 个项目按 GitHub 周榜顺序整理。你不一定都要试，"
        "先看它解决什么问题，再从里面挑几个值得收藏的位置：一个能马上试用的工具，"
        "一个适合系统学习的资料，或者一个和你当前工作最接近的项目。",
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


def should_render_project_image(item):
    return (item.get("_project_image") or {}).get("image_mode") in {"official_verified", "live_image2"}


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
    lines = [
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
    ]
    if should_render_project_image(item):
        lines.extend([f"![{image_label(item)}](images/项目-{index:02d}.png)", ""])
    lines.extend([
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
    ])
    return lines


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
        "## 最后，别让收藏夹变成仓库墓地",
        "",
        lead,
        "",
        detail,
        "",
        "如果只收藏三个，我会按这个顺序挑：",
        "",
        "- 先挑一个今晚就能打开试试的工具，看它是不是真的省事；",
        "- 再留一个能系统补课的资料型项目，给未来的自己铺路；",
        "- 最后选一个最贴近当前工作的问题，让热榜变成下周还能继续用的线索。",
        "",
        "> Star 会涨会跌，真正有用的项目，会在某个具体时刻替你省下一段弯路。",
        "",
        "![结尾图](images/结尾图.png)",
    ]
    second = [
        "## 最后，别让收藏夹变成仓库墓地",
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
        "## 最后，别让收藏夹变成仓库墓地",
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
