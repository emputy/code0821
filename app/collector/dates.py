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


def _valid_date(y, m, d) -> bool:
    """校验年月日是否合法：月 1-12、日 1-31、年 2020-2035。"""
    try:
        y, m, d = int(y), int(m), int(d)
        return 2020 <= y <= 2035 and 1 <= m <= 12 and 1 <= d <= 31
    except Exception:
        return False


def normalize(raw: str) -> str:
    """把日期字符串归一化为 YYYY-MM-DD；无法识别或非法返回空串。"""
    if not raw:
        return ""
    m = _ISO_RE.search(raw)
    if m:
        try:
            if _valid_date(m.group(1), m.group(2), m.group(3)):
                return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        except Exception:
            return ""
    m = _TEXT_RE.search(raw)
    if m:
        mon = _MONTHS.get(m.group(2).lower()[:3])
        if mon and _valid_date(m.group(3), mon, m.group(1)):
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


def _first_date(text: str) -> str:
    """按出现顺序找文本里第一个合法的 2020-2035 日期（数字或英文月名格式）。"""
    for m in _ISO_RE.finditer(text):
        if _valid_date(m.group(1), m.group(2), m.group(3)):
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    for m in _TEXT_RE.finditer(text):
        mon = _MONTHS.get(m.group(2).lower()[:3])
        if mon and _valid_date(m.group(3), mon, m.group(1)):
            return f"{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}"
    return ""


def from_soup(soup) -> str:
    """从文章页 BeautifulSoup 提取发布日期。

    优先级：meta 标签 -> <time> 元素 -> JSON-LD -> 标题(h1/h2)附近文本 -> 正文开头文本。
    监管机构页面常把日期写成正文文本（如 "20 AUG 2026"），因此最后两项很关键。
    """
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
    # 标题（h1/h2）附近文本：向上最多 3 层找日期
    for tag in soup.find_all(["h1", "h2"]):
        node = tag.parent
        for _ in range(3):
            if node is None:
                break
            txt = " ".join(node.get_text(" ", strip=True).split())[:1500]
            d = _first_date(txt)
            if d:
                return d
            node = node.parent
    # 正文可见文本开头：排除脚本/样式后扫前 4000 字符
    for bad in soup.find_all(["script", "style", "noscript"]):
        bad.decompose()
    txt = " ".join(soup.get_text(" ", strip=True).split())
    d = _first_date(txt[:4000])
    if d:
        return d
    return ""
