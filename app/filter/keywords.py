# 概念词表：用于按分类实时过滤（电力行业无线专网 / 频谱动态）

# 1. 电力行业概念词
POWER_TERMS = [
    "电力", "配电", "智能电网", "电网", "变电站", "用电", "微电网", "新能源",
    "公用事业", "电力公司", "电力物联网", "electric", "utility", "utilities",
    "grid", "smart grid", "power sector", "energy sector", "electricity",
    # 本地语言
    "الطاقة", "الكهرباء", "طاقة", "كهرباء", "énergie", "électricité", "électrique",
    "energia", "elétrica", "eletricidade", "tenaga", "elektrik",
    "energi", "listrik", "พลังงาน", "ไฟฟ้า",
    "energie", "electricite", "frequencias", "eletrica",
]

# 2. 无线专网概念词（私网专属，不含泛公网词）
PRIVATE_WIRELESS_TERMS = [
    "450MHz", "450 MHz", "LTE450", "450M",
    "专网", "无线专网", "专用网络", "电力无线专网",
    "private network", "private networks", "private lte", "private 5g",
    "private wireless", "enterprise private", "dedicated network",
    "industrial network", "industrial wireless", "critical communications",
    "mission critical", "utility network",
    # 本地语言
    "الشبكات الخاصة", "لاسلكي خاص", "réseau privé", "redes privadas",
    "redes privadas", "jaringan privat", "เครือข่ายเอกชน",
]

# 2.5 通信/网络概念词（与电力词组合，捕捉"电力通信/网络"类信息）
COMMUNICATION_TERMS = [
    "通信", "通讯", "网络", "无线通信", "宽带", "专网",
    "communications", "communication", "network", "networks", "connectivity",
    "broadband", "wireless", "telecom", "telecommunications",
    # 本地语言
    "الاتصالات", "اتصالات", "شبكة", "شبكات", "لاسلكي", "تكنولوجيا المعلومات",
    "télécommunications", "telecomunicações", "telekomunikasi", "komunikasi",
    "การสื่อสาร", "telekomunikacja",
]

# 3. 频谱概念词
SPECTRUM_TERMS = [
    "频谱", "spectrum", "frequency", "frequencies", "radio frequency",
    "frequency band", "MHz", "450MHz", "450 MHz",
    "auction", "leilão", "leilao", "spectral",
    # 本地语言
    "الطيف", "التردد", "الترددات", "تردد", "fréquences", "frequences",
    "spectre", "espectro", "frequências", "frequencias", "spektrum",
    "frekuensi", "คลื่นความถี่", "สเปกตรัม", "ประมูล", "المزاد",
]


def _has_any(text: str, terms) -> bool:
    """text 已小写；对词也统一小写再匹配，避免 450MHz/MHz 等大写词失效。"""
    return any(t.lower() in text for t in terms)


def load_keywords(config_path: str) -> list[str]:
    import json
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("keywords", [])


def _is_relevant(text: str, source_id: str, entity_re=None, source_categories=None,
                 extra_terms=None) -> bool:
    """判断一条内容是否与「电力无线专网 / 频谱动态」相关（实时过滤核心）。

    extra_terms：sources.json 顶层 keywords（用户可编辑的补充词表），命中任一即算相关。
    """
    if entity_re and entity_re.search(text):
        return True
    if extra_terms and _has_any(text, extra_terms):
        return True
    cat = (source_categories or {}).get(source_id, "")
    if cat == "alliance":
        return _has_any(text, PRIVATE_WIRELESS_TERMS) or _has_any(text, SPECTRUM_TERMS)
    if cat == "competitor":
        return _has_any(text, PRIVATE_WIRELESS_TERMS) or _has_any(text, SPECTRUM_TERMS)
    # country / other（重点国家与全球其他源）收紧规则：
    # 频谱词单独出现不再算相关（监管机构新闻几乎都含频谱词，会导致大量无关内容）。
    # 必须：命中强专网词（450MHz/private network/专用网络等），或 频谱词+电力词 同时出现。
    return (
        _has_any(text, PRIVATE_WIRELESS_TERMS)
        or (_has_any(text, SPECTRUM_TERMS) and _has_any(text, POWER_TERMS))
    )


def filter_items(items, entity_re=None, source_categories=None, extra_terms=None):
    """过滤 FetchedItem 列表（兼容旧调用）。"""
    return [it for it in items
            if _is_relevant(f"{it.title} {it.summary}".lower(), it.source_id,
                            entity_re, source_categories, extra_terms)]


def filter_db_rows(rows, entity_re=None, source_categories=None, extra_terms=None):
    """过滤数据库行。

    rows 每行列序：(id, source_id, source_name, title, url, published, summary, country, fetched_at)
    """
    return [r for r in rows
            if _is_relevant(f"{r[3]} {r[6]}".lower(), r[1],
                            entity_re, source_categories, extra_terms)]
