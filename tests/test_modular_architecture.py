from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ModularArchitectureTests(unittest.TestCase):
    def test_skill_metadata_utf8_and_no_placeholders(self):
        for name in ("daily-news-research", "github-hot-research", "wechat-content"):
            text = (ROOT / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertRegex(text, rf"(?s)^---\nname: {name}\ndescription: Use when .+?\n---")
            self.assertNotIn("TODO", text)
            self.assertLess(len(text.splitlines()), 500)
            self.assertIn("用户", text)

    def test_required_skills_and_chinese_guides_exist(self):
        for name in ("daily-news-research", "github-hot-research", "wechat-content"):
            skill = ROOT / name
            self.assertTrue((skill / "SKILL.md").exists(), name)
            guide = (skill / "README.md").read_text(encoding="utf-8")
            self.assertIn("## 使用步骤", guide)
            self.assertIn("## 功能", guide)
            self.assertRegex(guide, r"!\[[^]]+\]\(assets/")

    def test_research_outputs_are_platform_neutral_content_packages(self):
        cases = (
            ("daily-news-research", ROOT / "daily-news-wechat/tests/fixtures/raw-news.json", "2026-07-19T06:20:00+08:00", "daily-news"),
            ("github-hot-research", ROOT / "github-hot-wechat/tests/fixtures/candidates.json", "2026-07-25T09:00:00+08:00", "github-hot"),
        )
        with tempfile.TemporaryDirectory() as temp:
            output_root = Path(temp)
            for skill_name, fixture_path, run_at, content_type in cases:
                skill = ROOT / skill_name
                result = subprocess.run(
                    [sys.executable, str(skill / "scripts" / "run.py"), "all",
                     "--output-root", str(output_root), "--input",
                     str(fixture_path), "--run-at", run_at],
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                package = next(output_root.glob(f"{content_type}/*/content-package.json"))
                payload = json.loads(package.read_text(encoding="utf-8"))
                self.assertEqual(payload["schema_version"], 1)
                self.assertEqual(payload["content_type"], content_type)
                self.assertIn(payload["status"], {"ready_for_human_review", "needs_review"})
                self.assertTrue(payload["items"])
                self.assertNotIn("wechat_html", payload)

    def test_wechat_content_renders_both_columns_and_combined_cover(self):
        renderer = ROOT / "wechat-content"
        with tempfile.TemporaryDirectory() as temp:
            for fixture in ("daily-news-content-package.json", "github-hot-content-package.json"):
                result = subprocess.run(
                    [sys.executable, str(renderer / "scripts" / "run.py"), "all",
                     "--input", str(renderer / "tests" / "fixtures" / fixture),
                     "--output-root", temp, "--theme", "auto"],
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            outputs = list(Path(temp).glob("wechat/*/*"))
            self.assertEqual(len(outputs), 2)
            for output in outputs:
                page = (output / "微信版.html").read_text(encoding="utf-8")
                self.assertIn('id="copy-wechat"', page)
                self.assertIn('id="wechat-content"', page)
                self.assertTrue((output / "images" / "合并封面.png").exists())
                self.assertTrue((output / "images" / "横版封面.png").exists())
                self.assertTrue((output / "images" / "方形封面.png").exists())


if __name__ == "__main__":
    unittest.main()
