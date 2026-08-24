import sqlite3
c = sqlite3.connect(r"D:\code0821\data\intel.db")
rows = c.execute("select id, published from items where published != ''").fetchall()
bad = [(rid, p) for rid, p in rows if len(p) == 10 and (int(p[5:7]) not in range(1, 13) or int(p[8:10]) not in range(1, 32))]
for rid, p in bad:
    print("clear bad:", rid, p)
    c.execute("update items set published='' where id=?", (rid,))
c.commit()
print("cleared:", len(bad))
c.close()
