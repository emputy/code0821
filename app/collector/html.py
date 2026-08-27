import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import FetchedItem
from .dates import from_soup, from_url

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

_DATE_RE = re.compile(r"(20\d{2})[-/.]?(\d{1,2})[-/.]?(\d{1,2})")
_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
_MONTH_RE = re.compile(
    r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(20\d{2})", re.I
)


def _extract_page_date(soup, url: str = "") -> str:
    """从文章页提取发布时间：meta / time / JSON-LD，回退到 URL 里的日期。"""
    d = from_soup(soup)
    if d:
        return d
    return from_url(url)


def _fill_article_dates(items) -> list:
    """并行打开没有发布日期的文章页，提取发布时间（单源内 6 并发）。"""
    def _fill(it):
        if it.published:
            return
        try:
            d = from_url(it.url)
            if not d:
                resp = requests.get(it.url, timeout=15, headers=HEADERS)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml")
                    d = _extract_page_date(soup, it.url)
            if d:
                it.published = d
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(_fill, items))
    return items


def _find_date(text: str) -> str:
    """从文本里找日期，返回 YYYY-MM-DD；找不到返回空串。"""
    if not text:
        return ""
    m = _DATE_RE.search(text)
    if m:
        try:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        except Exception:
            return ""
    m = _MONTH_RE.search(text)
    if m:
        mon = _MONTHS.get(m.group(2).lower()[:3])
        if mon:
            return f"{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}"
    return ""

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
    min_link_text = int(opts.get("min_link_text", 15))  # 链接文本最短长度
    allow_parent_title = bool(opts.get("allow_parent_title", False))  # 文本短时回退父容器标题

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
        if len(text) < min_link_text:
            if not allow_parent_title:
                continue
            # 链接文本太短（如 "read more"）：向上找父容器里的 h1-h4 作为标题
            node = a
            found = False
            for _ in range(4):
                node = node.parent
                if node is None:
                    break
                h = node.find(["h1", "h2", "h3", "h4"])
                if h:
                    tt = " ".join(h.get_text().split())
                    if len(tt) >= min_link_text:
                        text = tt
                        found = True
                        break
            if not found:
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
        context = a.parent.get_text()[:200] if a.parent else ""
        published = _find_date(context) or _find_date(text) or from_url(full)
        items.append(FetchedItem(
            source_id=source.id,
            source_name=source.name,
            title=text,
            url=full,
            published=published,
            country=source.country,
        ))
        if len(items) >= max_items:
            break
    return _fill_article_dates(items)
