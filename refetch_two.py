"""重新抓取 TDRA + ICASA 两个源（新入口），并删除旧导航页条目。"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
CONFIG = BASE / "config" / "sources.json"
DB = BASE / "data" / "intel.db"

from app.collector.fetch import load_sources
from app.collector.html import fetch_html
from app.collector.rss import fetch_rss
from app.collector.sitemap import fetch_sitemap
from app.storage.database import Database

ids = {"tdra_uae", "icasa_southafrica"}
sources = [s for s in load_sources(str(CONFIG)) if s.id in ids]

def _fetch_one(src):
    if src.type == "rss":
        return fetch_rss(src)
    if src.type == "html":
        return fetch_html(src)
    if src.type == "sitemap":
        return fetch_sitemap(src)
    return []

db = Database(str(DB))
for src in sources:
    print(f"== 抓取 {src.id} {src.url}", flush=True)
    items = _fetch_one(src)
    print(f"  得到 {len(items)} 条", flush=True)
    for it in items[:5]:
        print(f"    - {it.title[:60]} | {it.url[:90]} | 日期:{it.published or '空'}", flush=True)
    added = db.save(items)
    print(f"  新增 {added} 条", flush=True)

# 删除旧导航页条目（新入口 URL 之外的旧条目）
conn = db.conn
del_td = conn.execute(
    "DELETE FROM items WHERE source_id='tdra_uae' AND url NOT LIKE '%/en/media/press-release/%'"
).rowcount
del_ic = conn.execute(
    "DELETE FROM items WHERE source_id='icasa_southafrica' AND url NOT LIKE '%/news/202%'"
).rowcount
conn.commit()
print(f"删除旧导航页：TDRA {del_td} 条，ICASA {del_ic} 条", flush=True)

total, by_source = db.summary()
print(f"数据库共 {total} 条")
for name, cnt in by_source:
    if name in ("TDRA UAE", "ICASA South Africa"):
        print(f"  {name}: {cnt}")
db.close()
