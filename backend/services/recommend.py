"""
핵심 추천 로직.
회귀 모델(또는 베이스라인)로 왕복 이동시간을 예측하고, 식사시간(+혼잡도 데이터가 있는
음식점은 예상 대기시간까지)을 더해 공강시간 안에 다녀올 수 있는 음식점만 걸러
여유시간(slack) 순으로 정렬합니다.
"""
import datetime

import db
from models.speed_predictor import predict_batch
from models.wait_predictor import predict_wait_batch
from services.category_map import to_group
from services.restaurant_service import haversine_m, restaurants_by_category


def recommend(break_minutes: float, meal_minutes: float, category: str, user_lat: float, user_lng: float, member: str = None):
    now = datetime.datetime.now()
    hour, dow, minute = now.hour, now.weekday(), now.minute

    candidates = restaurants_by_category(category)
    distances = [haversine_m(user_lat, user_lng, r["lat"], r["lng"]) for r in candidates]
    one_way_minutes, tier_used = predict_batch(distances, hour, dow, member)
    wait_minutes, congestion_pcts = predict_wait_batch([r["name"] for r in candidates], dow, hour, minute)
    favorite_ids = db.list_favorite_ids(member) if member else set()

    results = []
    for r, distance_m, one_way_min, wait_min, congestion_pct in zip(
        candidates, distances, one_way_minutes, wait_minutes, congestion_pcts
    ):
        round_trip_min = one_way_min * 2
        total_needed_min = round_trip_min + meal_minutes + wait_min
        slack_min = break_minutes - total_needed_min

        results.append(
            {
                **r,
                "category_group": to_group(r["category"]),
                "is_favorite": r["id"] in favorite_ids,
                "distance_m": round(distance_m),
                "one_way_min": round(one_way_min, 1),
                "round_trip_min": round(round_trip_min, 1),
                "congestion_pct": congestion_pct,
                "wait_min": wait_min,
                "total_needed_min": round(total_needed_min, 1),
                "slack_min": round(slack_min, 1),
                "feasible": slack_min >= 0,
            }
        )

    feasible = [r for r in results if r["feasible"]]
    feasible.sort(key=lambda r: r["slack_min"])  # 여유시간이 빠듯한(타이트한) 곳부터, 선택지를 넓게 보여줌
    infeasible = [r for r in results if not r["feasible"]]
    infeasible.sort(key=lambda r: r["slack_min"], reverse=True)  # 아깝게 못 가는 곳부터

    return feasible, infeasible, tier_used
