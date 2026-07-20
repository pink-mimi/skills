import json, subprocess, sys, tempfile, unittest
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]; FIXTURE=SKILL.parent/"daily-news-wechat/tests/fixtures/raw-news.json"
class DailyNewsResearchTests(unittest.TestCase):
    def test_offline_content_package(self):
        with tempfile.TemporaryDirectory() as temp:
            result=subprocess.run([sys.executable,str(SKILL/"scripts/run.py"),"all","--input",str(FIXTURE),"--output-root",temp,"--run-at","2026-07-19T06:20:00+08:00"],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            data=json.loads((Path(temp)/"daily-news/2026-07-19/content-package.json").read_text(encoding="utf-8"))
            self.assertEqual((data["schema_version"],data["content_type"]),(1,"daily-news")); self.assertNotIn("wechat_html",data)
    def test_chinese_docs(self):
        self.assertIn("## 使用步骤",(SKILL/"README.md").read_text(encoding="utf-8"))
if __name__=="__main__": unittest.main()

