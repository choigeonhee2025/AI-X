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

### 방법 B: 공공데이터 API (✅ 연동 성공, 수집 진행 중)

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

(참고: 소상공인시장진흥공단 상가정보 API(https://bigdata.sbiz.or.kr/#/notice/384818589907726336)는
아직 안 써봤지만, 업종 분류가 더 세분화되어 있어서 카테고리 보강용으로 나중에 볼 수도 있습니다.)

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
   사람은 누구나 남의 로그인 세션을 흉내낼 수 있어서 보안상 좋지 않습니다. (나중에 음식점
   API 키를 쓰게 되면 `DATA_GO_KR_API_KEY`도 여기에 같이 추가)

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
    speed_predictor.py        # 예측 함수 (3단계 개인화: 기본 ↔ 개인평균 ↔ 개인화모델)
    train_model.py            # DB의 trips로 회귀모델 학습 (member 원-핫 포함)
  services/
    restaurant_service.py     # 음식점 조회, 거리 계산 (DB 기반)
    restaurant_api.py         # 실제 공공데이터 API 연동 스텁 (TODO, 막혀있음)
    recommend.py              # 추천(여유시간 계산·필터링) 로직
  data/
    restaurants.json          # 더미 음식점 데이터 (수동 호출시에만 시드됨)
  .env                         # DATABASE_URL(Neon), SECRET_KEY, DATA_GO_KR_API_KEY (깃에 커밋 안 함)
  static/
    login.html, index.html, collect.html, restaurants.html, css/, js/
```
