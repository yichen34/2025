# yourapp/management/commands/crawl_once.py
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone

from pathlib import Path
import requests, json, tempfile
from bs4 import BeautifulSoup

LOCK_KEY = "cron:crawl_news"
LOCK_TTL = 600  # 10 分鐘

class Command(BaseCommand):
    help = "抓取目標網站並輸出為 JSON 檔"

    def handle(self, *args, **options):
        # ── 1) 拿鎖，避免重複執行 ─────────────────────────────
        if not cache.add(LOCK_KEY, "1", LOCK_TTL):
            self.stdout.write("Skip: another run in progress")
            return
        try:
            # ── 2) 抓資料 ──────────────────────────────────────
            url = "https://example.com/news"   # ← 改成你的目標
            headers = {"User-Agent": "Mozilla/5.0 (DjangoBot/1.0)"}
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # 這裡請依實際網站調整 selector ↓↓↓
            items = []
            for a in soup.select("a.article-link")[:50]:
                title = (a.get_text() or "").strip()
                link = (a.get("href") or "").strip()
                if link.startswith("/"):
                    link = f"https://example.com{link}"
                if title and link:
                    items.append({"title": title, "url": link})

            payload = {
                "fetched_at": timezone.now().isoformat(),
                "count": len(items),
                "items": items,
            }

            # ── 3) 寫 JSON（原子寫入），確保資料夾存在 ───────────
            json_path: Path = Path(settings.CRAWL_JSON_PATH)
            json_path.parent.mkdir(parents=True, exist_ok=True)

            # 先寫到暫存檔再 replace，避免讀到半寫入的檔案
            with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tf:
                json.dump(payload, tf, ensure_ascii=False, indent=2)
                tmp_name = tf.name
            Path(tmp_name).replace(json_path)

            self.stdout.write(self.style.SUCCESS(
                f"[{payload['fetched_at']}] 寫入 {json_path}（共 {payload['count']} 筆）"
            ))
        finally:
            cache.delete(LOCK_KEY)
