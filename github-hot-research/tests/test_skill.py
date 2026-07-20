import json, subprocess, sys, tempfile, unittest
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]; FIXTURE=SKILL.parent/"github-hot-wechat/tests/fixtures/candidates.json"
class GithubHotResearchTests(unittest.TestCase):
    def test_offline_content_package(self):
        with tempfile.TemporaryDirectory() as temp:
            result=subprocess.run([sys.executable,str(SKILL/"scripts/run.py"),"all","--input",str(FIXTURE),"--output-root",temp,"--run-at","2026-07-25T09:00:00+08:00"],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            data=json.loads((Path(temp)/"github-hot/2026-07-25/content-package.json").read_text(encoding="utf-8"))
            self.assertEqual((data["schema_version"],data["content_type"]),(1,"github-hot")); self.assertLessEqual(sum(bool(x.get("ai_related")) for x in data["items"]),3)
    def test_chinese_docs(self): self.assertIn("## 使用步骤",(SKILL/"README.md").read_text(encoding="utf-8"))
if __name__=="__main__": unittest.main()

