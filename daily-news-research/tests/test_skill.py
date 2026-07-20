import importlib.util, json, subprocess, sys, tempfile, time, unittest
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]; FIXTURE=SKILL.parent/"daily-news-wechat/tests/fixtures/raw-news.json"
SPEC=importlib.util.spec_from_file_location("daily_news_research_run",SKILL/"scripts/run.py"); run=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(run)
class DailyNewsResearchTests(unittest.TestCase):
    def test_default_sources_cover_four_categories(self):
        config=json.loads((SKILL/"assets/default-config.json").read_text(encoding="utf-8"))
        enabled=[x for x in config["sources"] if x.get("enabled",True)]
        self.assertGreaterEqual(len(enabled),6)
        self.assertGreaterEqual(len({x["category"] for x in enabled}),4)

    def test_collection_runs_sources_concurrently_and_records_failures(self):
        feed=b"<rss><channel><item><title>test</title><link>https://example.com/a</link><pubDate>Sun, 19 Jul 2026 03:00:00 GMT</pubDate></item></channel></rss>"
        class Response:
            def __init__(self,payload): self.payload=payload
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self): return self.payload
        def opener(request,timeout):
            time.sleep(0.15)
            if "broken" in request.full_url: raise OSError("offline")
            return Response(feed)
        config={"collection":{"timeout_seconds":2,"max_workers":4},"sources":[
            {"name":"one","url":"https://example.com/one","category":"society"},
            {"name":"two","url":"https://example.com/two","category":"tech"},
            {"name":"broken","url":"https://example.com/broken","category":"finance"}]}
        started=time.monotonic(); result=run.collect(config,run.datetime.fromisoformat("2026-07-20T06:00:00+08:00"),opener=opener); elapsed=time.monotonic()-started
        self.assertLess(elapsed,0.35)
        self.assertEqual(result["meta"]["successful_sources"],2)
        self.assertEqual(len(result["errors"]),1)
        self.assertEqual(len(result["items"]),2)

    def test_offline_content_package(self):
        with tempfile.TemporaryDirectory() as temp:
            result=subprocess.run([sys.executable,str(SKILL/"scripts/run.py"),"all","--input",str(FIXTURE),"--output-root",temp,"--run-at","2026-07-19T06:20:00+08:00"],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            data=json.loads((Path(temp)/"daily-news/2026-07-19/content-package.json").read_text(encoding="utf-8"))
            self.assertEqual((data["schema_version"],data["content_type"]),(1,"daily-news")); self.assertNotIn("wechat_html",data)
    def test_chinese_docs(self):
        self.assertIn("## 使用步骤",(SKILL/"README.md").read_text(encoding="utf-8"))
if __name__=="__main__": unittest.main()
