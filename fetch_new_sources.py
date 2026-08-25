"""抓取新增的国家监管源 + 其他国家源，把数据填进库。"""
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

NEW_IDS = {
    "chile_subtel", "argentina_enacom", "colombia_crc", "ecuador_arcotel",
    "nigeria_ncc", "kenya_ca", "egypt_ntra", "morocco_anrt", "algeria_arpt",
    "pakistan_pta", "oman_tra", "iraq_cmc", "romania_ancom", "greece_eett",
    "slovakia_urek", "other_power_eng", "other_smart_cities",
}

def _fetch_one(src):
    if src.type == "rss":
        return fetch_rss(src)
    if src.type == "html":
        return fetch_html(src)
    if src.type == "sitemap":
        return fetch_sitemap(src)
    return []

db = Database(str(DB))
sources = [s for s in load_sources(str(CONFIG)) if s.id in NEW_IDS]
for src in sources:
    print("== ", src.id, src.url, flush=True)
    try:
        items = _fetch_one(src)
        print("   拿到", len(items), "条", flush=True)
        for it in items[:3]:
            print("     -", (it.title or "")[:50], "|", (it.published or "无日期"), flush=True)
        added = db.save(items)
        print("   新增", added, "条", flush=True)
    except Exception as e:
        print("   错误:", str(e)[:120], flush=True)
total, _ = db.summary()
print("数据库共", total, "条", flush=True)
db.close()
