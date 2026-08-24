import re

import requests
from bs4 import BeautifulSoup

from .base import FetchedItem

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

DEFAULT_NOISE = [
    r"managers-transactions", r"own-shares", r"share-buyback", r"shares-",
    r"financial-report", r"financial-information", r"media-library",
    r"notification-under-chapter", r"stock-exchange", r"transactions-",
    r"fi-fi", r"de-de", r"sv-se",
]


def _fetch_sitemap_urls(url: str) -> list[str]:
    resp = requests.get(url, timeout=30, headers=HEADERS)
    resp.raise_for_status()
    urls = re.findall(r"<loc>([^<]+)</loc>", resp.text)
    # 如果是 sitemap 索引（内含多个子 sitemap），逐个取回合并
    sub = [u for u in urls if u.lower().endswith((".xml", ".xml.gz"))]
    if sub and len(sub) > len(urls) * 0.5:
        merged = []
        for u in sub[:20]:
            try:
                r = requests.get(u, timeout=30, headers=HEADERS)
                merged.extend(re.findall(r"<loc>([^<]+)</loc>", r.text))
            except Exception:
                continue
        return merged
    return urls


def _guess_title(url: str) -> str:
    """从 URL 的 slug 猜测标题（作为抓不到页面时的后备）。"""
    slug = url.rstrip("/").split("/")[-1]
    slug = re.sub(r"-\d+$", "", slug)
    slug = re.sub(r"[-_]+", " ", slug)
    return slug.strip().capitalize() or url


def _enrich_titles(items: list, n: int) -> list:
    """抓取前 n 篇文章页面的真实标题。"""
    if n <= 0:
        return items
    for it in items[:n]:
        try:
            resp = requests.get(it.url, timeout=20, headers=HEADERS)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                t = soup.title
                if t and t.string:
                    title = " ".join(t.string.split())
                    if len(title) > 10:
                        it.title = title
                meta = (
                    soup.find("meta", attrs={"property": "article:published_time"})
                    or soup.find("meta", attrs={"name": "date"})
                    or soup.find("time")
                )
                if meta:
                    d = meta.get("content") or meta.get("datetime") or ""
                    if d:
                        it.published = d[:10]
        except Exception:
            pass
    return items


def fetch_sitemap(source) -> list[FetchedItem]:
    """从站点地图抓取最新文章 URL（适用于 JS 动态站）。"""
    opts = source.options or {}
    noise = opts.get("noise_patterns") or DEFAULT_NOISE
    contains = opts.get("url_contains", "")
    max_items = int(opts.get("max_items", 15))
    enrich = int(opts.get("enrich_titles", 5))

    try:
        urls = _fetch_sitemap_urls(source.url)
    except Exception as e:
        print(f"  [SITEMAP 错误] {source.name}: {e}")
        return []

    noise_re = re.compile("|".join(noise), re.I)
    article_urls = []
    seen = set()
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        if noise_re.search(u):
            continue
        if contains and contains not in u:
            continue
        if u.rstrip("/").endswith(("/newsroom", "/newsroom/")):
            continue
        article_urls.append(u)

    # 站点地图通常按新到旧排列，取前 max_items 条
    article_urls = article_urls[:max_items]

    items = []
    for u in article_urls:
        items.append(FetchedItem(
            source_id=source.id,
            source_name=source.name,
            title=_guess_title(u),
            url=u,
            country=source.country,
        ))
    items = _enrich_titles(items, enrich)
    return items
