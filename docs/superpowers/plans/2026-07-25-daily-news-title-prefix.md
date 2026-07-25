# Daily News Title Prefix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 强制每日新闻标题使用统计窗口起始日加“国内要闻”前缀，同时保留上游标题的主题概括。

**Architecture:** 标题规范化集中在 `wechat-content/scripts/rendering.py` 的标题解析函数中。研究层仍可提供 `editorial.article_title`，排版层只提取主题概括并拼接统一前缀，所有下游标题文件继续复用 `build_article()` 的单一结果。

**Tech Stack:** Python 3、`unittest`、JSON 内容包、Markdown、内联 HTML。

---

### Task 1: 用失败测试固定标题前缀

**Files:**
- Modify: `wechat-content/tests/test_skill.py`
- Test: `wechat-content/tests/test_skill.py`

- [ ] **Step 1: 写入失败测试**

增加三个测试：

```python
def test_article_title_is_normalized_to_dated_domestic_news_prefix(self):
    editorial={"article_title":"昨日坐标：从外交、安全到AI治理的6条变化"}
    self.assertEqual(
        resolve_article_title(editorial,"7月24日",6),
        "7月24日国内要闻：从外交、安全到AI治理的6条变化",
    )

def test_compliant_article_title_is_preserved(self):
    editorial={"article_title":"7月24日国内要闻：外交与公共安全动态密集"}
    self.assertEqual(
        resolve_article_title(editorial,"7月24日",6),
        "7月24日国内要闻：外交与公共安全动态密集",
    )

def test_wrong_date_article_title_uses_window_start_date(self):
    editorial={"article_title":"7月25日国内要闻：外交与公共安全动态密集"}
    self.assertEqual(
        resolve_article_title(editorial,"7月24日",6),
        "7月24日国内要闻：外交与公共安全动态密集",
    )
```

- [ ] **Step 2: 运行定向测试确认失败**

Run:

```powershell
python -m unittest wechat-content.tests.test_skill.WechatContentTests.test_article_title_is_normalized_to_dated_domestic_news_prefix -v
```

Expected: FAIL；实际值仍为“昨日坐标：……”。

### Task 2: 实现标题规范化

**Files:**
- Modify: `wechat-content/scripts/rendering.py`
- Modify: `wechat-content/references/daily-news.md`
- Modify: `wechat-content/SKILL.md`
- Modify: `wechat-content/scripts/run.py`
- Test: `wechat-content/tests/test_skill.py`

- [ ] **Step 1: 增加主题概括提取**

在 `resolve_article_title()` 中：

```python
prefix=f"{date_label}国内要闻："
explicit=str(editorial.get("article_title") or "").strip()
topic=re.sub(r"^\d{1,2}月\d{1,2}日国内要闻[：:]\s*","",explicit)
if topic == explicit and re.match(r"^[^：:]+[：:]",explicit):
    topic=re.split(r"[：:]",explicit,maxsplit=1)[1].strip()
if topic:
    return f"{prefix}{topic}"
return f"{prefix}{item_count}条变化值得关注"
```

`editorial.title` 不再作为日报最终标题来源。

- [ ] **Step 2: 更新模板版本和文档**

将 `TEMPLATE_VERSION` 从 `2.3.0` 更新为 `2.4.0`。文档明确所有日报标题强制使用统计窗口起始日和“国内要闻”前缀。

- [ ] **Step 3: 运行定向测试确认通过**

Run:

```powershell
python -m unittest wechat-content.tests.test_skill.WechatContentTests.test_article_title_is_normalized_to_dated_domestic_news_prefix wechat-content.tests.test_skill.WechatContentTests.test_compliant_article_title_is_preserved wechat-content.tests.test_skill.WechatContentTests.test_wrong_date_article_title_uses_window_start_date -v
```

Expected: 3 tests PASS。

### Task 3: 更新当前审核包并完整验证

**Files:**
- Modify: `E:/mm/test-skill/news/outputs/daily-news/2026-07-25/content-package.json`
- Generate: `E:/mm/test-skill/news/outputs/wechat/daily-news/2026-07-25/微信版.html`
- Generate: `E:/mm/test-skill/news/outputs/wechat/daily-news/2026-07-25/render-manifest.json`

- [ ] **Step 1: 重新生成审核包**

Run:

```powershell
python E:/mm/wxgzh/skills-repo/wechat-content/scripts/run.py all --input E:/mm/test-skill/news/outputs/daily-news/2026-07-25/content-package.json --output-root E:/mm/test-skill/news/outputs --theme auto
```

Expected: `OK_WITH_REVIEW_REQUIRED`。

- [ ] **Step 2: 验证实际输出**

确认 Markdown、HTML 和备选标题首项均为：

```text
7月24日国内要闻：从外交、安全到AI治理的6条变化
```

确认 `render-manifest.json` 的 `template_version` 为 `2.4.0`，复制仍允许，`publish_ready` 仍为 `false`。

- [ ] **Step 3: 运行完整测试**

Run:

```powershell
python -m unittest discover -s daily-news-research/tests -v
python -m unittest discover -s wechat-content/tests -v
git diff --check
```

Expected: 两套测试全部通过，差异检查无错误。

### Task 4: 同步、提交并推送

**Files:**
- Sync: `E:/codex-config/skills/wechat-content/`
- Commit: `docs/superpowers/plans/2026-07-25-daily-news-title-prefix.md`, `wechat-content/`

- [ ] **Step 1: 同步本机 Skill**

将修改的 `SKILL.md`、`references/daily-news.md`、`scripts/rendering.py` 和 `scripts/run.py` 复制到已安装的 `wechat-content`。

- [ ] **Step 2: 提交代码**

```powershell
git add docs/superpowers/plans/2026-07-25-daily-news-title-prefix.md wechat-content
git commit -m "fix: enforce daily news title prefix"
```

- [ ] **Step 3: 推送并核对远端**

```powershell
git push https://github.com/pink-mimi/skills.git main:main
git fetch https://github.com/pink-mimi/skills.git main
git rev-parse HEAD
git rev-parse FETCH_HEAD
```

Expected: 本地与远端 SHA 一致。
