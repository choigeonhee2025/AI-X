"""
음식점 목록은 이제 DB(backend/data/app.db)에서 읽습니다.
실제 공공데이터 API 연동은 restaurant_api.py에 준비되어 있으니, API 키를 발급받으면
그 결과를 db.replace_restaurants()로 밀어넣기만 하면 됩니다.
"""
import math

import db
from services.category_map import GROUP_ORDER, to_group


def list_categories():
    """원본 카테고리가 너무 잘게 쪼개져 있어서(category_map.py 참고) 그룹 단위로 묶어서 보여줌."""
    present_groups = {to_group(c) for c in db.list_categories()}
    ordered = [g for g in GROUP_ORDER if g in present_groups]
    return ["전체"] + ordered


def haversine_m(lat1, lng1, lat2, lng2):
    """두 좌표 사이의 직선거리(미터)."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def restaurants_by_category(category):
    if not category or category == "전체":
        return db.list_restaurants()
    return [r for r in db.list_restaurants() if to_group(r["category"]) == category]
