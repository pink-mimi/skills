import importlib.util
import json
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
EDITORIAL_SPEC = importlib.util.spec_from_file_location(
    "github_hot_editorial", SKILL / "scripts/editorial.py"
)
EDITORIAL = importlib.util.module_from_spec(EDITORIAL_SPEC)
EDITORIAL_SPEC.loader.exec_module(EDITORIAL)

RUN_SPEC = importlib.util.spec_from_file_location("github_hot_run", SKILL / "scripts/run.py")
RUN = importlib.util.module_from_spec(RUN_SPEC)
RUN_SPEC.loader.exec_module(RUN)

CONFIG = json.loads((SKILL / "assets/default-config.json").read_text(encoding="utf-8"))
RUN_AT = datetime.fromisoformat("2026-07-27T09:00:00+08:00")


def complete_candidate(index, heat_class="new_breakout"):
    repo = f"example/hot-{index:02d}"
    created_at = "2026-07-23T08:00:00Z" if heat_class == "new_breakout" else "2025-01-01T08:00:00Z"
    evidence_kind = "github_trending" if heat_class == "new_breakout" else "release"
    return {
        "repo": repo,
        "official_url": f"https://github.com/{repo}",
        "created_at": created_at,
        "category": f"category-{index % 4}",
        "ai_related": index <= 3,
        "hot_reason": "项目发布完整教程后进入本周 GitHub Trending。",
        "use_case": "帮助开发者把复杂工作流程整理成可复用的自动化步骤。",
        "editorial_summary": "它把原本需要反复查阅资料的流程整理成清晰路径，并提供可以直接验证的示例。",
        "heat_evidence": [
            {
                "kind": evidence_kind,
                "observed_at": "2026-07-24T09:00:00+08:00",
                "url": f"https://github.com/{repo}",
            }
        ],
        "reader_card": {
            "category_label": "开发工具",
            "name": f"hot-{index:02d}",
            "summary": "帮助开发者整理和自动化复杂工作流程。",
            "recommendation": "把零散步骤整理成可验证的完整路径。",
            "highlights": ["提供完整示例", "支持本地运行", "流程可以复用"],
            "audience": ["开发者", "自动化工具用户"],
            "difficulty": {"level": "medium", "label": "中等", "note": "需要命令行基础"},
            "metrics": {
                "language": "Python",
                "stars": 12000 + index,
                "weekly_stars": 1000 - index,
                "forks": 300 + index,
                "verified_at": "2026-07-27T08:30:00+08:00",
            },
        },
        "verification": {
            "readme": {
                "url": f"https://github.com/{repo}#readme",
                "verified_at": "2026-07-27T08:20:00+08:00",
            },
            "license": {
                "status": "verified",
                "name": "MIT",
                "spdx_id": "MIT",
                "url": f"https://github.com/{repo}/blob/main/LICENSE",
            },
            "maintenance": {
                "status": "active",
                "last_commit_at": "2026-07-26T08:00:00Z",
                "latest_release_at": "2026-07-24T08:00:00Z",
                "evidence_urls": [f"https://github.com/{repo}/commits/main"],
            },
            "requirements": {
                "platforms": ["Windows", "macOS", "Linux"],
                "install": "需要 Python 3",
                "command_line": True,
            },
            "risks": [],
            "evidence": [f"https://github.com/{repo}"],
        },
        "visual_candidates": [],
        "image2_brief": {
            "subject": "本地自动化工作流程",
            "scene": "开发者桌面上的终端和工作步骤",
            "must_include": ["自动化流程", "本地运行"],
            "must_avoid": ["项目Logo", "虚构软件界面", "中文文字", "虚构数据"],
        },
    }


class WeeklyHeatTests(unittest.TestCase):
    def test_candidate_requires_heat_evidence_inside_window(self):
        result = EDITORIAL.assess_heat(
            complete_candidate(1),
            "2026-07-20T09:00:00+08:00",
            "2026-07-27T09:00:00+08:00",
        )
        self.assertTrue(result["eligible"])
        self.assertEqual(result["heat_class"], "new_breakout")

    def test_old_total_stars_without_weekly_evidence_is_not_hot(self):
        result = EDITORIAL.assess_heat(
            {"repo": "example/old", "stars": 90000, "heat_evidence": []},
            "2026-07-20T09:00:00+08:00",
            "2026-07-27T09:00:00+08:00",
        )
        self.assertFalse(result["eligible"])
        self.assertIn("本周热度证据不足", result["rejection_reasons"])

    def test_mature_resurging_projects_are_capped_at_two(self):
        rows = [complete_candidate(index, "mature" if index <= 4 else "new_breakout") for index in range(1, 13)]
        package = RUN.build(
            {"meta": {"rate_limited": False}, "items": rows},
            RUN_AT,
            deepcopy(CONFIG),
            tempfile.mkdtemp(),
        )
        mature = [
            item for item in package["items"]
            if item["heat"]["heat_class"] == "mature_resurgence"
        ]
        self.assertLessEqual(len(mature), 2)
        self.assertGreater(len(package["items"]) - len(mature), len(mature))


class EditorialMaterialTests(unittest.TestCase):
    def test_editorial_material_only_uses_selected_project_evidence(self):
        selected = []
        for index in range(1, 6):
            item = complete_candidate(index)
            item["category"] = "developer-tools"
            item["reader_card"]["category_label"] = "开发工具"
            heat = EDITORIAL.assess_heat(
                item,
                "2026-07-20T09:00:00+08:00",
                "2026-07-27T09:00:00+08:00",
            )
            item["editorial"] = EDITORIAL.project_editorial(item, heat)
            selected.append(item)
        material = EDITORIAL.derive_weekly_editorial(selected)
        self.assertEqual(material["opening_mode"], "theme")
        self.assertEqual(material["weekly_theme"], "开发工具")
        self.assertTrue(material["theme_evidence"])
        allowed = {item["repo"] for item in selected}
        self.assertTrue({row["repo"] for row in material["theme_evidence"]} <= allowed)

    def test_no_common_theme_uses_multiple_routes_mode(self):
        selected = []
        for index in range(1, 6):
            item = complete_candidate(index)
            item["category"] = f"unrelated-{index}"
            heat = EDITORIAL.assess_heat(
                item,
                "2026-07-20T09:00:00+08:00",
                "2026-07-27T09:00:00+08:00",
            )
            item["editorial"] = EDITORIAL.project_editorial(item, heat)
            selected.append(item)
        material = EDITORIAL.derive_weekly_editorial(selected)
        self.assertEqual(material["opening_mode"], "multiple_routes")
        self.assertEqual(material["weekly_theme"], "")

    def test_package_contains_project_and_weekly_editorial_material(self):
        rows = [complete_candidate(index) for index in range(1, 13)]
        package = RUN.build(
            {"meta": {"rate_limited": False}, "items": rows},
            RUN_AT,
            deepcopy(CONFIG),
            tempfile.mkdtemp(),
        )
        self.assertIn("editorial", package)
        for item in package["items"]:
            self.assertTrue(item["editorial"]["hot_reason"])
            self.assertTrue(item["editorial"]["hot_reason_evidence"])
            self.assertTrue(item["editorial"]["use_case"])
            self.assertGreaterEqual(len(item["editorial"]["summary"]), 40)
            self.assertEqual(len(item["reader_card"]["highlights"]), 3)


if __name__ == "__main__":
    unittest.main()
