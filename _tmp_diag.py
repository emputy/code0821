import re, sqlite3
import requests
from bs4 import BeautifulSoup

c = sqlite3.connect(r"D:\code0821\data\intel.db")
rows = c.execute("select id, url, title from items where source_name='ICASA South Africa' and (published is null or published='') limit 3").fetchall()
c.close()
print("ICASA missing-date rows:", len(rows))
for rid, url, title in rows:
    print("---", rid, url[:100])
    print("title:", title[:80])
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"})
        print("status:", r.status_code, "len:", len(r.text))
        # search raw html for date patterns
        hits = re.findall(r"(20\d{2})[-/.](\d{1,2})[-/.]?(\d{1,2})", r.text)[:5]
        mon = re.findall(r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+20\d{2}\b", r.text, re.I)[:5]
        print("numeric date hits:", hits)
        print("month-name date hits:", mon)
        soup = BeautifulSoup(r.text, "lxml")
        h1 = soup.find("h1")
        print("h1:", (h1.get_text(strip=True)[:80] if h1 else None))
        txt = soup.get_text(" ", strip=True)[:300]
        print("text start:", txt)
    except Exception as e:
        print("ERROR:", e)
