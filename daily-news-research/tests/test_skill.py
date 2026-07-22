import importlib.util, json, subprocess, sys, tempfile, time, unittest
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]; FIXTURE=SKILL/"tests/fixtures/raw-news.json"
SPEC=importlib.util.spec_from_file_location("daily_news_research_run",SKILL/"scripts/run.py"); run=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(run)
class DailyNewsResearchTests(unittest.TestCase):
    def test_domestic_digest_rejects_unrelated_foreign_items(self):
        config=json.loads((SKILL/"assets/default-config.json").read_text(encoding="utf-8"))
        base={"published_at":"2026-07-19T12:00:00+08:00","summary":"摘要","what_happened":"事实","why_it_matters":"影响","reader_action":"建议","editor_note":"提醒","keywords":["关键词"]}
        rows=[]
        domestic_categories=("时政","财经","科技","公共安全")
        for index,title in enumerate(("中国多地推进公共服务安排","国内服务消费数据发布","北京发布科技应用计划","广西更新防汛响应","加拿大调整边境措施","美军在伊拉克发生事故","世界杯决赛准备就绪")):
            row=dict(base,title=title,url=f"https://example.com/{index}",source="官方来源",category=domestic_categories[index] if index<4 else "国际")
            rows.append(row)
        package=run.build({"items":rows},run.datetime.fromisoformat("2026-07-20T06:00:00+08:00"),config)
        self.assertEqual([x["title"] for x in package["items"]],[x["title"] for x in rows[:4]])
        self.assertEqual(package["status"],"needs_review")

    def test_ready_status_requires_full_editorial_fields(self):
        config=json.loads((SKILL/"assets/default-config.json").read_text(encoding="utf-8"))
        items=[]
        categories=("时政","财经","社会","科技","公共安全")
        for index,category in enumerate(categories):
            items.append({"title":f"中国新闻{index}","url":f"https://example.com/{index}","source":"官方来源","category":category,"summary":"只有摘要","published_at":"2026-07-19T12:00:00+08:00"})
        package=run.build({"items":items},run.datetime.fromisoformat("2026-07-20T06:00:00+08:00"),config)
        self.assertEqual(package["status"],"needs_review")
        self.assertTrue(any("深度字段" in risk for risk in package["risks"]))

    def test_default_sources_cover_four_categories(self):
        config=json.loads((SKILL/"assets/default-config.json").read_text(encoding="utf-8"))
        enabled=[x for x in config["sources"] if x.get("enabled",True)]
        self.assertGreaterEqual(len(enabled),6)
        self.assertGreaterEqual(len({x["category"] for x in enabled}),4)

    def test_default_sources_declare_tiered_source_contract(self):
        config=json.loads((SKILL/"assets/default-config.json").read_text(encoding="utf-8"))
        required={"organization","tier","role","parser","daily_default","canonical_domains","max_response_bytes"}
        defaults=[source for source in config["sources"] if source.get("daily_default")]
        self.assertTrue(defaults)
        for source in defaults:
            self.assertFalse(required-set(source),source["name"])
        self.assertEqual(config["schema_version"],2)
        self.assertEqual({source["tier"] for source in defaults},{1,2})

    def test_default_daily_sources_cover_five_independent_organizations(self):
        config=json.loads((SKILL/"assets/default-config.json").read_text(encoding="utf-8"))
        defaults=[source for source in config["sources"] if source.get("daily_default")]
        self.assertGreaterEqual(len({source["organization"] for source in defaults}),5)
        self.assertTrue(any(source["role"]=="primary" for source in defaults))
        world=[source for source in defaults if source["category"]=="world"]
        self.assertLessEqual(len(world),1)
        self.assertEqual(config["selection"]["maximum_international"],1)

    def test_collection_and_selection_limits_are_explicit(self):
        config=json.loads((SKILL/"assets/default-config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["collection"]["maximum_candidates"],50)
        self.assertEqual(config["verification"]["maximum_queue"],15)
        self.assertGreaterEqual(config["health"]["minimum_successful_organizations"],5)
        self.assertEqual(config["selection"]["maximum_local"],1)

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

    def test_query_supports_category_keyword_limit_and_detail(self):
        rows=json.loads(FIXTURE.read_text(encoding="utf-8"))["items"]
        result=run.query_items(rows,category="tech",keyword="人工智能",limit=1,detail=12)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["category"],"tech")
        self.assertLessEqual(len(result[0]["summary"]),15)

    def test_sources_command_lists_all_supported_categories(self):
        result=subprocess.run([sys.executable,str(SKILL/"scripts/run.py"),"sources","--format","json"],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        payload=json.loads(result.stdout)
        for category in ("hot","politics","finance","tech","society","world","sports","entertainment","ai","ai-community"):
            self.assertIn(category,payload)

    def test_query_command_can_use_offline_input(self):
        result=subprocess.run([sys.executable,str(SKILL/"scripts/run.py"),"query","--input",str(FIXTURE),"--category","tech","--limit","2","--format","json"],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        payload=json.loads(result.stdout)
        self.assertLessEqual(len(payload),2)
        self.assertTrue(all(row["category"]=="tech" for row in payload))

    def test_offline_content_package(self):
        with tempfile.TemporaryDirectory() as temp:
            result=subprocess.run([sys.executable,str(SKILL/"scripts/run.py"),"all","--input",str(FIXTURE),"--output-root",temp,"--run-at","2026-07-19T06:20:00+08:00"],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            data=json.loads((Path(temp)/"daily-news/2026-07-19/content-package.json").read_text(encoding="utf-8"))
            self.assertEqual((data["schema_version"],data["content_type"]),(1,"daily-news")); self.assertNotIn("wechat_html",data)
            report=(Path(temp)/"daily-news/2026-07-19/source-report.md")
            self.assertTrue(report.exists())
            report_text=report.read_text(encoding="utf-8")
            self.assertIn("采集成功率",report_text)
            self.assertIn("类别分布",report_text)
    def test_chinese_docs(self):
        readme=(SKILL/"README.md").read_text(encoding="utf-8")
        self.assertIn("## 使用步骤",readme)
        for phrase in ("四级来源阶梯","全国性国内新闻","重要地方新闻","国际新闻","3—8 分钟","needs_review"):
            self.assertIn(phrase,readme)
        catalog=(SKILL/"references/source-catalog.md").read_text(encoding="utf-8")
        self.assertIn("来源平台",catalog)
        self.assertIn("不能保证 100%",catalog)
        self.assertIn("官方原始来源",catalog)
        self.assertIn("权威媒体",catalog)
        self.assertIn("热点平台",catalog)
        policy=(SKILL/"references/editorial-policy.md").read_text(encoding="utf-8")
        self.assertIn("先发现、再聚类、后核验",policy)
        self.assertIn("中国关联理由",policy)
        official=(SKILL/"references/official-source-directory.md").read_text(encoding="utf-8")
        self.assertIn("按类别触发",official)
        self.assertIn("仅允许官方域名",official)
if __name__=="__main__": unittest.main()
