import importlib.util
import json
import unittest
from copy import deepcopy
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "github_hot_column", SKILL / "scripts/github_hot_column.py"
)
COLUMN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLUMN)
VISUAL_SPEC = importlib.util.spec_from_file_location(
    "github_hot_visuals", SKILL / "scripts/github_hot_visuals.py"
)
VISUALS = importlib.util.module_from_spec(VISUAL_SPEC)
VISUAL_SPEC.loader.exec_module(VISUALS)
RENDERING_SPEC = importlib.util.spec_from_file_location(
    "github_hot_rendering", SKILL / "scripts/rendering.py"
)
RENDERING = importlib.util.module_from_spec(RENDERING_SPEC)
RENDERING_SPEC.loader.exec_module(RENDERING)


def payload_five(theme=True):
    base = json.loads(
        (SKILL / "tests/fixtures/github-hot-content-package-v2.json").read_text(encoding="utf-8")
    )
    items = []
    categories = ["ai-agent", "ai-agent", "ai-agent", "developer-tools", "data"]
    for index, category in enumerate(categories, 1):
        item = deepcopy(base["items"][0])
        item["rank"] = index
        item["repo"] = f"example/project-{index}"
        item["official_url"] = f"https://github.com/example/project-{index}"
        item["category"] = category if theme else f"route-{index}"
        item["reader_card"]["name"] = f"project-{index}"
        item["reader_card"]["category_label"] = "AI Agent" if index <= 3 else "开发工具"
        item["reader_card"]["metrics"]["weekly_stars"] = 1800 - index * 100
        item["heat"] = {
            "eligible": True,
            "heat_class": "new_breakout",
            "evidence": [{"kind": "github_trending", "url": item["official_url"], "observed_at": "2026-07-26T08:00:00+08:00"}],
            "rejection_reasons": [],
        }
        item["editorial"] = {
            "hot_reason": f"project-{index} 发布完整示例后进入本周 GitHub Trending。",
            "hot_reason_evidence": item["heat"]["evidence"],
            "use_case": "帮助开发者把复杂工具变成可复用的工作流程。",
            "summary": "如果你正在整理自动化流程，这个项目提供了从理解问题到完成配置的清晰路径，并附有可以验证的示例。",
        }
        item["_project_image"] = {"image_mode": "official_verified"}
        items.append(item)
    base["items"] = items
    base["selection"]["selected_count"] = 5
    base["editorial"] = {
        "opening_mode": "theme" if theme else "multiple_routes",
        "weekly_theme": "ai-agent" if theme else "",
        "theme_evidence": [
            {"repo": item["repo"], "hot_reason": item["editorial"]["hot_reason"]}
            for item in items[:3]
        ] if theme else [],
        "title_options": [
            "这周突然走红的 5 个开源项目：Agent 开始走出 Demo",
            "5 个本周新爆款，正在把复杂工具变简单",
            "本周开源坐标：从 Agent 到开发工具",
        ],
        "editorial_angles": [item["editorial"]["use_case"] for item in items[:3]],
        "closing_observations": [item["editorial"]["summary"] for item in items[:3]],
    }
    return base


def payload_ten():
    payload = payload_five(theme=False)
    first = deepcopy(payload["items"][0])
    items = []
    for index in range(1, 11):
        item = deepcopy(first)
        item["rank"] = index
        item["repo"] = f"example/project-{index:02d}"
        item["official_url"] = f"https://github.com/example/project-{index:02d}"
        item["reader_card"]["name"] = f"project-{index:02d}"
        item["reader_card"]["summary"] = f"project-{index:02d} helps developers understand a weekly trending repository."
        item["reader_card"]["metrics"]["stars"] = 7000 + index
        item["reader_card"]["metrics"]["weekly_stars"] = 500 + index
        item["reader_card"]["metrics"]["forks"] = 900 + index
        item["_project_image"] = {"image_mode": "official_verified"}
        items.append(item)
    payload["items"] = items
    payload["selection"]["selected_count"] = 10
    payload["editorial"]["title_options"] = []
    payload["editorial"]["editorial_angles"] = [
        "AI 工具继续降低试用门槛",
        "开发者工具强调本地可控",
        "数据与监控项目仍有热度",
    ]
    payload["editorial"]["closing_observations"] = [
        "这 10 个项目各自解决不同问题，适合先按需求收藏，再挑一个真正试用。"
    ]
    return payload


class GithubHotColumnTests(unittest.TestCase):
    def test_theme_is_selected_from_content_and_is_repeatable(self):
        payload = payload_five()
        families = {
            "ai_automation": {"primary": "#102A43", "accent": "#1FB6C9", "background": "#F5FAFD"},
            "developer_tools": {"primary": "#102A43", "accent": "#1FA87A", "background": "#F5FBF8"},
            "creative_tools": {"primary": "#102A43", "accent": "#F28C45", "background": "#FFF9F4"},
            "systems_data": {"primary": "#243746", "accent": "#D99A2B", "background": "#FFFAF0"},
            "mixed_default": {"primary": "#102A43", "accent": "#2D9B72", "background": "#F7FBF9"},
        }
        first = VISUALS.select_theme(payload, families)
        second = VISUALS.select_theme(payload, families)
        self.assertEqual(first, second)
        self.assertEqual(first["family"], "ai_automation")

    def test_article_has_dynamic_opening_five_projects_and_reflective_closing(self):
        payload = payload_five()
        article, title, _ = COLUMN.build_article(payload)
        self.assertNotEqual(title, "本周 GitHub 热门：5 个值得关注的开源项目")
        self.assertIn(payload["editorial"]["theme_evidence"][0]["repo"], article)
        self.assertEqual(article.count("<!-- github-project:start -->"), 5)
        self.assertIn("最后留一个坐标", article)

    def test_weekly_github_template_renders_exactly_ten_ranked_projects(self):
        article, title, summary = COLUMN.build_article(payload_ten())
        self.assertEqual(title, "本周 GitHub 热门：10 个正在变火的开源项目")
        self.assertIn("从 GitHub 周榜前 10 个项目看", article)
        self.assertEqual(article.count("<!-- github-project:start -->"), 10)
        self.assertIn("## 01 · project-01", article)
        self.assertIn("## 10 · project-10", article)
        self.assertIn("**项目地址：** [https://github.com/example/project-10](https://github.com/example/project-10)", article)
        self.assertIn("10 个项目", summary)

    def test_project_uses_approved_editorial_card_order(self):
        article, _, _ = COLUMN.build_article(payload_five())
        positions = [
            article.index("描述"),
            article.index("项目官方截图"),
            article.index("一句话概况"),
            article.index("重点内容"),
            article.index("适合谁"),
            article.index("项目地址"),
        ]
        self.assertEqual(positions, sorted(positions))

    def test_project_uses_compact_reader_fields(self):
        article, _, _ = COLUMN.build_article(payload_five())
        for phrase in ("**描述：**", "**一句话概况**", "**重点内容**", "**适合谁？**", "**项目地址：**"):
            self.assertIn(phrase, article)
        self.assertNotIn("**为什么这周火？**", article)
        self.assertNotIn("**上手条件：**", article)

    def test_project_address_shows_full_github_url(self):
        article, _, _ = COLUMN.build_article(payload_five())
        self.assertIn(
            "**项目地址：** [https://github.com/example/project-1](https://github.com/example/project-1)",
            article,
        )
        self.assertNotIn(
            "**项目地址：** [example/project-1](https://github.com/example/project-1)",
            article,
        )

    def test_reader_copy_omits_audit_burden(self):
        article, _, _ = COLUMN.build_article(payload_five())
        for phrase in ("未发现明确许可证", "license_status", "verified_at", "内部审核"):
            self.assertNotIn(phrase, article)

    def test_missing_common_theme_uses_multiple_routes_copy(self):
        article, _, _ = COLUMN.build_article(payload_five(theme=False))
        self.assertIn("几条不同路线", article)
        self.assertNotIn("共同趋势是", article)

    def test_external_audit_contains_theme_rejections_and_verification(self):
        payload = payload_five()
        payload["candidates"] = [{
            "repo": "example/rejected",
            "selected": False,
            "rejection_reasons": ["本周热度证据不足"],
        }]
        for item in payload["items"]:
            item["_project_image"] = {
                "image_mode": "local_project_visual",
                "license_status": "not_applicable",
                "usage_status": "not_applicable",
            }
        panel = RENDERING.build_editor_review_panel(
            payload,
            {"review_counts": {"verified": 0, "partial": 0, "unverified": 0}},
        )
        for phrase in ("本期主题证据", "未入选项目", "许可证核验", "图片审核", "本周热度证据不足"):
            self.assertIn(phrase, panel)

    def test_recent_opening_and_closing_hashes_select_fresh_variants(self):
        payload = payload_five()
        default_opening = "\n\n".join(COLUMN.build_opening(payload))
        default_closing = "\n\n".join(COLUMN.build_closing(payload))
        article, _, _ = COLUMN.build_article(
            payload,
            history={
                "opening_hashes": [COLUMN.hash_text(default_opening)],
                "closing_hashes": [COLUMN.hash_text(default_closing)],
            },
        )
        self.assertNotIn(default_opening, article)
        self.assertNotIn(default_closing, article)
        self.assertIn("本周突然升温", article)


if __name__ == "__main__":
    unittest.main()
