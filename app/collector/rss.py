import feedparser

from .base import FetchedItem


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
            published=entry.get("published", ""),
            summary=entry.get("summary", ""),
            country=source.country,
        ))
    return items
