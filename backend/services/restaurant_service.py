"""
음식점 목록은 이제 DB(backend/data/app.db)에서 읽습니다.
실제 공공데이터 API 연동은 restaurant_api.py에 준비되어 있으니, API 키를 발급받으면
그 결과를 db.replace_restaurants()로 밀어넣기만 하면 됩니다.
"""
import math

import db


def list_categories():
    return ["전체"] + db.list_categories()


def haversine_m(lat1, lng1, lat2, lng2):
    """두 좌표 사이의 직선거리(미터)."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def restaurants_by_category(category):
    return db.list_restaurants(category)
