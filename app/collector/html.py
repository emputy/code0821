from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import FetchedItem

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch_html(source) -> list[FetchedItem]:
    """抓取一个网页，提取其中的文章链接（标题 + URL）。"""
    try:
        resp = requests.get(source.url, timeout=20, headers=HEADERS)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [HTML 错误] {source.name}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    items = []
    seen = set()
    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text().split())
        if not text or len(text) < 15:
            continue
        href = a.get("href", "")
        if href.startswith(("javascript:", "#", "mailto:")):
            continue
        full = urljoin(source.url, href)
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
        if len(items) >= 50:
            break
    return items
