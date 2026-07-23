from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ModularArchitectureTests(unittest.TestCase):
    def research_fixture_arg(self, skill_name, fixture):
        if skill_name.startswith("daily"):
            return ["--fixture-input", str(fixture)]
        return ["--input", str(fixture)]

    def research_output_glob(self, skill_name, content_type):
        if skill_name.startswith("daily"):
            return f"test-fixtures/{content_type}/*/content-package.json"
        return f"{content_type}/*/content-package.json"

    def test_research_snapshot_modes_are_stable_and_revisioned(self):
        cases = (
            ("daily-news-research", ROOT / "daily-news-wechat/tests/fixtures/raw-news.json", "2026-07-19T06:20:00+08:00", "test-fixtures/daily-news/2026-07-19", "raw-news.json"),
            ("github-hot-research", ROOT / "github-hot-wechat/tests/fixtures/candidates.json", "2026-07-25T09:00:00+08:00", "github-hot/2026-07-25", "raw-candidates.json"),
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for skill_name, fixture, run_at, relative, raw_name in cases:
                skill = ROOT / skill_name
                changed = root / f"{skill_name}-changed.json"
                payload = json.loads(fixture.read_text(encoding="utf-8"))
                payload["items"][0]["title" if skill_name.startswith("daily") else "description"] = "第二次采集产生的变化"
                changed.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                base = [sys.executable, str(skill / "scripts/run.py"), "all", "--output-root", str(root), "--run-at", run_at]
                first = subprocess.run(base + self.research_fixture_arg(skill_name, fixture), capture_output=True, text=True)
                self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
                target = root / relative
                original_raw = (target / raw_name).read_text(encoding="utf-8")
                stable = subprocess.run(base + self.research_fixture_arg(skill_name, changed), capture_output=True, text=True)
                self.assertEqual(stable.returncode, 0, stable.stdout + stable.stderr)
                self.assertEqual((target / raw_name).read_text(encoding="utf-8"), original_raw)
                if skill_name.startswith("daily"):
                    continue
                refreshed = subprocess.run(base + self.research_fixture_arg(skill_name, changed) + ["--mode", "refresh"], capture_output=True, text=True)
                self.assertEqual(refreshed.returncode, 0, refreshed.stdout + refreshed.stderr)
                self.assertNotEqual((target / raw_name).read_text(encoding="utf-8"), original_raw)
                self.assertTrue((target / "revisions/revision-01" / raw_name).exists())
                self.assertTrue((target / "revisions/revision-01/content-package.json").exists())

    def test_rebuild_requires_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [sys.executable, str(ROOT / "daily-news-research/scripts/run.py"), "all",
                 "--output-root", temp, "--run-at", "2026-07-19T06:20:00+08:00", "--mode", "rebuild"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("原始快照", result.stdout + result.stderr)

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
                     "--output-root", str(output_root), "--run-at", run_at]
                    + self.research_fixture_arg(skill_name, fixture_path),
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                package = next(output_root.glob(self.research_output_glob(skill_name, content_type)))
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
