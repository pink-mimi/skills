# pink-mimi Skills 中文文档与目录整理设计

## 目标

将 `pink-mimi/skills` 建设为可持续扩展的中文 Agent Skills 工具库。仓库首页负责品牌与所有 Skill 的总览，每个 Skill 目录负责自身的完整介绍、效果图、实现文件和测试。

## 仓库信息架构

```text
skills/
├── README.md
├── assets/
│   └── pink-mimi-skills-banner.svg
├── daily-news-wechat/
│   ├── SKILL.md
│   ├── README.md
│   ├── assets/
│   │   └── preview.svg
│   ├── scripts/
│   ├── references/
│   └── tests/
├── .github/workflows/test.yml
└── LICENSE
```

根目录 `tests/` 移入 `daily-news-wechat/tests/`。GitHub Actions 和测试中的路径引用同步更新。以后每个 Skill 的测试都放在自己的目录中。

## 仓库 README

根目录 `README.md` 使用中文，作为整个 `pink-mimi Skills` 工具库的介绍页，依次包含：

1. 品牌粉色横幅，主题为“我的 AI 技能工具箱”。
2. 工具库定位和兼容平台说明。
3. Skill 总览表格，字段为名称、功能、特点和效果预览。
4. 安装全部或指定 Skill 的命令。
5. 仓库目录约定和新增 Skill 规范。
6. 维护、贡献与许可证信息。

总览表中的名称和效果预览链接到对应 Skill 的中文详情页。以后每新增一个 Skill，必须增加一行表格记录。

## Skill 文档

`daily-news-wechat/SKILL.md` 的 YAML 字段名和 `name` 保持英文；`description` 使用以 `Use when` 开头的中英混合触发描述，确保 Codex、Claude Code 和通用 Agent Skills 工具能够识别。正文改为中文，保留命令、文件名和配置字段的英文原文。

新增 `daily-news-wechat/README.md`，面向普通用户介绍该 Skill 的用途、功能特点、效果预览、安装、快速使用、输出文件和注意事项。`SKILL.md` 面向 Agent 执行，`README.md` 面向使用者阅读，避免职责混淆。

## 配图规则

- 仓库级横幅使用已确认的品牌粉色方向，展示 `pink-mimi Skills` 工具库，不突出单个 Skill。
- 每个 Skill 在自身 `assets/` 中保存一张具体效果图，并在自己的 README 中展示。
- 图片优先使用仓库内的 SVG，保证清晰、体积小、无需外部图床。
- 效果图展示真实输出结构，不使用虚构的新闻事实或无法兑现的产品功能。
- 后续 Skill 沿用统一画布比例和品牌识别，但可以按功能使用不同辅助色。

## 验证标准

- 根目录不再存在 `tests/`，测试位于 `daily-news-wechat/tests/`。
- 本地 8 项测试和 GitHub Actions 均使用新路径并通过。
- Skill 格式验证通过，在线工具仍只识别一个 `daily-news-wechat` Skill。
- 根 README 与 Skill README 的所有相对链接和图片路径有效。
- 中文文档无乱码、裸工作区绝对路径、占位符或失效命令。
- `SKILL.md` 的执行规则和现有新闻流水线行为不发生改变。

## 发布

完成验证后提交到 `main` 并推送 GitHub。该次更新作为 `v1.0.1` 文档与结构优化版本发布标签。
