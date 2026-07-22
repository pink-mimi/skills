import importlib.util
import sys
import unittest
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SKILL/"scripts"))
SPEC=importlib.util.spec_from_file_location("pipeline_verification",SKILL/"scripts/pipeline.py")
pipeline=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(pipeline)


class VerificationQueueTests(unittest.TestCase):
    def test_queue_is_ranked_and_limited_to_fifteen_events(self):
        clusters=[]
        for index in range(20):
            clusters.append({"event_id":f"evt-{index}","sources":[{"title":f"全国重要新闻{index}","category":"politics","impact_level":"major" if index<3 else "medium","organization":"媒体","url":f"https://example.com/{index}"}],"independent_organizations":["媒体"],"cluster_confidence":1.0})
        queue=pipeline.build_verification_queue(clusters,{"verification":{"maximum_queue":15}})
        self.assertEqual(len(queue),15)
        self.assertEqual(queue[0]["event_id"],"evt-0")
        self.assertTrue(all(row["recommended_official_sources"] for row in queue))

    def test_categories_route_to_controlled_official_domains(self):
        expected={
            "finance":"pbc.gov.cn",
            "education":"moe.gov.cn",
            "tech":"miit.gov.cn",
            "public-safety":"mem.gov.cn",
            "legal":"court.gov.cn",
        }
        for category,domain in expected.items():
            with self.subTest(category=category):
                routes=pipeline.official_routes(category)
                self.assertTrue(any(domain in row["domains"] for row in routes))

    def test_sensitive_media_only_event_requires_primary_verification(self):
        cluster={"event_id":"evt-sensitive","sources":[{"title":"全国防汛响应调整","category":"public-safety","source_role":"discovery","organization":"媒体","url":"https://example.com/a"}],"independent_organizations":["媒体"],"cluster_confidence":1.0}
        item=pipeline.build_verification_queue([cluster],{"verification":{"maximum_queue":15}})[0]
        self.assertEqual(item["verification_status"],"unverified")
        self.assertIn("官方原文",item["verification_notes"][0])

    def test_primary_source_can_mark_core_fact_verified(self):
        cluster={"event_id":"evt-policy","sources":[{"title":"国务院发布新政策","category":"politics","source_role":"primary","organization":"中国政府网","url":"https://www.gov.cn/a","published_at":"2026-07-21T10:00:00+08:00"}],"independent_organizations":["中国政府网"],"cluster_confidence":1.0}
        item=pipeline.build_verification_queue([cluster],{"verification":{"maximum_queue":15}})[0]
        self.assertEqual(item["verification_status"],"verified")
        self.assertTrue(item["primary_sources"])


if __name__=="__main__": unittest.main()
