# 공강 밥집 추천 (AI+X 팀과제, 팀 "아이들")

공강 시간 N분, 식사 시간, 먹고 싶은 음식을 입력하면, 왕복 이동 + 식사를 마치고 수업에 늦지 않게
복귀할 수 있는 음식점만 추려서 보여주는 웹 서비스입니다.

## ML 과제 정의 (5칸)

| 칸 | 내용 |
|---|---|
| 예측 대상 (y) | 편도 도보 이동 시간 (분) |
| 입력 특징 (X) | 직선거리(m), 시간대(hour), 요일(dow), **회원(member, 개인화)** |
| 예측 시점 | 학생이 출발 직전, 목적지(음식점)와 본인이 확정된 시점 |
| 과제 유형 | 회귀 |
| 평가 지표 | MAE(분). 베이스라인 = 고정 평균 보행속도(67m/분) 모델 |

추천 로직 자체(여유시간 계산·필터링)는 규칙 기반이고, **이동시간 예측 부분만 ML**로 대체하는 구조입니다.

### 개인화 3단계

데이터가 하나도 없는데 바로 "회원별 모델"을 학습하면 과적합되므로, 쌓인 데이터 양에 따라
자동으로 아래 3단계를 오갑니다 (`backend/models/speed_predictor.py`):

| 단계 | 조건 | 방법 |
|---|---|---|
| 0. 기본 | 아무 데이터 없음 | 전체 평균 속도 67m/분 고정값 |
| 1. 개인 평균 | 그 사람 기록 3건 이상 (전체 모델 학습 전) | 그 사람 자신의 평균 속도 |
| 2. 개인화 모델 | 전체 기록 5건 이상 | distance/hour/dow/**member**를 특징으로 쓰는 회귀모델 — 학습에 등장한 회원마다 다른 예측이 나옴 |

"회원"은 이제 고정된 4명이 아니라 **로그인한 사람**입니다. 로그인하면 세션에 이름이 저장되고,
추천·이동시간 기록 모두 그 이름 기준으로 자동 연결됩니다. 어떤 단계를 썼는지는 화면 하단에
표시됩니다. 실측 데이터는 `models/train_model.py`로 언제든 다시 학습시킬 수 있습니다.

### 로그인 (대충/간단 버전)

이름 + 비밀번호만 입력하면 됩니다 (`/login`). 처음 보는 이름이면 그 자리에서 바로 계정이
만들어지고, 있는 이름이면 로그인됩니다. `users` 테이블에 비밀번호는 해시로만 저장합니다
(`werkzeug.security`). 이메일 인증, 비밀번호 재설정 같은 건 없는 진짜 최소 버전이고,
CSRF 방어 등도 생략했습니다 — 팀 프로젝트 MVP 용도로만 쓰세요.

로그인 안 하면 `/`, `/collect` 모두 `/login`으로 튕깁니다.
세션 서명에 쓰는 `SECRET_KEY`는 `.env`에 있고, Render에도 같은 값을 환경변수로 등록해야
배포된 서비스에서도 로그인이 정상 동작합니다.

## ML 과제 정의 2 — 음식점 예상 대기시간 (팀원 제공 가상 데이터 기반)

| 칸 | 내용 |
|---|---|
| 예측 대상 (y) | 음식점 예상 대기시간 (분) |
| 입력 특징 (X) | 음식점, 요일(dow), 분단위 시각(minute_of_day) |
| 예측 시점 | 추천 계산 시점(지금 요일·시각 기준) |
| 과제 유형 | 회귀 |
| 평가 지표 | MAE(분). 베이스라인 = 전체 평균(global mean) 고정값 |

팀원이 토스페이먼츠 등 실제 결제 데이터 접근 권한이 없어서 만든 **가상 시뮬레이션
데이터**(42개 음식점 × 7일 × 1분 간격, 대학가 이용 패턴 반영)로 `backend/models/train_wait_model.py`가
RandomForest 회귀 모델을 학습합니다. 테스트 결과:

| 모델 | 구간 | MAE | R² |
|---|---|---|---|
| 베이스라인(전체 평균) | 전체 영업시간 | 1.66분 | -0.00 |
| 베이스라인(전체 평균) | 점심(12~13시) | 5.70분 | -1.87 |
| **RandomForest** | 전체 영업시간 | **0.27분** | **0.94** |
| **RandomForest** | 점심(12~13시) | **1.09분** | **0.88** |

(처음엔 팀원 노트북처럼 날짜로 통째로 분할했는데, 데이터가 딱 1주일이라 학습=평일,
테스트=주말로 쪼개져서 모델이 주말을 한 번도 못 보고 베이스라인보다 나쁘게 나왔습니다.
하루 안에서 분 단위로 60/20/20 섞어 모든 요일이 세 분할에 고르게 들어가도록 고쳤습니다.)

음식점 이름은 팀원이 직접 조사한 것이라 data.go.kr 상호명과 표기가 다른 경우가 많아서
(지점 표기 차이, 구내식당류는 애초에 일반음식점으로 등록돼 있지 않음), **이름이 확실하게
일치하는 것만** 골라 씁니다 — 42개 중 15개만 매칭됨.

추천 계산(`services/recommend.py`)에서 매칭된 음식점은 왕복 이동시간 + 식사시간에 예상
대기시간까지 더해서 "진짜 다녀올 수 있는지" 판단하고, 화면에 혼잡도 배지로 보여줍니다
(`backend/models/wait_predictor.py`, 3단계 구조는 이동시간 예측과 동일한 패턴):

| 단계 | 조건 | 방법 |
|---|---|---|
| 0. 기본 | 음식점 이름이 매칭 안 됨 | 대기시간 0 |
| 1. 평균 | 매칭은 됐는데 학습된 모델이 없음 | 요일×시간대 평균(`congestion_stats` 테이블) |
| 2. 모델 | 학습된 모델 있음 | 위 RandomForest 회귀 예측 (더 정밀함, 분 단위) |

팀원이 같이 보내준 `straight_distance_to_conference_hall_m`(특정 건물까지 직선거리) 컬럼은
안 썼습니다 — 우리는 이미 사용자의 실제 현재 위치 기준으로 매번 직접 거리를 계산하고 있어서,
고정된 기준점 거리를 쓰는 게 오히려 덜 정확하기 때문입니다.

다시 학습시키려면 (backend/ 에서):
```bash
python models/train_wait_model.py "<원본 CSV 경로>"
```

## 실행 방법

PostgreSQL 연결 문자열이 먼저 있어야 합니다 (바로 아래 "할 일 0" 참고).

```bash
cd backend
pip install -r requirements.txt
python app.py
```

브라우저에서 http://localhost:5000 (추천 화면), http://localhost:5000/collect (이동시간 수집 화면)

## 할 일 0 — PostgreSQL 연결하기

SQLite에서 **PostgreSQL**로 옮겼습니다.

**로컬 개발 (이 컴퓨터는 설정 완료)**: 이 컴퓨터엔 이미 PostgreSQL 18이 서비스로 설치되어 있어서,
그걸 그대로 씁니다. `ai_x_lunchbreak`라는 DB를 만들어뒀고, `backend/.env`에
```
DATABASE_URL=postgresql://postgres:1234@localhost:5432/ai_x_lunchbreak
```
가 이미 들어가 있습니다. `python app.py`만 하면 바로 됩니다. (다른 팀원 컴퓨터에서 실행하려면
그 컴퓨터에 Postgres가 없을 테니, 아래 Render 배포용 DB를 로컬에서도 같이 쓰는 게 더 간단합니다.)

**Render 배포용**: ✅ 완료. Neon(neon.tech) 무료 프로젝트 만들어서 Render 서비스 Environment에
`DATABASE_URL`로 등록해뒀습니다. 로컬 `.env`의 `DATABASE_URL`은 로컬 DB를 가리키고,
Render 쪽은 Neon 주소를 써서 서로 분리되어 있습니다. 배포 주소: https://ai-x-9gx2.onrender.com

(Render 자체 Postgres는 무료 플랜이 없어져서 월 요금이 또 붙습니다. Neon 무료 티어로 충분합니다.)

## 지금 상태

- 데이터는 **PostgreSQL**(`backend/db.py`, `DATABASE_URL` 환경변수로 접속)에 저장됩니다.
  실행 시 테이블(`trips`, `restaurants`, `users`)이 없으면 자동 생성됩니다.
- **음식점 테이블은 이제 비어있는 채로 시작**합니다 (더미 자동 시드 제거함 — 아래 "할 일 2" 참고).
  더미가 필요하면 `python -c "import db; db.seed_dummy_restaurants()"`로 수동으로만 넣을 수 있습니다.
- `trips` 테이블 : 로그인한 사람이 `/collect`에서 직접 측정한 이동시간 기록. 아직 비어 있음.
- 예측은 지금 고정 속도(67m/분) 베이스라인으로 동작 중입니다.
- 음식점 공공데이터 API 연동 성공. 지금 `backend/scripts/fetch_real_restaurants.py`로 안산시
  전체(32,761건) 중 캠퍼스 반경 안의 영업중인 곳만 걸러서 수집 중입니다 (서버가 느려서 시간이
  걸림 — 중간에 멈춰도 그때까지 모은 587건+ 데이터는 DB에 남아있음). 자세한 내용은 "할 일 2" 참고.
  `/restaurants` 페이지에서 수동으로 실제 음식점을 추가/삭제할 수도 있습니다.

## 할 일 1 — 실측 이동시간 데이터 모으기

1. 팀원들이 로그인한 뒤 `/collect` 페이지를 각자 휴대폰 브라우저로 열고,
   캠퍼스에서 식당까지 실제로 걸으면서 "출발 기록" → 도착 시 "도착 기록"을 눌러주세요.
   (위치 권한 허용 필요) 로그인한 이름이 자동으로 기록에 같이 저장됩니다.
2. 각 팀원이 다른 요일·시간대에 여러 번 걸어서 최소 10건 이상 모으는 걸 목표로 하세요.
3. 5건 이상 모이면:
   ```bash
   cd backend
   python models/train_model.py
   ```
   MAE가 출력되고, 베이스라인보다 나아지면 `speed_model.pkl`이 저장되어 자동으로 적용됩니다.
   사람(`member`)을 특징으로 포함해서 학습하므로, 사람마다 다른 예측이 나옵니다
   (자세한 내용은 위 "개인화 3단계" 참고).

## 할 일 2 — 실제 음식점 데이터 넣기

### 방법 A: 직접 입력 (지금 바로 가능, ✅ 구현 완료)

로그인한 뒤 `/restaurants` 페이지에서:
1. 이름, 카테고리(목록에 없으면 직접 입력), 주소(선택) 입력
2. 그 식당에 있는 상태라면 **"지금 내 위치 사용"**을 눌러 정확한 좌표를 바로 채우기
   (아니면 지도 앱에서 좌표 확인 후 직접 입력해도 됨)
3. "더미 데이터 한번에 삭제" 버튼으로 남은 샘플 데이터 정리

팀원들이 평소 다니는 진짜 식당을 하나씩 추가하면 됩니다. 누가 추가했는지는
`source` 필드에 `manual:이름`으로 남습니다.

### 방법 B: 공공데이터 API (✅ 연동 성공, 전체 수집 완료)

**행정안전부_식품_일반음식점 조회서비스** (https://www.data.go.kr/data/15154916/openapi.do) 실제로
연동해서 진짜 데이터 받아오는 거 확인했습니다. 알아낸 것들:

- Base URL: `https://apis.data.go.kr/1741000/general_restaurants/info`
- **개방자치단체코드(`OPN_ATMY_GRP_CD`)가 없으면 전국 데이터를 긁으려다 서버가 응답 없이 멈춥니다**
  (처음에 "API가 막혔다"고 생각했던 게 사실 이거였음). 안산시 전체 코드는 `3930000`
  (상록구/단원구 구분 없이 시 단위로 등록되어 있음) — data.go.kr 공지사항 첨부파일에서 확인.
- 카테고리(한식/중식 등)는 `BZSTAT_SE_NM` 필드.
- 좌표(`CRD_INFO_X`, `CRD_INFO_Y`)는 위경도가 아니라 **Bessel 중부원점 TM(EPSG:5174)** —
  `pyproj`로 변환 (`services/restaurant_api.py`에 구현됨, 실제 주소와 대조해서 검증함).
- 영업상태 `SALS_STTS_CD == "01"`이 "영업/정상".
- ⚠️ **서버가 많이 느립니다** (100건 요청에 10~50초, 가끔 더 걸림). 안산시 전체가
  32,761건이라 캠퍼스 반경 안의 것만 거르려면 전체를 다 훑어야 하는데, 다 받으려면 1~2시간+ 걸립니다.

**수집 스크립트**: `backend/scripts/fetch_real_restaurants.py`
```bash
cd backend
python -u scripts/fetch_real_restaurants.py
```
캠퍼스 좌표 기준 반경(`RADIUS_M`, 기본 3000m) 안에서 영업 중인 곳만 걸러서 페이지 단위로 바로
DB에 저장합니다 (중간에 멈춰도 그때까지 모은 건 안 날아감). 컴퓨터를 꺼야 하면 중단했다가
나중에 다시 켜고 그대로 재실행하면 됩니다 (처음부터 다시 받습니다 — 이어받기는 아직 없음).

2026-11-24에 전체 328페이지(32,776건) 다 돌려서 캠퍼스 반경 3km 안 영업중 음식점
**3,647건**을 로컬 DB에 모았고, `backend/scripts/sync_to_neon.py`로 Neon(배포용 DB)에도
그대로 복사해서 실제 사이트에도 반영했습니다.

(참고: 소상공인시장진흥공단 상가정보 API(https://bigdata.sbiz.or.kr/#/notice/384818589907726336)는
아직 안 써봤지만, 업종 분류가 더 세분화되어 있어서 카테고리 보강용으로 나중에 볼 수도 있습니다.)

### 음식점 혼잡도 / 예상 대기시간 (팀원 제공 가상 데이터)

자세한 내용은 위 "ML 과제 정의 2" 참고. 요약 평균 테이블(`congestion_stats`, 모델이 없을 때의
1단계 fallback)을 다시 만들거나 DB에 반영하려면 (backend/ 에서):
```bash
python scripts/build_congestion_stats.py "<원본 CSV 경로>"   # -> backend/data/congestion_stats.csv
python scripts/seed_congestion_stats.py                      # DATABASE_URL이 가리키는 DB에 저장
```
회귀 모델(2단계, 실제로 쓰이는 쪽)을 다시 학습시키려면:
```bash
python models/train_wait_model.py "<원본 CSV 경로>"          # -> backend/models/wait_model.pkl
```

## 지도에서 경로 보기 (카카오맵)

추천 결과 카드의 "🗺 지도 보기"를 누르면 모달로 지도가 뜨고, 내 위치 → 그 음식점까지
실제 도보 경로(길을 따라가는 선)와 거리·예상 시간을 보여줍니다.

- **지도 표시**: 카카오맵 JavaScript SDK (`backend/static/js/map.js`). JS 키는 도메인 제한이
  걸리는 키라 그대로 프론트에 노출돼도 되는데, `.env`에서 관리하다가 `/api/config`로
  내려주는 방식을 썼습니다 (정적 파일에 키를 하드코딩 안 해도 되게).
- **도보 경로 계산**: 카카오맵 Open API `GET https://dapi.kakao.com/v2/routing/walk`
  (`backend/services/kakao_directions.py`, REST 키 필요 - 서버에서만 호출, `/api/directions`로
  프록시). 하루 1,000건 무료, 초과하면 건당 10원.
  - ⚠️ 처음엔 카카오모빌리티의 "제휴" 길찾기 API(`apis-navi.kakaomobility.com/affiliate/...`)로
    시도했다가 `403 permission denied`를 받았습니다 — 그건 별도 제휴 신청이 필요한 구버전
    API였고, 2026-07-21에 새로 열린 "카카오맵 Open API"(`dapi.kakao.com/v2/routing/walk`)가
    맞는 주소였습니다. 헷갈리기 쉬운 부분이라 남겨둡니다.
  - 카카오 디벨로퍼스 콘솔에서 해당 앱의 "카카오맵" 제품을 활성화하고, Web 플랫폼에
    로컬(`http://localhost:5000`)/배포 도메인을 등록해야 동작합니다.
- **카카오내비처럼 따라가기**: 지도를 띄운 동안 `navigator.geolocation.watchPosition`으로
  내 위치를 계속 받아서 마커를 움직이고 지도를 따라 이동시킵니다(`panTo`). 경로선은 매번
  다시 계산하지 않고(API 할당량 아끼려고) 처음 받은 경로를 그대로 두고, 목적지까지 남은
  직선거리만 실시간으로 갱신해서 보여줍니다. 20m 이내로 가까워지면 "도착!" 표시.

## 카테고리 정리 / 랜덤 추천 / 즐겨찾기

- **카테고리 통합** (`backend/services/category_map.py`): data.go.kr 원본 카테고리가 28개로
  너무 잘게 쪼개져 있어서(예: "중식"/"중국식"이 완전히 같은 말, "통닭(치킨)"/"호프/통닭"이
  겹침) 한식/중식/일식/양식/분식/카페/치킨/술집/뷔페/패스트푸드/아시안/기타 12개로 묶었습니다.
  DB에 저장된 원본 category 값은 안 건드리고(카드에 마우스 올리면 원본 이름이 툴팁으로 보임),
  필터링·알약 표시할 때만 매핑을 거칩니다 - 나중에 그룹 기준을 바꿔도 데이터를 다시 받을
  필요가 없습니다.
- **🎲 랜덤 추천**: 추천 결과 중 조건을 만족하는(feasible) 곳 중 하나를 무작위로 골라서
  스크롤·하이라이트해줍니다. "⭐ 즐겨찾기만" 필터가 켜져 있으면 그 안에서만 고릅니다.
- **⭐ 즐겨찾기**: 카드마다 별 버튼으로 즐겨찾기 등록/해제 (`favorites` 테이블, 로그인한
  회원별로 따로 저장). "⭐ 즐겨찾기만" 버튼으로 지금 띄운 결과 중 즐겨찾기한 것만 걸러봅니다.

## 🚩 신고 기능 + /admin 관리 페이지

카드마다 깃발(🚩) 버튼으로 "카테고리 틀림/위치 틀림/폐업/중복/기타" 중 골라서 신고할 수
있고(`reports` 테이블), 관리자는 `/admin`에서 열린 신고를 보고 음식점 이름/카테고리/주소/
좌표를 바로 고친 뒤 해결됨/기각 처리할 수 있습니다.

- 관리자 판정은 역할 테이블 없이 간단하게 `.env`의 `ADMIN_USERNAMES`(쉼표로 여러 명 가능)에
  있는 로그인 이름인지로만 확인합니다. 그 이름으로 로그인(처음이면 자동 가입)하면 `/admin`
  접근 가능.
- 로컬 `.env`와 Render 환경변수에 `ADMIN_USERNAMES=관리자로_쓸_로그인이름` 추가해두시면,
  그 이름으로 로그인했을 때(처음 로그인하면 그 자리에서 계정이 만들어짐) 관리자 페이지에
  들어갈 수 있어요. 비밀번호는 다른 계정과 마찬가지로 처음 로그인할 때 직접 정하는 것이고
  README에 적어두지 않습니다.

## 웹에 바로 올리기 (Render)

GitHub 저장소가 필요합니다. 아래 순서대로 하면 `https://lunchbreak-recommender.onrender.com` 같은
주소로 팀원 누구나 바로 접속할 수 있습니다.

1. **GitHub에 올리기** (이 폴더에서, 터미널에 복사해서 실행):
   ```bash
   git add .
   git commit -m "업데이트"
   git push
   ```
   (처음이면 https://github.com/new 에서 저장소를 만들고 `git remote add origin ...`,
   `git push -u origin main`부터 하세요.)

2. **Render 가입/연결**: https://render.com 에서 "Get Started" → GitHub으로 로그인 → 방금 만든 저장소 Authorize.

3. **배포**: Render 대시보드에서 "New +" → "Blueprint" → 방금 연결한 저장소 선택.
   저장소 루트에 있는 `render.yaml`을 자동으로 읽어서 Build/Start 명령을 알아서 채워줍니다.
   "Apply" 누르면 몇 분 안에 `https://lunchbreak-recommender.onrender.com` 같은 주소가 생깁니다.

4. **환경변수 추가 (중요)**: Render 대시보드 > 해당 서비스 > **Environment** 탭에서
   `DATABASE_URL`을 Neon에서 복사한 연결 문자열 그대로 추가해주세요. 이게 없으면 배포된
   서비스는 DB에 못 붙어서 에러가 납니다. **`SECRET_KEY`도 꼭 추가**하세요 (로컬 `.env`에 있는
   값 그대로 복사). 안 넣으면 코드에 박혀있는 고정 기본값을 쓰게 되는데, 그러면 그 값을 아는
   사람은 누구나 남의 로그인 세션을 흉내낼 수 있어서 보안상 좋지 않습니다. `DATA_GO_KR_API_KEY`,
   `KAKAO_JS_KEY`, `KAKAO_REST_API_KEY`도 로컬 `.env`에 있는 값 그대로 똑같이 추가하세요.
   카카오 디벨로퍼스 콘솔의 해당 앱 > 플랫폼 설정 > Web 플랫폼 사이트 도메인에도 배포 주소
   (`https://ai-x-9gx2.onrender.com`)를 등록해둬야 배포된 사이트에서 지도가 뜹니다.

5. 이후 코드를 고치고 `git push`만 하면 Render가 자동으로 다시 배포합니다.

✅ Postgres(Neon)로 옮긴 덕분에, **Render가 재배포돼도 데이터는 안 날아갑니다** (DB가 Render
밖의 Neon에 있어서). 예전 SQLite 때 있던 "재배포하면 초기화" 문제는 해결됐어요.

⚠️ 플랜 주의사항
- 유휴 상태에서 깨어나는 데 시간이 걸릴 수 있어요. 발표 직전엔 미리 한 번 접속해서 깨워두세요.
- $7/month Starter는 **매달 자동 청구되는 구독**입니다. 발표 끝나면 Render 대시보드에서 서비스를
  Delete 하는 걸 잊지 마세요. (Neon 무료 티어는 그대로 둬도 과금 없음)

## 폴더 구조

```
backend/
  app.py                     # Flask 서버, 라우트, 로그인 미들웨어
  db.py                      # PostgreSQL 저장소 (trips, restaurants, users 테이블)
  models/
    speed_predictor.py        # 이동시간 예측 (3단계: 기본 ↔ 개인평균 ↔ 개인화모델)
    train_model.py            # DB의 trips로 이동시간 회귀모델 학습 (member 원-핫 포함)
    wait_predictor.py         # 대기시간 예측 (3단계: 0 ↔ 요일x시간대 평균 ↔ 학습모델)
    train_wait_model.py       # 팀원 CSV로 대기시간 회귀모델 학습 (wait_model.pkl 생성)
  scripts/
    fetch_real_restaurants.py     # data.go.kr API로 실제 음식점 수집
    sync_to_neon.py               # 로컬 DB의 실제 음식점 데이터를 Neon으로 복사
    build_congestion_stats.py     # 팀원 CSV -> 요일x시간대 평균 요약(congestion_stats.csv)
    seed_congestion_stats.py      # 그 요약을 DB congestion_stats 테이블에 저장
  services/
    restaurant_service.py     # 음식점 조회, 거리 계산 (DB 기반)
    restaurant_api.py         # data.go.kr 공공데이터 API 실제 연동 (검증 완료)
    recommend.py              # 추천(여유시간 계산·필터링) 로직
    kakao_directions.py       # 카카오맵 도보 경로 API 연동 (REST 키, 서버에서만 호출)
  data/
    restaurants.json          # 더미 음식점 데이터 (수동 호출시에만 시드됨)
    congestion_stats.csv      # 팀원 CSV 요약본 (요일x시간대별 평균 혼잡도/대기시간)
  .env                         # DATABASE_URL(Neon), SECRET_KEY, DATA_GO_KR_API_KEY,
                                # KAKAO_JS_KEY, KAKAO_REST_API_KEY (깃에 커밋 안 함)
  static/
    login.html, index.html, collect.html, restaurants.html, css/
    js/main.js, js/map.js(지도/경로 모달), ...
```
