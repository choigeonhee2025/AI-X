"""
카카오 로컬 API - 키워드로 장소 검색. 출발/도착 강의동을 직접 입력받을 때,
우리가 건물 좌표를 따로 들고 있지 않아도 카카오맵에 이미 등록된 건물을 검색해서
정확한 좌표를 바로 받아옵니다 (캠퍼스 반경 안으로 좁혀서 검색).

Base URL : https://dapi.kakao.com/v2/local/search/keyword.json
인증     : Authorization 헤더에 "KakaoAK {REST_API_KEY}"
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

BASE_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

# 캠퍼스 좌표 기준으로 검색 반경을 좁혀서, "공학관"처럼 흔한 이름을 검색해도
# 엉뚱한 지역의 동명 건물이 아니라 우리 학교 건물이 먼저 나오게 함.
CAMPUS_LAT = 37.2996
CAMPUS_LNG = 126.8350
SEARCH_RADIUS_M = 3000


def search_place(query: str, timeout: int = 10):
    if not KAKAO_REST_API_KEY:
        raise RuntimeError("KAKAO_REST_API_KEY가 .env에 없습니다.")

    params = {
        "query": query,
        "x": CAMPUS_LNG,
        "y": CAMPUS_LAT,
        "radius": SEARCH_RADIUS_M,
        "sort": "distance",
        "size": 8,
    }
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}

    resp = requests.get(BASE_URL, params=params, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"카카오 장소 검색 API 오류 ({resp.status_code}): {resp.text[:300]}")

    documents = resp.json().get("documents", [])
    return [
        {
            "name": d["place_name"],
            "address": d.get("road_address_name") or d.get("address_name"),
            "lat": float(d["y"]),
            "lng": float(d["x"]),
        }
        for d in documents
    ]
