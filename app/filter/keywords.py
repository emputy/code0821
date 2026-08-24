# 概念词表：用于按分类精确过滤（电力行业无线专网 / 频谱动态）

# 1. 电力行业概念词
POWER_TERMS = [
    "电力", "配电", "智能电网", "电网", "变电站", "用电", "微电网", "新能源",
    "公用事业", "电力公司", "电力物联网", "electric", "utility", "utilities",
    "grid", "smart grid", "power sector", "energy sector", "electricity",
    # 本地语言
    "الطاقة", "الكهرباء", "énergie", "électricité", "électrique",
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
    "الاتصالات", "تكنولوجيا المعلومات", "télécommunications", "telecomunicações",
    "telekomunikasi", "komunikasi", "การสื่อสาร", "telekomunikacja",
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
    return any(t in text for t in terms)


def load_keywords(config_path: str) -> list[str]:
    import json
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("keywords", [])


def filter_items(items, entity_re=None, source_categories=None):
    """按来源类别做相关性精确过滤（电力行业无线专网 / 频谱动态）：

    - 联盟：命中「无线专网」或「频谱」概念 → 保留（450MHz 生态天然相关）
    - 友商：命中「无线专网」或「频谱」概念 → 保留（涉无线专网都收）
    - 重点国家：命中「频谱」概念 → 保留；或「电力 + 无线专网」双概念 → 保留
    - 任何来源：命中跟踪客户/国家（实体）→ 保留
    """
    source_categories = source_categories or {}
    kept = []
    for it in items:
        text = f"{it.title} {it.summary}".lower()
        if entity_re and entity_re.search(text):
            kept.append(it)
            continue
        cat = source_categories.get(it.source_id, "")
        if cat == "alliance":
            if _has_any(text, PRIVATE_WIRELESS_TERMS) or _has_any(text, SPECTRUM_TERMS):
                kept.append(it)
        elif cat == "competitor":
            if _has_any(text, PRIVATE_WIRELESS_TERMS) or _has_any(text, SPECTRUM_TERMS):
                kept.append(it)
        else:  # country / 默认
            if _has_any(text, SPECTRUM_TERMS) or (
                _has_any(text, POWER_TERMS) and _has_any(text, PRIVATE_WIRELESS_TERMS)
            ) or (
                _has_any(text, POWER_TERMS) and _has_any(text, COMMUNICATION_TERMS)
            ):
                kept.append(it)
    return kept
