from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from pathlib import Path
import requests, time, json, tempfile, os, re
from bs4 import BeautifulSoup

URL = "https://ag.shuhao.idv.tw/content/ag/RiceData.aspx"
HEADERS = {"User-Agent": "Mozilla/5.0 (DjangoBot/1.0)"}
# 支援 2025/11/7 或 2025-11-07 兩種格式
DATE_RE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$")


# 全部縣市的「市場」清單（頁面查詢下拉選單出現者）
MARKETS = [
    "基隆市","台北市","新北市","桃園市","新竹市","新竹縣","苗栗縣",
    "台中市","彰化縣","南投縣","雲林縣","嘉義市","嘉義縣","台南市",
    "高雄市","屏東縣","宜蘭縣","花蓮縣","台東縣","澎湖縣"
]

COLUMNS = [
    "交易日期", "市場",
    "粳種白米_零售", "硬秈白米_零售", "軟秈白米_零售", "圓糯白米_零售", "長糯白米_零售",
    "粳種白米_躉售", "硬秈白米_躉售", "軟秈白米_躉售", "圓糯白米_躉售", "長糯白米_躉售",
]

def to_float(s: str) -> float:
    try:
        s = (s or "").strip().replace(",", "")
        return float(s) if s and s != "-" else 0.0
    except Exception:
        return 0.0

class Command(BaseCommand):
    help = "抓取指定頁數的米價資料，依交易日期分組（每日表格齊全、去重）並存成 JSON"

    def add_arguments(self, parser):
        parser.add_argument("--pages", type=int, default=1, help="要抓幾頁資料（預設 1 頁）")

    def handle(self, *args, **opts):
        total_pages = opts["pages"]
        self.stdout.write(self.style.HTTP_INFO(f"開始抓取前 {total_pages} 頁的米價資料..."))

        all_rows = []
        seen = set()  # 用於去重：(date, market)

        for p in range(1, total_pages + 1):
            self.stdout.write(f"📄 抓取第 {p}/{total_pages} 頁")

            html = self._fetch_page_html(p)
            if not html:
                self.stderr.write(self.style.ERROR(f"⚠️ 第 {p} 頁抓取失敗，略過"))
                continue

            soup = BeautifulSoup(html, "html.parser")

            # 以「12 欄且第 1 欄是日期」為判斷，避免抓到表頭或其他表格
            for tr in soup.select("tr"):
                tds = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if len(tds) >= 12 and DATE_RE.match(tds[0]):
                    row = dict(zip(COLUMNS, tds[:12]))

                    # 去重：同一天、同市場只留一筆（保留先遇到的）
                    key = (row["交易日期"], row["市場"])
                    if key in seen:
                        continue
                    seen.add(key)
                    all_rows.append(row)

            time.sleep(0.5)  # 禮貌性延遲

        # ===== 依日期分組，並「補齊所有市場」 =====
        by_date = {}
        for r in all_rows:
            date = r["交易日期"]
            by_date.setdefault(date, {})
            by_date[date][r["市場"]] = {
                "市場": r["市場"],
                "零售": {
                    "粳種白米": to_float(r["粳種白米_零售"]),
                    "硬秈白米": to_float(r["硬秈白米_零售"]),
                    "軟秈白米": to_float(r["軟秈白米_零售"]),
                    "圓糯白米": to_float(r["圓糯白米_零售"]),
                    "長糯白米": to_float(r["長糯白米_零售"]),
                },
                "躉售": {
                    "粳種白米": to_float(r["粳種白米_躉售"]),
                    "硬秈白米": to_float(r["硬秈白米_躉售"]),
                    "軟秈白米": to_float(r["軟秈白米_躉售"]),
                    "圓糯白米": to_float(r["圓糯白米_躉售"]),
                    "長糯白米": to_float(r["長糯白米_躉售"]),
                }
            }

        # 正規化：確保每一天都有 MARKETS 的完整清單，缺的就補零
        normalized = {}
        for date, market_map in by_date.items():
            day_list = []
            for m in MARKETS:
                if m in market_map:
                    day_list.append(market_map[m])
                else:
                    day_list.append({
                        "市場": m,
                        "零售": {k: 0.0 for k in ["粳種白米","硬秈白米","軟秈白米","圓糯白米","長糯白米"]},
                        "躉售": {k: 0.0 for k in ["粳種白米","硬秈白米","軟秈白米","圓糯白米","長糯白米"]},
                    })
            # 依市場名稱排序（可依你網站顯示順序調整）
            normalized[date] = sorted(day_list, key=lambda x: MARKETS.index(x["市場"]) if x["市場"] in MARKETS else 999)

        # ===== 輸出 JSON =====
        payload = {
            "source": URL,
            "fetched_at": timezone.now().isoformat(),
            "dates": dict(sorted(normalized.items(), reverse=True)),  # 日期新→舊
        }

        out_path = Path(getattr(
            settings,
            "CRAWL_JSON_PATH",
            Path(getattr(settings, "BASE_DIR", ".")) / "data" / "crawl_result.json",
        ))
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=out_path.parent) as tf:
            json.dump(payload, tf, ensure_ascii=False, indent=2)
            tmp = tf.name
        os.replace(tmp, out_path)

        # 統計
        total_days = len(payload["dates"])
        total_rows = sum(len(v) for v in payload["dates"].values())
        self.stdout.write(self.style.SUCCESS(
            f"✅ 完成！共 {total_days} 天、{total_rows} 筆（已補齊每日 {len(MARKETS)} 市場）。檔案：{out_path}"
        ))

    # --- helpers ---

    def _fetch_page_html(self, page_num: int) -> str:
        """
        嘗試以 ?p= 與 ?page= 兩種參數抓分頁（部分 ASP.NET 站會用 p）。
        任一成功就回傳文字，否則回 None。
        """
        sess = requests.Session()
        for key in ("p", "page"):
            try:
                resp = sess.get(URL, headers=HEADERS, params={key: page_num}, timeout=30)
                if resp.ok and "交易日期" in resp.text:
                    return resp.text
            except Exception:
                pass
        # 最後再嘗試不帶參數（可能第一頁）
        try:
            resp = sess.get(URL, headers=HEADERS, timeout=30)
            if resp.ok and "交易日期" in resp.text and page_num == 1:
                return resp.text
        except Exception:
            pass
        return None
