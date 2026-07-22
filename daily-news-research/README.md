# 每日新闻研究 Skill

![新闻研究流程](assets/preview.svg)

## 功能

`daily-news-research` 按北京时间 `[前一日 06:00，当日 06:00)` 采集并核验新闻，输出平台无关的标准内容包。默认定位是：全国性国内新闻为主，重要地方新闻按公共影响入选，国际新闻只保留与中国普通读者有直接关系的少量事件。

它采用四级来源阶梯：

```text
官方原始来源（事实核验）
        ↓
权威媒体（候选发现与现场背景）
        ↓
专业来源（类别不足时补充）
        ↓
热点平台（可选线索，不能单独作为正文依据）
```

默认先采集不超过 50 条候选，按时间、地域、转载关系和事件聚类后建立不超过 15 条的核验队列，最终保留 5—8 条、至少 4 类。同一类别通常最多 2 条，重要地方新闻通常最多 1 条，国际新闻通常最多 1 条。重大事件可以突破软配额，但必须记录原因。

## 使用步骤

1. 安装：`npx skills add pink-mimi/skills --skill daily-news-research`
2. 对 Codex 说：`使用 $daily-news-research，生成今天的新闻内容包。`
3. 或运行：

```powershell
python scripts/run.py all `
  --run-at 2026-07-22T06:00:00+08:00 `
  --output-root outputs
```

4. 检查 `verification-queue.json` 中仍需打开的官方原文。
5. 检查 `source-health.json`、`excluded-news.json` 和 `source-report.md`。
6. 只有 `content-package.json` 的状态和事实都经人工确认后，才交给公众号或其他平台制作 Skill。

临时分类查询：

```powershell
python scripts/run.py query --category finance --limit 10
python scripts/run.py query --category ai --keyword GPT --detail 500 --format json
python scripts/run.py sources --format json
```

正常运行目标为 3—8 分钟；网络较慢、官方站点改版或需要浏览器核验时可能为 8—15 分钟。达到软上限后会停止低优先级补采，生成可诊断的 `needs_review` 包，不无限搜索凑数量。

## 地域与内容口径

- 全国性国内新闻：通常 4—6 条，优先政策、经济民生、科技产业、公共安全和全国影响事件。
- 重要地方新闻：通常 0—1 条，必须涉及重大灾害、公共安全、广泛影响、政策示范或全国讨论价值。
- 国际新闻：通常 0—1 条，必须写清贸易、能源、供应链、出行、公民安全、金融、科技限制或公共卫生等中国关联理由。
- 普通地方会议、礼仪活动、常规工程宣传、营销软文、娱乐八卦、未证实传闻和旧闻默认排除。

## 输出文件

```text
daily-news/YYYY-MM-DD/
├── raw-news.json
├── verification-queue.json
├── source-health.json
├── excluded-news.json
├── content-package.json
└── source-report.md
```

来源请求成功不等于事实已经核验。政策、统计、灾害等级、处罚结果和其他敏感关键事实缺少官方原文时，状态只能是 `partial` 或 `unverified`；整体状态必须为 `needs_review`。

## 重复运行

- `stable`：默认复用本期原始快照，保证相同输入得到稳定结果。
- `refresh`：重新采集并把旧快照与内容包存入 `revisions/revision-NN/`。
- `rebuild`：只使用已有快照离线重建，不声称完成最新核验，并提示发布前刷新。

## 安全与独立性

采集器限制协议、私网地址、重定向和响应体积，不执行页面 JavaScript，不长期保存新闻全文、Cookie 或密钥。本 Skill 独立实现，不依赖 `$news`、`wechat-article-writer` 或公众号模板；它只生成研究内容包，不上传或发布。

详细来源见 [`references/source-catalog.md`](references/source-catalog.md)，官方核验路由见 [`references/official-source-directory.md`](references/official-source-directory.md)。
