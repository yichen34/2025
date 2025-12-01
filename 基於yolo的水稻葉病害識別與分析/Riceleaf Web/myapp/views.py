from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import RegisterForm
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from collections import defaultdict
from django.shortcuts import render
import requests
from django.conf import settings
import os
from ultralytics import YOLO
from PIL import Image
import json
from pathlib import Path
import datetime


# ✅ 匯入：把建議內容從 JSON 附加到辨識結果
from .utils import attach_guides_to_results


HEADS = [
    "市場",
    "粳種白米零售", "硬秈白米零售", "軟秈白米零售", "圓糯白米零售", "長糯白米零售",
    "粳種白米躉售", "硬秈白米躉售", "軟秈白米躉售", "圓糯白米躉售", "長糯白米躉售"
]

MODEL_PATH = os.path.join(settings.BASE_DIR, 'yolomodels', 'best.pt')
model = YOLO(MODEL_PATH)              # 只載一次
CLASS_NAME_MAPPING = model.names      # 類別對應表（id -> name）


import requests
from django.shortcuts import render

def home(request):
    # 使用者輸入，例如「台北」「東京」
    city_input = request.GET.get('city', '台北')
    api_key = '請輸入自己的api key'

    # 先用 Geocoding API 找經緯度 & 中文名稱
    geo_url = 'http://api.openweathermap.org/geo/1.0/direct'
    geo_params = {
        'q': city_input,
        'limit': 1,
        'appid': api_key,
    }

    geo_response = requests.get(geo_url, params=geo_params)
    geo_data = geo_response.json()

    if geo_response.status_code == 200 and len(geo_data) > 0:
        lat = geo_data[0]['lat']
        lon = geo_data[0]['lon']

        # 🔴 關鍵：決定要顯示的城市名稱（優先用 zh_tw，沒有就用使用者輸入）
        local_names = geo_data[0].get('local_names', {})
        city_display = local_names.get('zh_tw') or city_input

        # 查天氣
        weather_url = 'https://api.openweathermap.org/data/2.5/weather'
        weather_params = {
            'lat': lat,
            'lon': lon,
            'appid': api_key,
            'units': 'metric',
            'lang': 'zh_tw',
        }

        response = requests.get(weather_url, params=weather_params)
        weather_data = response.json()

        if response.status_code == 200 and weather_data.get('cod') == 200:
            context = {
                # ✅ 這裡改成 city_display（中文）
                'city': city_display,
                'temperature': weather_data['main']['temp'],
                'description': weather_data['weather'][0]['description'],
                'icon': weather_data['weather'][0]['icon'],
                'error': None
            }
        else:
            context = {
                'city': city_input,
                'temperature': None,
                'description': None,
                'icon': None,
                'error': '查詢天氣失敗，請稍後再試！'
            }
    else:
        context = {
            'city': city_input,
            'temperature': None,
            'description': None,
            'icon': None,
            'error': '找不到該城市，請重新輸入！'
        }

    return render(request, 'home.html', context)


def sick(request):
    """
    上傳稻葉圖片 -> YOLO 推論 -> 顯示類別清單
    並且將對應的「解決方法 / 預防建議」從 JSON 附加到 guides 一起傳給 sick.html
    """
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        image = Image.open(image_file)

        # 進行推論（可視需要調整 conf / iou）
        results = model.predict(image, conf=0.5, iou=0.4)
        result = results[0]

        # 取出框、信心度與類別
        probs = result.boxes.conf.tolist() if result.boxes is not None else []
        classes = result.boxes.cls.tolist() if result.boxes is not None else []

        # 只收信心度大於等於 0.5 的，且只保留不同的類別
        detected_set = set()
        for prob, cls in zip(probs, classes):
            if prob >= 0.5:
                class_id = int(cls)
                class_name = CLASS_NAME_MAPPING.get(class_id, f'未知類別 {class_id}')
                detected_set.add(class_name)

        detected_classes = sorted(detected_set)  # 排序讓顯示穩定

        # ✅ 由 JSON 附加建議（solutions / prevention）
        guides = attach_guides_to_results(detected_classes)

        context = {
            'uploaded': True,
            'detected_classes': detected_classes,
            'guides': guides,  # ← 新增給模板使用
        }
        return render(request, 'sick.html', context)

    # GET 或沒有檔案的情況
    return render(request, 'sick.html', {
        'uploaded': False,
        'detected_classes': [],
        'guides': [],  # 保持模板變數存在，避免空值判斷麻煩
    })


def trade(request):
    json_path = Path("data/crawl_result.json")
    if not json_path.exists():
        return render(request, "trade.html", {
            "error": "尚未有爬蟲資料，請稍後再試。",
            "day_tables": [],
            "fetched_at": None,
            "heads": [],
        })

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        dates_map = data.get("dates", {})
        fetched_at = data.get("fetched_at")
        day_tables = sorted(dates_map.items(), key=lambda kv: kv[0], reverse=True)

        # 從第一天的第一列推欄位
        sample_rows = next(iter(dates_map.values()), [])
        sample = sample_rows[0] if sample_rows else {}
        heads = [h for h in HEADS if h in sample]

    elif isinstance(data, list):
        today = datetime.datetime.now().strftime("%Y/%m/%d")
        day_tables = [(today, data)]
        fetched_at = today
        sample = data[0] if data else {}
        heads = [h for h in HEADS if h in sample]

    else:
        return render(request, "trade.html", {
            "error": "資料格式不符，請檢查 crawl_result.json。",
            "day_tables": [],
            "fetched_at": None,
            "heads": [],
        })

    return render(request, "trade.html", {
        "fetched_at": fetched_at,
        "day_tables": day_tables,
        "error": None,
        "heads": heads,
    })



def about(request):
    return render(request, 'about.html')


def custom_login(request):
    return render(request, 'login.html')


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})
