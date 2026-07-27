from __future__ import annotations

from datetime import datetime


def parse_time(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def assess_heat(candidate, window_start, window_end):
    start = parse_time(window_start)
    end = parse_time(window_end)
    evidence = []
    for row in candidate.get("heat_evidence") or []:
        if not row.get("url") or not row.get("observed_at"):
            continue
        observed = parse_time(row["observed_at"]).astimezone(start.tzinfo)
        if start <= observed < end:
            evidence.append(dict(row))

    created_at = candidate.get("created_at")
    new_in_window = False
    if created_at:
        created = parse_time(created_at).astimezone(start.tzinfo)
        new_in_window = start <= created < end
    resurgence = any(
        row.get("kind") in {"release", "official_launch", "major_update"}
        for row in evidence
    )
    eligible = bool(evidence)
    if not eligible:
        heat_class = "insufficient"
    elif new_in_window:
        heat_class = "new_breakout"
    elif resurgence:
        heat_class = "mature_resurgence"
    else:
        heat_class = "weekly_breakout"
    return {
        "eligible": eligible,
        "heat_class": heat_class,
        "evidence": evidence,
        "rejection_reasons": [] if eligible else ["本周热度证据不足"],
    }


def project_editorial(candidate, heat):
    card = candidate.get("reader_card") or {}
    hot_reason = str(candidate.get("hot_reason") or "").strip()
    if not hot_reason and heat.get("evidence"):
        kinds = {
            "github_trending": "进入 GitHub Trending",
            "release": "发布重要版本",
            "official_launch": "完成官方发布",
            "major_update": "发布重大更新",
        }
        signals = [
            kinds.get(row.get("kind"), "出现新的社区热度信号")
            for row in heat["evidence"]
        ]
        hot_reason = f"项目本周{'、'.join(dict.fromkeys(signals))}。"
    use_case = str(candidate.get("use_case") or card.get("summary") or "").strip()
    summary = str(
        candidate.get("editorial_summary")
        or card.get("recommendation")
        or card.get("summary")
        or ""
    ).strip()
    if summary and len(summary) < 40 and use_case and use_case not in summary:
        summary = f"{use_case}{summary}"
    return {
        "hot_reason": hot_reason,
        "hot_reason_evidence": list(heat.get("evidence") or []),
        "use_case": use_case,
        "summary": summary,
    }


def derive_weekly_editorial(selected):
    category_groups = {}
    for item in selected:
        category_groups.setdefault(str(item.get("category") or "其他"), []).append(item)
    dominant = max(category_groups.values(), key=len, default=[])
    has_theme = len(dominant) >= 3
    theme = str(dominant[0].get("category") or "") if has_theme else ""
    return {
        "opening_mode": "theme" if has_theme else "multiple_routes",
        "weekly_theme": theme,
        "theme_evidence": [
            {
                "repo": item["repo"],
                "hot_reason": item["editorial"]["hot_reason"],
                "evidence": item["editorial"]["hot_reason_evidence"],
            }
            for item in dominant
        ] if has_theme else [],
        "title_options": [
            f"这周突然走红的 {len(selected)} 个开源项目",
            f"本周开源坐标：{len(selected)} 个项目正在解决的新问题",
            f"从新爆款到成熟工具：本周值得关注的 {len(selected)} 个项目",
        ],
        "editorial_angles": [
            item["editorial"]["use_case"] for item in selected[:3]
            if item["editorial"]["use_case"]
        ],
        "closing_observations": [
            item["editorial"]["summary"] for item in selected[:3]
            if item["editorial"]["summary"]
        ],
    }
