import importlib.util
import unittest
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]
FIXTURES=SKILL/"tests/fixtures/sources"
SPEC=importlib.util.spec_from_file_location("source_adapters",SKILL/"scripts/source_adapters.py")
source_adapters=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(source_adapters)


class SourceAdapterTests(unittest.TestCase):
    def test_five_official_adapters_extract_title_absolute_url_and_time(self):
        cases=(
            ("gov_policy","gov-policy.html","https://www.gov.cn/"),
            ("stats_release","stats-release.html","https://www.stats.gov.cn/sj/zxfb/"),
            ("miit_release","miit-release.html","https://www.miit.gov.cn/"),
            ("mem_release","mem-release.html","https://www.mem.gov.cn/gk/"),
            ("cma_warning","cma-warning.html","https://www.cma.gov.cn/"),
        )
        for parser,fixture,url in cases:
            with self.subTest(parser=parser):
                source={"name":parser,"organization":parser,"category":"general","role":"primary","tier":1,"parser":parser,"url":url}
                result=source_adapters.parse(FIXTURES.joinpath(fixture).read_bytes(),source)
                self.assertEqual(result.status,"success_with_items")
                self.assertEqual(len(result.items),1)
                self.assertTrue(result.items[0]["url"].startswith("https://"))
                self.assertIn("2026-07-21",result.items[0]["published_at"])
                self.assertEqual(result.items[0]["source_role"],"primary")

    def test_rss_adapter_preserves_organization_and_source_role(self):
        source={"name":"新华网","organization":"新华社","category":"general","role":"discovery","tier":2,"parser":"rss_atom","url":"https://www.news.cn/feed.xml"}
        result=source_adapters.parse((FIXTURES/"media-feed.xml").read_bytes(),source)
        self.assertEqual(result.status,"success_with_items")
        self.assertEqual(result.items[0]["organization"],"新华社")
        self.assertEqual(result.items[0]["source_role"],"discovery")

    def test_empty_valid_page_is_distinct_from_changed_page(self):
        source={"name":"统计局","organization":"国家统计局","category":"finance","role":"primary","tier":1,"parser":"stats_release","url":"https://www.stats.gov.cn/sj/zxfb/"}
        empty=source_adapters.parse(b"<html><body><div class='list'></div></body></html>",source)
        changed=source_adapters.parse(b"this is not html",source)
        self.assertEqual(empty.status,"success_no_items")
        self.assertEqual(changed.status,"parse_error")

    def test_javascript_shell_is_parse_error_not_successful_empty_page(self):
        source={"name":"政策库","organization":"中国政府网","category":"politics","role":"primary","tier":1,"parser":"gov_policy","url":"https://sousuo.www.gov.cn/zcwjk/"}
        shell=b'<html><body><div id="app"></div><script src="app.js"></script></body></html>'
        self.assertEqual(source_adapters.parse(shell,source).status,"parse_error")

    def test_date_can_follow_long_official_card_markup(self):
        source={"name":"工信部","organization":"工业和信息化部","category":"tech","role":"primary","tier":1,"parser":"miit_release","url":"https://www.miit.gov.cn/"}
        spacer="<img src='x'>"*30
        payload=f'<html><body><div><a href="/article.html">工业和信息化部发布全国制造业运行情况</a>{spacer}<span>2026-07-21</span></div></body></html>'.encode()
        result=source_adapters.parse(payload,source)
        self.assertEqual(result.status,"success_with_items")

    def test_image_link_before_title_link_does_not_consume_official_card(self):
        source={"name":"工信部","organization":"工业和信息化部","category":"tech","role":"primary","tier":1,"parser":"miit_release","url":"https://www.miit.gov.cn/"}
        payload='<html><body><div class="list"><a href="/a"><img src="x.jpg"></a><h3><a href="/a">工业和信息化部发布全国制造业运行情况</a><span>2026-07-21</span></h3></div></body></html>'.encode()
        result=source_adapters.parse(payload,source)
        self.assertEqual(result.status,"success_with_items")

    def test_article_links_without_extractable_dates_are_parse_error(self):
        source={"name":"媒体","organization":"媒体","category":"general","role":"discovery","tier":2,"parser":"media_web","url":"https://example.com/"}
        payload=b'<html><body><div class="news-list"><a href="/a">National public service update without date</a></div></body></html>'
        self.assertEqual(source_adapters.parse(payload,source).status,"parse_error")

    def test_output_text_is_cleaned_and_not_executable_markup(self):
        source={"name":"媒体","organization":"媒体","category":"general","role":"discovery","tier":2,"parser":"media_web","url":"https://example.com/"}
        payload=b'<html><body><a href="/a"><script>alert(1)</script>National &amp; public service update</a><time>2026-07-21</time></body></html>'
        result=source_adapters.parse(payload,source)
        self.assertNotIn("<script>",result.items[0]["title"])
        self.assertNotIn("alert(1)",result.items[0]["title"])


if __name__=="__main__":
    unittest.main()
