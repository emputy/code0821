import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = sqlite3.connect(r"D:\code0821\data\intel.db")
for src in ('TDRA UAE', 'ICASA South Africa'):
    print("=====", src, "=====")
    rows = c.execute("select id, published, url, substr(title,1,60) from items where source_name=? order by id", (src,)).fetchall()
    print("count:", len(rows))
    for rid, pub, url, title in rows[:8]:
        print(rid, "|", (pub or "NO-DATE"), "|", url[:75], "|", title)
c.close()
