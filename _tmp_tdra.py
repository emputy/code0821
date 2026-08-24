import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = sqlite3.connect(r"D:\code0821\data\intel.db")
for src in ('TDRA UAE', 'MCMC Malaysia', 'ANATEL Brazil', 'Light Reading'):
    print("=====", src, "=====")
    rows = c.execute("select id, url, published, title from items where source_name=? order by id", (src,)).fetchall()
    for rid, url, pub, title in rows:
        print(rid, "|", (pub or "NO-DATE"), "|", (title or "")[:55].replace(chr(10), " "), "|", url[:85])
c.close()
