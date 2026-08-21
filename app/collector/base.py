from dataclasses import dataclass, field


@dataclass
class Source:
    """一个数据源的定义，对应 sources.json 中的条目。"""
    id: str
    name: str
    type: str            # "rss" | "html" | "sitemap"
    url: str
    country: str = "global"
    enabled: bool = True
    options: dict = field(default_factory=dict)


@dataclass
class FetchedItem:
    """从数据源抓到的一条内容。"""
    source_id: str
    source_name: str
    title: str
    url: str
    published: str = ""
    summary: str = ""
    country: str = "global"
