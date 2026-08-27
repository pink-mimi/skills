---
name: ai-discovery-research
description: Use when 用户需要搜索、核验和筛选 AI 模型、产品、应用、论文或案例，生成不绑定微信公众号或其他发布平台的标准内容包。
---

# AI 新发现研究

## 核心原则

围绕“AI 新发现”栏目发现近期值得普通读者了解的 AI 模型、产品、应用和实践案例。每期候选池建议 8-12 个，聚焦复核至少 3 个，最终只入选 1 个重点对象。

输出只生成平台无关的 `content-package.json`，不生成公众号排版、封面、登录或发布动作。

## 工作流程

1. 读取 `assets/default-config.json`、`references/sources-and-risks.md` 和 `references/content-package-v1.md`。
2. 运行 `collect`，或用 `--input` 载入离线候选。候选来源可以包括官方博客、发布页、文档、论文页、Hugging Face、ModelScope、GitHub、主流技术媒体和社区讨论。
3. 确定性事实必须回到官方来源核验：产品主页、官方文档、价格页、隐私政策、服务条款、区域可用性说明、论文页、GitHub README、Hugging Face model card 或发布公告。
4. 对每条候选补齐名称、类型、公司/团队、链接、发布时间或发现时间、官方来源、用途、适合谁、不适合谁、使用场景、费用/限制、大陆可用性、使用门槛、风险、核验状态、核验等级和推荐理由。
   - `verified` 或 `partial` 条目的官方来源都必须记录 `verified_at`。
   - `verification_grade: "C"` 的候选不得入选。
   - 只有存在 `experience_notes`、`test_notes` 或 `evidence` 记录时，才能把 `tested` 视为可追溯实测。
   - 可选记录 `official_images`，但只能把官方发布页、官方文档、官方博客、官方模型卡或官方演示页图片标为官方图；第三方介绍页图片不得标为官方图。
5. 运行 `build` 生成 `outputs/ai-discovery/YYYY-MM-DD/content-package.json`。
6. 运行 `verify`。`needs_review` 也可以交给 `wechat-content` 制作审核包，但不得标记为可直接发布。

```powershell
python scripts/run.py all --run-at 2026-07-30T19:30:00+08:00 --output-root outputs

# 离线或测试输入
python scripts/run.py all --input tests/fixtures/candidates.json --run-at 2026-07-30T19:30:00+08:00 --output-root outputs
```

## 重复运行模式

- `--mode stable`：默认。同一期已有 `raw-candidates.json` 时复用原始快照。
- `--mode refresh`：重新采集，并把上一版 `raw-candidates.json` 和 `content-package.json` 保存到 `revisions/revision-NN/`。
- `--mode rebuild`：不联网，只根据已有原始快照重新筛选；缺少快照时停止。

## 交付边界

- 本 skill 不写公众号成稿、HTML 或封面。
- 资料不足、官方来源缺失、费用/隐私/版权/大陆可用性不清楚时，输出 `needs_review`。
- 不虚构亲身体验；没有可追溯实测记录时只能写资料核验和可试用路径。
