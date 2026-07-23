---
name: github-hot-research
description: Use when 用户需要发现并核验执行时刻前连续 7 天的 GitHub 热门项目，生成不绑定微信公众号或其他发布平台的标准内容包。
---

# GitHub 热门研究

## 核心原则

发现 12—20 个候选，核验仓库、README、许可证和维护情况，默认精选 5 个。AI 项目最多 3 个，最近 8 期默认去重；不足 5 个合格项目时标记 `needs_review`。

## 工作流程

1. 读取配置和 `references/sources-and-risks.md`。
2. 运行 `collect`，或用 `--input` 载入离线候选。
3. 人工补充并核验用途、许可证、维护、门槛、风险和受众。
4. 运行 `build` 生成 `content-package.json`。
5. 运行 `verify`，再把内容包交给平台制作 Skill。

```powershell
python scripts/run.py all --run-at 2026-07-25T09:00:00+08:00 --output-root outputs
```

定时运行由外部自动化负责；本 Skill 不生成公众号排版、封面或发布操作。

## 重复运行模式

- `--mode stable`：默认。同一期已有 `raw-candidates.json` 时复用原始快照。
- `--mode refresh`：重新采集，并把上一版原始快照和内容包保存到 `revisions/revision-NN/`。
- `--mode rebuild`：不联网，只根据已有原始快照重新筛选；缺少快照时停止。
