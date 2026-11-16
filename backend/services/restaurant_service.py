"""
현재는 data/restaurants.json(샘플 데이터)에서 음식점 목록을 읽습니다.
실제 공공데이터 API 연동은 restaurant_api.py에 준비되어 있으니, API 키를 발급받으면
load_restaurants()의 데이터 소스만 바꿔 끼우면 됩니다.
"""
import json
import math
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESTAURANTS_PATH = os.path.join(BASE_DIR, "data", "restaurants.json")


def load_restaurants():
    with open(RESTAURANTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["restaurants"], data["campus_center"]


def list_categories():
    restaurants, _ = load_restaurants()
    return sorted({r["category"] for r in restaurants})


def haversine_m(lat1, lng1, lat2, lng2):
    """두 좌표 사이의 직선거리(미터)."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def restaurants_by_category(category):
    restaurants, _ = load_restaurants()
    if not category or category == "전체":
        return restaurants
    return [r for r in restaurants if r["category"] == category]
