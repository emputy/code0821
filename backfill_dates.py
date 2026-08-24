"""一次性回填：给 intel.db 里没有发布日期的情报补日期。
优先级：URL 里的日期 -> 抓文章页提取（meta/time/JSON-LD）-> 留空（显示端用抓取日期兜底）。"""
import sqlite3
import sys
import time

import requests
from bs4 import BeautifulSoup

from app.collector.dates import from_soup, from_url

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
DB = r"D:\code0821\data\intel.db"

def main():
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, url, source_name FROM items WHERE published IS NULL OR published = ''"
    ).fetchall()
    total = len(rows)
    print(f"待回填：{total} 条", flush=True)
    filled = 0
    for i, (rid, url, src) in enumerate(rows, 1):
        d = ""
        if url:
            d = from_url(url)
        if not d and url:
            try:
                resp = requests.get(url, timeout=12, headers=HEADERS)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml")
                    d = from_soup(soup)
            except Exception:
                pass
        if d:
            conn.execute("UPDATE items SET published = ? WHERE id = ?", (d, rid))
            conn.commit()
            filled += 1
        if i % 10 == 0 or i == total:
            print(f"  进度 {i}/{total} 已补 {filled}", flush=True)
    conn.close()
    print(f"完成：共补 {filled}/{total} 条", flush=True)

if __name__ == "__main__":
    main()
