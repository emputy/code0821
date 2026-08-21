import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import FetchedItem

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

# 常见的导航/非文章链接特征，抓取时排除
NAV_HINTS = re.compile(
    r"(/about-us|/contact|/careers|/investor|/login|/register|/terms|/privacy|"
    r"/cookie|/search|/sitemap|/help|/support|/download|/newsletter|/subscribe|"
    r"/member|mailto:|javascript:|tel:|#)",
    re.I,
)


def fetch_html(source) -> list[FetchedItem]:
    """抓取网页文章链接，支持按 URL 特征精准过滤。"""
    opts = source.options or {}
    contains = opts.get("url_contains", "")       # URL 必须包含
    ends_with = opts.get("url_ends_with", "")     # URL 必须以...结尾
    selector = opts.get("link_selector", "a")     # 链接 CSS 选择器
    max_items = int(opts.get("max_items", 30))

    try:
        resp = requests.get(source.url, timeout=20, headers=HEADERS)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [HTML 错误] {source.name}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    items = []
    seen = set()
    for a in soup.select(selector):
        if not a.get("href"):
            continue
        text = " ".join(a.get_text().split())
        href = a["href"].strip()
        low = href.lower()
        if len(text) < 15:
            continue
        if NAV_HINTS.search(low):
            continue
        if ends_with and not low.endswith(ends_with):
            continue
        full = urljoin(source.url, href)
        if contains and contains not in full:
            continue
        if full in seen:
            continue
        seen.add(full)
        items.append(FetchedItem(
            source_id=source.id,
            source_name=source.name,
            title=text,
            url=full,
            country=source.country,
        ))
        if len(items) >= max_items:
            break
    return items
