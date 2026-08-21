import json


def load_keywords(config_path: str) -> list[str]:
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("keywords", [])


def filter_items(items, keywords: list[str]):
    """保留标题或摘要命中任一关键词的内容（不区分大小写）。"""
    if not keywords:
        return items
    kws = [k.lower() for k in keywords]
    kept = []
    for it in items:
        text = f"{it.title} {it.summary}".lower()
        if any(k in text for k in kws):
            kept.append(it)
    return kept
