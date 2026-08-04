import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]


def news_item(index, category, scope="national", focus=True, **extra):
    value = {
        "event_id": f"evt-{index:02d}",
        "title": f"第{index}条新闻标题",
        "brief": f"第{index}条新闻的一句话核验摘要。",
        "category": category,
        "geographic_scope": scope,
        "what_happened": f"第{index}条新闻发生了明确事实变化。",
        "why_it_matters": f"第{index}条新闻影响公共安排。",
        "reader_action": "普通读者可关注官方后续安排。" if focus else "",
        "reader_tip": "出行前查看属地最新预警。" if category == "public-safety" else "",
        "keywords": [category],
        "verification_status": "verified",
        "published_at": "2026-08-02T12:00:00+08:00",
        "source": f"来源机构{index}",
        "url": f"https://example.com/news/{index}",
        "editor_note": "内部核验记录",
    }
    value.update(extra)
    return value


def package(**extra):
    items = [
        news_item(1, "politics"),
        news_item(2, "society"),
        news_item(3, "finance"),
        news_item(4, "tech"),
        news_item(5, "public-safety"),
        news_item(6, "world", scope="international", focus=False),
        news_item(7, "education", focus=False),
        news_item(8, "legal", focus=False),
    ]
    payload = {
        "schema_version": 2,
        "content_type": "daily-news",
        "package_id": "daily-news-2026-08-03",
        "run_at": "2026-08-03T06:00:00+08:00",
        "status": "ready_for_human_review",
        "edition_mode": "standard",
        "window": {
            "start": "2026-08-02T06:00:00+08:00",
            "end": "2026-08-03T06:00:00+08:00",
            "boundary": "left_closed_right_open",
        },
        "editorial": {
            "article_title": "8月3日今日简报：政策、科技与全球动态",
            "lead": "过去 24 小时，政策、产业和国际现场都有新变化。",
            "focus_event_ids": ["evt-01", "evt-03", "evt-04", "evt-05"],
        },
        "items": items,
        "risks": [],
    }
    payload.update(extra)
    return payload


class WechatDailyNewsV2Tests(unittest.TestCase):
    def build(self, payload):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "daily-news-v2.json"
            source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SKILL / "scripts/run.py"), "all", "--input", str(source), "--output-root", temp],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            out = next(Path(temp).glob("wechat/daily-news/*"))
            return {
                "stdout": result.stdout,
                "article": (out / "公众号成稿.md").read_text(encoding="utf-8"),
                "page": (out / "微信版.html").read_text(encoding="utf-8"),
                "manifest": json.loads((out / "render-manifest.json").read_text(encoding="utf-8")),
            }

    def test_v2_renders_grouped_quick_scan_and_focus_only_detail(self):
        result = self.build(package())
        article = result["article"]
        page = result["page"]

        self.assertTrue(article.startswith("# 8月3日今日简报：政策、科技与全球动态"))
        self.assertIn("## 今日速览", article)
        for heading in ("### 国内动态", "### 财经与产业", "### 科技与未来", "### 世界现场"):
            self.assertIn(heading, article)
        self.assertEqual(article.count("第6条新闻的一句话核验摘要。"), 1)
        self.assertIn("## 重点解读", article)
        self.assertIn("第1条新闻发生了明确事实变化。", article)
        self.assertNotIn("第6条新闻发生了明确事实变化。", article)
        self.assertIn("统计时段：北京时间 2026年8月2日06:00—8月3日06:00。", article)
        self.assertIn("data-role=\"time-window\"", page)
        self.assertEqual(result["manifest"]["input_schema_version"], 2)
        self.assertEqual(result["manifest"]["edition_mode"], "standard")

    def test_v2_missing_brief_or_bad_focus_disables_copy_with_reasons(self):
        payload = package()
        payload["items"][0].pop("brief")
        payload["editorial"]["focus_event_ids"] = ["evt-01", "evt-99"]
        result = self.build(payload)
        page = result["page"]
        button = page.split('<button id="copy-wechat"', 1)[1].split("</button>", 1)[0]
        self.assertIn("disabled", button)
        self.assertIn("缺少 brief", page)
        self.assertIn("focus_event_ids", page)
        self.assertFalse(result["manifest"]["copy_allowed"])

    def test_v2_copy_region_rejects_internal_brief_and_hides_collector_source_labels(self):
        payload = package()
        payload["items"][0]["brief"] = "直接面向读者的一句话事实摘要，适合重点提示。"
        payload["items"][0]["source"] = "中国新闻网·滚动·日期归档·2026-08-02"
        payload["items"][0]["organization"] = ""
        result = self.build(payload)
        article = result["article"]
        page = result["page"]

        self.assertNotIn("直接面向读者", article)
        self.assertNotIn("适合重点提示", article)
        self.assertNotIn("滚动·日期归档", article)
        self.assertIn("中国新闻网", article)
        button = page.split('<button id="copy-wechat"', 1)[1].split("</button>", 1)[0]
        self.assertIn("disabled", button)
        self.assertIn("brief 含内部编辑话术", page)

    def test_public_interest_items_are_quick_scan_domestic_not_forced_focus(self):
        payload = package()
        payload["items"].append(
            news_item(
                9,
                "public-interest",
                focus=False,
                title="微信地震预警服务新增位置更新功能",
                brief="常用公共服务功能出现变化，用户可按需检查授权设置。",
                what_happened="平台上线了与公共安全提醒相关的服务功能。",
                why_it_matters="",
                reader_action="",
                keywords=["公共服务", "预警"],
            )
        )
        result = self.build(payload)
        article = result["article"]
        self.assertIn("### 国内动态", article)
        self.assertIn("微信地震预警服务新增位置更新功能", article)
        self.assertNotIn("平台上线了与公共安全提醒相关的服务功能。", article)


if __name__ == "__main__":
    unittest.main()
