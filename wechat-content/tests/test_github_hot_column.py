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
        item["reader_card"]["original_description"] = "Original project description from GitHub."
        item["reader_card"]["translated_description"] = "来自 GitHub 的官方项目描述。"
        item["reader_card"]["summary"] = "编辑概况：这个项目适合观察自动化流程。"
        item["reader_card"]["recommendation"] = "一句话推荐：它把复杂工具变成更容易试用的流程。"
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


def payload_realistic_routes():
    payload = payload_ten()
    labels = ["AI 与情报看板", "开发者资源", "AI Agent 学习", "路线优化", "电商与履约"]
    for index, item in enumerate(payload["items"]):
        item["reader_card"]["category_label"] = labels[index % len(labels)]
    payload["editorial"]["editorial_angles"] = [
        "一个把新闻聚合、地缘监测和基础设施追踪放在同一界面的实时态势看板。",
        "面向 ADHD 开发者和创作者的工具、方法与资源清单。",
        "一本系统讲解 AI Agent 设计原理和工程实践的开源书。",
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
        self.assertIn("如果只收藏三个", article)

    def test_weekly_github_template_renders_exactly_ten_ranked_projects(self):
        article, title, summary = COLUMN.build_article(payload_ten())
        self.assertEqual(title, "本周 GitHub 热门：10 个正在变火的开源项目")
        self.assertIn("按 GitHub 周榜顺序整理", article)
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

    def test_description_uses_github_translated_description_not_editorial_summary(self):
        article, _, _ = COLUMN.build_article(payload_five())
        self.assertIn("**描述：** 来自 GitHub 的官方项目描述。", article)
        self.assertIn("> **一句话概况**　一句话推荐：它把复杂工具变成更容易试用的流程。", article)
        self.assertNotIn("**描述：** Original project description from GitHub.", article)
        self.assertNotIn("**描述：** 编辑概况：这个项目适合观察自动化流程。", article)

    def test_description_uses_faithful_chinese_translation_instead_of_original_or_recommendation(self):
        payload = payload_five()
        payload["items"][0]["reader_card"]["original_description"] = (
            "A curated list of ADHD-specific tools, apps, strategies, and resources for developers and makers."
        )
        payload["items"][0]["reader_card"]["translated_description"] = "ADHD 相关工具、应用、方法和资源清单，面向开发者和创作者整理。"
        article, _, _ = COLUMN.build_article(payload)
        self.assertIn(
            "**描述：** ADHD 相关工具、应用、方法和资源清单，面向开发者和创作者整理。",
            article,
        )
        self.assertNotIn("**描述：** A curated list of ADHD-specific tools", article)
        self.assertNotIn("**描述：** 一句话推荐", article)

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
        self.assertIn("GitHub 热榜有点分裂", article)
        self.assertNotIn("共同趋势是", article)

    def test_github_hot_reader_copy_has_no_template_or_audit_language(self):
        article, _, _ = COLUMN.build_article(payload_ten())
        forbidden = (
            "不写成冷冰冰",
            "只保留读者",
            "机械采集",
            "采集过程",
            "审核过程",
            "模板",
            "生成",
            "官方描述、数据、亮点、适合谁和项目地址",
        )
        for phrase in forbidden:
            self.assertNotIn(phrase, article)

    def test_multiple_routes_opening_is_specific_and_reader_facing(self):
        article, _, _ = COLUMN.build_article(payload_ten())
        self.assertIn("GitHub 热榜有点分裂", article)
        self.assertIn("AI 工具", article)
        self.assertIn("开发者工具", article)
        self.assertIn("你不一定都要试", article)
        self.assertIn("马上试用的工具", article)
        self.assertIn("系统学习的资料", article)
        self.assertIn("当前工作最接近", article)

    def test_opening_avoids_flat_report_language(self):
        article, _, _ = COLUMN.build_article(payload_ten())
        opening = article.split("<!-- github-opening:start -->", 1)[1].split("<!-- github-opening:end -->", 1)[0]
        self.assertIn("本周开源雷达", opening)
        self.assertIn("先看它解决什么问题", opening)
        self.assertNotIn("这期留下", opening)
        self.assertNotIn("数字让项目被看见", opening)

    def test_opening_uses_short_route_labels_instead_of_long_project_descriptions(self):
        article, _, _ = COLUMN.build_article(payload_realistic_routes())
        self.assertIn("AI 与情报看板", article)
        self.assertIn("开发者资源", article)
        self.assertIn("AI Agent 学习", article)
        self.assertNotIn("一个把新闻聚合、地缘监测和基础设施追踪放在同一界面的实时态势看板。；", article)

    def test_theme_opening_does_not_force_mixed_projects_into_one_narrow_theme(self):
        payload = payload_realistic_routes()
        payload["editorial"]["opening_mode"] = "theme"
        payload["editorial"]["weekly_theme"] = "AI 与情报看板"
        payload["editorial"]["theme_evidence"] = [{"repo": item["repo"]} for item in payload["items"][:3]]
        article, _, _ = COLUMN.build_article(payload)
        opening = article.split("<!-- github-opening:start -->", 1)[1].split("<!-- github-opening:end -->", 1)[0]
        self.assertIn("几条不同路线", opening)
        self.assertIn("AI 与情报看板", opening)
        self.assertIn("开发者资源", opening)
        self.assertIn("AI Agent 学习", opening)
        self.assertNotIn("同一个问题：AI 与情报看板", opening)

    def test_all_opening_variants_avoid_old_flat_report_phrases(self):
        payload = payload_realistic_routes()
        payload["editorial"]["opening_mode"] = "theme"
        payload["editorial"]["weekly_theme"] = "AI 与情报看板"
        payload["editorial"]["theme_evidence"] = [{"repo": item["repo"]} for item in payload["items"][:3]]

        openings = ["\n".join(value) for value in COLUMN.build_opening_variants(payload)]
        for opening in openings:
            self.assertIn("几条", opening)
            self.assertNotIn("同一条路线", opening)
            self.assertNotIn("都在尝试", opening)
            self.assertNotIn("这期留下", opening)
            self.assertNotIn("数字让项目被看见", opening)

    def test_closing_gives_specific_collection_choices(self):
        article, _, _ = COLUMN.build_article(payload_ten())
        self.assertIn("如果只收藏三个", article)
        self.assertIn("马上试用", article)
        self.assertIn("系统学习", article)
        self.assertIn("当前工作最接近", article)
        self.assertNotIn("没有一条可以概括所有项目的主线", article)
        self.assertNotIn("资料型项目，试用工具型项目", article)

    def test_closing_uses_issue_level_observation_not_first_project_pitch(self):
        payload = payload_realistic_routes()
        payload["editorial"]["closing_observations"] = [
            "如果你关注新闻、地缘事件或 OSINT 工作流，它像是一张可以继续深挖的实时观察地图。"
        ]
        article, _, _ = COLUMN.build_article(payload)
        closing = article.split("<!-- github-closing:start -->", 1)[1]
        self.assertIn("这期更像一组分岔路", closing)
        self.assertNotIn("实时观察地图", closing)

    def test_closing_never_uses_english_project_description_as_reflection(self):
        payload = payload_ten()
        payload["editorial"]["closing_observations"] = [
            "A hive mind communication platform，它把群体智能放进通信平台。"
        ]
        article, _, _ = COLUMN.build_article(payload)
        closing = article.split("<!-- github-closing:start -->", 1)[1]
        self.assertNotIn("A hive mind communication platform", closing)
        self.assertIn("真正值得留下来的", closing)

    def test_approved_visual_candidate_is_used_without_external_project_dir(self):
        payload = payload_ten()
        payload["items"][0]["visual_candidates"] = [
            {
                "type": "official_screenshot",
                "url": "https://raw.githubusercontent.com/example/project/main/docs/demo.png",
                "usage_status": "approved",
                "license_status": "verified",
                "is_real_interface": True,
                "verified_at": "2026-07-30T09:00:00+08:00",
            }
        ]
        records = VISUALS.select_project_images(
            payload,
            project_image_dir=None,
            image_input_dir=None,
            image_mode="auto",
            maximum_bytes=4_000_000,
        )
        self.assertEqual(records[0]["image_mode"], "official_verified")
        self.assertEqual(
            records[0]["source_url"],
            "https://raw.githubusercontent.com/example/project/main/docs/demo.png",
        )

    def test_project_without_usable_image_does_not_render_local_card_reference(self):
        payload = payload_ten()
        payload["items"][0]["_project_image"] = {
            "image_mode": "omitted",
            "fallback_reason": "no_usable_project_image",
        }
        article, _, _ = COLUMN.build_article(payload)
        first_project = article.split("<!-- github-project:start -->", 1)[1].split("<!-- github-project:end -->", 1)[0]
        self.assertNotIn("images/项目-01.png", first_project)
        self.assertNotIn("项目用途视觉", first_project)

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
        self.assertIn("换个角度看", article)


if __name__ == "__main__":
    unittest.main()
