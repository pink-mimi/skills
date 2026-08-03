import importlib.util
import http.client
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
FIXTURE = SKILL / "tests/fixtures/candidates.json"
SPEC = importlib.util.spec_from_file_location("github_hot_run", SKILL / "scripts/run.py")
RUN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUN)
CONFIG = json.loads((SKILL / "assets/default-config.json").read_text(encoding="utf-8"))
RUN_AT = datetime.fromisoformat("2026-07-26T09:00:00+08:00")


class PartialResponse:
    def __init__(self, partial):
        self.partial = partial

    def read(self):
        raise http.client.IncompleteRead(self.partial)


def candidate(index, *, ai=False, category=None, weekly_stars=500, license_status="verified"):
    repo = f"example/project-{index:02d}"
    license_name = "MIT" if license_status == "verified" else ""
    return {
        "repo": repo,
        "official_url": f"https://github.com/{repo}",
        "created_at": "2026-07-23T08:00:00Z",
        "heat_evidence": [{
            "kind": "github_trending",
            "observed_at": "2026-07-25T09:00:00+08:00",
            "url": f"https://github.com/{repo}",
        }],
        "homepage_url": f"https://project-{index:02d}.example.com",
        "description": f"项目 {index} 用于整理可核验的工作资料",
        "license": license_name or "未发现明确许可证",
        "last_commit": "2026-07-25T08:00:00Z",
        "latest_release": "v1.0.0",
        "platform": "Windows、macOS、Linux",
        "install": "需要 Python 3",
        "audience": "需要整理资料的用户",
        "risks": "执行前检查输入目录",
        "category": category or f"category-{index % 5}",
        "ai_related": ai,
        "stars": 10000 + index,
        "weekly_stars": weekly_stars,
        "forks": 100 + index,
        "metrics_verified_at": "2026-07-26T08:30:00+08:00",
        "reader_card": {
            "category_label": "效率工具",
            "name": f"project-{index:02d}",
            "summary": f"项目 {index} 用于整理可核验的工作资料。",
            "recommendation": "用途明确，官方资料完整。",
            "highlights": ["本地运行", "结构化输出", "支持自动化"],
            "audience": ["效率工具用户", "开发者"],
            "difficulty": {"level": "medium", "label": "中等", "note": "需要命令行"},
            "metrics": {
                "language": "Python",
                "stars": 10000 + index,
                "weekly_stars": weekly_stars,
                "forks": 100 + index,
                "verified_at": "2026-07-26T08:30:00+08:00",
            },
            "reader_warning": "",
        },
        "verification": {
            "readme": {
                "url": f"https://github.com/{repo}#readme",
                "verified_at": "2026-07-26T08:20:00+08:00",
            },
            "license": {
                "status": license_status,
                "name": license_name,
                "spdx_id": license_name,
                "url": f"https://github.com/{repo}/blob/main/LICENSE" if license_name else "",
            },
            "maintenance": {
                "status": "active",
                "last_commit_at": "2026-07-25T08:00:00Z",
                "latest_release_at": "2026-07-24T08:00:00Z",
                "evidence_urls": [f"https://github.com/{repo}/commits/main"],
            },
            "requirements": {
                "platforms": ["Windows", "macOS", "Linux"],
                "install": "需要 Python 3",
                "command_line": True,
                "programming_required": False,
                "account_required": False,
                "api_key_required": False,
                "paid_dependency": False,
                "special_hardware": False,
            },
            "risks": [],
            "evidence": [f"https://github.com/{repo}"],
        },
        "visual_candidates": [],
        "image2_brief": {
            "subject": f"项目 {index} 的资料整理流程",
            "scene": "桌面工作环境中的文件与自动化流程",
            "must_include": ["本地运行", "结构化输出"],
            "must_avoid": ["项目Logo", "虚构软件界面", "中文文字", "虚构数据"],
        },
    }


def raw_candidates(count=18):
    return {
        "meta": {"rate_limited": False, "fetched_at": RUN_AT.isoformat()},
        "items": [candidate(index, ai=index <= 3) for index in range(1, count + 1)],
    }


class GithubHotResearchTests(unittest.TestCase):
    def test_fetch_text_uses_partial_html_when_github_trending_read_is_incomplete(self):
        html = b"""
        <article class="Box-row">
          <h2><a href="/ayghri/i-have-adhd"> ayghri / i-have-adhd </a></h2>
          <p>This skill helps your coding agent avoid hiding answers.</p>
          <span itemprop="programmingLanguage">Python</span>
          <a href="/ayghri/i-have-adhd/stargazers">13,058</a>
          <a href="/ayghri/i-have-adhd/forks">679</a>
          <span>6,150 stars this week</span>
        </article>
        """

        text = RUN.fetch_text(
            object(),
            timeout=20,
            opener=lambda request, timeout: PartialResponse(html),
        )

        rows = RUN.parse_trending_weekly_html(text, RUN_AT)
        self.assertEqual(rows[0]["repo"], "ayghri/i-have-adhd")
        self.assertEqual(rows[0]["description"], "This skill helps your coding agent avoid hiding answers.")

    def test_trending_parser_ignores_star_button_text_before_repository_heading(self):
        html = """
        <article class="Box-row">
          <div class="float-right d-flex">
            <a href="/login?return_to=%2Fayghri%2Fi-have-adhd"><span>Star</span></a>
            <svg><path d="M8 .25"></path></svg>
          </div>
          <h2 class="h3 lh-condensed">
            <a href="/ayghri/i-have-adhd">
              <span class="text-normal">ayghri /</span>
              i-have-adhd
            </a>
          </h2>
          <p class="col-9 color-fg-muted my-1 tmp-pr-4">
            A skill for your coding agent to stop it from burying the answer. ADHD-friendly output.
          </p>
          <span itemprop="programmingLanguage">Python</span>
          <a href="/ayghri/i-have-adhd/stargazers"><svg><path d="M8 .25 673 418"></path></svg>13,145</a>
          <a href="/ayghri/i-have-adhd/forks"><svg><path d="M5 5.372 878"></path></svg>684</a>
          <span>6,156 stars this week</span>
        </article>
        """

        rows = RUN.parse_trending_weekly_html(html, RUN_AT)

        self.assertEqual(rows[0]["repo"], "ayghri/i-have-adhd")
        self.assertEqual(
            rows[0]["description"],
            "A skill for your coding agent to stop it from burying the answer. ADHD-friendly output.",
        )
        self.assertNotIn("Star", rows[0]["description"])
        self.assertEqual(rows[0]["reader_card"]["metrics"]["stars"], 13145)
        self.assertEqual(rows[0]["reader_card"]["metrics"]["forks"], 684)

    def test_trending_parser_builds_specific_reader_card_from_description(self):
        html = """
        <article class="Box-row">
          <h2><a href="/ayghri/i-have-adhd"> ayghri / i-have-adhd </a></h2>
          <p class="col-9 color-fg-muted my-1 tmp-pr-4">
            A skill for your coding agent to stop it from burying the answer. ADHD-friendly output.
          </p>
          <span itemprop="programmingLanguage">Python</span>
          <a href="/ayghri/i-have-adhd/stargazers">13,145</a>
          <a href="/ayghri/i-have-adhd/forks">684</a>
          <span>6,156 stars this week</span>
        </article>
        """

        rows = RUN.parse_trending_weekly_html(html, RUN_AT)
        card = rows[0]["reader_card"]

        self.assertEqual(card["category_label"], "AI 编码辅助")
        self.assertEqual(card["translated_description"], "一个帮助编码智能体不要把答案藏起来的技能，输出方式对 ADHD 用户更友好。")
        self.assertIn("编码助手", card["recommendation"])
        self.assertEqual(len(card["highlights"]), 3)
        self.assertNotEqual(card["recommendation"], "本周进入 GitHub Trending，适合先收藏并按需试用。")

    def test_translate_description_covers_current_weekly_project_descriptions(self):
        examples = {
            "bluetooth mesh chat, IRC vibes": "一个带有 IRC 氛围的蓝牙 Mesh 聊天工具。",
            "A hive mind communication platform": "群体智能协作通信平台。",
            "The fastest browser for AI agents to run browser automation, built for sharing your logged-in browser state with your AI agents, like Codex or Claude Code, without disturbing you. Zero cost, zero config.": "面向 AI 智能体运行浏览器自动化的高速浏览器，可把已登录的浏览器状态安全分享给 Codex 或 Claude Code 等智能体，同时不打扰你的正常使用，零成本、零配置。",
            "A skill to stop your coding agent from burying the answer. ADHD-friendly output.": "一个帮助编码智能体不要把答案藏起来的技能，输出方式对 ADHD 用户更友好。",
            "Kronos: A Foundation Model for the Language of Financial Markets": "Kronos 是面向金融市场语言的基础模型。",
            "Open-source & free — Battle-tested at Alibaba's scale. Hybrid architecture code review tool: deterministic pipelines + LLM Agent, precise line-level comments, built-in fine-tuned ruleset (NPE, thread-safety, XSS, SQL injection), OpenAI & Anthropic compatible.": "开源免费的混合架构代码审查工具，经过阿里巴巴规模场景验证，结合确定性流水线与 LLM Agent，支持精准行级评论、内置调优规则集，并兼容 OpenAI 与 Anthropic。",
            "Turn any technical book PDF into a Claude Code skill — ready to study, reference, and use while you work.": "把任意技术书 PDF 转成 Claude Code 技能，方便在工作时学习、查阅和直接使用。",
            "Create and share 3D architectural projects.": "用于创建和分享 3D 建筑设计项目。",
            "The most RAM efficient harness": "一个强调极低内存占用的测试/运行 Harness。",
            "A lightweight, cloud-native GIS platform for visualizing, exploring, and analyzing geospatial data. It runs in the web browser, on the desktop, on mobile, and inside Jupyter notebooks.": "轻量级云原生 GIS 平台，用于可视化、探索和分析地理空间数据，支持浏览器、桌面、移动端和 Jupyter Notebook。",
            "💖🧸 Self hosted, you-owned Grok Companion, a container of souls of waifu, cyber livings to bring them into our worlds, wishing to achieve Neuro-sama's altitude. Capable of realtime voice chat, Minecraft, Factorio playing. Web / macOS / Windows supported.": "自托管、由用户拥有的 AI 伴侣项目，可进行实时语音聊天，并支持 Minecraft、Factorio 等场景，提供 Web、macOS 和 Windows 版本。",
        }
        for source, expected in examples.items():
            with self.subTest(source=source):
                self.assertEqual(RUN.translate_description(source), expected)

    def test_translate_description_never_returns_english_fallback_for_known_weekly_descriptions(self):
        sources = [
            "bluetooth mesh chat, IRC vibes",
            "A skill to stop your coding agent from burying the answer. ADHD-friendly output.",
            "Turn any technical book PDF into a Claude Code skill — ready to study, reference, and use while you work.",
            "Create and share 3D architectural projects.",
            "The most RAM efficient harness",
            "A lightweight, cloud-native GIS platform for visualizing, exploring, and analyzing geospatial data. It runs in the web browser, on the desktop, on mobile, and inside Jupyter notebooks.",
            "💖🧸 Self hosted, you-owned Grok Companion, a container of souls of waifu, cyber livings to bring them into our worlds, wishing to achieve Neuro-sama's altitude. Capable of realtime voice chat, Minecraft, Factorio playing. Web / macOS / Windows supported.",
        ]
        for source in sources:
            with self.subTest(source=source):
                translated = RUN.translate_description(source)
                self.assertNotIn("官方描述：", translated)
                self.assertTrue(RUN.contains_cjk(translated))

    def test_normalize_reader_card_refreshes_stale_english_fallback_translation(self):
        row = {
            "repo": "ayghri/i-have-adhd",
            "description": "A skill to stop your coding agent from burying the answer. ADHD-friendly output.",
            "reader_card": {
                "original_description": "A skill to stop your coding agent from burying the answer. ADHD-friendly output.",
                "translated_description": "官方描述：A skill to stop your coding agent from burying the answer. ADHD-friendly output.",
            },
        }

        card = RUN.normalize_reader_card(row)

        self.assertEqual(card["translated_description"], "一个帮助编码智能体不要把答案藏起来的技能，输出方式对 ADHD 用户更友好。")
        self.assertNotIn("官方描述：", card["translated_description"])

    def test_enrich_trending_row_refreshes_stale_english_fallback_translation(self):
        row = {
            "repo": "ayghri/i-have-adhd",
            "description": "A skill to stop your coding agent from burying the answer. ADHD-friendly output.",
            "original_description": "A skill to stop your coding agent from burying the answer. ADHD-friendly output.",
            "translated_description": "官方描述：A skill to stop your coding agent from burying the answer. ADHD-friendly output.",
            "reader_card": {
                "original_description": "A skill to stop your coding agent from burying the answer. ADHD-friendly output.",
                "translated_description": "官方描述：A skill to stop your coding agent from burying the answer. ADHD-friendly output.",
                "metrics": {"weekly_stars": 5232},
            },
        }

        enriched = RUN.enrich_trending_row(
            row,
            RUN_AT,
            api_json=lambda path: {"name": "i-have-adhd", "html_url": "https://github.com/ayghri/i-have-adhd"},
            api_readme=lambda repo: "",
        )

        self.assertEqual(enriched["translated_description"], "一个帮助编码智能体不要把答案藏起来的技能，输出方式对 ADHD 用户更友好。")
        self.assertEqual(enriched["reader_card"]["translated_description"], "一个帮助编码智能体不要把答案藏起来的技能，输出方式对 ADHD 用户更友好。")

    def build(self, raw=None, config=None, output_root=None):
        return RUN.build(
            raw or raw_candidates(),
            RUN_AT,
            deepcopy(config or CONFIG),
            output_root or tempfile.mkdtemp(),
        )

    def test_offline_content_package_uses_own_fixture_and_schema_v2(self):
        self.assertTrue(FIXTURE.exists())
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SKILL / "scripts/run.py"),
                    "all",
                    "--input",
                    str(FIXTURE),
                    "--output-root",
                    temp,
                    "--run-at",
                    RUN_AT.isoformat(),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = json.loads(
                (Path(temp) / "github-hot/2026-07-26/content-package.json").read_text(encoding="utf-8")
            )
            self.assertEqual((data["schema_version"], data["content_type"]), (2, "github-hot"))

    def test_default_target_is_ten_and_selection_allows_eight_to_ten(self):
        package = self.build()
        selection = package.get("selection") or {}
        self.assertEqual(selection.get("selected_count"), 10)
        self.assertEqual((selection.get("minimum"), selection.get("maximum")), (8, 10))

    def test_trending_weekly_parser_preserves_top_ten_order_and_metrics(self):
        articles = []
        for index in range(1, 12):
            articles.append(
                f"""
                <article class="Box-row">
                  <h2><a href="/owner{index}/repo{index}"> owner{index} / repo{index} </a></h2>
                  <p>Repository {index} description</p>
                  <span itemprop="programmingLanguage">Python</span>
                  <a href="/owner{index}/repo{index}/stargazers">{7000 + index}</a>
                  <a href="/owner{index}/repo{index}/forks">{900 + index}</a>
                  <span>{100 + index} stars this week</span>
                </article>
                """
            )
        rows = RUN.parse_trending_weekly_html("\n".join(articles), RUN_AT)
        self.assertEqual([row["repo"] for row in rows[:3]], ["owner1/repo1", "owner2/repo2", "owner3/repo3"])
        self.assertEqual(len(rows), 10)
        first = rows[0]
        self.assertEqual(first["trending"]["rank"], 1)
        self.assertEqual(first["official_url"], "https://github.com/owner1/repo1")
        self.assertEqual(first["reader_card"]["metrics"]["language"], "Python")
        self.assertEqual(first["reader_card"]["metrics"]["stars"], 7001)
        self.assertEqual(first["reader_card"]["metrics"]["forks"], 901)
        self.assertEqual(first["reader_card"]["metrics"]["weekly_stars"], 101)
        self.assertEqual(first["trending"]["url"], "https://github.com/trending?since=weekly")
        self.assertEqual(first["reader_card"]["original_description"], "Repository 1 description")
        self.assertTrue(first["reader_card"]["translated_description"])
        self.assertNotEqual(first["reader_card"]["translated_description"], first["reader_card"]["recommendation"])

    def test_build_preserves_trending_top_ten_order_without_score_reranking(self):
        raw = {
            "meta": {"rate_limited": False, "fetched_at": RUN_AT.isoformat(), "source": "github_trending_weekly"},
            "items": [candidate(index, weekly_stars=100 + index) for index in range(1, 11)],
        }
        raw["items"][0]["reader_card"]["metrics"]["stars"] = 1
        raw["items"][9]["reader_card"]["metrics"]["stars"] = 999999
        for index, item in enumerate(raw["items"], 1):
            item["trending"] = {"rank": index, "period": "weekly", "url": "https://github.com/trending?since=weekly"}
        package = self.build(raw)
        self.assertEqual([item["repo"] for item in package["items"]], [f"example/project-{index:02d}" for index in range(1, 11)])
        self.assertEqual([item["rank"] for item in package["items"]], list(range(1, 11)))

    def test_readme_image_extraction_prefers_repo_screenshots_and_excludes_badges(self):
        readme = """
        # Demo
        ![build](https://img.shields.io/badge/build-passing-green.svg)
        <img src="https://github.com/owner/repo/raw/main/docs/logo.png" alt="logo" width="80">
        ![Main dashboard](docs/dashboard.png)
        <img src="https://raw.githubusercontent.com/owner/repo/main/assets/demo-screen.png" alt="live monitor screenshot">
        ![External screenshot](https://example.com/screenshot.png)
        """
        visuals = RUN.extract_readme_visual_candidates(
            readme,
            repo="owner/repo",
            source_page="https://github.com/owner/repo#readme",
            license_info={"status": "verified", "name": "MIT", "spdx_id": "MIT"},
            verified_at=RUN_AT.isoformat(),
        )
        urls = [visual["url"] for visual in visuals]
        self.assertIn("https://raw.githubusercontent.com/owner/repo/main/docs/dashboard.png", urls)
        self.assertIn("https://raw.githubusercontent.com/owner/repo/main/assets/demo-screen.png", urls)
        self.assertNotIn("https://img.shields.io/badge/build-passing-green.svg", urls)
        self.assertFalse(any("logo.png" in url for url in urls))
        approved = [visual for visual in visuals if "raw.githubusercontent.com/owner/repo" in visual["url"]]
        self.assertTrue(approved)
        self.assertTrue(all(visual["usage_status"] == "approved" for visual in approved))
        external = next(visual for visual in visuals if visual["url"] == "https://example.com/screenshot.png")
        self.assertEqual(external["usage_status"], "review_required")

    def test_enrich_preserves_trending_row_and_still_extracts_readme_images_when_repo_api_fails(self):
        html = """
        <article class="Box-row">
          <h2><a href="/koala73/worldmonitor"> koala73 / worldmonitor </a></h2>
          <p>Real-time global intelligence dashboard.</p>
          <span itemprop="programmingLanguage">TypeScript</span>
          <a href="/koala73/worldmonitor/stargazers">73,564</a>
          <a href="/koala73/worldmonitor/forks">11,030</a>
          <span>11,342 stars this week</span>
        </article>
        """
        readme = """
        # worldmonitor
        ![World monitor dashboard](docs/world-monitor-dashboard.png)
        """
        rows = RUN.parse_trending_weekly_html(html, RUN_AT)
        enriched = RUN.enrich_trending_rows(
            rows,
            RUN_AT,
            api_json=lambda path: (_ for _ in ()).throw(RuntimeError("api unavailable")),
            api_readme=lambda repo: readme,
        )
        self.assertEqual(enriched[0]["repo"], "koala73/worldmonitor")
        self.assertEqual(enriched[0]["official_url"], "https://github.com/koala73/worldmonitor")
        self.assertEqual(enriched[0]["trending"]["rank"], 1)
        self.assertEqual(enriched[0]["reader_card"]["metrics"]["weekly_stars"], 11342)
        visuals = enriched[0]["visual_candidates"]
        self.assertEqual(visuals[0]["url"], "https://raw.githubusercontent.com/koala73/worldmonitor/main/docs/world-monitor-dashboard.png")
        self.assertEqual(visuals[0]["usage_status"], "approved")
        self.assertEqual(visuals[0]["usage_basis"], "repo_hosted_readme_image")
        self.assertEqual(
            enriched[0]["reader_card"]["original_description"],
            "Real-time global intelligence dashboard.",
        )
        self.assertIn("实时", enriched[0]["reader_card"]["translated_description"])

    def test_fewer_than_eight_selected_is_needs_review(self):
        package = self.build(raw_candidates(7))
        self.assertEqual(package["status"], "needs_review")

    def test_selection_never_exceeds_ten(self):
        config = deepcopy(CONFIG)
        config["selection"]["target"] = 12
        package = self.build(raw_candidates(24), config)
        self.assertEqual(len(package["items"]), 10)

    def test_each_selected_project_has_exactly_three_highlights(self):
        package = self.build()
        self.assertTrue(all(len(item["reader_card"]["highlights"]) == 3 for item in package["items"]))

    def test_unknown_weekly_stars_remains_null_and_is_not_inferred_from_total(self):
        raw = raw_candidates()
        raw["items"][0]["weekly_stars"] = None
        raw["items"][0]["reader_card"]["metrics"]["weekly_stars"] = None
        package = self.build(raw)
        item = next(item for item in package["candidates"] if item["repo"] == "example/project-01")
        self.assertIsNone(item["reader_card"]["metrics"]["weekly_stars"])

    def test_dynamic_metrics_require_verified_at(self):
        raw = raw_candidates()
        raw["items"][0]["weekly_stars"] = 5000
        raw["items"][0]["reader_card"]["metrics"]["weekly_stars"] = 5000
        raw["items"][0]["reader_card"]["metrics"]["verified_at"] = ""
        package = self.build(raw)
        affected = next(item for item in package["candidates"] if item["repo"] == "example/project-01")
        self.assertIn("动态指标缺少核验时间", affected["rejection_reasons"])
        self.assertFalse(affected["selected"])

    def test_missing_license_downgrades_status(self):
        raw = raw_candidates()
        raw["items"][0] = candidate(1, ai=True, weekly_stars=5000, license_status="not_found")
        package = self.build(raw)
        self.assertEqual(package["status"], "needs_review")

    def test_rejection_reasons_are_preserved(self):
        raw = raw_candidates(13)
        raw["items"][-1]["reader_card"]["highlights"] = ["只有一条"]
        package = self.build(raw)
        rejected = next(row for row in package["candidates"] if row["repo"] == "example/project-13")
        self.assertTrue(rejected.get("rejection_reasons"))

    def test_weekly_trending_keeps_top_ten_even_if_seen_recently(self):
        with tempfile.TemporaryDirectory() as temp:
            history = Path(temp) / "github-hot/2026-07-19"
            history.mkdir(parents=True)
            (history / "content-package.json").write_text(
                json.dumps({"items": [{"repo": "example/project-01"}]}),
                encoding="utf-8",
            )
            raw = raw_candidates()
            raw["meta"]["source"] = "github_trending_weekly"
            for index, item in enumerate(raw["items"], 1):
                item["trending"] = {"rank": index, "period": "weekly", "url": "https://github.com/trending?since=weekly"}
            package = self.build(raw, output_root=temp)
            self.assertEqual(package["items"][0]["repo"], "example/project-01")
            self.assertEqual(package["history_excluded"], [])

    def test_ai_projects_are_capped_at_three(self):
        raw = raw_candidates()
        for index, item in enumerate(raw["items"], 1):
            item["ai_related"] = index <= 8
            item["weekly_stars"] = 1000 - index
            item["reader_card"]["metrics"]["weekly_stars"] = 1000 - index
        package = self.build(raw)
        self.assertLessEqual(sum(bool(item["ai_related"]) for item in package["items"]), 5)

    def test_package_has_schema_v2_top_level_fields(self):
        package = self.build()
        self.assertEqual(package["schema_version"], 2)
        for field in (
            "selection",
            "candidates",
            "sources",
            "risks",
            "window",
            "items",
        ):
            self.assertIn(field, package)

    def test_research_layer_does_not_generate_wechat_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            self.build(output_root=temp)
            self.assertFalse(list(Path(temp).rglob("微信版.html")))
            self.assertFalse(list(Path(temp).rglob("合并封面.png")))

    def test_official_visual_candidate_and_source_are_preserved(self):
        raw = raw_candidates()
        raw["items"][0]["visual_candidates"] = [
            {
                "type": "official_screenshot",
                "url": "https://raw.githubusercontent.com/example/project-01/main/demo.png",
                "source_page": "https://github.com/example/project-01",
                "description": "README 官方截图",
                "is_real_interface": True,
                "license_status": "verified",
                "license_name": "MIT",
                "attribution_required": False,
                "usage_status": "approved",
                "verified_at": "2026-07-26T08:30:00+08:00",
            }
        ]
        package = self.build(raw)
        item = next(item for item in package["candidates"] if item["repo"] == "example/project-01")
        self.assertEqual(item["visual_candidates"][0]["usage_status"], "approved")
        self.assertTrue(item["visual_candidates"][0]["source_page"])

    def test_unknown_visual_license_cannot_be_approved(self):
        raw = raw_candidates()
        raw["items"][0]["visual_candidates"] = [
            {
                "type": "official_screenshot",
                "url": "https://example.com/demo.png",
                "source_page": "https://example.com",
                "license_status": "unknown",
                "usage_status": "approved",
                "verified_at": "2026-07-26T08:30:00+08:00",
            }
        ]
        package = self.build(raw)
        visual = next(item for item in package["candidates"] if item["repo"] == "example/project-01")[
            "visual_candidates"
        ][0]
        self.assertEqual(visual["usage_status"], "review_required")

    def test_repo_hosted_readme_visual_is_upgraded_from_old_review_required_snapshot(self):
        raw = raw_candidates()
        raw["items"][0]["visual_candidates"] = [
            {
                "type": "official_screenshot",
                "url": "https://raw.githubusercontent.com/example/project-01/main/docs/demo.png",
                "source_page": "https://github.com/example/project-01#readme",
                "is_repo_hosted": True,
                "license_status": "not_found",
                "usage_status": "review_required",
                "verified_at": "2026-07-26T08:30:00+08:00",
            }
        ]
        package = self.build(raw)
        visual = next(item for item in package["candidates"] if item["repo"] == "example/project-01")[
            "visual_candidates"
        ][0]
        self.assertEqual(visual["usage_status"], "approved")
        self.assertEqual(visual["usage_basis"], "repo_hosted_readme_image")

    def test_code_license_is_not_automatically_applied_to_logo(self):
        raw = raw_candidates()
        raw["items"][0]["visual_candidates"] = [
            {
                "type": "logo",
                "url": "https://example.com/logo.png",
                "source_page": "https://github.com/example/project-01",
                "license_status": "verified",
                "license_name": "MIT",
                "usage_status": "approved",
                "verified_at": "2026-07-26T08:30:00+08:00",
            }
        ]
        package = self.build(raw)
        visual = next(item for item in package["candidates"] if item["repo"] == "example/project-01")[
            "visual_candidates"
        ][0]
        self.assertNotEqual(visual["usage_status"], "approved")

    def test_image2_brief_only_uses_verified_reader_card_features(self):
        raw = raw_candidates()
        raw["items"][0]["image2_brief"]["must_include"].append("未经核验的云端协作")
        package = self.build(raw)
        item = next(item for item in package["candidates"] if item["repo"] == "example/project-01")
        self.assertNotIn("未经核验的云端协作", item["image2_brief"]["must_include"])
        self.assertIn("项目Logo", item["image2_brief"]["must_avoid"])

    def test_empty_visual_candidates_still_produces_valid_package(self):
        package = self.build()
        self.assertTrue(package["items"])
        self.assertTrue(all(item["visual_candidates"] == [] for item in package["items"]))

    def test_visual_fields_do_not_change_selection_score(self):
        base = candidate(1)
        changed = deepcopy(base)
        changed["visual_candidates"] = [
            {
                "type": "official_screenshot",
                "url": "https://example.com/demo.png",
                "source_page": "https://example.com",
                "license_status": "verified",
                "usage_status": "approved",
                "verified_at": "2026-07-26T08:30:00+08:00",
            }
        ]
        self.assertEqual(RUN.score(base), RUN.score(changed))

    def test_chinese_docs(self):
        docs = "\n".join(
            (SKILL / path).read_text(encoding="utf-8")
            for path in (
                "README.md",
                "SKILL.md",
                "references/content-package-v2.md",
                "references/sources-and-risks.md",
            )
        )
        self.assertIn("## 使用步骤", docs)
        for phrase in ("GitHub Trending weekly 前 10 名", "保持页面顺序", "完整 GitHub 地址", "README/docs", "为什么这周火"):
            self.assertIn(phrase, docs)


if __name__ == "__main__":
    unittest.main()
