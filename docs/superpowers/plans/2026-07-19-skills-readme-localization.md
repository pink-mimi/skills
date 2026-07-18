# Skills 中文文档与目录整理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将仓库改造成中文可扩展 Skills 工具库，迁移每个 Skill 的测试，并为仓库及 `daily-news-wechat` 增加独立配图和说明。

**Architecture:** 根 README 只承担工具库品牌、总览和统一安装说明；每个 Skill 目录自包含 Agent 指令、用户 README、效果图、脚本、参考资料和测试。测试路径由 GitHub Actions 显式指向 Skill 内部，保证后续增加其他 Skill 时互不混杂。

**Tech Stack:** Markdown、SVG、Python `unittest`、GitHub Actions、Agent Skills 规范。

---

### Task 1: 迁移 daily-news-wechat 测试

**Files:**
- Move: `tests/test_skill.py` → `daily-news-wechat/tests/test_skill.py`
- Move: `tests/fixtures/raw-news.json` → `daily-news-wechat/tests/fixtures/raw-news.json`
- Modify: `daily-news-wechat/tests/test_skill.py`
- Modify: `.github/workflows/test.yml`

- [ ] **Step 1: 记录旧路径基线**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: 8 tests pass.

- [ ] **Step 2: 逐个移动测试文件并修正路径**

使用 `Move-Item` 逐个移动两个明确文件。将测试中的 Skill 根目录从：

```python
ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "daily-news-wechat"
```

改为：

```python
SKILL = Path(__file__).resolve().parents[1]
ROOT = SKILL.parent
```

- [ ] **Step 3: 更新 CI 测试入口**

将工作流命令改为：

```yaml
- run: python -m unittest discover -s daily-news-wechat/tests -v
- run: python -m py_compile daily-news-wechat/scripts/*.py
```

- [ ] **Step 4: 验证新旧路径**

Run:

```powershell
python -m unittest discover -s daily-news-wechat/tests -v
Test-Path tests
```

Expected: 8 tests pass；根目录 `tests` 不再存在。

### Task 2: 创建仓库级中文 README 与品牌横幅

**Files:**
- Create: `assets/pink-mimi-skills-banner.svg`
- Modify: `README.md`

- [ ] **Step 1: 创建品牌粉色 SVG**

创建 1200×360 的自包含 SVG，包含 `PINK-MIMI SKILLS`、“我的 AI 技能工具箱”和“持续维护 · 即装即用 · 中文友好”，使用浅粉到玫瑰粉渐变并保证 GitHub 明暗主题下均可读。

- [ ] **Step 2: 重写中文仓库 README**

README 依次包含：横幅、工具库定位、Skill 表格、安装命令、目录规范、维护说明和 MIT License。表格字段固定为：

```markdown
| Skill | 功能 | 特点 | 效果预览 |
|---|---|---|---|
| [`daily-news-wechat`](daily-news-wechat/README.md) | 每日新闻采集、筛选、核验与公众号成稿 | 北京时间窗口、来源核验、7 套主题、双封面 | [查看详情](daily-news-wechat/README.md) |
```

- [ ] **Step 3: 检查仓库链接和图片**

Run:

```powershell
Test-Path assets/pink-mimi-skills-banner.svg
Test-Path daily-news-wechat/README.md
```

Expected: both paths return `True` after Task 3.

### Task 3: 中文化 Skill 并增加独立详情页

**Files:**
- Create: `daily-news-wechat/README.md`
- Create: `daily-news-wechat/assets/preview.svg`
- Modify: `daily-news-wechat/SKILL.md`
- Modify: `daily-news-wechat/tests/test_skill.py`

- [ ] **Step 1: 增加中文文档结构测试**

在 `StructureTests` 中增加断言：根 README 包含 `pink-mimi Skills 工具库`，Skill README 包含 `效果预览`，两个 SVG 均存在，`SKILL.md` 包含 `## 工作流程` 且 frontmatter name 仍为 `daily-news-wechat`。

- [ ] **Step 2: 运行结构测试并确认失败**

Run:

```powershell
python -m unittest daily-news-wechat.tests.test_skill.StructureTests -v
```

Expected: FAIL because the Chinese README and SVG files do not yet exist.

- [ ] **Step 3: 创建 Skill 效果图和用户 README**

创建 1200×675 SVG，真实展示“30 秒速览、重要事件卡片、今天值得关注、信息来源、横版/方形封面”输出结构。README 包含功能、特点、预览、安装、快速开始、输出文件、配置和人工审核边界。

- [ ] **Step 4: 中文化 SKILL.md**

保留：

```yaml
---
name: daily-news-wechat
description: Use when 用户需要采集每日新闻、整理昨日国内外大事、生成经核验的中文新闻摘要、微信公众号文章或定时新闻审核包。
---
```

正文改为中文章节：概述、工作流程、命令、编辑审核门槛、自定义和常见错误。命令与现有执行语义保持不变。

- [ ] **Step 5: 运行结构测试并确认通过**

Run:

```powershell
python -m unittest daily-news-wechat.tests.test_skill.StructureTests -v
```

Expected: all `StructureTests` pass.

### Task 4: 完整验证并发布 v1.0.1

**Files:**
- Modify: `.gitignore`
- Verify: all changed files

- [ ] **Step 1: 忽略视觉讨论临时目录**

在 `.gitignore` 中增加：

```gitignore
.superpowers/
```

- [ ] **Step 2: 运行完整测试和 Skill 校验**

Run:

```powershell
python -m unittest discover -s daily-news-wechat/tests -v
python E:/codex-config/skills/.system/skill-creator/scripts/quick_validate.py daily-news-wechat
python -m py_compile daily-news-wechat/scripts/*.py
```

Expected: 8 or more tests pass, `Skill is valid!`, compilation exits 0.

- [ ] **Step 3: 检查文档质量与 Git 状态**

Run:

```powershell
git diff --check
git status --short
```

Expected: no whitespace errors；只显示计划内文件。

- [ ] **Step 4: 提交、打标签并推送**

Run:

```powershell
git add .github .gitignore README.md assets daily-news-wechat docs/superpowers/plans
git commit -m "docs: localize skill library and colocate tests"
git tag -a v1.0.1 -m "v1.0.1"
git push origin main
git push origin v1.0.1
```

Expected: `main` and annotated `v1.0.1` are present on GitHub.

- [ ] **Step 5: 验证线上 Skill 识别**

Run:

```powershell
pnpm dlx skills add pink-mimi/skills --list
```

Expected: exactly one available Skill named `daily-news-wechat`.
