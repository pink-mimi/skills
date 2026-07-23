# 官方核验来源目录

## 按类别触发

| 类别 | 优先核验机构 | 受控官方域名示例 |
|---|---|---|
| 政策与国家事务 | 中国政府网、全国人大 | `gov.cn`、`npc.gov.cn` |
| 经济与民生数据 | 国家统计局、人民银行、财政部、发改委、海关总署 | `stats.gov.cn`、`pbc.gov.cn`、`mof.gov.cn`、`ndrc.gov.cn`、`customs.gov.cn` |
| 科技与产业 | 工信部、科技部、中央网信办 | `miit.gov.cn`、`most.gov.cn`、`cac.gov.cn` |
| 教育与健康 | 教育部、国家卫健委、中国疾控中心 | `moe.gov.cn`、`nhc.gov.cn`、`chinacdc.cn` |
| 灾害与公共安全 | 应急管理部、中国气象局、交通运输部 | `mem.gov.cn`、`cma.gov.cn`、`mot.gov.cn` |
| 法治 | 最高人民法院、最高人民检察院、全国人大 | `court.gov.cn`、`spp.gov.cn`、`npc.gov.cn` |
| 国际与出行 | 外交部及中国驻外使领馆 | `fmprc.gov.cn` |

仅允许官方域名和配置白名单中的来源作为 `primary_sources`。媒体转载、搜索摘要、百科、自媒体和热榜不能冒充官方原文。

官方页面无法自动解析时，保留标题、候选事实和推荐机构到 `verification-queue.json`，由 Codex 或人工打开官方页面核验；无法确认时保持 `unverified`。
