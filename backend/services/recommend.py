"""
핵심 추천 로직.
회귀 모델(또는 베이스라인)로 왕복 이동시간을 예측하고, 식사시간(+혼잡도 데이터가 있는
음식점은 예상 대기시간까지)을 더해 공강시간 안에 다녀올 수 있는 음식점만 걸러
여유시간(slack) 순으로 정렬합니다.
"""
import db
from kst import now_kst
from models.speed_predictor import predict_batch
from models.wait_predictor import predict_wait_batch
from services.category_map import to_group
from services.restaurant_service import haversine_m, restaurants_by_category


def recommend(
    break_minutes: float,
    meal_minutes: float,
    category: str,
    user_lat: float,
    user_lng: float,
    member: str = None,
    dest_lat: float = None,
    dest_lng: float = None,
):
    """dest_lat/dest_lng(다음 수업 강의동 등 복귀 목적지)가 따로 있으면 출발지->음식점,
    음식점->도착지 두 구간을 각각 계산합니다. 안 주면 출발지와 같다고 보고(왕복) 계산."""
    now = now_kst()
    hour, dow, minute = now.hour, now.weekday(), now.minute
    if dest_lat is None or dest_lng is None:
        dest_lat, dest_lng = user_lat, user_lng

    candidates = restaurants_by_category(category)
    distances_to = [haversine_m(user_lat, user_lng, r["lat"], r["lng"]) for r in candidates]
    distances_from = [haversine_m(r["lat"], r["lng"], dest_lat, dest_lng) for r in candidates]
    minutes_to, tier_used = predict_batch(distances_to, hour, dow, member)
    minutes_from, _ = predict_batch(distances_from, hour, dow, member)
    wait_minutes, congestion_pcts = predict_wait_batch([r["name"] for r in candidates], dow, hour, minute)
    favorite_ids = db.list_favorite_ids(member) if member else set()

    results = []
    for r, distance_to_m, distance_from_m, min_to, min_from, wait_min, congestion_pct in zip(
        candidates, distances_to, distances_from, minutes_to, minutes_from, wait_minutes, congestion_pcts
    ):
        round_trip_min = min_to + min_from
        total_needed_min = round_trip_min + meal_minutes + wait_min
        slack_min = break_minutes - total_needed_min

        results.append(
            {
                **r,
                "category_group": to_group(r["category"]),
                "is_favorite": r["id"] in favorite_ids,
                "distance_m": round(distance_to_m),
                "return_distance_m": round(distance_from_m),
                "one_way_min": round(min_to, 1),
                "return_min": round(min_from, 1),
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
