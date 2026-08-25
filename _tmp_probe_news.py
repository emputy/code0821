import re, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import requests
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
NEWS_HINTS = ("news", "media", "press", "noticia", "actualite", "comunicado", "sala-de", "anuncio", "publicacion", "ultimas")

SOURCES = [
    ("chile_subtel", "https://www.subtel.gob.cl/", ["espectro", "frecuencias"]),
    ("argentina_enacom", "https://www.enacom.gob.ar/", ["espectro", "frecuencias"]),
    ("colombia_crc", "https://www.crcom.gov.co/", ["espectro", "frecuencias"]),
    ("ecuador_arcotel", "https://www.arcotel.gob.ec/", ["espectro", "frecuencias"]),
    ("nigeria_ncc", "https://www.ncc.gov.ng/", ["spectrum", "frequency"]),
    ("kenya_ca", "https://www.ca.go.ke/", ["spectrum", "frequency"]),
    ("egypt_ntra", "https://www.tra.gov.eg/", ["spectrum", "frequency"]),
    ("morocco_anrt", "https://www.anrt.ma/", ["spectre", "frequences"]),
    ("algeria_arpt", "https://www.arpt.dz/", ["spectre", "frequences"]),
    ("pakistan_pta", "https://www.pta.gov.pk/", ["spectrum", "frequency"]),
    ("oman_tra", "https://www.tra.gov.om/", ["spectrum", "frequency"]),
    ("iraq_cmc", "https://www.cmc.iq/", ["spectrum", "frequency"]),
    ("romania_ancom", "https://www.ancom.ro/", ["spectru", "frecventa"]),
    ("greece_eett", "https://www.eett.gr/", ["phasma", "sychnotita"]),
    ("slovakia_urek", "https://www.teleoff.gov.sk/", ["spektrum", "frekvencia"]),
]

S = requests.Session()
S.headers.update(H)

for sid, url, kws in SOURCES:
    print("=" * 20, sid, url)
    try:
        r = S.get(url, timeout=15)
        print("  status:", r.status_code, "len:", len(r.text))
        soup = BeautifulSoup(r.text, "lxml")
        seen = set()
        found = []
        for a in soup.select("a[href]"):
            t = " ".join(a.get_text().split())
            href = a["href"].strip()
            if not href or href in seen or len(t) < 4:
                continue
            seen.add(href)
            low = href.lower()
            if any(k in low for k in NEWS_HINTS):
                found.append((t[:40], href[:90]))
        for t, h in found[:6]:
            print("   [", t, "] ->", h)
        if not found:
            print("   (no news links found)")
    except Exception as e:
        print("  ERROR:", str(e)[:80])
    time.sleep(1)
