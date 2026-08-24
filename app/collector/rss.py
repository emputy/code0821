import email.utils
from datetime import datetime

import feedparser

from .base import FetchedItem


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
    """抓取一个 RSS 订阅源，返回前 50 条内容。"""
    try:
        feed = feedparser.parse(source.url)
    except Exception as e:
        print(f"  [RSS 错误] {source.name}: {e}")
        return []

    if getattr(feed, "bozo", 0) and not feed.entries:
        print(f"  [RSS 警告] {source.name}: 解析异常，无内容")

    items = []
    for entry in feed.entries[:50]:
        items.append(FetchedItem(
            source_id=source.id,
            source_name=source.name,
            title=entry.get("title", "").strip(),
            url=entry.get("link", ""),
            published=_norm_date(entry.get("published", "")),
            summary=entry.get("summary", ""),
            country=source.country,
        ))
    return items
