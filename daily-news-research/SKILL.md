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
   - 重新采集已经结束的历史窗口时，优先使用来源配置的日期归档页；窗口跨越两个自然日时同时读取两天归档。
   - 每个来源先寻找窗口内条目，再执行全局候选上限，避免当天稍晚的新内容把昨日新闻挤出候选池。
3. 运行一次 `build`，对候选执行北京时间过滤、全国/地方/国际判断、转载识别和事件聚类，默认从更宽的候选池中建立 24—30 条 `verification-queue.json` 和 `editorial-workbench.json`，再择优收束到 8—15 条。
4. 按类别打开推荐主管部门原文核验，并在工作副本中逐条补齐工作台字段。政策、统计、灾害等级和处罚结果缺少官方原文时不得写成确定性事实。
5. 国际新闻不再要求必须与中国直接相关，但必须有重大政策、经济、科技、公共安全、地缘变化或广泛社会影响。重要地方新闻必须说明公共影响。普通娱乐、明星动态、综艺内容、常规体育赛果和赛事宣传默认淘汰；只有具备明确全国性公共利益影响时才允许例外进入，并填写 `domestic_relevance: true`、`public_interest_reason` 和重大影响等级。
6. 补齐必填的 `what_happened`、`editor_note`、`keywords` 和核验状态；只有存在明确公共影响或可执行事项时才填写 `why_it_matters`、`reader_action` 和 `reader_tip`。`brief`、`lead`、`reader_tip` 等读者字段不得包含“直接面向读者”“适合重点提示”“适合放在”“发布前”“待核验”“运营者”等内部编辑或审核话术。`editorial.article_title` 用于公众号文章标题，`editorial.title` 可保留为内容包归档名称。RSS 摘要不能直接成为发布级内容。
7. 将补齐后的 JSON 保存为单独文件，运行 `build --editorial-input <文件>`，再运行 `verify`。
8. 只有 `content-package.json` 状态为 `ready_for_human_review` 时才能交给 `wechat-content`。仍为 `needs_review` 时不得交给 `wechat-content`，必须继续核验或向用户说明不足。

默认来源必须由 `assets/default-config.json` 明确列出并并行采集。来源不足、官方覆盖不完整或采集失败时输出 `needs_review` 和错误清单；不得因为候选为空而启动无边界的泛搜索，也不得持续搜索凑够数量。网页搜索只用于核验已经发现的候选或补充明确指定的官方来源。

## 命令

```powershell
python scripts/run.py all --run-at 2026-07-20T06:00:00+08:00 --output-root outputs

# Codex 打开原文并补齐 editorial-workbench 的工作副本后：
python scripts/run.py build --run-at 2026-07-20T06:00:00+08:00 --output-root outputs --editorial-input work/verified-editorial.json
```

通用查询无需安装其他新闻 Skill：

```powershell
python scripts/run.py query --category tech --keyword AI --limit 10
python scripts/run.py query --category ai --detail -1 --format json
python scripts/run.py sources --format json
```

支持 `hot`、`politics`、`finance`、`tech`、`society`、`world`、`sports`、`entertainment`、`ai` 和 `ai-community`。体育、娱乐和 AI 来源只在明确查询时启用，不拖慢默认日报。

默认窗口为早报模式 `[前一日 06:00，当日 06:00)`，可在配置中修改。若当天中午或下午生成，可将 `window.mode` 改为 `rolling`，统计窗口会从前一日 06:00 延伸到实际 `run_at`，正文和报告仍明确显示窗口边界。定时执行由 Codex 自动化或系统任务计划负责，本 Skill 不自行常驻运行。

## 重复运行模式

- `--mode stable`：默认。同一期已有 `raw-news.json` 时复用原始快照，保证重复生成稳定。
- `--mode refresh`：重新采集，并把上一版原始快照和内容包保存到 `revisions/revision-NN/`。
- `--mode rebuild`：不联网，只根据已有原始快照重新筛选；缺少快照时停止。

正式的 `collect`、`build` 和 `all` 禁止使用通用 `--input`。`--editorial-input` 是唯一允许写回人工或 Codex 原文核验结果的入口，仅合并白名单编辑字段，不替换原始采集证据。`--input` 仅供 `query` 做离线查询；自动化测试必须显式使用 `--fixture-input`，其结果隔离写入 `test-fixtures/daily-news/`，强制标记 `needs_review`，不得覆盖正式审核包。`refresh` 必须联网采集，不能与任何 fixture 输入同时使用。

每次构建同时生成 `source-report.md`，列出采集平台、成功率、失败来源、候选数量和类别分布。读取详细来源边界时打开 `references/source-catalog.md`。

## 今日简报 v2

默认日报栏目已升级为国内外综合的“今日简报”。正常版目标为 12 条速览，允许 8—15 条；国内目标约 8 条，国际目标约 4 条，国际最多 5 条。合格新闻不足时允许生成 5—7 条精简版，少于 5 条必须保持 `needs_review`，不得用旧闻、娱乐、普通赛事或低质量转载凑数。

为提高简报丰富度，默认采集池扩大到 150 条候选、核验队列扩大到最多 30 个事件；这只是拓宽发现层，最终仍以核验质量、公共影响和类别多样性决定是否入选。微信、支付宝、交通、考试、公积金、医保、预警服务等与普通生活明确相关的平台或公共服务变化，可归入 `public-interest`/公共服务速览；没有明确影响路径的热搜、奇闻和娱乐话题仍然淘汰。

`content-package.json` 默认使用 daily-news schema v2：每条 `items[]` 必须包含 `event_id`、可直接面向读者的 `brief`、来源机构、时间、核验状态和 `what_happened`。`brief` 不能直接复制 RSS 摘要，也不能写入“适合重点提示”“适合放在某栏目”等筛选判断；出现这类话术时必须保持 `needs_review`。`editorial.focus_event_ids` 只引用 `items[].event_id`，用于从速览池中选出 3—5 条重点，不复制新闻对象。

国际新闻不再要求必须与中国直接相关，但必须属于重大政策、经济、科技、公共安全、地缘变化或具有广泛社会影响的事件，并填写 `international_impact_reason` 或等价公共影响说明。国际奇闻、空泛口头表态、明星综艺、影视宣传、普通体育赛果和赛事宣传继续默认排除。
