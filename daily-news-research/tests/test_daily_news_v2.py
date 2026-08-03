import importlib.util
import sys
import unittest
from datetime import datetime
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
SPEC = importlib.util.spec_from_file_location("daily_news_run", SKILL / "scripts/run.py")
run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run)


CONFIG = {
    "window": {"end_time": "06:00", "duration_hours": 24},
    "collection": {},
    "health": {"minimum_successful_organizations": 5},
    "selection": {
        "minimum": 8,
        "compact_minimum": 5,
        "maximum": 15,
        "target": 12,
        "minimum_categories": 4,
        "maximum_per_category": 5,
        "maximum_local": 2,
        "maximum_international": 5,
        "target_domestic": 8,
        "target_international": 4,
        "focus_target": 4,
        "focus_minimum": 3,
        "focus_maximum": 5,
        "scope": "domestic-international",
        "required_editorial_fields": ["brief", "what_happened", "editor_note", "keywords"],
    },
}


def item(index, category, scope="national", impact="medium", **extra):
    value = {
        "event_id": f"evt-{index:02d}",
        "title": f"第{index}条重要新闻",
        "brief": f"第{index}条新闻已经由来源核验，适合放入今日速览。",
        "summary": f"第{index}条新闻摘要",
        "category": category,
        "geographic_scope": scope,
        "verification_status": "verified",
        "verified_at": "2026-08-03T05:20:00+08:00",
        "published_at": "2026-08-02T12:00:00+08:00",
        "source": f"来源机构{index}",
        "url": f"https://example.com/news/{index}",
        "what_happened": f"第{index}条新闻发生了明确事实变化。",
        "why_it_matters": f"第{index}条新闻有公共影响。",
        "reader_action": "普通读者可关注后续官方安排。",
        "editor_note": "内部核验记录",
        "keywords": [category, "今日简报"],
        "impact_level": impact,
    }
    value.update(extra)
    return value


class DailyNewsV2Tests(unittest.TestCase):
    def test_builds_standard_v2_brief_with_valid_focus_ids(self):
        rows = [
            item(1, "politics", impact="major"),
            item(2, "finance", impact="major"),
            item(3, "tech", impact="major"),
            item(4, "public-safety", impact="major"),
            item(5, "society"),
            item(6, "education"),
            item(7, "legal"),
            item(8, "finance"),
            item(9, "world", scope="international", impact="major", international_impact_reason="主要经济体公布重大经济政策，影响全球市场预期。"),
            item(10, "world", scope="international", international_impact_reason="海外公共安全事件涉及大范围交通和供应链中断。"),
            item(11, "world", scope="international", international_impact_reason="国际科技监管变化影响全球数字产品规则。"),
            item(12, "world", scope="international", international_impact_reason="地缘局势出现实质变化并引发多国公开应对。"),
        ]
        package = run.build({"items": rows, "meta": {"successful_organizations": 8}}, datetime.fromisoformat("2026-08-03T06:00:00+08:00"), CONFIG)

        self.assertEqual(package["schema_version"], 2)
        self.assertEqual(package["editorial"]["article_title"], "8月3日今日简报：政策、科技与全球动态")
        self.assertEqual(package["edition_mode"], "standard")
        self.assertEqual(len(package["items"]), 12)
        self.assertEqual(sum(row["geographic_scope"] == "international" for row in package["items"]), 4)
        self.assertEqual(len(package["editorial"]["focus_event_ids"]), 4)
        self.assertTrue(set(package["editorial"]["focus_event_ids"]).issubset({row["event_id"] for row in package["items"]}))
        self.assertTrue(all(row.get("brief") for row in package["items"]))

    def test_compact_and_too_short_modes_are_explicit(self):
        compact_rows = [item(index, category) for index, category in enumerate(("politics", "finance", "tech", "public-safety", "world"), 1)]
        compact_rows[-1]["geographic_scope"] = "international"
        compact_rows[-1]["international_impact_reason"] = "重大国际公共安全事件具有广泛影响。"
        compact = run.build({"items": compact_rows, "meta": {"successful_organizations": 8}}, datetime.fromisoformat("2026-08-03T06:00:00+08:00"), CONFIG)
        self.assertEqual(compact["edition_mode"], "compact")
        self.assertEqual(compact["status"], "ready_for_human_review")
        self.assertGreaterEqual(len(compact["editorial"]["focus_event_ids"]), 3)

        too_short = run.build({"items": compact_rows[:4], "meta": {"successful_organizations": 8}}, datetime.fromisoformat("2026-08-03T06:00:00+08:00"), CONFIG)
        self.assertEqual(too_short["status"], "needs_review")
        self.assertTrue(any("少于 5 条" in risk for risk in too_short["risks"]))

    def test_major_international_items_no_longer_require_china_relevance(self):
        rows = [item(1, "politics"), item(2, "finance"), item(3, "tech"), item(4, "public-safety")]
        rows += [
            item(5, "world", scope="international", title="主要经济体发布重大货币政策", international_impact_reason="主要经济体公布重大货币政策，影响全球金融市场。"),
            item(6, "world", scope="international", title="海外奇闻引发围观", international_impact_reason=""),
        ]
        package = run.build({"items": rows, "meta": {"successful_organizations": 8}}, datetime.fromisoformat("2026-08-03T06:00:00+08:00"), CONFIG)
        titles = [row["title"] for row in package["items"]]
        self.assertIn("主要经济体发布重大货币政策", titles)
        self.assertNotIn("海外奇闻引发围观", titles)

    def test_missing_brief_and_invalid_focus_ids_keep_needs_review(self):
        rows = [item(index, category) for index, category in enumerate(("politics", "finance", "tech", "public-safety", "society"), 1)]
        rows[0].pop("brief")
        raw = {
            "items": rows,
            "meta": {"successful_organizations": 8},
            "editorial": {"focus_event_ids": ["evt-01", "evt-99", "evt-99"]},
        }
        package = run.build(raw, datetime.fromisoformat("2026-08-03T06:00:00+08:00"), CONFIG)
        self.assertEqual(package["status"], "needs_review")
        self.assertTrue(any("brief" in risk for risk in package["risks"]))
        self.assertTrue(any("focus_event_ids" in risk for risk in package["risks"]))


if __name__ == "__main__":
    unittest.main()
