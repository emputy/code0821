import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = sqlite3.connect(r"D:\code0821\data\intel.db")
# 新国家监管源抓到的导航页条目全部删除（保留两个 RSS 源的数据）
NEW_NAV_IDS = {
    "chile_subtel", "argentina_enacom", "colombia_crc", "ecuador_arcotel",
    "nigeria_ncc", "kenya_ca", "egypt_ntra", "morocco_anrt", "algeria_arpt",
    "pakistan_pta", "oman_tra", "iraq_cmc", "romania_ancom", "greece_eett",
    "slovakia_urek",
}
for sid in NEW_NAV_IDS:
    n = c.execute("delete from items where source_id=?", (sid,)).rowcount
    print(sid, "deleted:", n)
c.commit()
total = c.execute("select count(*) from items").fetchone()[0]
print("DB total now:", total)
for row in c.execute("select source_name, count(*) from items group by source_name order by 2 desc").fetchall():
    print("  ", row[0], ":", row[1])
c.close()
