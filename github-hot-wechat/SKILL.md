---
name: github-hot-wechat
description: Use when 用户需要获取前一周 GitHub 热门或趋势项目、核验开源仓库、制作“未完地图”GitHub 热门栏目、生成可复制的微信公众号文章或安排按日期运行每周开源审核包。
---

# GitHub 热门微信公众号工作流

> 兼容入口：本 Skill 保留原有“一次运行完成项目研究与公众号审核包”的用法。新工作流优先使用 `github-hot-research` 生成标准内容包，再交给 `wechat-content` 制作公众号版本；旧命令在迁移期继续可用。

## 概述

按北京时间执行时刻向前连续 7 天发现并核验 GitHub 项目，生成一套“先审核、后发布”的公众号材料。此 Skill 自带写作、主题、微信 HTML、封面和降级图片规则，可独立安装运行。

## 工作流程

1. 读取 `assets/default-config.json`，计算左闭右开的 7 天窗口。
2. 运行 `collect`，扫描 GitHub Trending 综合周榜及配置中的语言周榜，并用 GitHub 官方 API 补充仓库资料。社区信息只用于发现。
3. 对 12—20 个候选核验仓库主页、README、LICENSE、Release、Commit、Issues 和安全政策。执行判断时必须读取 [references/editorial-policy.md](references/editorial-policy.md) 与 [references/sources-and-risks.md](references/sources-and-risks.md)。
4. 扫描最近 8 期 `selected.json`，排除重复项目；只有存在可核验重大变化时才能再次入选。
5. 默认精选 5 个项目，AI 与同主题数量按配置限制。少于 5 个合格项目、非 AI 候选不足、关键事实不全或发生限流时标记 `needs_review`，不得凑数。
6. 按 [references/writing-and-html.md](references/writing-and-html.md) 写作并生成 Markdown、微信 HTML、标题、摘要、来源与审核记录。
7. 按 [references/themes-and-images.md](references/themes-and-images.md) 选择主题并制作图片。
8. 运行 `verify`。只有返回 `OK` 才能描述为“可进入人工审核”；无论状态如何都不得自动发布。

## 快速使用

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run.ps1 all `
  --run-at 2026-07-25T09:00:00+08:00 `
  --output-root E:\mm\wxgzh\outputs `
  --theme auto `
  --image-mode auto
```

Windows 启动器会依次查找 `GITHUB_HOT_PYTHON`、`python`、`python3`、`py -3` 和 Codex 桌面 bundled Python。macOS/Linux 使用可用的 Python 3 解释器运行 `scripts/run.py`。

命令：

| 命令 | 行为 |
|---|---|
| `collect` | 在线发现并保存原始候选；可用 `--input fixture.json` 离线复现 |
| `build` | 核验字段、历史去重、筛选并生成审核包 |
| `verify` | 检查状态、文件、字数、图片与复制 HTML |
| `all` | 依次执行以上阶段 |

`GITHUB_TOKEN` 仅为可选的 API 限额增强，不得保存到配置或输出。定时器位于 Skill 外，只需在目标日期调用相同命令；`--run-at` 决定统计窗口与输出日期。

## 图片模式

- `auto`：脚本生成完整模板降级图，确保无生图工具时仍能交付。
- 检测到 Image 2 时：先按参考文件生成无文字主视觉和项目图，再将最终文件替换到输出 `images/`；准确中文只用本地 SVG/Pillow 叠加。
- `image2`：记录为待 Image 2 编排模式；调用者必须完成替换并重新运行 `verify`。

禁止在图片中生成日期、错误文字、真实产品界面、水印或未经授权的品牌标识。

## 人工审核边界

- Star、Release、Commit 和许可证必须在发布前重新打开官方页面复核。
- 未明确许可证的仓库不得写成“可自由使用或商用”。
- HTML 复制按钮只复制正文；封面和标题在公众号后台单独填写。
- 只生成审核包，不上传草稿、不点击发布、不保存公众号凭证。
