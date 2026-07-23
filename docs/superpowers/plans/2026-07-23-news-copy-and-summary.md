# News Copy and Summary Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 允许正文完整且至少部分核验的新闻审核包复制，并修复速览拆字与关键词视觉回归。

**Architecture:** 研究层保留核验状态；公众号层用独立 `copy_eligibility` 判断是否可复制，不篡改研究状态。渲染层在输出 Markdown 前标准化速览，在 HTML 中使用单条关键词信息栏。

**Tech Stack:** Python 3、Pillow、内联 HTML/CSS、unittest。

---

### Task 1: 核验状态保留

**Files:**
- Modify: `daily-news-research/scripts/run.py`
- Test: `daily-news-research/tests/test_skill.py`

- [ ] 写测试：带 `verified_at`、编辑字段和背景证据的 `partial` 条目经过 `prepare_research` 后仍为 `partial`。
- [ ] 运行该测试，确认当前因状态变成 `unverified` 而失败。
- [ ] 修改候选聚合，只在没有已有核验结果时使用队列状态。
- [ ] 运行 `daily-news-research` 全部测试，预期全部通过。

### Task 2: 独立复制资格

**Files:**
- Modify: `wechat-content/scripts/run.py`
- Modify: `wechat-content/scripts/rendering.py`
- Test: `wechat-content/tests/test_skill.py`

- [ ] 写测试：完整的 `verified + partial` 包按钮启用并显示复核提示。
- [ ] 写测试：含 `unverified` 或缺少编辑字段时按钮保持禁用。
- [ ] 运行测试，确认 `partial` 场景失败。
- [ ] 实现返回 `allowed`、`reason`、`partial_count` 的 `copy_eligibility(payload)`，并传给 HTML 和 manifest。
- [ ] 运行针对性测试，预期通过。

### Task 3: 速览与关键词渲染

**Files:**
- Modify: `wechat-content/scripts/rendering.py`
- Test: `wechat-content/tests/test_skill.py`

- [ ] 写测试：字符串速览拆成完整句子，不产生单字项目。
- [ ] 写测试：关键词区域包含单一信息栏和 `关键词：词1｜词2`，不包含 `keyword-chip`。
- [ ] 运行测试并确认失败。
- [ ] 实现 `normalize_overview`，兼容字符串和列表。
- [ ] 恢复关键词单条信息栏的内联样式。
- [ ] 运行 `wechat-content` 全部测试，预期通过。

### Task 4: 文档、真实预览与部署

**Files:**
- Modify: `wechat-content/SKILL.md`
- Modify: `wechat-content/references/daily-news.md`
- Test: `wechat-content/tests/test_skill.py`

- [ ] 文档写明 `partial` 的复制边界、复核提示和关键词信息条。
- [ ] 用 2026-07-23 内容包生成临时预览，检查按钮、速览、关键词和封面。
- [ ] 运行两套完整测试与 `git diff --check`。
- [ ] 逐文件同步本地安装的两个 Skill。
- [ ] 提交为 `fix: allow reviewed partial news copy` 并推送 `codex/modular-content-pipeline`。

