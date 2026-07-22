---
name: daily-news-research
description: Use when 用户需要采集、核验和筛选前一日新闻，查询热点、时政、财经、科技、社会、国际、体育、娱乐或 AI 资讯，或生成不绑定发布平台的标准新闻内容包。
---

# 每日新闻研究

## 核心原则

按北京时间配置的左闭右开窗口采集新闻，保留原始来源和核验状态，只输出平台无关的 `content-package.json`。新闻不足时标记 `needs_review`，不得用旧闻凑数。

## 工作流程

1. 读取 `assets/default-config.json`、`references/editorial-policy.md`、`references/source-catalog.md` 和 `references/official-source-directory.md`。
2. 运行 `scripts/run.py collect`：第一阶梯官方列表和第二阶梯权威媒体并行发现，专业来源按需补充，热点平台默认关闭。
3. 对候选执行北京时间过滤、全国/地方/国际判断、转载识别和事件聚类，建立不超过 15 条的 `verification-queue.json`。
4. 按类别打开推荐主管部门原文核验。政策、统计、灾害等级和处罚结果缺少官方原文时不得写成确定性事实。
5. 国际新闻必须填写具体中国关联理由；重要地方新闻必须说明公共影响。不能满足时淘汰。
6. 补齐发生了什么、为什么重要、普通人需要注意什么、克制提醒和关键词。RSS 摘要不能直接成为发布级内容。
7. 运行 `build` 和 `verify`；只把平台无关内容包交给制作 Skill，不在本 Skill 中写公众号文章或发布。

默认来源必须由 `assets/default-config.json` 明确列出并并行采集。来源不足、官方覆盖不完整或采集失败时输出 `needs_review` 和错误清单；不得因为候选为空而启动无边界的泛搜索，也不得持续搜索凑够数量。网页搜索只用于核验已经发现的候选或补充明确指定的官方来源。

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

正式的 `collect`、`build` 和 `all` 禁止使用 `--input`。`--input` 仅供 `query` 做离线查询；自动化测试必须显式使用 `--fixture-input`，其结果隔离写入 `test-fixtures/daily-news/`，强制标记 `needs_review`，不得覆盖正式审核包。`refresh` 必须联网采集，不能与任何 fixture 输入同时使用。

每次构建同时生成 `source-report.md`，列出采集平台、成功率、失败来源、候选数量和类别分布。读取详细来源边界时打开 `references/source-catalog.md`。
