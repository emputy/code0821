import re
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup

from .base import FetchedItem
from .dates import from_soup, normalize

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

DEFAULT_NOISE = [
    r"managers-transactions", r"own-shares", r"share-buyback", r"shares-",
    r"financial-report", r"financial-information", r"media-library",
    r"notification-under-chapter", r"stock-exchange", r"transactions-",
    r"fi-fi", r"de-de", r"sv-se",
]


def _fetch_sitemap_entries(url: str, verify: bool = True, proxies=None) -> list[tuple[str, str]]:
    """抓取站点地图，返回 [(url, lastmod), ...]，lastmod 为空串表示没有。"""
    resp = requests.get(url, timeout=30, headers=HEADERS, verify=verify, proxies=proxies)
    resp.raise_for_status()
    text = resp.text
    entries = []
    for block in re.findall(r"<url>(.*?)</url>", text, re.S):
        loc = re.search(r"<loc>([^<]+)</loc>", block)
        last = re.search(r"<lastmod>([^<]+)</lastmod>", block)
        if loc:
            lastmod = normalize(last.group(1).strip()) if last else ""
            entries.append((loc.group(1), lastmod))
    if not entries:  # 无 <url> 块（索引或简单 sitemap），退化为直接找 loc
        entries = [(u, "") for u in re.findall(r"<loc>([^<]+)</loc>", text)]
    # 如果是 sitemap 索引（内含多个子 sitemap），并行取回合并（最多 20 个子图）
    sub = [u for u, _ in entries if u.lower().endswith((".xml", ".xml.gz"))]
    if sub and len(sub) > len(entries) * 0.5:
        def _get(u):
            try:
                return _fetch_sitemap_entries(u, verify=verify, proxies=proxies)
            except Exception:
                return []
        with ThreadPoolExecutor(max_workers=6) as ex:
            parts = list(ex.map(_get, sub[:20]))
        return [e for part in parts for e in part]
    return entries


def _guess_title(url: str) -> str:
    """从 URL 的 slug 猜测标题（作为抓不到页面时的后备）。"""
    slug = url.rstrip("/").split("/")[-1]
    slug = re.sub(r"-\d+$", "", slug)
    slug = re.sub(r"[-_]+", " ", slug)
    return slug.strip().capitalize() or url


def _enrich_titles(items: list, n: int, verify: bool = True, proxies=None) -> list:
    """并行抓取前 n 篇文章页面的真实标题和发布日期（单源内 6 并发）。"""
    if n <= 0:
        return items

    def _enrich(it):
        try:
            resp = requests.get(it.url, timeout=20, headers=HEADERS, verify=verify, proxies=proxies)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                t = soup.title
                if t and t.string:
                    title = " ".join(t.string.split())
                    if len(title) > 10:
                        it.title = title
                if not it.published:
                    d = from_soup(soup)
                    if d:
                        it.published = d
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(_enrich, items[:n]))
    return items


def fetch_sitemap(source) -> list[FetchedItem]:
    """从站点地图抓取最新文章 URL（适用于 JS 动态站）。"""
    opts = source.options or {}
    noise = opts.get("noise_patterns") or DEFAULT_NOISE
    contains = opts.get("url_contains", "")
    max_items = int(opts.get("max_items", 15))
    enrich = int(opts.get("enrich_titles", 5))
    verify = bool(opts.get("verify_ssl", True))
    proxies = {"http": opts["proxy"], "https": opts["proxy"]} if opts.get("proxy") else None

    try:
        entries = _fetch_sitemap_entries(source.url, verify=verify, proxies=proxies)
    except Exception as e:
        print(f"  [SITEMAP 错误] {source.name}: {e}")
        return []

    noise_re = re.compile("|".join(noise), re.I)
    exclude = opts.get("url_exclude", "")   # URL 含此片段则排除（可多个，用 | 分隔）
    article_urls = []
    seen = set()
    for u, lastmod in entries:
        if u in seen:
            continue
        seen.add(u)
        if noise_re.search(u):
            continue
        if contains and contains not in u:
            continue
        if exclude and any(x in u for x in exclude.split("|")):
            continue
        if u.rstrip("/").endswith(("/newsroom", "/newsroom/")):
            continue
        article_urls.append((u, lastmod))

    # 站点地图通常按新到旧排列，取前 max_items 条
    article_urls = article_urls[:max_items]

    items = []
    for u, lastmod in article_urls:
        items.append(FetchedItem(
            source_id=source.id,
            source_name=source.name,
            title=_guess_title(u),
            url=u,
            published=lastmod,
            country=source.country,
        ))
    items = _enrich_titles(items, enrich, verify=verify, proxies=proxies)
    return items
