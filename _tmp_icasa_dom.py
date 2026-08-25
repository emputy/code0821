import requests
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
r = requests.get("https://www.icasa.org.za/news", timeout=15, headers=H)
print("status:", r.status_code, "len:", len(r.text))
soup = BeautifulSoup(r.text, "lxml")
# print structure around news links
import re
count = 0
for a in soup.select("a[href]"):
    href = a["href"].strip()
    if re.search(r"/news/202", href):
        t = " ".join(a.get_text().split())
        # walk up to find container with a heading
        node = a
        h = None
        for _ in range(4):
            node = node.parent
            if node is None:
                break
            h = node.find(["h1", "h2", "h3", "h4"])
            if h:
                break
        heading = " ".join(h.get_text().split())[:70] if h else None
        print(f"a-text={t!r} | heading={heading!r} | href={href[:80]}")
        count += 1
        if count >= 8:
            break
