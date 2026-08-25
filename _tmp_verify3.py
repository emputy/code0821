import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = sqlite3.connect(r"D:\code0821\data\intel.db")
for src in ('TDRA UAE', 'ICASA South Africa'):
    print("=====", src, "=====")
    rows = c.execute("select id, published, url, title from items where source_name=? order by id", (src,)).fetchall()
    print("count:", len(rows), "| with date:", sum(1 for r in rows if r[1]))
    for rid, pub, url, title in rows[:25]:
        print(rid, "|", (pub or "NO-DATE"), "|", (title or "")[:50], "|", url[:70])
c.close()
