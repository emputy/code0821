import sqlite3
c = sqlite3.connect(r"D:\code0821\data\intel.db")
for src in ('ICASA South Africa', 'TDRA UAE', 'MCMC Malaysia', 'ANATEL Brazil'):
    print("=====", src, "=====")
    for row in c.execute("select id, url, published, substr(title,1,70) from items where source_name=? order by id", (src,)).fetchall():
        print(row[0], "|", row[2] or "NO-DATE", "|", row[3][:60], "|", row[1][:80])
c.close()
