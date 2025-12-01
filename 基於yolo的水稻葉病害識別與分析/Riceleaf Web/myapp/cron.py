# myapp/cron.py
import requests
from bs4 import BeautifulSoup
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache

LOCK_KEY = "cron:crawl_news"
LOCK_TTL = 60 * 10  # 10 分鐘，避免重複執行

def crawl_news():
    # ---- 分布式/多進程鎖，避免重疊 ----
    got = cache.add(LOCK_KEY, "1", LOCK_TTL)  # 建議用 django-redis 當 cache backend
    if not got:
        print(f"[{timezone.now()}] Skip: job already running")
        return

    try:
        url = "https://example.com/news"
        headers = {"User-Agent": "Mozilla/5.0 (DjangoBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        for a in soup.select("a.article-link")[:50]:
            title = (a.get_text() or "").strip()
            link = a.get("href")
            if link and link.startswith("/"):
                link = f"https://example.com{link}"
            if title and link:
                items.append((title, link))

        # TODO：寫入資料庫（示範用交易包起來）
        # from myapp.models import Article
        # with transaction.atomic():
        #     for title, link in items:
        #         Article.objects.get_or_create(url=link, defaults={"title": title})

        print(f"[{timezone.now()}] Crawled {len(items)} items.")
    except Exception as e:
        # 讓輸出進 log，方便排錯
        print(f"[{timezone.now()}] ERROR: {e}")
        raise
    finally:
        cache.delete(LOCK_KEY)
