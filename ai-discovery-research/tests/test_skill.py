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
            self.assertEqual(data["selection"]["selected_count"], 1)
            self.assertGreaterEqual(data["selection"]["focused_review_count"], 3)

    def test_missing_official_source_marks_needs_review(self):
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        raw["items"][0]["official_sources"] = []
        package = self.build(raw)
        affected = next(item for item in package["candidates"] if item["name"] == "Atlas Agent Studio")
        self.assertIn("缺少官方来源", affected["rejection_reasons"])
        self.assertEqual(package["status"], "needs_review")

    def test_verified_candidate_requires_source_verified_at(self):
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        raw["items"][0]["official_sources"][0]["verified_at"] = ""
        raw["items"][0]["verification_status"] = "verified"
        package = self.build(raw)
        affected = next(item for item in package["candidates"] if item["name"] == "Atlas Agent Studio")
        self.assertIn("官方来源缺少核验时间", affected["rejection_reasons"])
        self.assertEqual(package["status"], "needs_review")

    def test_claimed_real_test_requires_evidence(self):
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        raw["items"][0]["tested"] = True
        raw["items"][0]["evidence"] = []
        package = self.build(raw)
        affected = next(item for item in package["candidates"] if item["name"] == "Atlas Agent Studio")
        self.assertIn("实测声明缺少证据记录", affected["rejection_reasons"])
        self.assertEqual(package["status"], "needs_review")

    def test_selects_one_grade_a_or_b_candidate_and_keeps_c_unselected(self):
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        raw["items"][0]["verification_grade"] = "C"
        package = self.build(raw)
        self.assertEqual(len(package["items"]), 1)
        self.assertNotEqual(package["items"][0]["name"], "Atlas Agent Studio")
        self.assertIn(package["items"][0]["verification_grade"], {"A", "B"})
        rejected = next(item for item in package["candidates"] if item["name"] == "Atlas Agent Studio")
        self.assertIn("C 级候选不发布", rejected["rejection_reasons"])

    def test_selected_item_contains_reader_decision_fields(self):
        package = self.build()
        item = package["items"][0]
        for field in (
            "company",
            "platforms",
            "supports_chinese",
            "mainland_availability",
            "not_for",
            "scenarios",
            "pricing_details",
            "privacy_and_rights",
            "public_feedback",
            "verification_grade",
        ):
            self.assertIn(field, item)
        self.assertGreaterEqual(len(item["scenarios"]), 3)
        self.assertIn(item["mainland_availability"]["status"], {"可直接使用", "存在限制", "需海外账号"})
        self.assertTrue(item["pricing_details"]["verified_at"])

    def test_official_images_are_preserved_as_optional_metadata(self):
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        raw["items"][0].pop("official_images", None)
        raw["items"][0]["official_image_url"] = "https://example.com/atlas-agent-studio/demo.png"
        raw["items"][0]["official_image_source_page"] = "https://example.com/atlas-agent-studio"
        raw["items"][0]["official_image_source_path"] = "work/images/demo.png"
        raw["items"][0]["official_image_description"] = "官方产品演示图"
        package = self.build(raw)
        item = package["items"][0]
        self.assertEqual(item["official_images"][0]["url"], "https://example.com/atlas-agent-studio/demo.png")
        self.assertTrue(item["official_images"][0]["is_official"])
        self.assertEqual(item["official_images"][0]["usage_status"], "approved")

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
