from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

import core
import render


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = core.load_config(SKILL / "assets" / "default-config.json")
        cls.run_at = datetime.fromisoformat("2026-07-25T09:00:00+08:00")
        cls.rows = json.loads((SKILL / "tests" / "fixtures" / "candidates.json").read_text(encoding="utf-8"))["items"]

    def test_seven_day_left_closed_right_open_window(self):
        start, end = core.window_for(self.run_at, self.config)
        self.assertEqual(start.isoformat(), "2026-07-18T09:00:00+08:00")
        self.assertEqual(end.isoformat(), "2026-07-25T09:00:00+08:00")
        self.assertTrue(core.in_window("2026-07-18T01:00:00Z", start, end))
        self.assertFalse(core.in_window("2026-07-25T01:00:00Z", start, end))

    def test_selection_caps_ai_and_category(self):
        selected = core.select_projects([core.normalize(row) for row in self.rows], self.config, set())
        self.assertEqual(len(selected), 5)
        self.assertLessEqual(sum(row.ai_related for row in selected), 3)
        self.assertLessEqual(max(sum(x.category == row.category for x in selected) for row in selected), 3)

    def test_history_blocks_repeat_unless_major_change(self):
        history = {"notify/ntfy"}
        selected = core.select_projects([core.normalize(row) for row in self.rows], self.config, history)
        self.assertNotIn("notify/ntfy", {row.repo for row in selected})
        changed = dict(self.rows[4], significant_change=True)
        selected = core.select_projects([core.normalize(changed)] + [core.normalize(row) for row in self.rows[5:]], self.config, history)
        self.assertIn("notify/ntfy", {row.repo for row in selected})

    def test_missing_license_is_not_eligible(self):
        row = dict(self.rows[0], license="")
        self.assertFalse(core.normalize(row).eligible)

    def test_collection_placeholders_are_not_verified_facts(self):
        row = dict(self.rows[0], platform="请根据 README 核验", audience="请人工确认")
        project = core.normalize(row)
        self.assertFalse(project.eligible)
        self.assertIn("platform", project.rejection_reason)

    def test_status_requires_candidate_depth_and_non_ai(self):
        projects = [core.normalize(row) for row in self.rows]
        selected = core.select_projects(projects, self.config, set())
        self.assertEqual(core.package_status(projects, selected, False, self.config), "ready_for_human_review")
        self.assertEqual(core.package_status(projects[:8], selected, False, self.config), "needs_review")
        self.assertEqual(core.package_status(projects, selected, True, self.config), "needs_review")

    def test_theme_rotation_is_stable_and_all_four_exist(self):
        self.assertEqual(set(render.THEMES), {"open-coordinates", "code-archive", "field-notes", "clean-grid"})
        first = render.theme_for(self.run_at, "auto")
        self.assertEqual(first, render.theme_for(self.run_at, "auto"))


class RenderTests(unittest.TestCase):
    def test_html_has_copy_boundary_and_clickable_links(self):
        project = core.normalize(json.loads((SKILL / "tests" / "fixtures" / "candidates.json").read_text(encoding="utf-8"))["items"][0])
        html = render.wechat_html(render.article_markdown([project], self.run_at()), "open-coordinates")
        self.assertIn('id="copy-wechat"', html)
        self.assertIn('id="wechat-content"', html)
        self.assertLess(html.index('id="copy-wechat"'), html.index('id="wechat-content"'))
        self.assertIn('href="https://github.com/map/hallmark"', html)
        self.assertIn("ClipboardItem", html)
        self.assertIn("overflow-wrap:anywhere", html)

    @staticmethod
    def run_at():
        return datetime.fromisoformat("2026-07-25T09:00:00+08:00")

    def test_fallback_images_have_expected_dimensions(self):
        with tempfile.TemporaryDirectory() as temp:
            render.fallback_images(Path(temp), "open-coordinates", "AI 占了热榜，也没占满世界", 5)
            expected = {"合并封面.png": (1283, 383), "横版封面.png": (900, 383), "方形封面.png": (383, 383)}
            for name, size in expected.items():
                self.assertEqual(render.png_size(Path(temp) / name), size)
            self.assertEqual(len(list(Path(temp).glob("*.png"))), 9)


class EndToEndTests(unittest.TestCase):
    def test_all_and_verify_offline_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            command = [sys.executable, str(SCRIPTS / "run.py"), "all", "--output-root", temp, "--input", str(SKILL / "tests" / "fixtures" / "candidates.json"), "--run-at", "2026-07-25T09:00:00+08:00", "--theme", "auto", "--image-mode", "auto"]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            output = Path(temp) / "github-hot" / "2026-07-25"
            required = ["raw-candidates.json", "candidates.json", "selected.json", "执行信息.md", "候选项目核验表.md", "入选理由.md", "公众号成稿.md", "微信版.html", "备选标题.txt", "公众号摘要.txt", "来源清单.md", "淘汰项目及原因.md", "风险和待人工确认项.md", "人工审核清单.md", "运行报告.md"]
            for name in required:
                self.assertTrue((output / name).exists(), name)
            selected = json.loads((output / "selected.json").read_text(encoding="utf-8"))
            self.assertEqual(selected["meta"]["status"], "ready_for_human_review")
            self.assertEqual(selected["meta"]["image_mode"], "template_fallback")
            self.assertEqual(len(selected["items"]), 5)
            verify = subprocess.run([sys.executable, str(SCRIPTS / "run.py"), "verify", "--output-root", temp, "--run-at", "2026-07-25T09:00:00+08:00"], capture_output=True, text=True)
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)


class StructureTests(unittest.TestCase):
    def test_skill_is_independent_and_has_no_placeholders(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(text, r"(?s)^---\nname: github-hot-wechat\ndescription: Use when .+?\n---")
        self.assertNotIn("TODO", text)
        self.assertNotIn("wechat-article-writer", text)
        self.assertLess(len(text.splitlines()), 500)

    def test_windows_launcher_discovers_codex_python(self):
        launcher = (SKILL / "scripts" / "run.ps1").read_text(encoding="utf-8")
        self.assertIn("GITHUB_HOT_PYTHON", launcher)
        self.assertIn("codex-primary-runtime", launcher)
        self.assertIn("run.py", launcher)

    def test_readme_shows_real_article_and_cover_previews(self):
        readme = (SKILL / "README.md").read_text(encoding="utf-8")
        for name in ("preview-cover.png", "preview-article.png"):
            self.assertTrue((SKILL / "assets" / name).exists(), name)
            self.assertIn(f"assets/{name}", readme)
        self.assertLess(readme.index("assets/preview-cover.png"), readme.index("assets/preview.svg"))


if __name__ == "__main__":
    unittest.main()
