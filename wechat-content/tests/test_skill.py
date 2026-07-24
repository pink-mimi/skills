import hashlib, json, shutil, subprocess, sys, tempfile, unittest
from datetime import datetime
from pathlib import Path
from PIL import Image

SKILL=Path(__file__).resolve().parents[1]
ASSETS=SKILL/"assets"
CONFIG=json.loads((ASSETS/"default-config.json").read_text(encoding="utf-8"))
sys.path.insert(0,str(SKILL/"scripts"))
class WechatContentTests(unittest.TestCase):
    def test_cover_title_fitting_preserves_full_text_without_ellipsis(self):
        from PIL import Image, ImageDraw
        from rendering import fit_cover_title
        title="昨天，这6件事值得关注"
        draw=ImageDraw.Draw(Image.new("RGB",(900,383),"white"))
        lines, _font=fit_cover_title(draw,title,430,max_lines=2,preferred_size=39,minimum_size=26)
        self.assertEqual("".join(lines),title.replace(" ",""))
        self.assertNotIn("…","".join(lines))

    def test_daily_news_cover_title_falls_back_to_topic_not_fixed_count(self):
        from run import resolve_cover_title
        fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
        fixture["editorial"].pop("cover_title",None)
        fixture["items"][0]["title"]="\u65c5\u6e38\u5e02\u573a\u76d1\u7ba1\u4e0e\u57fa\u7840\u6559\u80b2\u65b0\u52a8\u6001"
        title=resolve_cover_title(fixture,"")
        self.assertIn("\u65c5\u6e38\u5e02\u573a\u76d1\u7ba1",title)
        self.assertNotIn("\u8fd9",title)
        self.assertNotIn("\u4ef6\u4e8b",title)

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
        for phrase in ("部分核验","发布前复核","关键词信息条"):
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
            self.assertIn("参考来源",article)
            self.assertIn('<a href="https://example.com/news"',page)
            self.assertIn("原文地址：https://example.com/news",page)

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
            self.assertIn('data-role="editor-review-panel"',page)
            self.assertIn('data-role="section-label"',page)
            labels=[part.split("</p>",1)[0] for part in page.split('data-role="section-label"')[1:]]
            self.assertTrue(labels)
            self.assertTrue(all("background:" not in label for label in labels))

    def test_news_information_cards_use_rounded_hierarchy_and_keyword_bar(self):
        with tempfile.TemporaryDirectory() as temp:
            out=self.build("daily-news-content-package.json",temp)
            page=(out/"微信版.html").read_text(encoding="utf-8")
            manifest=json.loads((out/"render-manifest.json").read_text(encoding="utf-8"))
            time_card=page.split('data-role="time-window"',1)[1].split("</blockquote>",1)[0]
            keyword_card=page.split('data-role="keywords"',1)[1].split("</p>",1)[0]
            review_panel=page.split('data-role="editor-review-panel"',1)[1].split("</aside>",1)[0]
            self.assertIn("border-radius:10px",time_card)
            self.assertIn("box-shadow:",time_card)
            self.assertIn("关键词：",keyword_card)
            self.assertIn("｜",keyword_card)
            self.assertNotIn('data-role="keyword-chip"',keyword_card)
            self.assertIn("border-radius:8px",keyword_card)
            self.assertIn("border-radius:10px",review_panel)
            self.assertIn("不会被复制到公众号正文",review_panel)
            self.assertEqual(manifest["template_version"],"2.2.0")

    def test_incomplete_news_package_is_downgraded_to_needs_review(self):
        fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
        fixture["items"][0].pop("why_it_matters")
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"incomplete.json"; source.write_text(json.dumps(fixture,ensure_ascii=False),encoding="utf-8")
            out=self.build(source,temp)
            self.assertIn("1 条新闻缺少读者正文必填字段",(out/"微信版.html").read_text(encoding="utf-8"))
            manifest=json.loads((out/"render-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["input_status"],"needs_review")

    def test_incomplete_news_disables_copy_outside_article(self):
        fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
        fixture["items"][0].pop("why_it_matters")
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"incomplete-copy.json"
            source.write_text(json.dumps(fixture,ensure_ascii=False),encoding="utf-8")
            out=self.build(source,temp)
            page=(out/"微信版.html").read_text(encoding="utf-8")
            button=page.split('<button id="copy-wechat"',1)[1].split("</button>",1)[0]
            self.assertIn("disabled",button)
            self.assertIn('data-role="review-notice"',page)
            self.assertLess(page.index('data-role="review-notice"'),page.index('id="wechat-content"'))

    def test_incomplete_news_reports_structure_only_not_validation_success(self):
        fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
        fixture["items"][0].pop("why_it_matters")
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"incomplete-status.json"
            source.write_text(json.dumps(fixture,ensure_ascii=False),encoding="utf-8")
            result=subprocess.run([sys.executable,str(SKILL/"scripts/run.py"),"all","--input",str(source),"--output-root",temp],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn("STRUCTURE_OK_CONTENT_NEEDS_REVIEW",result.stdout)
            self.assertNotEqual(result.stdout.strip(),"OK")

    def test_complete_news_keeps_copy_enabled_without_review_notice(self):
        with tempfile.TemporaryDirectory() as temp:
            out=self.build("daily-news-content-package.json",temp)
            page=(out/"微信版.html").read_text(encoding="utf-8")
            button=page.split('<button id="copy-wechat"',1)[1].split("</button>",1)[0]
            self.assertNotIn("disabled",button)
            self.assertNotIn('data-role="review-notice"',page)

    def test_complete_partial_news_allows_copy_with_review_notice(self):
        fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
        fixture["status"]="needs_review"
        fixture["items"][0]["verification_status"]="partial"
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"partial.json"
            source.write_text(json.dumps(fixture,ensure_ascii=False),encoding="utf-8")
            out=self.build(source,temp)
            page=(out/"微信版.html").read_text(encoding="utf-8")
            button=page.split('<button id="copy-wechat"',1)[1].split("</button>",1)[0]
            self.assertNotIn("disabled",button)
            self.assertIn("0 条未核验，1 条部分核验",page)

    def test_complete_unverified_news_allows_copy_but_is_not_publish_ready(self):
        fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
        fixture["status"]="needs_review"
        fixture["items"][0]["verification_status"]="unverified"
        fixture["items"][0]["editor_note"]="内部审核：发布前补齐官方原文。"
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"unverified.json"
            source.write_text(json.dumps(fixture,ensure_ascii=False),encoding="utf-8")
            out=self.build(source,temp)
            page=(out/"微信版.html").read_text(encoding="utf-8")
            manifest=json.loads((out/"render-manifest.json").read_text(encoding="utf-8"))
            button=page.split('<button id="copy-wechat"',1)[1].split("</button>",1)[0]
            article=page.split('id="wechat-content"',1)[1].split("</article>",1)[0]
            self.assertNotIn("disabled",button)
            self.assertIn("复制正文（发布前需核验）",button)
            self.assertIn("内部审核：发布前补齐官方原文。",page[:page.index('id="wechat-content"')])
            self.assertNotIn("内部审核：发布前补齐官方原文。",article)
            self.assertTrue(manifest["copy_allowed"])
            self.assertFalse(manifest["publish_ready"])
            self.assertEqual(manifest["review_counts"]["unverified"],1)

    def test_verified_news_is_copyable_and_publish_ready(self):
        with tempfile.TemporaryDirectory() as temp:
            out=self.build("daily-news-content-package.json",temp)
            page=(out/"微信版.html").read_text(encoding="utf-8")
            manifest=json.loads((out/"render-manifest.json").read_text(encoding="utf-8"))
            button=page.split('<button id="copy-wechat"',1)[1].split("</button>",1)[0]
            self.assertIn("复制正文，可发布",button)
            self.assertTrue(manifest["copy_allowed"])
            self.assertTrue(manifest["publish_ready"])

    def test_legacy_nested_partial_evidence_allows_copy(self):
        fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
        fixture["status"]="needs_review"
        item=fixture["items"][0]
        item["verification_status"]="unverified"
        item["discovery_sources"]=[{"verification_status":"partial","verified_at":"2026-07-23T05:30:00+08:00","background_sources":[{"url":"https://example.com/official"}]}]
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"legacy-partial.json"
            source.write_text(json.dumps(fixture,ensure_ascii=False),encoding="utf-8")
            out=self.build(source,temp)
            page=(out/"微信版.html").read_text(encoding="utf-8")
            button=page.split('<button id="copy-wechat"',1)[1].split("</button>",1)[0]
            self.assertNotIn("disabled",button)
            self.assertIn("0 条未核验，1 条部分核验",page)

    def test_string_overview_is_split_into_sentences_not_characters(self):
        from rendering import build_article
        fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
        fixture["editorial"]["overview"]="市场监管公布典型案件；基础教育发布新安排；周边外交保持沟通。"
        article,_title,_summary=build_article(fixture)
        self.assertIn("- 市场监管公布典型案件",article)
        self.assertIn("- 基础教育发布新安排",article)
        self.assertNotIn("\n- 市\n- 场\n",article)

    def test_news_overview_filters_internal_review_language(self):
        from rendering import build_article
        fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
        fixture["editorial"]["overview"]="\u5e02\u573a\u76d1\u7ba1\u603b\u5c40\u516c\u5e03\u65c5\u6e38\u884c\u4e1a\u4e0d\u6b63\u5f53\u7ade\u4e89\u5178\u578b\u6848\u4ef6\uff1b\u90e8\u5206\u793e\u4f1a\u4e0e\u79d1\u6280\u8bae\u9898\u76ee\u524d\u4ec5\u6709\u6743\u5a01\u5a92\u4f53\u62a5\u9053\uff0c\u4ecd\u9700\u53d1\u5e03\u524d\u590d\u6838\uff1b\u4e2d\u83f2\u5916\u957f\u5728\u9a6c\u5c3c\u62c9\u4f1a\u89c1\u3002"
        article,_title,_summary=build_article(fixture)
        self.assertIn("\u65c5\u6e38\u884c\u4e1a\u4e0d\u6b63\u5f53\u7ade\u4e89",article)
        self.assertIn("\u4e2d\u83f2\u5916\u957f",article)
        self.assertNotIn("\u53d1\u5e03\u524d\u590d\u6838",article)
        self.assertNotIn("\u4ec5\u6709\u6743\u5a01\u5a92\u4f53\u62a5\u9053",article)

    def test_news_reminder_label_matches_content_and_has_stable_default(self):
        from rendering import choose_news_reminder_label
        cases = [
            ({"keywords": ["传闻", "辟谣"]}, "边界说明"),
            ({"category": "society", "title": "暴雨交通预警"}, "实用提醒"),
            ({"summary": "相关部门仍在持续通报进展"}, "接下来关注"),
            ({"title": "公共服务政策公布"}, "与你有关"),
            ({"summary": "信息不完整，但伴随台风预警"}, "边界说明"),
            ({"keywords": ["公共安全"]}, "实用提醒"),
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

    def test_news_reminder_label_ignores_action_and_editor_note_keywords(self):
        from rendering import choose_news_reminder_label
        item = {
            "category": "international",
            "title": "联合声明发布",
            "keywords": ["合作"],
            "summary": "各方公布合作方向。",
            "reader_action": "关注后续安全通报。",
            "editor_note": "这不代表规则立即改变。",
        }
        self.assertEqual(choose_news_reminder_label(item), "值得留意")

    def test_dynamic_news_notice_matches_selected_topics(self):
        from rendering import build_news_notice
        items = [
            {"category": "society", "title": "强降雨预警", "keywords": ["天气", "灾害"]},
            {"category": "finance", "title": "市场数据公布", "keywords": ["市场"]},
            {"category": "politics", "title": "政策发布", "keywords": ["政策"]},
        ]
        notice = build_news_notice(items)
        self.assertIn("权威预警", notice)
        self.assertIn("统计口径", notice)
        self.assertIn("正式文件", notice)
        self.assertNotIn("人工审核", notice)

    def test_dynamic_news_notice_has_neutral_fallback(self):
        from rendering import build_news_notice
        self.assertEqual(
            build_news_notice([{"category": "sports", "title": "比赛结束", "keywords": ["比赛"]}]),
            "本文依据公开资料整理，相关信息请以原始来源最新内容为准。",
        )

    def test_news_article_excludes_internal_language_and_formats_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            out = self.build("daily-news-content-package.json", temp)
            article = (out / "公众号成稿.md").read_text(encoding="utf-8")
            for phrase in ("内容包核验", "人工审核包", "尚未发布"):
                self.assertNotIn(phrase, article)
            self.assertIn("## 参考来源", article)
            self.assertNotIn("## 信息来源与动态说明", article)
            self.assertRegex(
                article,
                r"\[官方来源：.+\]\(https://example.com/news\)\n\s+原文地址：https://example.com/news",
            )
            page=(out/"微信版.html").read_text(encoding="utf-8")
            source_url=page.split('data-role="source-url"',1)[1].split("</p>",1)[0]
            self.assertIn("text-align:left",source_url)
            self.assertNotIn("text-align:justify",source_url)

    def test_incomplete_news_article_has_no_internal_placeholders(self):
        fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
        for field in ("what_happened", "why_it_matters", "reader_action", "editor_note"):
            fixture["items"][0].pop(field)
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"incomplete.json"
            source.write_text(json.dumps(fixture,ensure_ascii=False),encoding="utf-8")
            out=self.build(source,temp)
            article=(out/"公众号成稿.md").read_text(encoding="utf-8")
            for phrase in ("待人工补充", "内容包未提供", "发布前请结合原文补充"):
                self.assertNotIn(phrase,article)

    def test_news_follow_up_heading_is_omitted_when_points_repeat_titles(self):
        fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
        title=fixture["items"][0]["title"]
        fixture["editorial"]["follow_up"]=[title, f"{title}。"]
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"duplicate-follow-up.json"
            source.write_text(json.dumps(fixture,ensure_ascii=False),encoding="utf-8")
            out=self.build(source,temp)
            article=(out/"公众号成稿.md").read_text(encoding="utf-8")
            self.assertNotIn("## 今天值得关注",article)

    def test_news_editor_note_is_only_in_external_review_panel(self):
        with tempfile.TemporaryDirectory() as temp:
            out = self.build("daily-news-content-package.json", temp)
            article = (out / "公众号成稿.md").read_text(encoding="utf-8")
            page = (out / "微信版.html").read_text(encoding="utf-8")
            copy_start=page.index('id="wechat-content"')
            self.assertNotIn("先确认自己是否属于适用人群，再安排办理。",article)
            self.assertIn('data-role="editor-review-panel"',page[:copy_start])
            self.assertIn("先确认自己是否属于适用人群，再安排办理。",page[:copy_start])
            self.assertNotIn('data-role="editor-note"',page[copy_start:])

if __name__=="__main__": unittest.main()
