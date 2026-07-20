# 微信公众号内容制作 Skill

![公众号制作流程](assets/preview.svg)

## 功能

读取新闻或 GitHub 热门标准内容包，自动选择对应栏目结构，生成标题、摘要、可一键复制的微信 HTML、正文图片，以及“左长、右方”的组合封面。

## 使用步骤

1. 安装：`npx skills add pink-mimi/skills --skill wechat-content`
2. 先运行研究 Skill 得到 `content-package.json`。
3. 对 Codex 说：`使用 $wechat-content 把这个内容包制作成公众号审核包。`
4. 打开 `微信版.html`，点击“一键复制公众号正文”。
5. 分别上传横版和方形封面，手机预览后人工发布。

组合封面尺寸为 `1283×383`，左侧 `900×383`，右侧 `383×383`；组合图用于审核，两个独立文件用于上传。

