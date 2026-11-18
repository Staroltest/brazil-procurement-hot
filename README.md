# 巴西政府采购HOT · Brazil Procurement HOT

巴西各级政府采购依法必须在国家公共采购门户 PNCP 集中公示（Lei 14.133/2021 第 174 条），但公告量大、只有葡萄牙语，中小企业每天要盯新标、盯截标日，错过即失去资格。

本站每半小时从 PNCP 公开查询 API 拉取「提案截止日在未来 14 天内」的招标，按城市、类别、采购方式、估算金额与截止时间整理成中文与英文清单：

- 主站（GitHub Pages）：https://staroltest.github.io/brazil-procurement-hot
- 英文版：https://staroltest.github.io/brazil-procurement-hot/en/
- Cloudflare 镜像：https://brazil-procurement-hot.pages.dev
- MCP：https://brazil-procurement-hot.pages.dev/mcp

## 数据与版权

- 唯一信源：PNCP 查询 API `pncp.gov.br/api/consulta/v1/contratacoes/proposta`（公开、免注册、免 key，返回结构化 JSON），招标列表页 `pncp.gov.br/app/editais` 同样公开。每条都附 PNCP 官方详情页链接，投标以官方公告为准。
- 本站不照抄官方公告：标题由本站按「城市 + 类别 + 方式 + 截止日」原创生成，一句话简介是本站基于金额、方式、截止时间等事实字段自己写的解读。只写标题与摘要，不转载正文、摘要原文，不使用任何源站图片。PNCP 原始采购对象文本只保存在本机未公开的 `data/store.json` 里作分类核对用，永不推送。
- 覆盖 caveat：人口 2 万以下的小市镇可延至 2027-04-01 才强制上 PNCP，本站不宣称全量覆盖；本站展示窗口内按截止时间靠前的一批（2026-11-18 核查时未来 14 天窗口内公告超过 2.2 万条），每日新增条数随官方节奏变化，不编造。

## 流水线

`tools/pncp_fetch.py`（抓 PNCP → 本地库 + 原创双语标题/简介草稿）→ `tools/generate.py`（HOT 模板生成器 → 全站静态页，中英双树）→ git 推 GitHub Pages + Cloudflare Pages 直传镜像。每半小时一轮，另有每日把关。模板来自 hot-site-template，本仓库不启用 GitHub Actions。

## 许可

MIT License。流水线模板源自 IndieHOT 的实践，信息架构参考卡兹克（张仁杰）的开源项目 AIHOT（MIT 协议），署名链保留。
