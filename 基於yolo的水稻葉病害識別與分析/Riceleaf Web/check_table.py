import requests
from bs4 import BeautifulSoup

URL = "https://ag.shuhao.idv.tw/content/ag/RiceData.aspx"
headers = {"User-Agent": "Mozilla/5.0"}

print("== Fetching ==", URL)
r = requests.get(URL, headers=headers, timeout=30)
print("HTTP:", r.status_code, " length:", len(r.text))

soup = BeautifulSoup(r.text, "html.parser")

tables = soup.find_all("table")
print("tables found:", len(tables))

if not tables:
    print(">>> 沒找到 <table>，可能是 AJAX/iframe 載入或需要其他參數")
else:
    tbl = tables[0]
    rows = tbl.find_all("tr")
    print("first table rows:", len(rows))
    print(">>> 列出前 3 列（同時抓 td 和 th）：")
    for i, tr in enumerate(rows[:3]):
        cells = [c.get_text(strip=True) for c in tr.find_all(["td","th"])]
        print(f"row {i+1} ->", cells)
