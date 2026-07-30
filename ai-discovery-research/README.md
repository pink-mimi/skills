# AI 新发现研究
![AI 新发现研究预览](assets/preview.svg)

## 功能

搜索、核验并筛选近期值得普通读者了解的 AI 模型、产品、应用、论文和案例，生成平台无关的标准内容包。

本 skill 只负责研究层：先发现 8-12 个候选，聚焦复核至少 3 个，最终只选择 1 个重点对象。它不生成微信公众号排版、不登录、不上传、不发布。

## 使用步骤

1. 对 Codex 说：`使用 $ai-discovery-research，生成本期 AI 新发现内容包。`
2. 复核官方来源、价格限制、隐私条款、适用场景、大陆可用性和风险。
3. 使用 `$wechat-content` 把 `content-package.json` 制作成公众号审核包。
4. 打开 `微信版.html`，复制正文并人工预览；最终发布由运营者完成。

## 输出

```text
outputs/ai-discovery/YYYY-MM-DD/
├── raw-candidates.json
└── content-package.json
```

`content-package.json` 的 `content_type` 固定为 `ai-discovery`。如果官方来源、价格、地区限制或实测证据不足，输出状态为 `needs_review`。

## 边界

- 不虚构亲身体验；没有可追溯实测记录时，只写公开资料核验和可试用路径。
- 不做“最好用”“最强”“人人必备”等排名式判断。
- 不把官方宣传写成实际效果。
- 不自动发布公众号内容。
