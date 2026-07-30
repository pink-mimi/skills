---
name: ai-discovery-research
description: Use when 用户需要搜索、核验和筛选 AI 模型、产品、应用、论文或案例，生成不绑定微信公众号或其他发布平台的标准内容包。
---

# AI 新发现研究

## 核心原则

围绕“AI 新发现”栏目发现近期值得普通读者了解的 AI 模型、产品、应用和实践案例。输出只生成平台无关的 `content-package.json`，不生成公众号排版、封面、登录或发布操作。

## 工作流程

1. 读取 `assets/default-config.json` 和 `references/sources-and-risks.md`。
2. 运行 `collect`，或用 `--input` 载入离线候选。候选来源可以包括官方博客、发布页、文档、论文页、Hugging Face、GitHub、主流技术媒体和社区讨论。
3. 确定性事实必须回到官方来源核验：模型/产品主页、官方文档、论文页、GitHub README、Hugging Face model card 或发布公告。
4. 对每条候选补齐名称、类型、链接、发布时间或发现时间、官方来源、用途、适合谁、费用/限制、使用门槛、风险、核验状态和推荐理由。
5. 运行 `build` 生成 `outputs/ai-discovery/YYYY-MM-DD/content-package.json`。
6. 运行 `verify`。只有状态为 `ready_for_human_review` 的内容包才适合交给 `wechat-content` 制作公众号审核包。

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

- 本 Skill 不写公众号成稿、HTML 或封面。
- 资料不足、官方来源缺失、费用/隐私/版权风险不清楚时，输出 `needs_review`。
- 不编造亲身体验；没有实际测试时只能写资料核验和可试用路径。
