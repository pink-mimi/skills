import importlib.util
import sys
import unittest
from datetime import datetime
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SKILL/"scripts"))
SPEC=importlib.util.spec_from_file_location("pipeline_events",SKILL/"scripts/pipeline.py")
pipeline=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(pipeline)


class EventProcessingTests(unittest.TestCase):
    def test_time_window_is_left_closed_right_open_and_records_basis(self):
        rows=[
            {"title":"起点新闻","url":"https://a.example/1","published_at":"2026-07-21T06:00:00+08:00"},
            {"title":"终点新闻","url":"https://a.example/2","published_at":"2026-07-22T06:00:00+08:00"},
        ]
        accepted,rejected=pipeline.filter_time_window(rows,datetime.fromisoformat("2026-07-21T06:00:00+08:00"),datetime.fromisoformat("2026-07-22T06:00:00+08:00"))
        self.assertEqual([row["title"] for row in accepted],["起点新闻"])
        self.assertEqual(accepted[0]["time_basis"],"published")
        self.assertEqual(rejected[0]["exclusion_reason"],"outside_time_window")

    def test_geographic_scope_rejects_ordinary_local_publicity(self):
        ordinary={"title":"某县举行常规项目开工仪式","category":"society","summary":"当地举行一般活动"}
        major={"title":"多省遭遇强降雨并启动防汛响应","category":"public-safety","summary":"影响长江中下游多个地区"}
        self.assertEqual(pipeline.classify_scope(ordinary)[0],"local")
        self.assertFalse(pipeline.local_is_newsworthy(ordinary))
        self.assertEqual(pipeline.classify_scope(major)[0],"national")

    def test_international_item_requires_concrete_china_relevance_reason(self):
        vague={"title":"全球市场出现变化","category":"world","summary":"受到广泛关注","china_relevance_reason":""}
        direct={"title":"主要经济体调整芯片出口规则","category":"world","summary":"规则影响中国企业供应链","china_relevance_reason":"出口规则将影响中国企业芯片供应链"}
        self.assertFalse(pipeline.international_is_relevant(vague))
        self.assertTrue(pipeline.international_is_relevant(direct))

    def test_cluster_uses_actor_location_date_and_action(self):
        rows=[
            {"title":"应急管理部部署长江中下游防汛工作","organization":"应急管理部","published_at":"2026-07-21T10:00:00+08:00","url":"https://mem.gov.cn/a","summary":"部署长江中下游防汛"},
            {"title":"长江中下游防汛工作作出新部署","organization":"新华社","published_at":"2026-07-21T11:00:00+08:00","url":"https://news.cn/a","summary":"应急管理部部署防汛"},
            {"title":"应急管理部通报长江中下游另一事故","organization":"应急管理部","published_at":"2026-07-21T12:00:00+08:00","url":"https://mem.gov.cn/b","summary":"通报道路事故"},
        ]
        clusters=pipeline.cluster_events(rows)
        self.assertEqual(len(clusters),2)
        self.assertEqual(len(clusters[0]["sources"]),2)
        self.assertGreaterEqual(clusters[0]["cluster_confidence"],0.7)

    def test_syndicated_copy_does_not_create_independent_organization(self):
        rows=[
            {"title":"全国公共服务政策发布","organization":"新华社","published_at":"2026-07-21T10:00:00+08:00","url":"https://news.cn/a","summary":"新华社通稿"},
            {"title":"全国公共服务政策发布","organization":"地方媒体","published_at":"2026-07-21T10:02:00+08:00","url":"https://local.example/a","summary":"新华社通稿","syndicated_from":"新华社"},
        ]
        cluster=pipeline.cluster_events(rows)[0]
        self.assertEqual(cluster["independent_organizations"],["新华社"])
        self.assertTrue(cluster["event_id"].startswith("evt-"))


if __name__=="__main__": unittest.main()
