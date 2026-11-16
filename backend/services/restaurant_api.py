"""
실제 음식점 공공데이터 연동용. 아직 API 키가 없으므로 지금은 호출하지 않습니다.
키를 발급받으면 이 파일을 완성해서 db.replace_restaurants(fetch_restaurants_near(...))처럼 쓰면 됩니다.

[행정안전부_식품_일반음식점 조회서비스] (data.go.kr/data/15154916/openapi.do) 실제 문서 확인 결과:

Base URL : https://apis.data.go.kr/1741000/general_restaurants
Endpoint : GET /info

필수 파라미터:
  serviceKey                      - 발급받은 인증키 (Decoding 키 사용)
  pageNo, numOfRows (최대 100)
  returnType                      - "JSON" 권장
  cond[OPN_ATMY_GRP_CD::EQ]       - 개방자치단체코드. data.go.kr 페이지의 "참고문서" xlsx에서
                                     "안산시 상록구"를 찾아 코드를 넣어야 함 (TODO: 직접 확인)

선택 파라미터(필터링에 유용):
  cond[SALS_STTS_CD::EQ]          - 영업상태코드. "영업중"만 보려면 이 값을 써야 하는데,
                                     정확한 코드값(예: "01")은 실제 호출해서 SALS_STTS_NM과
                                     대조해 확인 필요 (TODO)
  cond[BPLC_NM::LIKE]             - 상호명에 특정 글자가 포함된 곳만 조회

응답 item의 주요 필드 (Swagger 예시에서 확인됨):
  BPLC_NM         업소명(상호명)
  ROAD_NM_ADDR    도로명주소
  LOTNO_ADDR      지번주소
  SALS_STTS_NM    영업상태명 (예: "영업/정상")
  SALS_STTS_CD    영업상태코드
  CRD_INFO_X      좌표 X  ⚠️ 위경도 아님! Bessel 중부원점 TM(EPSG:5174)
  CRD_INFO_Y      좌표 Y  ⚠️ 위경도 아님! Bessel 중부원점 TM(EPSG:5174)
  TELNO           전화번호
  LCPMT_YMD       인허가일자

⚠️ 아직 확인 못 한 것 (키 받으면 실제로 호출해서 직접 확인해야 함):
  - "한식/중식/분식" 같은 음식 카테고리에 대응하는 필드가 Swagger 예시엔 안 보입니다.
    BZSTAT_SE_NM, DTL_SALS_STTS_NM 등 후보가 있지만 실제 값을 찍어보기 전엔 확신할 수 없습니다.
  - cond[SALS_STTS_CD::EQ]에 넣을 정확한 코드값
  - cond[OPN_ATMY_GRP_CD::EQ]에 넣을 "안산시 상록구" 코드값

좌표 변환에는 pyproj가 필요합니다: pip install pyproj (requirements.txt에 추가 필요)
"""
import datetime
import os

import requests
from dotenv import load_dotenv

load_dotenv()

DATA_GO_KR_API_KEY = os.getenv("DATA_GO_KR_API_KEY")
ANSAN_SANGNOK_GU_CODE = os.getenv("OPN_ATMY_GRP_CD")  # TODO: 참고문서 xlsx에서 찾아 .env에 넣기

BASE_URL = "https://apis.data.go.kr/1741000/general_restaurants/info"


def _bessel_tm_to_wgs84(x: float, y: float):
    """EPSG:5174(Bessel 중부원점 TM) -> EPSG:4326(WGS84 위경도) 변환."""
    from pyproj import Transformer

    transformer = Transformer.from_crs("EPSG:5174", "EPSG:4326", always_xy=True)
    lng, lat = transformer.transform(x, y)
    return lat, lng


def fetch_restaurants_near(page_no: int = 1, num_of_rows: int = 100):
    """
    TODO: 실제 호출 후 아래를 다듬어야 합니다. 지금은 키/지역코드가 없으면 예외를 던져서
    restaurant_service가 기존 DB(더미 시드) 데이터를 계속 쓰게 합니다.
    """
    if not DATA_GO_KR_API_KEY:
        raise RuntimeError("DATA_GO_KR_API_KEY가 .env에 없습니다. README '할 일 2' 참고.")
    if not ANSAN_SANGNOK_GU_CODE:
        raise RuntimeError("OPN_ATMY_GRP_CD(개방자치단체코드)가 .env에 없습니다. 참고문서 xlsx에서 찾아주세요.")

    params = {
        "serviceKey": DATA_GO_KR_API_KEY,
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "returnType": "JSON",
        "cond[OPN_ATMY_GRP_CD::EQ]": ANSAN_SANGNOK_GU_CODE,
    }
    resp = requests.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    body = resp.json()["response"]["body"]
    items = body.get("items", {}).get("item", [])

    results = []
    now = datetime.datetime.now().isoformat()
    for item in items:
        try:
            lat, lng = _bessel_tm_to_wgs84(float(item["CRD_INFO_X"]), float(item["CRD_INFO_Y"]))
        except (KeyError, ValueError, TypeError):
            continue  # 좌표 없는 업소는 추천에 못 쓰므로 제외

        results.append(
            {
                "name": item.get("BPLC_NM", "이름없음"),
                # TODO: 실제 카테고리 필드로 교체. 확인 전까지는 전부 "미분류"로 둡니다.
                "category": "미분류",
                "lat": lat,
                "lng": lng,
                "address": item.get("ROAD_NM_ADDR") or item.get("LOTNO_ADDR"),
                "source": "data.go.kr_general_restaurants",
                "fetched_at": now,
            }
        )
    return results
