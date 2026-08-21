import json

from .base import Source
from .html import fetch_html
from .rss import fetch_rss


def load_sources(config_path: str) -> list[Source]:
    """从 sources.json 读取启用的数据源。"""
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    sources = []
    for s in data.get("sources", []):
        if not s.get("enabled", True):
            continue
        sources.append(Source(**s))
    return sources


def fetch_all(config_path: str) -> list:
    """遍历所有数据源并采集。"""
    sources = load_sources(config_path)
    all_items = []
    for src in sources:
        print(f"抓取 {src.name} ...")
        if src.type == "rss":
            items = fetch_rss(src)
        elif src.type == "html":
            items = fetch_html(src)
        else:
            print(f"  [跳过] 未知类型: {src.type}")
            items = []
        print(f"  得到 {len(items)} 条")
        all_items.extend(items)
    return all_items
