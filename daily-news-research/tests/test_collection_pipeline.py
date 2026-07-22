import importlib.util
import sys
import unittest
from datetime import datetime
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SKILL/"scripts"))
SPEC=importlib.util.spec_from_file_location("pipeline",SKILL/"scripts/pipeline.py")
pipeline=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pipeline)


class Result:
    def __init__(self,status,payload=b"",error=""):
        self.status=status; self.payload=payload; self.error=error; self.final_url="https://example.com"; self.content_type="application/xml"


class CollectionPipelineTests(unittest.TestCase):
    def test_collection_distinguishes_source_statuses_and_organizations(self):
        feed=b"<rss><channel><item><title>National public service update</title><link>https://example.com/a</link><pubDate>Tue, 21 Jul 2026 10:00:00 +0800</pubDate></item></channel></rss>"
        sources=[]
        for index,status in enumerate(("success","success","timeout","rate_limited","blocked","fetch_error")):
            sources.append({"name":f"source-{index}","organization":"org-a" if index<2 else f"org-{index}","url":f"https://example.com/{index}","parser":"rss_atom","category":"general","tier":2,"role":"discovery","daily_default":True,"enabled":True,"test_status":status})
        config={"collection":{"max_workers":6,"maximum_candidates":50},"sources":sources}
        raw=pipeline.collect_sources(config,datetime.fromisoformat("2026-07-22T06:00:00+08:00"),fetcher=lambda source:Result(source["test_status"],feed if source["test_status"]=="success" else b"",source["test_status"]))
        statuses={row["status"] for row in raw["source_health"]}
        self.assertTrue({"success_with_items","timeout","rate_limited","blocked","fetch_error"}.issubset(statuses))
        self.assertEqual(raw["meta"]["successful_sources"],2)
        self.assertEqual(raw["meta"]["successful_organizations"],1)

    def test_parse_error_and_success_no_items_are_not_counted_as_item_success(self):
        sources=[
            {"name":"empty","organization":"empty","url":"https://example.com/empty","parser":"media_web","category":"general","tier":2,"role":"discovery","daily_default":True,"enabled":True,"payload":b"<html><body><ul></ul></body></html>"},
            {"name":"changed","organization":"changed","url":"https://example.com/changed","parser":"media_web","category":"general","tier":2,"role":"discovery","daily_default":True,"enabled":True,"payload":b"not html"},
        ]
        config={"collection":{"max_workers":2,"maximum_candidates":50},"sources":sources}
        raw=pipeline.collect_sources(config,datetime.now().astimezone(),fetcher=lambda source:Result("success",source["payload"]))
        self.assertEqual([row["status"] for row in raw["source_health"]],["success_no_items","parse_error"])
        self.assertEqual(raw["meta"]["successful_sources"],1)
        self.assertEqual(raw["items"],[])

    def test_candidate_limit_is_applied_after_deterministic_source_order(self):
        items="".join(f"<item><title>National update number {index:02d}</title><link>https://example.com/{index}</link><pubDate>Tue, 21 Jul 2026 10:00:00 +0800</pubDate></item>" for index in range(60))
        feed=f"<rss><channel>{items}</channel></rss>".encode()
        source={"name":"source","organization":"org","url":"https://example.com/feed","parser":"rss_atom","category":"general","tier":2,"role":"discovery","daily_default":True,"enabled":True}
        raw=pipeline.collect_sources({"collection":{"max_workers":2,"maximum_candidates":50},"sources":[source]},datetime.now().astimezone(),fetcher=lambda source:Result("success",feed))
        self.assertEqual(len(raw["items"]),50)
        self.assertTrue(raw["meta"]["candidate_limit_reached"])

    def test_transient_timeout_is_retried_once(self):
        feed=b"<rss><channel><item><title>National public service update</title><link>https://example.com/a</link><pubDate>Tue, 21 Jul 2026 10:00:00 +0800</pubDate></item></channel></rss>"
        source={"name":"source","organization":"org","url":"https://example.com/feed","parser":"rss_atom","category":"general","tier":2,"role":"discovery","daily_default":True,"enabled":True}
        attempts=[]
        def fetcher(value):
            attempts.append(value["url"])
            return Result("timeout",error="temporary") if len(attempts)==1 else Result("success",feed)
        raw=pipeline.collect_sources({"collection":{"max_workers":1,"maximum_candidates":50,"retry_count":1},"sources":[source]},datetime.now().astimezone(),fetcher=fetcher)
        self.assertEqual(len(attempts),2)
        self.assertEqual(raw["source_health"][0]["status"],"success_with_items")

    def test_candidate_cap_round_robins_across_sources_for_breadth(self):
        def feed(prefix):
            items="".join(f"<item><title>{prefix} national update {index:02d}</title><link>https://example.com/{prefix}/{index}</link><pubDate>Tue, 21 Jul 2026 10:00:00 +0800</pubDate></item>" for index in range(40))
            return f"<rss><channel>{items}</channel></rss>".encode()
        sources=[
            {"name":"alpha","organization":"alpha","url":"https://example.com/alpha","parser":"rss_atom","category":"politics","tier":1,"role":"primary","daily_default":True,"enabled":True},
            {"name":"beta","organization":"beta","url":"https://example.com/beta","parser":"rss_atom","category":"society","tier":2,"role":"discovery","daily_default":True,"enabled":True},
        ]
        raw=pipeline.collect_sources({"collection":{"max_workers":2,"maximum_candidates":50},"sources":sources},datetime.now().astimezone(),fetcher=lambda source:Result("success",feed(source["name"])))
        counts={name:sum(row["source"]==name for row in raw["items"]) for name in ("alpha","beta")}
        self.assertEqual(counts,{"alpha":25,"beta":25})


if __name__=="__main__": unittest.main()
