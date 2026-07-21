import hashlib, json, shutil, subprocess, sys, tempfile, unittest
from datetime import datetime
from pathlib import Path
from PIL import Image

SKILL=Path(__file__).resolve().parents[1]
ASSETS=SKILL/"assets"
CONFIG=json.loads((ASSETS/"default-config.json").read_text(encoding="utf-8"))
sys.path.insert(0,str(SKILL/"scripts"))
class WechatContentTests(unittest.TestCase):
    def build(self, fixture, temp, extra=None):
        source=Path(fixture) if Path(fixture).is_absolute() else SKILL/"tests/fixtures"/fixture
        command=[sys.executable,str(SKILL/"scripts/run.py"),"all","--input",str(source),"--output-root",temp]
        command.extend(extra or [])
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        return next(Path(temp).glob(f"wechat/*/*/微信版.html")).parent

    def test_both_column_templates(self):
        with tempfile.TemporaryDirectory() as temp:
            for fixture in ("daily-news-content-package.json","github-hot-content-package.json"):
                result=subprocess.run([sys.executable,str(SKILL/"scripts/run.py"),"all","--input",str(SKILL/"tests/fixtures"/fixture),"--output-root",temp],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(len(list(Path(temp).glob("wechat/*/*/微信版.html"))),2)
            self.assertEqual(len(list(Path(temp).glob("wechat/*/*/images/合并封面.png"))),2)
    def test_rejects_unknown_schema(self):
        bad=SKILL/"tests/fixtures/unknown-schema.json"
        with tempfile.TemporaryDirectory() as temp:
            result=subprocess.run([sys.executable,str(SKILL/"scripts/run.py"),"all","--input",str(bad),"--output-root",temp],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)

    def test_seven_weekdays_use_seven_news_themes_and_default_is_separate(self):
        from news_visuals import choose_news_visual
        names=[]
        for day in range(13,20):
            choice=choose_news_visual(datetime.fromisoformat(f"2026-07-{day:02d}T06:00:00+08:00"),CONFIG,ASSETS)
            names.append(choice["name"])
        self.assertEqual(len(set(names)),7)
        self.assertEqual(choose_news_visual(datetime.fromisoformat("2026-07-20T06:00:00+08:00"),CONFIG,ASSETS)["name"],names[0])
        self.assertNotIn(CONFIG["news_visuals"]["default"]["name"],names)

    def test_missing_weekday_theme_uses_default(self):
        from news_visuals import choose_news_visual
        broken=json.loads(json.dumps(CONFIG))
        broken["news_visuals"]["weekdays"].pop("monday")
        choice=choose_news_visual(datetime.fromisoformat("2026-07-20T06:00:00+08:00"),broken,ASSETS)
        self.assertEqual(choice["name"],"unfinished-map-default")
        self.assertEqual(choice["fallback_reason"],"weekday_theme_missing")

    def test_all_news_visual_assets_exist_and_are_valid(self):
        from news_visuals import WEEKDAY_KEYS
        for variant in (*WEEKDAY_KEYS,"default"):
            for filename in ("cover.png","overview.png"):
                path=ASSETS/"news-weekday"/variant/filename
                self.assertTrue(path.exists(),path)
                with Image.open(path) as image:
                    self.assertGreaterEqual(image.width,1200)
                    self.assertEqual(round(image.width/image.height,2),round(16/9,2))
                self.assertLess(path.stat().st_size,2*1024*1024)

    def test_chinese_docs_explain_weekday_visual_workflow(self):
        docs="\n".join((SKILL/path).read_text(encoding="utf-8") for path in (
            "SKILL.md",
            "README.md",
            "references/image2-workflow.md",
            "references/daily-news.md",
        ))
        for phrase in ("七天七色","--image-input-dir","live_image2","weekday_fallback","默认兜底"):
            self.assertIn(phrase,docs)

    def test_valid_live_images_are_used_and_recorded(self):
        with tempfile.TemporaryDirectory() as temp:
            live=Path(temp)/"live"; live.mkdir()
            shutil.copy(ASSETS/"news-weekday/monday/cover.png",live/"cover.png")
            shutil.copy(ASSETS/"news-weekday/monday/overview.png",live/"overview.png")
            out=self.build("daily-news-content-package.json",temp,extra=["--image-input-dir",str(live)])
            manifest=json.loads((out/"render-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["image_mode"],"live_image2")
            self.assertEqual(manifest["fallback_reason"],"")

    def test_invalid_live_images_fall_back_to_weekday_asset(self):
        with tempfile.TemporaryDirectory() as temp:
            live=Path(temp)/"live"; live.mkdir()
            (live/"cover.png").write_bytes(b"not-png")
            out=self.build("daily-news-content-package.json",temp,extra=["--image-input-dir",str(live)])
            manifest=json.loads((out/"render-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["image_mode"],"weekday_fallback")
            self.assertEqual(manifest["fallback_reason"],"live_image_invalid")

    def test_news_uses_news_template_and_embedded_copy_images(self):
        with tempfile.TemporaryDirectory() as temp:
            out=self.build("daily-news-content-package.json",temp)
            page=(out/"微信版.html").read_text(encoding="utf-8")
            article=(out/"公众号成稿.md").read_text(encoding="utf-8")
            self.assertIn("30秒速览",page)
            self.assertIn("发生了什么",page)
            self.assertIn("为什么重要",page)
            self.assertIn("普通人需要注意什么",page)
            self.assertIn("data:image/png;base64,",page)
            self.assertNotIn('src="images/',page)
            self.assertIn("images/新闻一日脉络.png",article)
            self.assertNotIn("images/项目-01.png",article)
            self.assertIn("7月19日国内新闻梳理",article)
            self.assertIn("信息来源与动态说明",article)
            self.assertIn('<a href="https://example.com/news"',page)
            self.assertIn("链接：https://example.com/news",page)

    def test_news_overview_does_not_place_dynamic_labels_on_fixed_artwork(self):
        fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp:
            source_a=Path(temp)/"a.json"; source_b=Path(temp)/"b.json"
            source_a.write_text(json.dumps(fixture,ensure_ascii=False),encoding="utf-8")
            fixture["items"][0]["category"]="technology"
            source_b.write_text(json.dumps(fixture,ensure_ascii=False),encoding="utf-8")
            out_a=self.build(source_a,temp+"-a"); out_b=self.build(source_b,temp+"-b")
            digest=lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest(out_a/"images/新闻一日脉络.png"),digest(out_b/"images/新闻一日脉络.png"))

    def test_github_uses_project_template(self):
        with tempfile.TemporaryDirectory() as temp:
            out=self.build("github-hot-content-package.json",temp)
            page=(out/"微信版.html").read_text(encoding="utf-8")
            self.assertIn("开源坐标",page)
            self.assertIn("许可证",page)
            self.assertIn("images/项目-01.png",(out/"公众号成稿.md").read_text(encoding="utf-8"))

    def test_github_render_does_not_use_news_weekday_visuals(self):
        with tempfile.TemporaryDirectory() as temp:
            out=self.build("github-hot-content-package.json",temp)
            page=(out/"微信版.html").read_text(encoding="utf-8")
            manifest=json.loads((out/"render-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["content_template"],"github-hot")
            self.assertNotIn("weekday",manifest.get("visual_variant","").lower())
            self.assertIn("开源坐标",page)
            self.assertNotIn("昨日新闻",page)

    def test_cover_is_composed_and_versioned(self):
        with tempfile.TemporaryDirectory() as temp:
            out=self.build("daily-news-content-package.json",temp)
            with Image.open(out/"images/合并封面.png") as combined:
                self.assertEqual(combined.size,(1283,383))
                colors=combined.convert("RGB").getcolors(maxcolors=2_000_000)
                self.assertIsNotNone(colors)
                self.assertGreater(len(colors),20)
            manifest=json.loads((out/"render-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["content_template"],"daily-news")
            self.assertRegex(manifest["template_version"],r"^\d+\.\d+\.\d+$")
            self.assertEqual(manifest["image_mode"],"weekday_fallback")

    def test_news_preview_title_is_outside_copy_region(self):
        with tempfile.TemporaryDirectory() as temp:
            out=self.build("daily-news-content-package.json",temp)
            page=(out/"微信版.html").read_text(encoding="utf-8")
            preview=page.index('id="cover-preview"')
            copy=page.index('id="wechat-content"')
            self.assertLess(preview,copy)
            self.assertIn("封面和标题不包含在复制区域",page[preview:copy])

    def test_news_layout_uses_continuous_reading_hierarchy(self):
        with tempfile.TemporaryDirectory() as temp:
            out=self.build("daily-news-content-package.json",temp)
            page=(out/"微信版.html").read_text(encoding="utf-8")
            self.assertIn('data-role="time-window"',page)
            self.assertIn('border-left:4px solid',page)
            self.assertIn('data-role="keywords"',page)
            self.assertIn('data-role="editor-note"',page)
            self.assertIn('data-role="section-label"',page)
            labels=[part.split("</p>",1)[0] for part in page.split('data-role="section-label"')[1:]]
            self.assertTrue(labels)
            self.assertTrue(all("background:" not in label for label in labels))

    def test_incomplete_news_package_is_downgraded_to_needs_review(self):
        fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
        fixture["items"][0].pop("why_it_matters")
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"incomplete.json"; source.write_text(json.dumps(fixture,ensure_ascii=False),encoding="utf-8")
            out=self.build(source,temp)
            self.assertIn("输入内容仍需人工核验",(out/"微信版.html").read_text(encoding="utf-8"))
            manifest=json.loads((out/"render-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["input_status"],"needs_review")

    def test_news_reminder_label_matches_content_and_has_stable_default(self):
        from rendering import choose_news_reminder_label
        cases = [
            ({"keywords": ["传闻", "辟谣"]}, "边界说明"),
            ({"category": "society", "title": "暴雨交通预警"}, "实用提醒"),
            ({"summary": "相关部门仍在持续通报进展"}, "接下来关注"),
            ({"what_happened": "公共服务政策公布"}, "与你有关"),
            ({"why_it_matters": "信息不完整，但伴随台风预警"}, "边界说明"),
            ({"reader_action": "请注意公共安全"}, "实用提醒"),
            ({"category": "sports", "keywords": ["比赛"]}, "值得留意"),
        ]
        for item, expected in cases:
            with self.subTest(item=item):
                self.assertEqual(choose_news_reminder_label(item), expected)
        default_item = {"category": "sports", "keywords": ["比赛"]}
        self.assertEqual(
            choose_news_reminder_label(default_item),
            choose_news_reminder_label(default_item),
        )
if __name__=="__main__": unittest.main()
