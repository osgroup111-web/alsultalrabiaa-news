#!/usr/bin/env python3
"""Fetch RSS feeds from Iraqi news sites and write news.json (headline + source + link only)."""
import json, sys, re, html
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

FEEDS = [
    ("شفق نيوز", "https://shafaq.com/ar?rss=1"),
    ("السومرية", "https://www.alsumaria.tv/Rss/iraq-latest-news/ar"),
    ("المدى", "https://www.almadapaper.net/feed"),
    # لإضافة مصدر جديد: أضف سطرًا بنفس الشكل ("الاسم", "رابط RSS")
]
PER_FEED = 12      # عدد الأخبار المأخوذة من كل مصدر
MAX_ITEMS = 36     # الحد الأعلى للأخبار في الشريط
MAX_AGE_H = 72     # تجاهل الأخبار الأقدم من هذا

def parse_date(s):
    try:
        d = parsedate_to_datetime(s.strip())
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except Exception:
        return None

def fetch(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; AlsultaRabiaaNewsBot/1.0)",
                                "Accept": "application/rss+xml, application/xml, text/xml, */*"})
    with urlopen(req, timeout=25) as r:
        return r.read()

def clean(t):
    t = html.unescape(re.sub(r"<[^>]+>", "", t or ""))
    return re.sub(r"\s+", " ", t).strip()

def main():
    now = datetime.now(timezone.utc)
    items, ok = [], []
    for name, url in FEEDS:
        try:
            root = ET.fromstring(fetch(url))
            got = 0
            for it in root.iter("item"):
                title = clean(it.findtext("title"))
                link = (it.findtext("link") or "").strip()
                d = parse_date(it.findtext("pubDate") or "")
                if not title or not link.startswith(("http://", "https://")):
                    continue
                if d is None:
                    d = now
                if (now - d).total_seconds() > MAX_AGE_H * 3600:
                    continue
                items.append({"source": name, "title": title, "link": link, "ts": int(d.timestamp())})
                got += 1
                if got >= PER_FEED:
                    break
            print(f"OK   {name}: {got} items")
            if got:
                ok.append(name)
        except Exception as e:
            print(f"FAIL {name}: {e}", file=sys.stderr)
    if not items:
        print("No items fetched; keeping the old news.json", file=sys.stderr)
        return 0
    seen, uniq = set(), []
    for x in sorted(items, key=lambda x: x["ts"], reverse=True):
        k = x["title"][:60]
        if k in seen:
            continue
        seen.add(k); uniq.append(x)
    out = {"updated": int(now.timestamp()), "sources": ok, "items": uniq[:MAX_ITEMS]}
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"Wrote {len(out['items'])} items")
    return 0

if __name__ == "__main__":
    sys.exit(main())
