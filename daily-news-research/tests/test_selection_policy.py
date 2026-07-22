import importlib.util
import sys
import unittest
from datetime import datetime
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SKILL/"scripts"))
SPEC=importlib.util.spec_from_file_location("pipeline_selection",SKILL/"scripts/pipeline.py")
pipeline=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(pipeline)


def item(index,category,scope="national",status="verified",organization=None,**extra):
    value={
        "event_id":f"evt-{index}","title":f"新闻{index}","category":category,"geographic_scope":scope,
        "verification_status":status,"verified_at":"2026-07-22T05:30:00+08:00","organization":organization or f"机构{index}",
        "what_happened":"发生事实","why_it_matters":"具有公共影响","reader_action":"关注权威更新","editor_note":"信息仍可能更新","keywords":["新闻"],
        "impact_level":"major" if index==0 else "medium",
    }
    value.update(extra); return value


CONFIG={
    "selection":{"minimum":5,"maximum":8,"minimum_categories":4,"maximum_per_category":2,"maximum_local":1,"maximum_international":1,"required_editorial_fields":["what_happened","why_it_matters","reader_action","editor_note","keywords"]},
    "health":{"minimum_successful_organizations":5},
}


class SelectionPolicyTests(unittest.TestCase):
    def test_verified_diverse_items_are_ready(self):
        rows=[item(0,"politics"),item(1,"finance"),item(2,"tech"),item(3,"public-safety"),item(4,"society")]
        result=pipeline.select_verified_items(rows,CONFIG,{"successful_organizations":7},datetime.fromisoformat("2026-07-22T06:00:00+08:00"))
        self.assertEqual(result["status"],"ready_for_human_review")
        self.assertEqual(len(result["items"]),5)

    def test_unverified_and_stale_dynamic_facts_force_needs_review(self):
        rows=[item(0,"politics",status="unverified"),item(1,"finance"),item(2,"tech"),item(3,"public-safety",recheck_before_publish=True,verified_at="2026-07-21T06:00:00+08:00"),item(4,"society")]
        result=pipeline.select_verified_items(rows,CONFIG,{"successful_organizations":7},datetime.fromisoformat("2026-07-22T06:00:00+08:00"))
        self.assertEqual(result["status"],"needs_review")
        self.assertTrue(any("未核验" in risk for risk in result["risks"]))
        self.assertTrue(any("重新核验" in risk for risk in result["risks"]))

    def test_soft_scope_quotas_exclude_extra_local_and_international_items(self):
        rows=[item(0,"politics"),item(1,"finance"),item(2,"tech"),item(3,"public-safety"),item(4,"society"),item(5,"society",scope="local"),item(6,"culture",scope="local"),item(7,"world",scope="international",china_relevance_reason="能源价格变化影响中国进口成本"),item(8,"world",scope="international",china_relevance_reason="供应链规则影响中国企业")]
        result=pipeline.select_verified_items(rows,CONFIG,{"successful_organizations":9},datetime.fromisoformat("2026-07-22T06:00:00+08:00"))
        self.assertLessEqual(sum(row["geographic_scope"]=="local" for row in result["items"]),1)
        self.assertLessEqual(sum(row["geographic_scope"]=="international" for row in result["items"]),1)
        self.assertTrue(any(row["exclusion_reason"]=="scope_quota" for row in result["excluded"]))

    def test_quota_exception_requires_reason(self):
        rows=[item(0,"politics"),item(1,"finance"),item(2,"tech"),item(3,"public-safety"),item(4,"society"),item(5,"world",scope="international",china_relevance_reason="能源价格影响中国进口成本"),item(6,"world",scope="international",china_relevance_reason="重大冲突影响中国公民安全",quota_exception=True)]
        result=pipeline.select_verified_items(rows,CONFIG,{"successful_organizations":7},datetime.fromisoformat("2026-07-22T06:00:00+08:00"))
        self.assertNotIn("evt-6",[row["event_id"] for row in result["items"]])
        rows[-1]["quota_exception_reason"]="全球重大冲突直接影响中国公民安全"
        result=pipeline.select_verified_items(rows,CONFIG,{"successful_organizations":7},datetime.fromisoformat("2026-07-22T06:00:00+08:00"))
        self.assertIn("evt-6",[row["event_id"] for row in result["items"]])

    def test_source_health_and_editorial_completeness_gate_ready_status(self):
        rows=[item(0,"politics"),item(1,"finance"),item(2,"tech"),item(3,"public-safety"),item(4,"society",why_it_matters="")]
        result=pipeline.select_verified_items(rows,CONFIG,{"successful_organizations":3},datetime.fromisoformat("2026-07-22T06:00:00+08:00"))
        self.assertEqual(result["status"],"needs_review")
        self.assertTrue(any("机构" in risk for risk in result["risks"]))
        self.assertTrue(any("编辑字段" in risk for risk in result["risks"]))


if __name__=="__main__": unittest.main()
