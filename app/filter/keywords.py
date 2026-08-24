import json


def load_keywords(config_path: str) -> list[str]:
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("keywords", [])


def filter_items(items, keywords: list[str], entity_re=None, source_keywords=None):
    """保留命中领域关键词、来源级扩展关键词或跟踪实体的内容。

    source_keywords: {source_id: [额外关键词]}，用于按来源放宽过滤（如友商）。
    """
    kws = [k.lower() for k in keywords]
    source_keywords = source_keywords or {}
    extra_map = {sid: [k.lower() for k in extras] for sid, extras in source_keywords.items()}
    kept = []
    for it in items:
        text = f"{it.title} {it.summary}".lower()
        if any(k in text for k in kws):
            kept.append(it)
            continue
        extras = extra_map.get(it.source_id, [])
        if extras and any(k in text for k in extras):
            kept.append(it)
            continue
        if entity_re and entity_re.search(text):
            kept.append(it)
    return kept
