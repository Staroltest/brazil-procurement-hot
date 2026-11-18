#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PNCP 抓取器：把巴西政府采购公开数据写进本站本地库。

数据来源（公开、免注册、免 key，2026-11-18 核查）：
  PNCP 查询 API  https://pncp.gov.br/api/consulta/v1/contratacoes/proposta
  参数 dataInicial / dataFinal 指「提案截止日期」窗口（YYYYMMDD），
  pagina 从 1 起，tamanhoPagina >= 10。
  制度依据：Lei 14.133/2021 第 174 条（PNCP 集中公示）。
  覆盖 caveat：2 万人口以下小市镇可延至 2027-04-01 才强制上 PNCP，
  本站数据不是巴西政府采购的全量。

版权铁律（本站比模板更严，用户明确要求）：
  - PNCP 的 objetoCompra（采购对象原文）只在本机 data/store.json 里
    作分类与核对用，store.json 永不推送、永不公开。
  - 对外标题与一句话简介全部由本脚本按「事实字段模板」原创生成：
    城市/州 + 采购类别 + 采购方式 + 截止时间 + 估算金额。
    不复制 objetoCompra 的任何句子，不使用源站标题（PNCP 本就没有
    独立标题字段），不使用任何图片。
  - 每条都带 PNCP 官方详情页链接，读者以官方公告为准。
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
API = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"
UA = {"User-Agent": "brazil-procurement-hot/1.0 (+https://github.com/Staroltest/brazil-procurement-hot)"}
BRT = timezone(timedelta(hours=-3))  # America/Sao_Paulo 现行无夏令时

PAGE_SIZE = 20
MAX_PAGES = 6           # 每轮最多 120 条，按截止日临近窗口取（API 单页约 40 秒，页数要克制）
WINDOW_DAYS = 14        # 提案截止日在 [今天, 今天+14天] 的招标
MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def norm_link(link):
    link = (link or "").strip().split("#")[0]
    if "?" in link:
        base, qs = link.split("?", 1)
        kept = [p for p in qs.split("&") if p and not p.lower().startswith("utm_")]
        link = base + ("?" + "&".join(kept) if kept else "")
    return link.rstrip("/")


def fetch_json(url, timeout=75, attempts=2):
    """用 curl 拉 PNCP：urllib 对这个慢接口会出现读挂死，curl 的 -m 是硬超时。
    每页打印进度（flush），方便定时任务看日志判断卡在哪。"""
    import subprocess
    import tempfile
    last = None
    for i in range(attempts):
        try:
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
                tmp = tf.name
            p = subprocess.run(
                ["curl", "-s", "-o", tmp, "-w", "%{http_code}",
                 "-m", str(timeout), "-A", UA["User-Agent"], url],
                capture_output=True, text=True, timeout=timeout + 15)
            code = (p.stdout or "").strip()
            if code != "200":
                raise RuntimeError(f"HTTP {code or p.stderr[:100]}")
            with open(tmp, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  fetch attempt {i + 1} failed: {e}", file=sys.stderr, flush=True)
            if i < attempts - 1:
                time.sleep(4)
    raise last


# ---------------------------------------------------------------- 分类
# 只读 objetoCompra 做关键词分类（内部处理），输出只有类别词，不引原文。
CAT_RULES = [
    ("health", ["saúde", "saude", "hospital", "medicamento", "farmac", "vacina",
                "odontol", "médic", "medic", "enfermagem", "eletrocardiógrafo",
                "ambulat", "clínic", "clinic", "laborator", "raio-x", "seringa",
                "luva cirúrgica", "ubs", "upa ", "pronto socorro", "samu"]),
    ("education", ["educação", "educacao", "escola", "ensino", "universidade",
                   "creche", "didátic", "didatic", "pedagóg", "pedagog",
                   "biblioteca", "aluno", "docente", "merenda escolar é",
                   "transporte escolar", "material escolar", "kit escolar"]),
    ("works", ["obra", "construção", "construcao", "pavimentação", "pavimentacao",
               "reforma", "engenharia", "saneamento", "drenagem", "ponte",
               "estrada", "asfalto", "infraestrutura", "edificação", "edificacao",
               "manutenção predial", "manutencao predial", "rede de esgoto",
               "abastecimento de água", "iluminação pública", "iluminacao publica"]),
    ("transport", ["veículo", "veiculo", "caminhão", "caminhao", "ônibus", "onibus",
                   "transporte", "frota", "retroescavadeira", "trator", "máquina",
                   "maquina", "combustível", "combustivel", "pneu", "locação de veículos",
                   "locacao de veiculos", "transporte escolar já", "motoniveladora"]),
    ("food", ["aliment", "merenda", "gêneros alimentícios", "generos alimenticios",
              "refeição", "refeicao", "restaurante", "cozinha", "hortifruti",
              "carne", "leite", "cesta básica", "cesta basica", "lanche"]),
    ("tech", ["informática", "informatica", "tecnologia da informação", "software",
              "computador", "notebook", "internet", "sistema de informação",
              "sistema de informacao", "licença de uso", "licenca de uso",
              "datacenter", "impressora", "toner", "rede lógica", "câmera de monitoramento",
              "camera de monitoramento", "circuito fechado"]),
    ("supplies", ["material de expediente", "expediente", "papelaria", "mobiliário",
                  "mobiliario", "equipamento", "material de consumo", "material permanente",
                  "uniforme", "material de limpeza", "higiene", "material de construção é",
                  "aquisição de materiais", "aquisicao de materiais", "gás de cozinha",
                  "gas de cozinha", "material esportivo", "material gráfico", "material grafico"]),
    ("services", ["serviço", "servico", "limpeza", "vigilância", "vigilancia",
                  "segurança", "seguranca", "consultoria", "assessoria", "locação",
                  "locacao", "terceiriz", "manutenção", "manutencao", "coleta de lixo",
                  "artista", "cultura", "esporte", "evento", "oficina", "capacitação",
                  "capacitacao", "treinamento", "publicidade", "propaganda"]),
]
CAT_ZH = {  # key -> (标题用类别词, 简介用类别短语)
    "health": ("医疗卫生采购", "医疗卫生方面的物资或服务"),
    "education": ("教育采购", "教育方面的物资或服务"),
    "works": ("工程与基建采购", "工程、维修或基础设施方面的服务或物资"),
    "transport": ("交通与车辆采购", "车辆、运输或相关设备与服务"),
    "food": ("食品与餐饮采购", "食品、餐饮或相关物资"),
    "tech": ("信息技术采购", "信息技术设备、系统或服务"),
    "services": ("综合服务采购", "专业服务或外包服务"),
    "supplies": ("物资与设备采购", "物资、设备或耗材"),
}
CAT_EN = {
    "health": ("Health & medical procurement", "healthcare goods or services"),
    "education": ("Education procurement", "education-related goods or services"),
    "works": ("Works & infrastructure procurement", "works, repairs or infrastructure services"),
    "transport": ("Transport & vehicles procurement", "vehicles, transport or related equipment and services"),
    "food": ("Food & catering procurement", "food, catering or related supplies"),
    "tech": ("IT procurement", "IT equipment, systems or services"),
    "services": ("Services procurement", "professional or outsourced services"),
    "supplies": ("Supplies & equipment procurement", "supplies, equipment or consumables"),
}


def classify(objeto):
    text = (objeto or "").lower()
    for key, kws in CAT_RULES:
        for kw in kws:
            if kw in text:
                return key
    return "supplies"


# ---------------------------------------------------------------- 方式
MODALITY_RULES = [
    ("pregao-eletronico", "Pregão - Eletrônico", "电子竞价", "electronic pregão (reverse auction)"),
    ("pregao-presencial", "Pregão - Presencial", "现场竞价", "in-person pregão (reverse auction)"),
    ("concorrencia-eletronica", "Concorrência - Eletrônica", "电子竞争性招标", "electronic competitive bidding (concorrência)"),
    ("concorrencia-presencial", "Concorrência - Presencial", "现场竞争性招标", "in-person competitive bidding (concorrência)"),
    ("credenciamento", "Credenciamento", "资格登记", "accreditation (credenciamento)"),
    ("dispensa", "Dispensa", "免招标直接采购", "direct award (dispensa)"),
    ("inexigibilidade", "Inexigibilidade", "不经招标直接采购", "direct award (inexigibilidade)"),
    ("concurso", "Concurso", "公开竞赛征集", "public contest (concurso)"),
    ("dialogo", "Diálogo Competitivo", "竞争性对话", "competitive dialogue"),
    ("leilao", "Leilão", "拍卖", "auction (leilão)"),
    ("pre-qualificacao", "Pré-qualificação", "资格预审", "pre-qualification"),
    ("manifestacao", "Manifestação de Interesse", "意向征集", "expression of interest"),
]


def modality(rec):
    name = (rec.get("modalidadeNome") or "").strip()
    for _key, pt, zh, en in MODALITY_RULES:
        if name.lower() == pt.lower():
            return zh, en
    low = name.lower()
    for _key, pt, zh, en in MODALITY_RULES:
        if pt.lower().split(" - ")[0].split()[0] in low and low:
            return zh, en
    return "政府采购", "government procurement procedure"


# ---------------------------------------------------------------- 格式化
def parse_dt(text):
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=BRT)


def fmt_money(v):
    """国际通用格式 R$ 190,644 / R$ 14,901.65，中英文都不会误读数量级。"""
    if not v:
        return ""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return ""
    if v <= 0:
        return ""
    if v == int(v):
        return "R$ " + f"{int(v):,}"
    return "R$ " + f"{v:,.2f}"


def deadline_parts(rec):
    dt = parse_dt(rec.get("dataEncerramentoProposta"))
    if not dt:
        return "", ""
    hm = dt.strftime("%H:%M")
    zh = f"{dt.month}月{dt.day}日" + (f" {hm}" if hm != "00:00" else "")
    en = f"{MONTHS_EN[dt.month - 1]} {dt.day}" + (f", {hm}" if hm != "00:00" else "")
    return zh, en


def build_texts(rec):
    """按事实字段原创生成标题与一句话简介（中英）。绝不引用 objeto 原文。"""
    uni = rec.get("unidadeOrgao") or {}
    city = (uni.get("municipioNome") or "").strip()
    uf = (uni.get("ufSigla") or "").strip()
    cat = classify(rec.get("objetoCompra"))
    mod_zh, mod_en = modality(rec)
    dl_zh, dl_en = deadline_parts(rec)
    money = fmt_money(rec.get("valorTotalEstimado"))
    num = (rec.get("numeroCompra") or "").strip()

    place_zh = f"{city}（{uf}）" if city and uf else (city or "巴西")
    place_en = f"{city} ({uf})" if city and uf else (city or "Brazil")
    cat_title_zh, cat_phrase_zh = CAT_ZH[cat]
    cat_title_en, cat_phrase_en = CAT_EN[cat]

    zh_title = f"{place_zh}{cat_title_zh} · {mod_zh}"
    en_title = f"{place_en} {cat_title_en} · {mod_en}"
    if dl_zh:
        zh_title += f" · {dl_zh.split(' ')[0]}截止"
        en_title += f" · closes {dl_en.split(',')[0]}"
    if num:
        zh_title += f" #{num}"
        en_title += f" #{num}"

    money_zh = f"，估算金额约 {money}" if money else ""
    money_en = f", with an estimated value of about {money}" if money else ""
    dl_clause_zh = f"，提案截止时间为 {dl_zh}（巴西利亚时间）" if dl_zh else ""
    dl_clause_en = f"; proposals close {dl_en} (Brasília time)" if dl_en else ""
    zh_one = (f"{place_zh}一公共机构以{mod_zh}方式采购{cat_phrase_zh}"
              f"{money_zh}{dl_clause_zh}，有意参与的中小企业请尽早到 PNCP 官方公告页核对资格与文件要求。")
    en_one = (f"A public buyer in {place_en} is procuring {cat_phrase_en} through "
              f"{mod_en}{money_en}{dl_clause_en}, so interested SMEs should check the "
              f"eligibility and document requirements on the official PNCP notice page early.")
    return cat, zh_title, en_title, zh_one, en_one


def record_to_entries(rec, now):
    cnpj = ((rec.get("orgaoEntidade") or {}).get("cnpj") or "").strip()
    ano = rec.get("anoCompra")
    seq = rec.get("sequencialCompra")
    if not (cnpj and ano and seq):
        return None
    link = norm_link(f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}")
    cat, zh_title, en_title, zh_one, en_one = build_texts(rec)
    pub = (parse_dt(rec.get("dataAtualizacaoGlobal"))
           or parse_dt(rec.get("dataPublicacaoPncp"))
           or parse_dt(rec.get("dataInclusao")) or now)
    entry = {
        "id": hashlib.sha1(link.encode()).hexdigest(),
        "title": en_title,  # 原始 title 字段放本站原创英文标题，不放源站任何文字
        "link": link,
        "source": "PNCP",
        "source_id": "pncp",
        "published": pub.astimezone(timezone.utc).isoformat(),
        "summary": rec.get("objetoCompra") or "",  # 仅本地 store 用，不公开
        "fetched_at": now.isoformat(),
        "category": cat,
    }
    draft = {"zh_title": zh_title, "zh_oneliner": zh_one,
             "en_title": en_title, "en_oneliner": en_one}
    return entry, draft


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def main():
    os.makedirs(DATA, exist_ok=True)
    now = datetime.now(timezone.utc)
    today_brt = now.astimezone(BRT).date()
    d_ini = today_brt.strftime("%Y%m%d")
    d_fim = (today_brt + timedelta(days=WINDOW_DAYS)).strftime("%Y%m%d")

    store_path = os.path.join(DATA, "store.json")
    store = load_json(store_path, {"items": []})
    by_id = {it["id"]: it for it in store.get("items", [])}
    draft_path = os.path.join(DATA, "zh_draft.json")
    draft = load_json(draft_path, {})

    counters = {"got": 0, "added": 0}

    def process(rows):
        for rec in rows:
            counters["got"] += 1
            built = record_to_entries(rec, now)
            if not built:
                continue
            entry, texts = built
            if entry["id"] not in by_id:
                by_id[entry["id"]] = entry
                counters["added"] += 1
            # 草稿字段级合并：已存在的同字段不覆盖（本地优先，铁律 2）
            key = norm_link(entry["link"])
            cur = draft.get(key, {})
            for k, v in texts.items():
                cur.setdefault(k, v)
            draft[key] = cur

    # 切片 A：即将截止（proposta，截止日窗口，按截止时间升序）
    total_pages = 1
    page = 1
    while page <= min(total_pages, MAX_PAGES):
        qs = urllib.parse.urlencode({
            "dataInicial": d_ini, "dataFinal": d_fim,
            "pagina": page, "tamanhoPagina": PAGE_SIZE,
        })
        try:
            resp = fetch_json(f"{API}?{qs}")
        except Exception as e:  # noqa: BLE001
            print(f"pncp page {page} failed: {e}", file=sys.stderr)
            break
        total_pages = resp.get("totalPaginas") or page
        print(f"pncp page {page}/{min(total_pages, MAX_PAGES)} ok", flush=True)
        rows = resp.get("data") or []
        if not rows:
            break
        process(rows)
        page += 1

    # 切片 B：刚刚发布（publicacao，按招标方式逐个查最近 3 天，取最后一页=最新一批）
    # publicacao 必须带 codigoModalidadeContratacao；结果按发布日升序，末页最新。
    pub_ini = (today_brt - timedelta(days=2)).strftime("%Y%m%d")
    for mod in (6, 4, 8, 9, 12, 7, 5, 14):
        base = ("https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao?"
                + urllib.parse.urlencode({
                    "dataInicial": pub_ini, "dataFinal": d_ini,
                    "codigoModalidadeContratacao": mod,
                    "tamanhoPagina": PAGE_SIZE}))
        try:
            first = fetch_json(base + "&pagina=1")
            tp = first.get("totalPaginas") or 1
            resp = first if tp == 1 else fetch_json(base + f"&pagina={tp}")
            rows = resp.get("data") or []
            process(rows)
            print(f"pncp pub mod {mod}: {len(rows)} newest (of "
                  f"{first.get('totalRegistros')} in 3d)", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"pncp pub mod {mod} failed: {e}", file=sys.stderr)

    got, added = counters["got"], counters["added"]

    store["updated_at"] = now.isoformat()
    store["items"] = list(by_id.values())
    save_json(store_path, store)
    save_json(draft_path, draft)
    print(f"pncp: fetched {got} records in window {d_ini}-{d_fim}, "
          f"{added} new, store now {len(by_id)}, draft {len(draft)}")
    if got == 0:
        sys.exit(3)  # 一条都没拉到：让调用方停下来汇报


if __name__ == "__main__":
    main()
