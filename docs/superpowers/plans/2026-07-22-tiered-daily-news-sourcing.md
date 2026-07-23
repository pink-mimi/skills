# 阶梯式每日新闻采集实施计划

> **执行要求：** 使用 `executing-plans` 逐项实施；每个功能先写失败测试，再写最小实现；不得自动发布内容。

**目标：** 将 `daily-news-research` 升级为可独立安装、以官方原文核验为核心、全国新闻为主并可审计降级的阶梯式新闻研究 Skill。

**架构：** 保留 `scripts/run.py` 作为 CLI 入口，将安全请求、来源适配、事件处理和报告拆成独立模块。发现阶段并行采集官方列表与权威媒体，随后聚类为 10—15 条核验队列；构建阶段只允许满足来源角色、时间和编辑字段门槛的 5—8 条进入平台无关内容包。所有在线能力均用离线 fixture 测试，实时网络只做最后烟雾验证。

**技术栈：** Python 标准库、`unittest`、JSON、RSS/Atom、HTMLParser/受控正则、PowerShell、Git。

---

## 任务 1：冻结新版配置契约和失败基线

**文件：**
- 修改：`daily-news-research/tests/test_skill.py`
- 修改：`daily-news-research/assets/default-config.json`

1. 增加失败测试，要求每个默认来源具备 `organization`、`tier`、`role`、`parser`、`daily_default`、`canonical_domains` 和响应上限。
2. 增加失败测试，要求默认日报包含第一、第二阶梯，至少 5 家不同机构，并明确国际来源是否默认启用。
3. 运行 `python -m unittest daily-news-research/tests/test_skill.py -v`，确认旧配置失败。
4. 将配置升级为 schema v2：采集上限、核验上限、软配额、来源健康门槛和安全参数全部显式化。
5. 再次运行测试，确认契约测试通过且现有查询分类未回归。

## 任务 2：实现安全请求与来源状态

**文件：**
- 新建：`daily-news-research/scripts/safe_fetch.py`
- 新建：`daily-news-research/tests/test_safe_fetch.py`

1. 先测试允许受控 HTTPS、拒绝 localhost/私网/链路本地/云元数据/非网页协议。
2. 测试重定向后重新校验目标、响应体积上限、超时、限流和阻断状态。
3. 实现 `validate_url()`、`fetch()` 和结构化 `FetchResult`，不执行 JavaScript、不下载附件。
4. 运行 `python -m unittest daily-news-research/tests/test_safe_fetch.py -v`。

## 任务 3：建立来源适配器和离线样本

**文件：**
- 新建：`daily-news-research/scripts/source_adapters.py`
- 新建：`daily-news-research/tests/test_source_adapters.py`
- 新建：`daily-news-research/tests/fixtures/sources/gov-policy.html`
- 新建：`daily-news-research/tests/fixtures/sources/stats-release.html`
- 新建：`daily-news-research/tests/fixtures/sources/miit-release.html`
- 新建：`daily-news-research/tests/fixtures/sources/mem-release.html`
- 新建：`daily-news-research/tests/fixtures/sources/cma-warning.html`
- 新建：`daily-news-research/tests/fixtures/sources/media-feed.xml`

1. 为中国政府网、国家统计局、工信部、应急管理部和气象预警入口分别编写失败测试。
2. 测试 RSS/Atom 兼容、相对链接归一化、HTML 转义、发布时间和更新时间提取。
3. 实现适配器注册表，未知或改版页面返回 `parse_error`，不能返回假成功空列表。
4. 运行适配器测试并确认所有 fixture 离线通过。

## 任务 4：重构发现阶段和来源健康统计

**文件：**
- 修改：`daily-news-research/scripts/run.py`
- 新建：`daily-news-research/scripts/pipeline.py`
- 新建：`daily-news-research/tests/test_collection_pipeline.py`

1. 先测试来源并发、机构去重、候选最多 50 条，以及 `success_with_items`、`success_no_items`、`parse_error`、`timeout`、`rate_limited`、`blocked`、`invalid_time`、`fetch_error` 的准确区分。
2. 实现按 `daily_default`、类别和阶梯选源，调用安全请求与适配器。
3. 生成当前运行的 URL/机构成功率、耗时、候选数和失败原因；保留失败证据。
4. 保持 `collect/query/sources/build/verify/all` CLI 向后兼容。
5. 运行新旧采集测试。

## 任务 5：实现时间、地域、关联度和事件聚类

**文件：**
- 修改：`daily-news-research/scripts/pipeline.py`
- 新建：`daily-news-research/tests/test_event_processing.py`

1. 测试北京时间左闭右开边界、源时区转换、发布时间/更新时间/发现时间和 `time_basis`。
2. 测试全国、重要地方、国际分类；普通地方宣传和无中国直接关联的国际新闻应排除。
3. 测试 `china_relevance_reason` 不能为空，不能只凭“中国”等关键词通过。
4. 测试聚类同时使用标题、主体、地点、日期、文件编号和动作；低置信度事件不合并。
5. 测试转载指纹、`syndicated_from` 和同机构多频道去重。
6. 实现稳定 `event_id`、聚类置信度与版本关系字段。

## 任务 6：建立核验队列和官方路由

**文件：**
- 修改：`daily-news-research/scripts/pipeline.py`
- 修改：`daily-news-research/assets/default-config.json`
- 新建：`daily-news-research/references/official-source-directory.md`
- 新建：`daily-news-research/tests/test_verification_queue.py`

1. 测试原始候选聚类后只取 10—15 个高价值事件进入核验队列。
2. 测试财经、民生、科技、公共安全和法治分别路由至受控官方域名目录。
3. 测试政策、统计、灾害等级、处罚结果没有官方原文时只能为 `partial/unverified`。
4. 实现 `verification-queue.json`，包含待核验事实、推荐主管部门、现有发现来源和停止原因。
5. 对无法自动解析的官方页面保留人工/Codex 浏览器核验入口，不伪造完成状态。

## 任务 7：实现选择门槛、动态复核与状态判定

**文件：**
- 修改：`daily-news-research/scripts/pipeline.py`
- 修改：`daily-news-research/scripts/run.py`
- 新建：`daily-news-research/tests/test_selection_policy.py`

1. 测试最终 5—8 条、至少 4 类、每类通常最多 2 条、国际和地方通常各最多 1 条。
2. 测试重大事件允许突破软配额，但必须填写 `quota_exception_reason`。
3. 测试高变化事实带 `verified_at` 和 `recheck_before_publish`；过期核验触发 `needs_review`。
4. 测试少于 5 条、少于 4 类、成功机构不足、敏感事实官方覆盖不足或有 `unverified` 时不得 ready。
5. 实现价值优先评分和明确淘汰原因，禁止旧闻或低质量内容补位。

## 任务 8：实现报告、快照刷新和健康历史

**文件：**
- 修改：`daily-news-research/scripts/run.py`
- 修改：`daily-news-research/scripts/pipeline.py`
- 新建：`daily-news-research/tests/test_reports_and_modes.py`

1. 测试生成 `verification-queue.json`、`source-health.json`、`excluded-news.json` 和扩展 `source-report.md`。
2. 测试覆盖率、类别/地域分布、机构多样性、官方覆盖率和未解决风险均可审计。
3. 测试 `stable` 结果确定但会提示过期；`refresh` 保留差异；`rebuild` 不声称最新核验。
4. 测试滚动来源健康记录连续失败、最近成功、平均耗时和适配器维护告警。
5. 确保输出只含标题、链接、结构化事实和短摘要，不保存新闻全文或凭证。

## 任务 9：更新 Skill 使用规范和中文说明

**文件：**
- 修改：`daily-news-research/SKILL.md`
- 修改：`daily-news-research/README.md`
- 修改：`daily-news-research/references/editorial-policy.md`
- 修改：`daily-news-research/references/source-catalog.md`
- 修改：`daily-news-research/agents/openai.yaml`
- 修改：`README.md`

1. 先扩展文档测试，要求说明四阶梯、全国/地方/国际口径、运行耗时、状态降级、官方核验和安全边界。
2. 更新 Skill 指令：先发现、再聚类、后核验；媒体标题和热点不能直接写正文。
3. 用中文图示说明来源阶梯、完整命令、重复运行模式和输出文件。
4. 明确其独立运行，不依赖 `$news` 或 `wechat-article-writer`；只产出平台无关内容包。

## 任务 10：端到端验证、安装同步与提交

**文件：**
- 修改：`daily-news-research/tests/fixtures/` 下相关端到端样本
- 按需修改：仓库级测试和安装脚本

1. 用离线 fixture 运行 `collect/build/verify/all`，确认输出结构、状态和确定性。
2. 运行：`python -m unittest discover -s daily-news-research/tests -p "test_*.py" -v`。
3. 运行仓库现有测试和 Skill 校验脚本；执行 `git diff --check`。
4. 在网络可用时对核心官方来源做一次只读烟雾采集，记录成功、改版或阻断，不把实时结果提交为固定事实。
5. 同步已安装的 `daily-news-research`，在安装目录再次运行入口和离线测试。
6. 执行 `git status --short`，列出全部改动；不提交输出快照、密钥或用户草稿。
7. 按功能拆分提交，最终推送当前 `codex/modular-content-pipeline` 分支，仍不执行任何公众号发布操作。

