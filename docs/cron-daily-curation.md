# 定时任务：每日精选把关（本站实际版）

> 这是 brazil-procurement-hot 已在用的版本，不是模板占位稿。cron 任务
> `brazil-procurement-hot-daily-curation`（每天 07:42，timeout 3600 秒，
> 归属 goal「巴西政府采购 HOT 站点运营」）的 body 与本文一致。

---

巴西政府采购HOT 每日精选把关（循环持续跑、没用户命令不许停；绝不要自己停掉或删除这个任务）。

站点：https://staroltest.github.io/brazil-procurement-hot（英文版 /en/）；镜像 https://brazil-procurement-hot.pages.dev；仓库 Staroltest/brazil-procurement-hot（main）；本地工作目录 ~/workspace/brazil-procurement-hot。更新主力是每半小时一轮的 brazil-procurement-hot-half-hourly-update（抓 PNCP、原创改写、推送、部署全包，北京时间 06:00 那轮出日报）。你的工作是每天一次质量把关，不是再抓一遍。推送走 `python3 ~/workspace/custom-connectors/custom.github-token/bin/push_snapshot.py --repo Staroltest/brazil-procurement-hot --dir ~/workspace/brazil-procurement-hot --message "<信息>"`，部署走 `python3 ~/workspace/custom-connectors/custom.cloudflare/bin/cf.py deploy --project brazil-procurement-hot --dir ~/workspace/brazil-procurement-hot`；绝不启用 GitHub Actions，绝不推 .github/workflows/*。

每轮做：

1. 看精选质量：读线上 data/hot.json（精选 10、热点 20）与 data/daily.json（当日日报），对照 config.json 的打分权重与精选门槛。受众是盯巴西政府采购机会的中小企业，分类共八个：医疗卫生、教育、工程与基建、交通与车辆、食品与餐饮、信息技术、综合服务、物资与设备。检查：精选里有没有跑题或低价值条目（金额极小、与采购无关）；分类分布是否严重失衡（如医疗卫生长期占一半以上，多半是分类关键词需要修）；标题/简介有没有葡语原文残留、金额格式错误、截止时间错误。英文版同查：en/data/hot.json 与 en/data/daily.json 的英文标题/简介是否对味，en/ 全树是否零中文。
2. 查 PNCP 信源健康：实测 proposta 接口（窗口今天起 14 天）与 publicacao 接口（方式 6，最近 3 天）各一次，看返回码、totalRegistros 量级与响应耗时；对照 data/store.json 里最近 3 天的 published 分布，哪类招标方式连续多天 0 条新发布要记下来。已知：proposta 单页可慢到 40 秒属正常；publicacao 必须带 codigoModalidadeContratacao 参数。
3. 找缺口（本站的「找新源」= 找 PNCP 覆盖缺口，不是加 RSS）：对照八个分类看哪类长期没新条目——先分清是该类本身发布少，还是 tools/pncp_fetch.py 的分类关键词漏词；是漏词就补 config.json 的 categories keywords（葡/中/英三组都补），改完本地跑一轮 pncp_fetch + generate 验证分布有改善再推。切片参数（页数、方式清单、窗口天数）明显不够用时也可以调，但要在日志里写清理由。没有缺口就如实记一笔，绝不硬凑改动。
4. 动手修时：在工作目录改 config.json / tools/pncp_fetch.py，本地跑 `python3 tools/pncp_fetch.py && python3 tools/generate.py --daily` 验证（selected/hot 非空、geo-audit failed=0、英文树零中文），再 push_snapshot 推送、cf.py deploy 部署。若动了 data/zh_draft.json（一般不动），必须字段级合并：按链接、按字段取并集，同字段冲突保留本地，en_title/en_oneliner 永不丢。推送失败就记下来下一轮再推，不要强行重试。
5. 只在有事时向用户汇报（主聊天）：改了权重/关键词/切片参数（改了什么、为什么）、PNCP 接口异常、精选质量明显变差、或需要用户拍板。什么都没变就保持沉默，不要发「一切正常」的消息。不要改 MEMORY.md；观察记到 ~/memory/YYYY-MM-DD.md。

版权铁律同样适用：公开内容只有本站原创标题 + 一句话简介 + PNCP 官方链接；objetoCompra 原文永不公开；不编造每日新增条数；不宣称全量覆盖（人口 2 万以下市镇可延至 2027-04-01）。
