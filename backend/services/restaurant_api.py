"""
실제 음식점 공공데이터 연동용 스텁(TODO). 아직 API 키가 없으므로 지금은 호출하지 않습니다.
API 키를 발급받으면 이 파일을 완성해서 restaurant_service.load_restaurants()가
이 함수를 쓰도록 바꿔주세요.

키 발급 방법 (팀과제1에서 조사한 출처 기준):

1) 공공데이터포털 - 일반음식점 조회서비스
   https://www.data.go.kr/data/15154916/openapi.do
   - data.go.kr 회원가입 → 위 페이지에서 "활용신청" → 보통 자동승인
   - 마이페이지 > 데이터활용 > Open API > 인증키 발급현황에서 "일반 인증키(Decoding)" 확인
   - .env 파일에 DATA_GO_KR_API_KEY=발급받은키 로 저장 (커밋 금지)

2) 소상공인시장진흥공단 상가(상권)정보 API
   https://bigdata.sbiz.or.kr/#/notice/384818589907726336
   - 소상공인시장진흥공단 상권정보시스템 가입 후 오픈API 신청
   - 발급키를 .env에 SBIZ_API_KEY=발급받은키 로 저장

3) 식품안전나라 API (업소 상세정보 보강용)
   https://www.foodsafetykorea.go.kr/api/main.do
   - 회원가입 후 인증키 신청 → .env에 FOODSAFETY_API_KEY=발급받은키

주의: 실제 응답 스키마(필드명)는 신청 후 콘솔에서 테스트 호출을 한 번 해보고
아래 TODO 부분을 그 결과에 맞게 고쳐야 합니다. 지금 아래 함수는 호출 흐름의 뼈대만 잡아둔 것입니다.
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

DATA_GO_KR_API_KEY = os.getenv("DATA_GO_KR_API_KEY")


def fetch_restaurants_near(lat: float, lng: float, radius_m: int = 1000):
    """
    TODO: 일반음식점 조회서비스 실제 호출로 교체.
    현재는 키가 없으므로 예외를 던져 restaurant_service가 샘플 데이터를 계속 쓰게 합니다.
    """
    if not DATA_GO_KR_API_KEY:
        raise RuntimeError(
            "DATA_GO_KR_API_KEY가 설정되지 않았습니다. .env 파일을 만들고 키를 발급받아 넣어주세요. "
            "그 전까지는 data/restaurants.json 샘플 데이터를 사용합니다."
        )

    # TODO: 아래는 뼈대 예시입니다. 실제 요청 파라미터/엔드포인트는
    # data.go.kr 콘솔의 "요청변수" 문서를 그대로 보고 맞춰야 합니다.
    # endpoint = "https://openapi.data.go.kr/.../getRestaurantList"
    # params = {
    #     "serviceKey": DATA_GO_KR_API_KEY,
    #     "pageNo": 1,
    #     "numOfRows": 100,
    #     "type": "json",
    # }
    # resp = requests.get(endpoint, params=params, timeout=10)
    # resp.raise_for_status()
    # items = resp.json()["response"]["body"]["items"]
    # return [normalize(item) for item in items]
    raise NotImplementedError("콘솔에서 실제 응답을 확인한 뒤 이 함수를 완성해주세요.")
