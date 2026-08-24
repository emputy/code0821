import sqlite3
c = sqlite3.connect(r"D:\code0821\data\intel.db")
total = c.execute("select count(*) from items").fetchone()[0]
withdate = c.execute("select count(*) from items where published is not null and published != ''").fetchone()[0]
print("total:", total, "| with publish date:", withdate, "| still missing:", total - withdate)
print("--- per source ---")
for row in c.execute("select source_name, count(*), sum(published is not null and published != '') from items group by source_name order by 2 desc").fetchall():
    print(row)
print("--- sample filled dates (TDRA/ICASA etc) ---")
for row in c.execute("select source_name, published, substr(title,1,50) from items where source_name in ('TDRA UAE','ICASA South Africa','MCMC Malaysia','ANATEL Brazil','Nokia Newsroom') and published != '' order by published desc limit 10").fetchall():
    print(row)
c.close()
