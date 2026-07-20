---
name: daily-news-research
description: Use when 用户需要采集、核验和筛选前一日新闻，生成不绑定微信公众号、小红书或其他发布平台的标准新闻内容包。
---

# 每日新闻研究

## 核心原则

按北京时间配置的左闭右开窗口采集新闻，保留原始来源和核验状态，只输出平台无关的 `content-package.json`。新闻不足时标记 `needs_review`，不得用旧闻凑数。

## 工作流程

1. 读取 `assets/default-config.json` 和 `references/editorial-policy.md`。
2. 运行 `scripts/run.py collect` 获取候选，或用 `--input` 载入离线数据。
3. 运行 `build` 完成时间过滤、去重、分类与筛选。
4. 打开原始链接核验政策、灾害、公共安全和关键数字。
5. 运行 `verify`；只把内容包交给平台制作 Skill，不在本 Skill 中写公众号文章。

## 命令

```powershell
python scripts/run.py all --run-at 2026-07-20T06:00:00+08:00 --output-root outputs
```

默认窗口为 `[前一日 06:00，当日 06:00)`，可在配置中修改。定时执行由 Codex 自动化或系统任务计划负责，本 Skill 不自行常驻运行。

## 重复运行模式

- `--mode stable`：默认。同一期已有 `raw-news.json` 时复用原始快照，保证重复生成稳定。
- `--mode refresh`：重新采集，并把上一版原始快照和内容包保存到 `revisions/revision-NN/`。
- `--mode rebuild`：不联网，只根据已有原始快照重新筛选；缺少快照时停止。
