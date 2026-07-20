# 每日新闻研究 Skill

![新闻研究流程](assets/preview.svg)

## 功能

查询北京时间前一日新闻，完成时间过滤、去重、分类、来源保留与质量门槛检查，输出可交给公众号或其他平台制作 Skill 的标准内容包。

## 使用步骤

1. 安装：`npx skills add pink-mimi/skills --skill daily-news-research`
2. 对 Codex 说：`使用 $daily-news-research，生成今天的新闻内容包。`
3. 或运行：`python scripts/run.py all --output-root outputs`
4. 检查 `content-package.json`、候选记录和人工确认项。

默认统计 `[前一日 06:00，当日 06:00)`；下载 Skill 后不会自行定时执行。

## 重复运行

默认 `stable` 模式会复用同一期的原始快照，因此再次运行不会因为网站临时变化而改写选题。需要主动更新时使用 `--mode refresh`，旧版本会进入 `revisions/revision-NN/`；只想用原快照重新筛选时使用 `--mode rebuild`。
