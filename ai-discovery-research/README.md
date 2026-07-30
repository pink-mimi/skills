# AI 新发现研究

![AI 新发现研究预览](assets/preview.svg)

## 功能

搜索、核验并筛选近期值得普通读者了解的 AI 模型、产品、应用、论文和案例，生成平台无关的标准内容包。

## 使用步骤

1. 对 Codex 说：`使用 $ai-discovery-research，生成本期 AI 新发现内容包。`
2. 复核官方来源、费用限制、隐私条款、适用场景和风险。
3. 使用 `$wechat-content` 把 `content-package.json` 制作成公众号审核包。
4. 打开 `微信版.html`，复制正文并人工预览发布。

## 输出

```text
outputs/ai-discovery/YYYY-MM-DD/
├── raw-candidates.json
└── content-package.json
```

只生成审核包，不登录、不上传、不发布。
