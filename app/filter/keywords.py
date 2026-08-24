import json

# 电力行业概念词（与无线/频谱概念叠加判断相关性）
POWER_TERMS = [
    "电力", "配电", "智能电网", "电网", "变电站", "用电", "微电网", "新能源",
    "公用事业", "电力公司", "电力物联网", "electric", "utility", "utilities",
    "grid", "smart grid", "power sector", "energy sector", "electricity",
]

# 无线专网 / 频谱概念词
WIRELESS_TERMS = [
    "450MHz", "450 MHz", "LTE450", "450M", "专网", "无线专网", "专用网络",
    "private network", "private networks", "private lte", "private 5g",
    "private wireless", "频谱", "spectrum", "frequency", "radio spectrum",
    "wireless", "lte", "5g",
]


def _has_any(text: str, terms) -> bool:
    return any(t in text for t in terms)


def load_keywords(config_path: str) -> list[str]:
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("keywords", [])


def filter_items(items, entity_re=None, source_categories=None):
    """按来源类别做相关性精确过滤：
    - 联盟：命中无线/频谱概念即保留（450MHz 生态天然相关）
    - 友商：命中无线/频谱概念即保留（涉无线专网都收）
    - 重点国家：须同时命中「电力概念」与「无线/频谱概念」（精确到频谱信息）
    - 任何来源：命中跟踪客户/国家（实体）即保留
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
            if _has_any(text, WIRELESS_TERMS):
                kept.append(it)
        elif cat == "competitor":
            if _has_any(text, WIRELESS_TERMS):
                kept.append(it)
        else:  # country / 默认：电力 + 无线/频谱 双概念
            if _has_any(text, POWER_TERMS) and _has_any(text, WIRELESS_TERMS):
                kept.append(it)
    return kept
