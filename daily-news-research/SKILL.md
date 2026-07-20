---
name: daily-news-research
description: Use when 用户需要采集、核验和筛选前一日新闻，查询热点、时政、财经、科技、社会、国际、体育、娱乐或 AI 资讯，或生成不绑定发布平台的标准新闻内容包。
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

默认来源必须由 `assets/default-config.json` 明确列出并并行采集。来源不足或采集失败时输出 `needs_review` 和错误清单；不得因为候选为空而启动无边界的泛搜索，也不得持续搜索凑够数量。网页搜索只用于核验已经发现的候选或补充明确指定的官方来源。

## 命令

```powershell
python scripts/run.py all --run-at 2026-07-20T06:00:00+08:00 --output-root outputs
```

通用查询无需安装其他新闻 Skill：

```powershell
python scripts/run.py query --category tech --keyword AI --limit 10
python scripts/run.py query --category ai --detail -1 --format json
python scripts/run.py sources --format json
```

支持 `hot`、`politics`、`finance`、`tech`、`society`、`world`、`sports`、`entertainment`、`ai` 和 `ai-community`。体育、娱乐和 AI 来源只在明确查询时启用，不拖慢默认日报。

默认窗口为 `[前一日 06:00，当日 06:00)`，可在配置中修改。定时执行由 Codex 自动化或系统任务计划负责，本 Skill 不自行常驻运行。

## 重复运行模式

- `--mode stable`：默认。同一期已有 `raw-news.json` 时复用原始快照，保证重复生成稳定。
- `--mode refresh`：重新采集，并把上一版原始快照和内容包保存到 `revisions/revision-NN/`。
- `--mode rebuild`：不联网，只根据已有原始快照重新筛选；缺少快照时停止。

每次构建同时生成 `source-report.md`，列出采集平台、成功率、失败来源、候选数量和类别分布。读取详细来源边界时打开 `references/source-catalog.md`。
