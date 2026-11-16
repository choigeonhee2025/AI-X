# 공강 밥집 추천 (AI+X 팀과제, 팀 "아이들")

공강 시간 N분, 식사 시간, 먹고 싶은 음식을 입력하면, 왕복 이동 + 식사를 마치고 수업에 늦지 않게
복귀할 수 있는 음식점만 추려서 보여주는 웹 서비스입니다.

## ML 과제 정의 (5칸)

| 칸 | 내용 |
|---|---|
| 예측 대상 (y) | 편도 도보 이동 시간 (분) |
| 입력 특징 (X) | 직선거리(m), 시간대(hour), 요일(dow) |
| 예측 시점 | 학생이 출발 직전, 목적지(음식점)가 확정된 시점 |
| 과제 유형 | 회귀 |
| 평가 지표 | MAE(분). 베이스라인 = 고정 평균 보행속도(67m/분) 모델 |

추천 로직 자체(여유시간 계산·필터링)는 규칙 기반이고, **이동시간 예측 부분만 ML**로 대체하는 구조입니다.
실측 데이터가 쌓이기 전까지는 고정 속도 베이스라인으로 동작하고, `models/train_model.py`로 언제든
회귀 모델로 전환할 수 있습니다.

## 실행 방법

```bash
cd backend
pip install -r requirements.txt
python app.py
```

브라우저에서 http://localhost:5000 (추천 화면), http://localhost:5000/collect (이동시간 수집 화면)

## 지금 상태

- 데이터는 이제 `data/app.db` (SQLite)에 저장됩니다. 실행 시 테이블이 없으면 자동 생성되고,
  음식점 테이블은 `data/restaurants.json`(샘플/더미 데이터)으로 처음 한 번 시드됩니다.
- `trips` 테이블 : 팀원이 `/collect`에서 직접 측정한 이동시간 기록 (이름 태그 포함). 아직 비어 있음.
- 예측은 지금 고정 속도(67m/분) 베이스라인으로 동작 중입니다.

## 할 일 1 — 회원별로 실측 이동시간 데이터 모으기

1. 팀원들이 `/collect` 페이지를 각자 휴대폰 브라우저로 열고, 맨 위에서 **본인 이름을 선택**한 뒤
   캠퍼스에서 식당까지 실제로 걸으면서 "출발 기록" → 도착 시 "도착 기록"을 눌러주세요. (위치 권한 허용 필요)
   기록마다 이름이 `trips` 테이블에 같이 저장되어 누가 몇 건 모았는지 화면에서 바로 보입니다.
2. 각 팀원이 다른 요일·시간대에 여러 번 걸어서 최소 10건 이상 모으는 걸 목표로 하세요.
3. 5건 이상 모이면:
   ```bash
   cd backend
   python models/train_model.py
   ```
   MAE가 출력되고, 베이스라인보다 나아지면 `speed_model.pkl`이 저장되어 자동으로 적용됩니다.
   (지금은 회원 구분 없이 전체 데이터를 풀링해서 학습합니다. 나중에 인원이 늘면 `member`를
   특징으로 추가하는 것도 고려해보세요.)

## 할 일 2 — 실제 음식점 데이터로 교체하기

지금은 더미 데이터라 식당 이름이 전부 "테스트식당N"입니다. 팀과제1에서 조사한 공공데이터로 교체해야 합니다.

1. **공공데이터포털 – 일반음식점 조회서비스**: https://www.data.go.kr/data/15154916/openapi.do
   - data.go.kr 로그인 → 페이지 중간 "활용신청" → 활용목적 작성(예: "대학 수업 팀 프로젝트") → 상세기능 "조회" 체크 → 신청
   - 자동승인이라 바로 승인됨 → 마이페이지 > 데이터활용 > Open API > 활용신청현황에서 **일반 인증키(Decoding)** 확인
   - ⚠️ 이 API는 `개방자치단체코드`라는 필수 파라미터가 있습니다. 페이지의 "참고문서" xlsx를 받아서
     "안산시 상록구"를 검색해 코드를 찾아야 합니다.
   - ⚠️ 응답의 좌표(`CRD_INFO_X`, `CRD_INFO_Y`)는 위경도가 아니라 **Bessel 중부원점 TM(EPSG:5174)**
     좌표계입니다. `pyproj`로 EPSG:5174 → EPSG:4326(WGS84) 변환을 해야 우리 앱의 위경도 계산과 맞습니다.
   - 업소명(`BPLC_NM`), 주소(`ROAD_NM_ADDR`), 영업상태(`SALS_STTS_NM`/`SALS_STTS_CD`)는 필드가 확인됐지만,
     "한식/중식/분식" 같은 음식 카테고리 필드는 이 데이터셋에 명확히 없어 보입니다. 실제로 키 받아서
     한 번 호출해보고 어떤 필드가 카테고리에 해당하는지 직접 확인해야 합니다 (AI가 짐작한 필드명을
     그대로 믿지 말 것 — 수업 자료에서 강조한 바로 그 이유입니다).
2. **소상공인시장진흥공단 상가(상권)정보 API**: https://bigdata.sbiz.or.kr/#/notice/384818589907726336
   (업종 분류가 더 세분화되어 있어서 카테고리 정보는 이쪽이 나을 수도 있습니다)
3. 발급받은 키를 `backend/.env` 파일에 넣기 (절대 깃에 커밋하지 말 것):
   ```
   DATA_GO_KR_API_KEY=발급받은키
   SBIZ_API_KEY=발급받은키
   ```
4. `backend/services/restaurant_api.py`의 `fetch_restaurants_near()` 안에 있는 TODO를
   실제 응답 구조에 맞춰 채우고, 결과를 `db.replace_restaurants(...)`로 넣기.
   (키 받으면 저한테 알려주세요 — 같이 실제 호출해보고 필드 매핑 확정하겠습니다.)

## 웹에 바로 올리기 (Render, 무료)

GitHub 저장소가 필요합니다. 아래 순서대로 하면 `https://lunchbreak-recommender.onrender.com` 같은
주소로 팀원 누구나 바로 접속할 수 있습니다.

1. **GitHub에 올리기** (이 폴더에서, 터미널에 복사해서 실행):
   ```bash
   git init
   git add .
   git commit -m "공강 밥집 추천 초기 버전"
   ```
   그다음 https://github.com/new 에서 저장소를 하나 만들고(Public이어도 됨), 거기 나오는
   `git remote add origin ...`, `git push -u origin main` 명령어를 그대로 실행하세요.

2. **Render 가입/연결**: https://render.com 에서 "Get Started" → GitHub으로 로그인 → 방금 만든 저장소 Authorize.

3. **배포**: Render 대시보드에서 "New +" → "Blueprint" → 방금 연결한 저장소 선택.
   저장소 루트에 있는 `render.yaml`을 자동으로 읽어서 Build/Start 명령을 알아서 채워줍니다.
   "Apply" 누르면 몇 분 안에 `https://lunchbreak-recommender.onrender.com` 같은 주소가 생깁니다.
   (이름이 겹치면 Render가 자동으로 다른 이름을 붙여줘요.)

4. 이후 코드를 고치고 `git push`만 하면 Render가 자동으로 다시 배포합니다.

⚠️ 플랜 주의사항
- 유휴 상태에서 깨어나는 데 시간이 걸릴 수 있어요. 발표 직전엔 미리 한 번 접속해서 깨워두세요.
- **다시 배포(deploy)할 때마다 디스크가 초기화**돼서 `data/app.db`에 쌓인 실측 데이터가 날아갑니다.
  팀원들이 `/collect`로 모은 데이터는 주기적으로 받아서(Render Shell에서 DB 파일을 받거나,
  `python models/train_model.py`로 학습한 `speed_model.pkl`만이라도) 로컬 저장소에 커밋해두는 걸 추천합니다.
- $7/month Starter는 **매달 자동 청구되는 구독**입니다. 발표 끝나면 Render 대시보드에서 서비스를
  Delete 하는 걸 잊지 마세요.

## 폴더 구조

```
backend/
  app.py                     # Flask 서버, 라우트
  db.py                      # SQLite 저장소 (trips, restaurants 테이블)
  models/
    speed_predictor.py        # 예측 함수 (베이스라인 ↔ 학습모델 전환)
    train_model.py            # DB의 trips로 회귀모델 학습
  services/
    restaurant_service.py     # 음식점 조회, 거리 계산 (DB 기반)
    restaurant_api.py         # 실제 공공데이터 API 연동 스텁 (TODO)
    recommend.py              # 추천(여유시간 계산·필터링) 로직
  data/
    restaurants.json          # 샘플 음식점 시드 데이터 (더미, DB 초기화에만 쓰임)
    app.db                     # SQLite DB (trips, restaurants) — 실행하면 자동 생성
  static/
    index.html, collect.html, css/, js/
```
