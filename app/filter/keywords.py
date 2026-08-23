import json


def load_keywords(config_path: str) -> list[str]:
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("keywords", [])


def filter_items(items, keywords: list[str], entity_re=None):
    """保留命中领域关键词或跟踪实体（重点客户/国家）的内容。"""
    kws = [k.lower() for k in keywords]
    kept = []
    for it in items:
        text = f"{it.title} {it.summary}".lower()
        if any(k in text for k in kws):
            kept.append(it)
            continue
        if entity_re and entity_re.search(text):
            kept.append(it)
    return kept
