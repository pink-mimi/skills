---
name: github-hot-research
description: Use when 用户需要发现并核验执行时刻前连续 7 天的 GitHub 热门项目，生成不绑定微信公众号或其他发布平台的标准内容包。
---

# GitHub 热门研究

## 核心原则

默认以 `https://github.com/trending?since=weekly` 的 GitHub Trending 周榜为准，锁定页面前 10 个项目并保持原始顺序，不用搜索 API、评分或历史去重替换榜单项目。每个项目必须保留名称、描述、语言、总 Star、Fork、本周新增 Star、完整 GitHub 地址、读者推荐字段、核验信息、图片候选和 Image2 brief。许可证、维护或图片授权不完整时，项目仍留在前十列表中，但内容包状态标记 `needs_review`，审核负担留在平台外部审核区。输出固定为平台无关的 `schema_version: 2`，契约见 [references/content-package-v2.md](references/content-package-v2.md)。

## 工作流程

1. 读取配置和 `references/sources-and-risks.md`。
2. 运行 `collect`，或用 `--input` 载入离线候选；联网采集只取 GitHub Trending weekly 前 10 名。
3. 对前 10 个项目补充核验用途、README、许可证、维护、门槛、风险和受众；同时从 README/docs/homepage 提取项目截图候选，并排除 badge、Logo、头像、社交预览和装饰图。
4. 运行 `build` 生成 `content-package.json`。
5. 运行 `verify`，再把内容包交给平台制作 Skill。动态指标必须带 `verified_at`；无法确认的 `weekly_stars` 使用 `null`，不得写成 0。

```powershell
python scripts/run.py all --run-at 2026-07-25T09:00:00+08:00 --output-root outputs
```

定时运行由外部自动化负责；本 Skill 不生成公众号排版、封面或发布操作。

## 重复运行模式

- `--mode stable`：默认。同一期已有 `raw-candidates.json` 时复用原始快照。
- `--mode refresh`：重新采集，并把上一版原始快照和内容包保存到 `revisions/revision-NN/`。
- `--mode rebuild`：不联网，只根据已有原始快照重新筛选；缺少快照时停止。
