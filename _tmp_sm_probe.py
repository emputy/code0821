import re, time
import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

def probe(url):
    print("=" * 60)
    print(url)
    try:
        r = requests.get(url, timeout=15, headers=H)
        print("status:", r.status_code, "len:", len(r.text))
        text = r.text[:3000]
        # show sample loc/lastmod blocks
        blocks = re.findall(r"<url>(.*?)</url>", r.text, re.S)[:3]
        for b in blocks:
            loc = re.search(r"<loc>([^<]+)</loc>", b)
            last = re.search(r"<lastmod>([^<]+)</lastmod>", b)
            print("  loc:", (loc.group(1)[:90] if loc else None))
            print("  lastmod:", (last.group(1) if last else None))
        print("  url blocks:", len(re.findall(r"<url>", r.text)))
        print("  sitemap index links:", len(re.findall(r"<sitemap>", r.text)))
        # count news-ish URLs
        news = [u for u in re.findall(r"<loc>([^<]+)</loc>", r.text) if "/news" in u or "press-release" in u]
        print("  news-ish URLs:", len(news))
        for u in news[:5]:
            print("    ", u[:100])
    except Exception as e:
        print("ERROR:", e)

probe("https://www.icasa.org.za/sitemap.xml")
time.sleep(2)
probe("https://tdra.gov.ae/sitemap.xml")
time.sleep(2)
probe("https://tdra.gov.ae/en/sitemap.xml")
