"""
data.go.kr 행정안전부_식품_일반음식점 조회서비스 실제 연동. 2026-11-17에 실제 키로 호출해서
검증 완료했습니다.

Base URL : https://apis.data.go.kr/1741000/general_restaurants/info

중요한 점들 (실제로 호출해서 확인한 내용):
  - cond[OPN_ATMY_GRP_CD::EQ](개방자치단체코드)를 안 넣으면 전국 데이터를 한 번에 긁으려다
    서버가 응답 없이 멈춥니다(45초+). 반드시 시/군/구 단위 코드를 넣어야 합니다.
  - 안산시 전체 코드는 3930000 (상록구/단원구로 나뉘어 있지 않고 시 단위로 등록되어 있음).
    data.go.kr 공지사항에 첨부된 "개방자치단체코드_영업상태코드_..." 파일에서 확인했습니다.
  - 카테고리(한식/중식 등)는 BZSTAT_SE_NM 필드입니다. (SNTTN_BZSTAT_NM도 같은 값을 담고 있음)
  - 좌표(CRD_INFO_X, CRD_INFO_Y)는 위경도가 아니라 Bessel 중부원점 TM(EPSG:5174)입니다.
    pyproj로 EPSG:5174 -> EPSG:4326 변환 필요 (아래 _tm_to_wgs84).
  - 영업상태: SALS_STTS_CD "01" = "영업/정상". 폐업/휴업 등은 다른 코드.
  - 서버가 전반적으로 느립니다 (페이지당 10~20초, 가끔 더 걸리거나 타임아웃). 안산시만 해도
    전체 32,000여 건이라 전체를 다 받으려면 오래 걸립니다 — scripts/fetch_real_restaurants.py에서
    캠퍼스 반경 안에 있는 것만 걸러서 DB에 쌓습니다.
"""
import os
import time

import requests
from dotenv import load_dotenv

from kst import now_kst

load_dotenv()

DATA_GO_KR_API_KEY = os.getenv("DATA_GO_KR_API_KEY")
OPN_ATMY_GRP_CD = os.getenv("OPN_ATMY_GRP_CD")  # 안산시 = 3930000

BASE_URL = "https://apis.data.go.kr/1741000/general_restaurants/info"

ACTIVE_STATUS_CODE = "01"  # 영업/정상


def _tm_to_wgs84(x: float, y: float):
    from pyproj import Transformer

    transformer = Transformer.from_crs("EPSG:5174", "EPSG:4326", always_xy=True)
    lng, lat = transformer.transform(x, y)
    return lat, lng


def fetch_page(page_no: int, num_of_rows: int = 100, timeout: int = 40, retries: int = 3):
    """한 페이지(최대 100건) 가져오기. 느린 서버라 재시도를 넣었습니다."""
    if not DATA_GO_KR_API_KEY:
        raise RuntimeError("DATA_GO_KR_API_KEY가 .env에 없습니다.")
    if not OPN_ATMY_GRP_CD:
        raise RuntimeError("OPN_ATMY_GRP_CD가 .env에 없습니다 (안산시 = 3930000).")

    params = {
        "serviceKey": DATA_GO_KR_API_KEY,
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "returnType": "JSON",
        "cond[OPN_ATMY_GRP_CD::EQ]": OPN_ATMY_GRP_CD,
    }

    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=timeout)
            resp.raise_for_status()
            body = resp.json()["response"]["body"]
            return body.get("items", {}).get("item", []) or [], body.get("totalCount", 0)
        except (requests.RequestException, KeyError, ValueError) as e:
            last_err = e
            time.sleep(2)
    raise RuntimeError(f"{retries}번 재시도했지만 실패했습니다: {last_err}")


def normalize_item(item):
    """원본 item 하나를 우리 DB 스키마에 맞게 변환. 좌표 없거나 이상하면 None."""
    try:
        lat, lng = _tm_to_wgs84(float(item["CRD_INFO_X"]), float(item["CRD_INFO_Y"]))
    except (KeyError, ValueError, TypeError):
        return None

    return {
        "name": item.get("BPLC_NM") or "이름없음",
        "category": item.get("BZSTAT_SE_NM") or item.get("SNTTN_BZSTAT_NM") or "기타",
        "lat": lat,
        "lng": lng,
        "address": item.get("ROAD_NM_ADDR") or item.get("LOTNO_ADDR"),
        "source": "data.go.kr_general_restaurants",
        "fetched_at": now_kst().isoformat(),
        "is_active": item.get("SALS_STTS_CD") == ACTIVE_STATUS_CODE,
    }
