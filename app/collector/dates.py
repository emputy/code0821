"""通用日期提取工具：把各种格式的日期字符串归一化为 YYYY-MM-DD。"""
import re

_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
_ISO_RE = re.compile(r"(20\d{2})[-/.]?(\d{1,2})[-/.]?(\d{1,2})")
_TEXT_RE = re.compile(
    r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(20\d{2})", re.I
)
_URL_RE = re.compile(r"/(20\d{2})[/-](\d{1,2})[/-](\d{1,2})")

META_SELECTORS = [
    {"property": "article:published_time"},
    {"property": "og:published_time"},
    {"name": "date"},
    {"name": "pubdate"},
    {"name": "publishdate"},
    {"name": "dc.date"},
    {"name": "dcterms.date"},
    {"itemprop": "datePublished"},
    {"itemprop": "dateCreated"},
    {"name": "parsely-pub-date"},
    {"name": "sailthru.date"},
]


def normalize(raw: str) -> str:
    """把日期字符串归一化为 YYYY-MM-DD；无法识别返回空串。"""
    if not raw:
        return ""
    m = _ISO_RE.search(raw)
    if m:
        try:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        except Exception:
            return ""
    m = _TEXT_RE.search(raw)
    if m:
        mon = _MONTHS.get(m.group(2).lower()[:3])
        if mon:
            return f"{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}"
    return ""


def from_url(url: str) -> str:
    """从 URL 里的 /2025/03/14/ 或 /2025-03-14/ 提取日期。"""
    m = _URL_RE.search(url or "")
    if m:
        try:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        except Exception:
            return ""
    return ""


def from_soup(soup) -> str:
    """从文章页 BeautifulSoup 提取发布日期：meta / time / JSON-LD。"""
    for sel in META_SELECTORS:
        m = soup.find("meta", attrs=sel)
        if m and m.get("content"):
            d = normalize(str(m["content"]).strip())
            if d:
                return d
    t = soup.find("time")
    if t:
        d = normalize((t.get("datetime") or t.get_text()).strip())
        if d:
            return d
    for sc in soup.find_all("script", attrs={"type": "application/ld+json"}):
        txt = sc.string or ""
        m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', txt)
        if m:
            d = normalize(m.group(1))
            if d:
                return d
    return ""
