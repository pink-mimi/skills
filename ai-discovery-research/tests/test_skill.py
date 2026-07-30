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
SPEC = importlib.util.spec_from_file_location("ai_discovery_run", SKILL / "scripts/run.py")
RUN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUN)
CONFIG = json.loads((SKILL / "assets/default-config.json").read_text(encoding="utf-8"))
RUN_AT = datetime.fromisoformat("2026-07-30T19:30:00+08:00")


class AiDiscoveryResearchTests(unittest.TestCase):
    def build(self, raw=None, config=None):
        return RUN.build(raw or json.loads(FIXTURE.read_text(encoding="utf-8")), RUN_AT, deepcopy(config or CONFIG))

    def test_offline_fixture_generates_content_package(self):
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
            package = Path(temp) / "ai-discovery/2026-07-30/content-package.json"
            self.assertTrue(package.exists())
            data = json.loads(package.read_text(encoding="utf-8"))
            self.assertEqual(data["content_type"], "ai-discovery")
            self.assertEqual(data["schema_version"], 1)

    def test_missing_official_source_marks_needs_review(self):
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        raw["items"][0]["official_sources"] = []
        package = self.build(raw)
        affected = next(item for item in package["candidates"] if item["name"] == "Atlas Agent Studio")
        self.assertIn("缺少官方来源", affected["rejection_reasons"])
        self.assertEqual(package["status"], "needs_review")

    def test_research_layer_does_not_generate_wechat_outputs(self):
        package = self.build()
        blob = json.dumps(package, ensure_ascii=False)
        self.assertNotIn("wechat_html", blob)
        self.assertNotIn("微信版.html", blob)
        self.assertNotIn("合并封面.png", blob)

    def test_stable_reuses_snapshot_and_refresh_archives_revision(self):
        changed = json.loads(FIXTURE.read_text(encoding="utf-8"))
        changed["items"][0]["name"] = "Changed Agent Studio"
        with tempfile.TemporaryDirectory() as temp:
            changed_path = Path(temp) / "changed.json"
            changed_path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
            base = [
                sys.executable,
                str(SKILL / "scripts/run.py"),
                "all",
                "--output-root",
                temp,
                "--run-at",
                RUN_AT.isoformat(),
            ]
            first = subprocess.run(base + ["--input", str(FIXTURE)], capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            raw_path = Path(temp) / "ai-discovery/2026-07-30/raw-candidates.json"
            original = raw_path.read_text(encoding="utf-8")
            stable = subprocess.run(base + ["--input", str(changed_path)], capture_output=True, text=True)
            self.assertEqual(stable.returncode, 0, stable.stdout + stable.stderr)
            self.assertEqual(raw_path.read_text(encoding="utf-8"), original)
            refreshed = subprocess.run(base + ["--input", str(changed_path), "--mode", "refresh"], capture_output=True, text=True)
            self.assertEqual(refreshed.returncode, 0, refreshed.stdout + refreshed.stderr)
            self.assertNotEqual(raw_path.read_text(encoding="utf-8"), original)
            self.assertTrue((raw_path.parent / "revisions/revision-01/raw-candidates.json").exists())
            self.assertTrue((raw_path.parent / "revisions/revision-01/content-package.json").exists())

    def test_chinese_docs_have_core_boundaries(self):
        docs = "\n".join(
            (SKILL / path).read_text(encoding="utf-8")
            for path in ("README.md", "SKILL.md", "references/sources-and-risks.md", "references/content-package-v1.md")
        )
        for phrase in ("AI 新发现", "官方来源", "不生成公众号排版", "不得写“我试了”", "## 使用步骤"):
            self.assertIn(phrase, docs)


if __name__ == "__main__":
    unittest.main()
