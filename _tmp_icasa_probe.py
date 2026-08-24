import re
import requests
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

def probe(url, label):
    print("=" * 60)
    print(label, url)
    try:
        r = requests.get(url, timeout=15, headers=H)
        print("status:", r.status_code, "len:", len(r.text))
        soup = BeautifulSoup(r.text, "lxml")
        # links with text, prefer those containing date-like or news-like slugs
        seen = set()
        for a in soup.select("a[href]"):
            t = " ".join(a.get_text().split())
            href = a["href"].strip()
            if len(t) < 12 or href in seen:
                continue
            seen.add(href)
            low = href.lower()
            if any(k in low for k in ("notice", "news", "media", "press", "announcement", "publication")):
                print(f"  [{t[:55]}] -> {href[:110]}")
    except Exception as e:
        print("ERROR:", e)

probe("https://www.icasa.org.za/", "ICASA home")
probe("https://www.icasa.org.za/pages/published-notices-i-ecns-inquiry", "ICASA published notices")
