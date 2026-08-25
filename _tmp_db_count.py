import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = sqlite3.connect(r"D:\code0821\data\intel.db")
total = c.execute("select count(*) from items").fetchone()[0]
print("DB total:", total)
for row in c.execute("select source_name, count(*) from items group by source_name order by 2 desc").fetchall():
    print("  ", row[0], ":", row[1])
c.close()
