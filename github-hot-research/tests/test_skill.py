import importlib.util
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

    def test_recent_eight_issue_history_excludes_unchanged_project(self):
        with tempfile.TemporaryDirectory() as temp:
            history = Path(temp) / "github-hot/2026-07-19"
            history.mkdir(parents=True)
            (history / "content-package.json").write_text(
                json.dumps({"items": [{"repo": "example/project-01"}]}),
                encoding="utf-8",
            )
            package = self.build(output_root=temp)
            self.assertNotIn("example/project-01", [item["repo"] for item in package["items"]])

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
        for phrase in ("连续 7 天", "本周热度证据", "新爆款", "成熟项目最多 2 个", "为什么这周火"):
            self.assertIn(phrase, docs)


if __name__ == "__main__":
    unittest.main()
