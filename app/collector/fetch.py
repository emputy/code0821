import json
from concurrent.futures import ThreadPoolExecutor

from .base import Source
from .html import fetch_html
from .rss import fetch_rss
from .sitemap import fetch_sitemap


def load_sources(config_path: str) -> list[Source]:
    """从 sources.json 读取启用的数据源。

    若顶层配置了 "proxy"（如 127.0.0.1:7890），自动注入到每个数据源的
    options.proxy（标记 "direct": true 的源除外，它们保持直连）。
    """
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    proxy = data.get("proxy", "")
    sources = []
    for s in data.get("sources", []):
        if not s.get("enabled", True):
            continue
        opts = dict(s.get("options") or {})
        if proxy and not opts.get("direct"):
            opts.setdefault("proxy", proxy)
        s = dict(s)
        s["options"] = opts
        sources.append(Source(**s))
    return sources


def _fetch_one(src):
    """抓取单个数据源，返回 (源, 条目列表)。"""
    if src.type == "rss":
        items = fetch_rss(src)
    elif src.type == "html":
        items = fetch_html(src)
    elif src.type == "sitemap":
        items = fetch_sitemap(src)
    else:
        print(f"  [skip] unknown type: {src.type}")
        items = []
    return src, items


def fetch_all(config_path: str, on_progress=None, max_workers: int = 6) -> list:
    """并发遍历所有数据源并采集。

    on_progress(done, total)：每完成一个源回调一次，用于界面显示进度。
    并发数默认 6，兼顾速度与对方网站反爬压力。
    代理配置见 sources.json 顶层 "proxy"（load_sources 已按源注入）。
    """
    sources = load_sources(config_path)
    total = len(sources)
    results = [None] * total

    def _worker(i):
        try:
            results[i] = _fetch_one(sources[i])
        except Exception as e:
            print(f"  [error] {sources[i].id}: {e}")
            results[i] = (sources[i], [])
        if on_progress:
            done = sum(1 for r in results if r is not None)
            on_progress(done, total)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for i in range(total):
            ex.submit(_worker, i)

    all_items = []
    for src, items in results:
        # 源名可能含非 ASCII（如 ÚREK），用 id 打印避免编码崩溃
        print(f"[{src.id}] got {len(items)} items")
        all_items.extend(items)
    return all_items
