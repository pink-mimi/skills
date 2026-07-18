<p align="center">
  <img src="assets/pink-mimi-skills-banner.svg" alt="pink-mimi Skills 工具库" width="100%">
</p>

# pink-mimi Skills 工具库

这里收录由 `pink-mimi` 持续维护的 Agent Skills。每个 Skill 都是一套可复用的 AI 工作规范，可以安装到 Codex、Claude Code，以及兼容 [Agent Skills](https://agentskills.io/) 规范的工具中。

## Skills 一览

| Skill | 功能 | 特点 | 效果预览 |
|---|---|---|---|
| [`daily-news-wechat`](daily-news-wechat/README.md) | 每日新闻采集、筛选、核验与公众号成稿 | 北京时间窗口、来源核验、7 套主题、双封面 | [查看详情与效果图](daily-news-wechat/README.md) |

## 安装

查看仓库中所有可安装的 Skill：

```bash
npx skills add pink-mimi/skills --list
```

安装指定 Skill：

```bash
npx skills add pink-mimi/skills --skill daily-news-wechat
```

使用 pnpm 也可以：

```bash
pnpm dlx skills add pink-mimi/skills --skill daily-news-wechat
```

## 仓库结构

每个 Skill 都放在仓库根目录下的独立文件夹中，并自带说明、资源和测试：

```text
skills/
├── README.md
├── assets/
├── daily-news-wechat/
│   ├── SKILL.md
│   ├── README.md
│   ├── assets/
│   ├── scripts/
│   ├── references/
│   └── tests/
└── another-skill/
    ├── SKILL.md
    ├── README.md
    └── tests/
```

新增 Skill 时，需要同时提供：

- 独立目录及符合规范的 `SKILL.md`
- 面向普通用户的中文 `README.md`
- 至少一张真实效果图或功能示意图
- 放在 Skill 自身目录中的测试
- 在本页 Skills 表格中增加一行介绍

## 维护说明

仓库会持续增加新 Skill，也会根据实际使用调整时间范围、新闻类别、模板和平台兼容性。所有自动化输出默认应经过人工审核后再对外发布。

## 许可证

[MIT License](LICENSE)
