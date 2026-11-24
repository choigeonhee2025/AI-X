"""
카카오맵 도보 경로 조회 API 연동 (2026-07-21에 새로 열린, 별도 심사 없이 바로 쓸 수 있는
"카카오맵 Open API" 쪽입니다 - 예전에 제휴 신청이 필요했던 카카오모빌리티
apis-navi.kakaomobility.com/affiliate/... 쪽이 아닙니다. 그쪽으로 먼저 시도했다가
403 permission denied를 받고 이 엔드포인트로 바꿨습니다).

Base URL : https://dapi.kakao.com/v2/routing/walk
인증     : Authorization 헤더에 "KakaoAK {REST_API_KEY}"
좌표     : start_x/start_y, end_x/end_y로 따로 받음 (x=경도, y=위도)
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

BASE_URL = "https://dapi.kakao.com/v2/routing/walk"


def get_walking_route(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float, timeout: int = 10):
    """성공하면 {"path": [{"lat","lng"}, ...], "distance_m": int, "duration_sec": int} 를 돌려주고,
    실패하면 RuntimeError를 던집니다."""
    if not KAKAO_REST_API_KEY:
        raise RuntimeError("KAKAO_REST_API_KEY가 .env에 없습니다.")

    params = {
        "start_x": origin_lng,
        "start_y": origin_lat,
        "end_x": dest_lng,
        "end_y": dest_lat,
    }
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}

    resp = requests.get(BASE_URL, params=params, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"카카오 도보 경로 API 오류 ({resp.status_code}): {resp.text[:300]}")

    body = resp.json()
    if body.get("status") != "OK":
        raise RuntimeError(f"경로를 찾을 수 없습니다: {body.get('status')}")

    route = body["route"]
    path = []
    for leg in route.get("legs", []):
        for step in leg.get("steps", []):
            for x, y in step.get("path", {}).get("points", []):
                path.append({"lng": x, "lat": y})

    props = route.get("properties", {})
    return {
        "path": path,
        "distance_m": props.get("totalDistance"),
        "duration_sec": props.get("totalTime"),
    }
