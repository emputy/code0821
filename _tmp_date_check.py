import sqlite3
c = sqlite3.connect(r"D:\code0821\data\intel.db")
total = c.execute("select count(*) from items").fetchone()[0]
withdate = c.execute("select count(*) from items where published is not null and published != ''").fetchone()[0]
print("total:", total, "| with-date:", withdate, "| no-date:", total - withdate)
print("--- per source ---")
for row in c.execute("select source_name, count(*), sum(published is not null and published != '') from items group by source_name order by 2 desc").fetchall():
    print(row)
c.close()
