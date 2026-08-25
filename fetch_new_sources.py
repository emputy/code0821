"""抓取已配好新闻入口的国家源 + 其他国家源。"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
CONFIG = BASE / "config" / "sources.json"
DB = BASE / "data" / "intel.db"

from app.collector.fetch import load_sources
from app.collector.html import fetch_html
from app.collector.rss import fetch_rss
from app.storage.database import Database

FETCH_IDS = {
    "chile_subtel", "ecuador_arcotel", "nigeria_ncc", "kenya_ca",
    "morocco_anrt", "pakistan_pta", "romania_ancom", "iraq_cmc",
    "other_power_eng", "other_smart_cities",
}

def _fetch_one(src):
    if src.type == "rss":
        return fetch_rss(src)
    if src.type == "html":
        return fetch_html(src)
    return []

db = Database(str(DB))
sources = [s for s in load_sources(str(CONFIG)) if s.id in FETCH_IDS]
for src in sources:
    print("== ", src.id, src.url, flush=True)
    try:
        items = _fetch_one(src)
        print("   拿到", len(items), "条", flush=True)
        for it in items[:4]:
            print("     -", (it.title or "")[:48], "|", (it.published or "无日期"), flush=True)
        added = db.save(items)
        print("   新增", added, "条", flush=True)
    except Exception as e:
        print("   错误:", str(e)[:100], flush=True)
total, _ = db.summary()
print("数据库共", total, "条", flush=True)
db.close()
