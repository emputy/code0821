import email.utils
from datetime import datetime

import feedparser
import requests

from .base import FetchedItem

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}


def _norm_date(raw: str) -> str:
    """把 RSS 的 RFC822 日期转为 YYYY-MM-DD；无法解析则原样截取前 10 位。"""
    if not raw:
        return ""
    try:
        dt = email.utils.parsedate_to_datetime(raw)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return raw[:10] if len(raw) >= 10 else raw


def fetch_rss(source) -> list[FetchedItem]:
    """抓取一个 RSS 订阅源，返回前 50 条内容。

    用 requests 先取内容（带 20s 超时和浏览器 UA），再交给 feedparser 解析，
    避免 feedparser 直连无超时导致长时间挂起。支持按源配置代理。
    """
    opts = source.options or {}
    proxies = {"http": opts["proxy"], "https": opts["proxy"]} if opts.get("proxy") else None
    try:
        resp = requests.get(source.url, timeout=20, headers=HEADERS,
                            verify=bool(opts.get("verify_ssl", True)), proxies=proxies)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception as e:
        print(f"  [RSS 错误] {source.name}: {e}")
        return []

    if getattr(feed, "bozo", 0) and not feed.entries:
        print(f"  [RSS 警告] {source.name}: 解析异常，无内容")

    items = []
    for entry in feed.entries[:50]:
        published = ""
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if parsed:
            try:
                published = datetime(*parsed[:6]).strftime("%Y-%m-%d")
            except Exception:
                published = ""
        if not published:
            published = _norm_date(entry.get("published", "") or entry.get("updated", ""))
        items.append(FetchedItem(
            source_id=source.id,
            source_name=source.name,
            title=entry.get("title", "").strip(),
            url=entry.get("link", ""),
            published=published,
            summary=entry.get("summary", ""),
            country=source.country,
        ))
    return items
