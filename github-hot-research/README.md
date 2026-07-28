# GitHub 热门研究 Skill

![GitHub 热门研究流程](assets/preview.svg)

## 功能

默认检索 `https://github.com/trending?since=weekly` 的 GitHub Trending 周榜，锁定页面前 10 个项目并保持原始顺序，输出平台无关的 schema v2 标准内容包。内容包保留名称、描述、语言、总 Star、Fork、本周新增 Star、完整项目地址、读者卡、核验证据、风险、README/docs 图片候选、Image2 brief，以及审核状态。

## 使用步骤

1. 安装：`npx skills add pink-mimi/skills --skill github-hot-research`
2. 对 Codex 说：`使用 $github-hot-research，生成本周 GitHub 热门内容包。`
3. 或运行：`python scripts/run.py all --output-root outputs`
4. 发布前复核仓库主页、README、LICENSE、Release、最近 Commit、动态指标核验时间和图片授权。

默认约束：周榜前 10 个全部保留，不因评分、分类、AI 占比或历史推荐记录替换项目。周增 Star 无法确认时为 `null`，绝不以 0 代替；许可证、维护或图片授权不完整时标记 `needs_review`。

下载 Skill 后不会自行每周运行；请使用 Codex 自动化或系统任务计划定时调用。

## 重复运行

默认 `stable` 模式复用本期原始候选，保证重复生成稳定。主动重新联网使用 `--mode refresh`，旧快照和内容包会保存到 `revisions/revision-NN/`；只重新评分和筛选使用 `--mode rebuild`。
