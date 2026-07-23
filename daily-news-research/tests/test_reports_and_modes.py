import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]
FIXTURE=SKILL/"tests/fixtures/raw-news.json"


class ReportsAndModesTests(unittest.TestCase):
    def run_cli(self,*args):
        return subprocess.run([sys.executable,str(SKILL/"scripts/run.py"),*args],capture_output=True,text=True)

    def test_all_writes_auditable_tiered_research_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            result=self.run_cli("all","--fixture-input",str(FIXTURE),"--output-root",temp,"--run-at","2026-07-19T06:20:00+08:00")
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            out=Path(temp)/"test-fixtures/daily-news/2026-07-19"
            for name in ("raw-news.json","verification-queue.json","source-health.json","excluded-news.json","content-package.json","source-report.md"):
                self.assertTrue((out/name).exists(),name)
            history=Path(temp)/"test-fixtures/daily-news/source-health-history.json"
            self.assertTrue(history.exists())
            history_data=json.loads(history.read_text(encoding="utf-8"))
            self.assertIn("sources",history_data)
            report=(out/"source-report.md").read_text(encoding="utf-8")
            self.assertIn("来源阶梯",report)
            self.assertIn("机构多样性",report)
            self.assertIn("官方原文覆盖率",report)
            self.assertIn("时间窗口诊断",report)

    def test_rebuild_is_offline_and_does_not_claim_fresh_verification(self):
        with tempfile.TemporaryDirectory() as temp:
            first=self.run_cli("all","--fixture-input",str(FIXTURE),"--output-root",temp,"--run-at","2026-07-19T06:20:00+08:00")
            self.assertEqual(first.returncode,0,first.stdout+first.stderr)
            rebuilt=self.run_cli("all","--fixture-input",str(FIXTURE),"--mode","rebuild","--output-root",temp,"--run-at","2026-07-19T06:20:00+08:00")
            self.assertEqual(rebuilt.returncode,0,rebuilt.stdout+rebuilt.stderr)
            package=json.loads((Path(temp)/"test-fixtures/daily-news/2026-07-19/content-package.json").read_text(encoding="utf-8"))
            self.assertEqual(package["snapshot"]["mode"],"rebuild")
            self.assertTrue(package["snapshot"]["refresh_recommended"])
            self.assertIn("离线重建",package["risks"][-1])

    def test_refresh_rejects_external_input_in_formal_collection(self):
        with tempfile.TemporaryDirectory() as temp:
            result=self.run_cli("all","--input",str(FIXTURE),"--mode","refresh","--output-root",temp,"--run-at","2026-07-19T06:20:00+08:00")
            self.assertNotEqual(result.returncode,0)
            self.assertIn("--input 仅供 query",result.stdout+result.stderr)
            self.assertFalse((Path(temp)/"daily-news/2026-07-19/raw-news.json").exists())

    def test_fixture_input_is_isolated_and_marked_non_production(self):
        with tempfile.TemporaryDirectory() as temp:
            result=self.run_cli("all","--fixture-input",str(FIXTURE),"--output-root",temp,"--run-at","2026-07-19T06:20:00+08:00")
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertFalse((Path(temp)/"daily-news/2026-07-19/raw-news.json").exists())
            package=json.loads((Path(temp)/"test-fixtures/daily-news/2026-07-19/content-package.json").read_text(encoding="utf-8"))
            self.assertEqual(package["execution"]["kind"],"test_fixture")
            self.assertEqual(package["status"],"needs_review")

    def test_verify_requires_all_audit_files(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/"daily-news/2026-07-19"; out.mkdir(parents=True)
            (out/"content-package.json").write_text(json.dumps({"schema_version":1,"content_type":"daily-news","items":[{"title":"x"}]},ensure_ascii=False),encoding="utf-8")
            result=self.run_cli("verify","--output-root",temp,"--run-at","2026-07-19T06:20:00+08:00")
            self.assertNotEqual(result.returncode,0)
            self.assertIn("verification-queue.json",result.stdout+result.stderr)


if __name__=="__main__": unittest.main()
