# 每日新闻研究 Skill

![新闻研究流程](assets/preview.svg)

## 功能

`daily-news-research` 默认按北京时间早报窗口 `[前一日 06:00，当日 06:00)` 采集并核验新闻，输出平台无关的标准内容包。默认产品已升级为国内外综合“今日简报”：全国性国内新闻为主，重要地方新闻按公共影响入选，国际新闻可收录重大政策、经济、科技、公共安全、地缘变化和全球性公共影响事件。

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

默认先采集不超过 150 条候选，按时间、地域、转载关系和事件聚类后建立 24—30 条核验队列，最终保留 8—15 条、目标 12 条、至少 4 类。同一类别通常最多 5 条，重要地方新闻通常最多 1 条，国际新闻目标约 4 条、最多 5 条。重大事件可以突破软配额，但必须记录原因。

## 使用步骤

1. 安装：`npx skills add pink-mimi/skills --skill daily-news-research`
2. 对 Codex 说：`使用 $daily-news-research，生成今天的新闻内容包。`
3. 或运行：

```powershell
python scripts/run.py all `
  --run-at 2026-07-22T06:00:00+08:00 `
  --output-root outputs
```

4. 打开 `verification-queue.json` 推荐的原文，按 `editorial-workbench.json` 补齐每条新闻的事实、意义、读者提示、边界提醒和关键词。
5. 把补齐结果另存为 `verified-editorial.json`，重新构建：

```powershell
python scripts/run.py build `
  --run-at 2026-07-22T06:00:00+08:00 `
  --output-root outputs `
  --editorial-input work/verified-editorial.json
```

6. 检查 `source-health.json`、`excluded-news.json` 和 `source-report.md`。
7. 只有 `content-package.json` 状态为 `ready_for_human_review`，才交给公众号或其他平台制作 Skill；`needs_review` 不能直接制作可复制正文。

临时分类查询：

```powershell
python scripts/run.py query --category finance --limit 10
python scripts/run.py query --category ai --keyword GPT --detail 500 --format json
python scripts/run.py sources --format json
```

正常运行目标为 3—8 分钟；候选池扩大后，网络较慢、官方站点改版或需要浏览器核验时可能为 8—15 分钟。达到软上限后会停止低优先级补采，生成可诊断的 `needs_review` 包，不无限搜索凑数量。

## 地域与内容口径

- 全国性国内新闻：通常 4—6 条，优先政策、经济民生、科技产业、公共安全和全国影响事件。
- 重要地方新闻：通常 0—1 条，必须涉及重大灾害、公共安全、广泛影响、政策示范或全国讨论价值。
- 国际新闻：目标约 4 条、最多 5 条，不要求必须与中国直接相关，但必须属于重大政策、经济、科技、公共安全、地缘变化或全球性公共影响事件，并写清影响路径。
- 轻公共影响新闻：微信、支付宝、交通、考试、公积金、医保、预警服务等与普通生活明确相关的平台或公共服务变化，可以归入 `public-interest`/公共服务速览；通常不进入重点解读，除非确有重大公共影响。
- 普通地方会议、礼仪活动、常规工程宣传、营销软文、娱乐八卦、未证实传闻和旧闻默认排除。

## 输出文件

```text
daily-news/YYYY-MM-DD/
├── raw-news.json
├── verification-queue.json
├── editorial-workbench.json
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

## 今日简报 v2

默认产品现在是国内外综合的“今日简报”，不是只收国内新闻的昨日简讯。内容包使用 daily-news schema v2：目标 12 条速览，允许 8—15 条；其中约 8 条国内、4 条国际；再从同一个 `items` 池里用 `editorial.focus_event_ids` 选择 3—5 条重点展开。

每条入选新闻必须有 `brief`，这是核验后写给读者的一句话事实摘要，不能直接使用 RSS 摘要。`why_it_matters`、`reader_action` 和 `reader_tip` 仍然按需填写，没有明确公共影响或可执行事项时留空。少于 5 条、缺 `brief`、重点引用失效或关键事实未核验时，输出保持 `needs_review`。

国际新闻可以入选重大政策、经济、科技、公共安全、地缘变化和全球性公共影响事件；普通奇闻、明星综艺、影视宣传、常规体育赛果、营销稿和只有口头表态而无实质变化的消息继续排除。当天中午或下午补采可把配置里的 `window.mode` 改为 `rolling`，统计窗口会从前一日 06:00 延伸到实际生成时间，并在内容包和报告中记录。
