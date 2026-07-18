from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
ROOT = SKILL.parent
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

import core
import render


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = core.load_config(SKILL / "assets" / "default-config.json")
        cls.run_at = datetime.fromisoformat("2026-07-19T06:20:00+08:00")

    def item(self, title, time, category="general", source="新华社"):
        return core.NewsItem(title, source, "https://example.com/x", category, "安全 出行", time, source_tier=core.source_tier(source, self.config))

    def test_left_closed_right_open_window(self):
        rows = [
            self.item("start", "2026-07-18T06:00:00+08:00"),
            self.item("last", "2026-07-19T05:59:59+08:00"),
            self.item("end", "2026-07-19T06:00:00+08:00"),
            self.item("before", "2026-07-18T05:59:59+08:00"),
        ]
        accepted, _ = core.partition(rows, self.run_at, self.config)
        self.assertEqual([row.title for row in accepted], ["start", "last"])

    def test_cross_year_and_missing_time(self):
        reference = datetime.fromisoformat("2027-01-01T06:20:00+08:00")
        parsed, confidence = core.parse_time("12-31 23:59", reference)
        self.assertEqual(parsed.year, 2026)
        self.assertEqual(confidence, "assumed_bjt")
        _, review = core.partition([self.item("missing", None)], self.run_at, self.config)
        self.assertEqual(len(review), 1)

    def test_deduplicate_and_diverse_select(self):
        payload = json.loads((SKILL / "tests" / "fixtures" / "raw-news.json").read_text(encoding="utf-8"))
        rows = [core.normalize(row, self.run_at, self.config) for row in payload["items"]]
        merged = core.deduplicate(rows)
        self.assertLess(len(merged), len(rows))
        eligible, _ = core.partition(merged, self.run_at, self.config)
        chosen = core.select_diverse(eligible, self.config)
        self.assertGreaterEqual(len(chosen), 5)
        self.assertLessEqual(len(chosen), 8)
        self.assertGreaterEqual(len({row.category for row in chosen}), 4)
        self.assertLessEqual(max(sum(row.category == category for row in chosen) for category in {r.category for r in chosen}), 2)

    def test_international_is_config_driven(self):
        config = json.loads(json.dumps(self.config))
        self.assertEqual(config["regions"], ["china"])
        config["regions"].append("international")
        self.assertIn("international", config["regions"])

    def test_general_feeds_are_classified_by_event(self):
        row = core.normalize({
            "title": "银行发布金融消费风险提示",
            "source": "中国新闻网",
            "link": "https://example.com/finance",
            "category": "society",
            "published_at": "2026-07-18T08:00:00+08:00",
        }, self.run_at, self.config)
        self.assertEqual(row.category, "finance")

    def test_seven_themes_and_hidden_url(self):
        self.assertEqual(len(render.THEMES), 7)
        page = render.markdown_to_html("1. 新华社：[《测试》](https://example.com)", "news-blue")
        self.assertIn('href="https://example.com"', page)
        self.assertNotIn(">https://example.com<", page)


class EndToEndTests(unittest.TestCase):
    def test_build_and_verify_offline_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            command = [
                sys.executable, str(SCRIPTS / "run.py"), "build",
                "--output-root", temp,
                "--input", str(SKILL / "tests" / "fixtures" / "raw-news.json"),
                "--run-at", "2026-07-19T06:20:00+08:00",
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)
            verify = subprocess.run([
                sys.executable, str(SCRIPTS / "run.py"), "verify",
                "--output-root", temp,
                "--run-at", "2026-07-19T06:20:00+08:00",
            ], capture_output=True, text=True)
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            output = Path(temp) / "daily-news" / "2026-07-19"
            for name in ("selected.json", "article.md", "wechat.html", "cover-wide.svg", "cover-square.svg", "cover-wide.png", "cover-square.png", "titles.txt", "verification-notes.md", "run-report.md"):
                self.assertTrue((output / name).exists(), name)
            self.assertEqual((output / "cover-wide.png").read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


class StructureTests(unittest.TestCase):
    def test_skill_metadata_and_no_placeholders(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(text, r"(?s)^---\nname: daily-news-wechat\ndescription: Use when .+?\n---")
        self.assertNotIn("TODO", text)
        self.assertNotIn("[TODO", text)
        self.assertLess(len(text.splitlines()), 500)

    def test_chinese_documentation_and_previews(self):
        repository_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        skill_readme = (SKILL / "README.md").read_text(encoding="utf-8")
        skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("pink-mimi Skills 工具库", repository_readme)
        self.assertIn("效果预览", skill_readme)
        self.assertTrue((ROOT / "assets" / "pink-mimi-skills-banner.svg").exists())
        self.assertTrue((SKILL / "assets" / "preview.svg").exists())
        self.assertIn("## 工作流程", skill_text)
        self.assertRegex(skill_text, r"(?s)^---\nname: daily-news-wechat\n")


if __name__ == "__main__":
    unittest.main()
