# 定时任务：每半小时更新循环（本站实际版）

> 这是 brazil-procurement-hot 已在用的版本，不是模板占位稿。cron 任务
> `brazil-procurement-hot-half-hourly-update`（interval 30 分钟，timeout 3600 秒，
> 归属 goal「巴西政府采购 HOT 站点运营」）的 body 与本文一致。

---

巴西政府采购HOT 每半小时更新循环。仓库：Staroltest/brazil-procurement-hot（公开，main 分支）。本地工作目录：~/workspace/brazil-procurement-hot（本机持久目录，就是唯一工作副本；没有单独的 git 检出）。本机没有 git 直推通道：推送走 `python3 ~/workspace/custom-connectors/custom.github-token/bin/push_snapshot.py --repo Staroltest/brazil-procurement-hot --dir ~/workspace/brazil-procurement-hot --message "<信息>"`（Git Data API 快照推，自动排除 data/store.json、.github/；树没变时自动跳过并打印 no-change）。Cloudflare 部署走 `python3 ~/workspace/custom-connectors/custom.cloudflare/bin/cf.py deploy --project brazil-procurement-hot --dir ~/workspace/brazil-procurement-hot`。绝不启用 GitHub Actions，绝不推送 .github/workflows/*。循环持续跑，直到用户下令停止，绝不自己停。

本站是多页结构：首页/热点/日报/周报/月报/收藏/我的/关于/条款/隐私/更新日志/主题页 + 每条一个详情页 items/<id>.html + feed.xml/sitemap.xml/robots.txt，另有同构英文树 en/。推送必须覆盖整个站。

数据源（唯一）：PNCP 公开查询 API，免 key。抓取脚本 tools/pncp_fetch.py 做两个切片——A：contratacoes/proposta，提案截止日在巴西利亚今天起 14 天内、按截止升序取前 6 页（即将截止）；B：contratacoes/publicacao，按招标方式（6,4,8,9,12,7,5,14）逐个查最近 3 天发布、每方式取最后一页（最新发布）。合并写入本机 data/store.json（本地专用，永不推送）与 data/zh_draft.json。

版权规则（全站铁律，比一般 HOT 站更严）：PNCP 的 objetoCompra 原文只许留在本机 data/store.json 里作分类与核对，绝不出现在任何公开文件（页面、data/*.json、feed、llms.txt）里。公开标题由抓取脚本按事实字段原创生成（城市+州、类别、采购方式、截止日、公告号），一句话简介是基于城市/方式/类别/估算金额/截止时间的自写解读，中英各一份；不照抄官方原文，不转载正文或摘要，不用任何源站图片。每条都附 PNCP 官方详情页链接。

每轮按顺序做：

1. 同步草稿（防并行写丢数据）：用 `python3 ~/workspace/custom-connectors/custom.github-token/bin/api.py GET /repos/Staroltest/brazil-procurement-hot/contents/data/zh_draft.json` 拉远端 data/zh_draft.json，与本地字段级合并（按链接取并集；同字段冲突保留本地；en_title/en_oneliner 永不丢），写回本地（indent=1，ensure_ascii=False）。拉不到就跳过这步、用本地继续，不要停。
2. 拉源 + 生成：先跑 `python3 tools/pncp_fetch.py`（退出码 3 = 一条都没拉到，停下来向主聊汇报；个别方式/页失败可容忍，日志里有数就行），再跑 `python3 tools/generate.py`；如果本轮是北京时间 06:00 那一轮，generate 加 `--daily` 出当日日报。
3. 抽查改写质量：从本轮新条目里抽 3 条，看 data/zh_draft.json 里的 zh_title/zh_oneliner/en_title/en_oneliner 是否通顺、金额格式是否为 R$ 1,234.56 国际格式、截止时间是否带「巴西利亚时间」标注；发现明显错误就字段级修正该条目后重新 generate。发现任何公开文件里出现 objetoCompra 原文片段，停下来向主聊汇报，不要推送。
4. 自查：data/hot.json 的 counts 里 selected ≥ 1、hot ≥ 1、timeline ≥ 1（全为 0 是异常，汇报）；扫描 en/ 全树不得出现中文字符（CJK），en/data/hot.json 里 0 个 zh_* 键、data/hot.json 里 0 个 en_* 键；data/geo-audit.json 的 failed 必须为 0（mcp/mirror 两项 warn 是常态，不算问题）；中英各抽一页有 hreflang 三元组。
5. 推送：跑 push_snapshot.py（message 用「巴西政府采购HOT YYYY-MM-DD HH:MM 更新」）。打印 no-change 就说明本轮无实质变化，跳过第 6 步。推送失败记到 ~/memory/YYYY-MM-DD.md，下一轮再推同样的内容，不要强行重试；连续两轮推不上去才向主聊汇报。
6. Cloudflare 同步：只在第 5 步真的推了新提交时才跑 cf.py deploy。部署后抽查 https://brazil-procurement-hot.pages.dev/ 返回 200 且页头更新时间是当前时间。部署失败与推送分开记、分开算，连续两轮失败才汇报。

汇报：没事就别说话。只有出问题或需要用户拍板才向主聊汇报。观察记到 ~/memory/YYYY-MM-DD.md，绝不要改 MEMORY.md。

铁律：全程不用任何付费 API key；不编造每日新增条数；不宣称全量覆盖（人口 2 万以下市镇可延至 2027-04-01 才强制上 PNCP）。
