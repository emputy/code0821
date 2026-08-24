"""一次性回填：给 intel.db 里没有发布日期的情报补发布日期。
16 线程并发抓取：URL 日期 -> 文章页提取（meta/time/JSON-LD/正文文本）。
"""
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

from app.collector.dates import from_soup, from_url

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
DB = r"D:\code0821\data\intel.db"
WORKERS = 16


def _fetch_date(url: str) -> str:
    """返回发布日期 YYYY-MM-DD；抓不到返回空串。"""
    if not url:
        return ""
    d = from_url(url)
    if d:
        return d
    try:
        resp = requests.get(url, timeout=8, headers=HEADERS)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            d = from_soup(soup)
    except Exception:
        pass
    return d


def main():
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, url FROM items WHERE published IS NULL OR published = ''"
    ).fetchall()
    total = len(rows)
    print(f"待回填：{total} 条（{WORKERS} 线程并发）", flush=True)
    filled = 0
    pending = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(_fetch_date, url): rid for rid, url in rows}
        for i, fut in enumerate(as_completed(futs), 1):
            rid = futs[fut]
            try:
                d = fut.result()
            except Exception:
                d = ""
            if d:
                pending.append((d, rid))
                filled += 1
                if len(pending) >= 20:
                    conn.executemany("UPDATE items SET published = ? WHERE id = ?", pending)
                    conn.commit()
                    pending.clear()
            if i % 20 == 0 or i == total:
                print(f"  进度 {i}/{total} 已补 {filled}", flush=True)
    if pending:
        conn.executemany("UPDATE items SET published = ? WHERE id = ?", pending)
        conn.commit()
    conn.close()
    print(f"完成：共补 {filled}/{total} 条", flush=True)


if __name__ == "__main__":
    main()
