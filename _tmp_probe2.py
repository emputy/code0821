import time
import requests
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
S = requests.Session()
S.headers.update(H)

def probe(url, label, link_filter=None):
    print("=" * 66)
    print(label, url)
    try:
        r = S.get(url, timeout=15)
        print("status:", r.status_code, "len:", len(r.text))
        soup = BeautifulSoup(r.text, "lxml")
        seen = set()
        n = 0
        for a in soup.select("a[href]"):
            t = " ".join(a.get_text().split())
            href = a["href"].strip()
            if len(t) < 8 or href in seen:
                continue
            seen.add(href)
            low = href.lower()
            if link_filter and not any(k in low for k in link_filter):
                continue
            print(f"  [{t[:48]}] -> {href[:105]}")
            n += 1
            if n >= 18:
                break
        if n == 0:
            print("  (no matching links)")
    except Exception as e:
        print("ERROR:", e)

# TDRA: media-centre news variants
probe("https://tdra.gov.ae/en/media-centre/news", "TDRA EN news", ["news", "media"])
time.sleep(2)
probe("https://tdra.gov.ae/ar/media-centre/news", "TDRA AR news", ["news", "media"])
time.sleep(2)
probe("https://tdra.gov.ae/en", "TDRA EN home", ["news", "media", "press", "announcement"])
time.sleep(3)

# ICASA: news pages (may still be blocked)
probe("https://www.icasa.org.za/news", "ICASA news", ["notice", "news", "media", "press"])
time.sleep(2)
probe("https://www.icasa.org.za/pages/news", "ICASA pages/news", ["notice", "news", "media", "press"])
