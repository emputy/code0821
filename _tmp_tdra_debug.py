import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\code0821")
from app.collector.fetch import load_sources
from app.collector.sitemap import _fetch_sitemap_entries, fetch_sitemap

src = [s for s in load_sources(r"D:\code0821\config\sources.json") if s.id == "tdra_uae"][0]
print("source:", src.id, src.type, src.url)

entries = _fetch_sitemap_entries(src.url)
print("total entries:", len(entries))
matching = [(u, lm) for u, lm in entries if "/en/media/press-release/" in u]
print("matching url_contains:", len(matching))
for u, lm in matching[:5]:
    print("  ", lm, u[:100])
items = fetch_sitemap(src)
print("fetch_sitemap items:", len(items))
for it in items[:5]:
    print("  -", (it.published or "NO-DATE"), "|", it.title[:50], "|", it.url[:90])
