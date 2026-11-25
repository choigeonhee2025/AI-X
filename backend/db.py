"""
PostgreSQL 기반 데이터 저장소 (psycopg2). DATABASE_URL 환경변수로 접속합니다.
(이전에는 SQLite였는데, 팀 요청으로 PostgreSQL로 전환)

trips  : 팀원이 /collect에서 직접 측정한 이동시간 기록 (회원 이름 태그 포함)
restaurants : 추천에 쓰는 음식점 목록 (지금은 더미 시드, 추후 공공데이터 API로 교체)
"""
import datetime
import json
import os

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_RESTAURANTS_PATH = os.path.join(BASE_DIR, "data", "restaurants.json")

DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL이 설정되지 않았습니다. backend/.env에 Postgres 연결 문자열을 넣어주세요. "
            "README '할 일 3 — PostgreSQL 연결하기' 참고."
        )
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS trips (
            id SERIAL PRIMARY KEY,
            member TEXT NOT NULL,
            distance_m REAL NOT NULL,
            duration_min REAL NOT NULL,
            hour INTEGER NOT NULL,
            dow INTEGER NOT NULL,
            recorded_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS restaurants (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            address TEXT,
            source TEXT NOT NULL,
            fetched_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS congestion_stats (
            id SERIAL PRIMARY KEY,
            restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
            dow INTEGER NOT NULL,
            hour INTEGER NOT NULL,
            avg_congestion_pct REAL NOT NULL,
            avg_wait_min REAL NOT NULL,
            UNIQUE (restaurant_id, dow, hour)
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_congestion_stats_dow_hour ON congestion_stats (dow, hour)"
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS favorites (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            UNIQUE (username, restaurant_id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
            reporter TEXT NOT NULL,
            reason TEXT NOT NULL,
            detail TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS recommend_logs (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            category TEXT NOT NULL,
            feasible_count INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    cur.close()
    conn.close()


def seed_dummy_restaurants():
    """
    테스트용 더미 음식점을 수동으로 채워 넣고 싶을 때만 호출하세요.
    (init_db()에서는 더 이상 자동으로 부르지 않습니다 — 실제 음식점을
    /restaurants 페이지에서 입력하면 더미가 다시 살아나지 않도록 하기 위해서입니다.)
    """
    if not os.path.exists(SEED_RESTAURANTS_PATH):
        return
    conn = get_conn()
    cur = conn.cursor()
    with open(SEED_RESTAURANTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    now = datetime.datetime.now().isoformat()
    rows = [
        (r["name"], r["category"], r["lat"], r["lng"], r.get("address"), r.get("source", "dummy_sample"), now)
        for r in data["restaurants"]
    ]
    cur.executemany(
        "INSERT INTO restaurants (name, category, lat, lng, address, source, fetched_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        rows,
    )
    conn.commit()
    cur.close()
    conn.close()


# ---------- trips ----------

def add_trip(member, distance_m, duration_min, hour, dow, recorded_at):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO trips (member, distance_m, duration_min, hour, dow, recorded_at) VALUES (%s, %s, %s, %s, %s, %s)",
        (member, distance_m, duration_min, hour, dow, recorded_at),
    )
    conn.commit()
    cur.close()
    conn.close()


def trip_count():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM trips")
    n = cur.fetchone()["n"]
    cur.close()
    conn.close()
    return n


def list_trips(limit=50):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM trips ORDER BY id DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def get_training_rows():
    """회귀 모델 학습용 원본 행. member를 개인화 특징으로 쓰기 위해 같이 반환합니다."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT member, distance_m, hour, dow, duration_min FROM trips")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def trips_per_member():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT member, COUNT(*) as n FROM trips GROUP BY member")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {r["member"]: r["n"] for r in rows}


def get_member_average_speed_m_per_min(member, min_trips=3):
    """
    개인화 1단계: 그 사람 본인 기록만으로 평균 보행속도(m/분)를 계산합니다.
    기록이 min_trips건 미만이면 아직 믿을 수 없다고 보고 None을 돌려줍니다
    (그러면 전체 평균 베이스라인을 씁니다).
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT distance_m, duration_min FROM trips WHERE member = %s", (member,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if len(rows) < min_trips:
        return None
    speeds = [r["distance_m"] / r["duration_min"] for r in rows if r["duration_min"] > 0]
    if not speeds:
        return None
    return sum(speeds) / len(speeds)


# ---------- restaurants ----------

def list_restaurants(category=None):
    conn = get_conn()
    cur = conn.cursor()
    if category and category != "전체":
        cur.execute("SELECT * FROM restaurants WHERE category = %s", (category,))
    else:
        cur.execute("SELECT * FROM restaurants")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def search_restaurants(query, limit=20):
    """관리자 페이지용. 음식점이 3천 개가 넘어서 전체를 다 내려줄 수 없으니,
    이름으로 검색한 일부만 돌려줍니다."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM restaurants WHERE name ILIKE %s ORDER BY name LIMIT %s",
        (f"%{query}%", limit),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def list_manual_restaurants():
    """관리자 페이지 기본 목록용. 자동 수집된 3천 개가 넘는 데이터 말고(그건 🚩 신고로
    고침), 직접 추가한 것/더미만 보여줌."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM restaurants WHERE source = 'dummy_sample' OR source LIKE 'manual:%' ORDER BY id DESC"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def list_categories():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM restaurants ORDER BY category")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r["category"] for r in rows]


def restaurant_count():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM restaurants")
    n = cur.fetchone()["n"]
    cur.close()
    conn.close()
    return n


def replace_restaurants(restaurants):
    """공공데이터 API 연동 후 호출할 함수. 각 dict에 name/category/lat/lng/address/source/fetched_at 필요."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM restaurants")
    cur.executemany(
        "INSERT INTO restaurants (name, category, lat, lng, address, source, fetched_at) "
        "VALUES (%(name)s, %(category)s, %(lat)s, %(lng)s, %(address)s, %(source)s, %(fetched_at)s)",
        restaurants,
    )
    conn.commit()
    cur.close()
    conn.close()


def insert_restaurants_batch(restaurants):
    """replace_restaurants와 달리 기존 데이터를 지우지 않고 그대로 추가합니다.
    오래 걸리는 API 수집을 페이지 단위로 중간 저장할 때 씁니다."""
    if not restaurants:
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO restaurants (name, category, lat, lng, address, source, fetched_at) "
        "VALUES (%(name)s, %(category)s, %(lat)s, %(lng)s, %(address)s, %(source)s, %(fetched_at)s)",
        restaurants,
    )
    conn.commit()
    cur.close()
    conn.close()


def add_restaurant(name, category, lat, lng, address, added_by):
    """팀원이 직접 입력하는 실제 음식점 1곳 추가."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO restaurants (name, category, lat, lng, address, source, fetched_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (name, category, lat, lng, address, f"manual:{added_by}", datetime.datetime.now().isoformat()),
    )
    new_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return new_id


def delete_restaurant(restaurant_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM restaurants WHERE id = %s", (restaurant_id,))
    conn.commit()
    cur.close()
    conn.close()


def delete_dummy_restaurants():
    """source가 'dummy_sample'인 샘플 데이터를 한 번에 정리할 때 씁니다."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM restaurants WHERE source = 'dummy_sample'")
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return deleted


# ---------- congestion_stats ----------
# 팀원이 만든 가상 결제/혼잡도 시뮬레이션 데이터(scripts/build_congestion_stats.py로 요약)를
# 요일(dow, 0=월~6=일) x 시간대(hour)별 평균으로 저장. 이름이 확실히 매칭된 음식점만 있음.


def replace_congestion_stats(rows):
    """rows: [{restaurant_name, restaurant_address, dow, hour, avg_congestion_pct, avg_wait_min}, ...]
    (restaurant_name, restaurant_address) 조합으로 이 DB에서 id를 다시 찾아서 넣습니다
    (local/Neon처럼 같은 음식점도 SERIAL id가 DB마다 다르기 때문에, id가 아니라 이 조합
    기준으로 저장해둔 걸 여기서 변환합니다 - 이름만 쓰면 이름이 완전히 같은 다른 지점끼리
    섞일 수 있어서 주소까지 같이 봄)."""
    key_to_id = {(r["name"], r["address"]): r["id"] for r in list_restaurants()}
    resolved = []
    skipped = []
    for r in rows:
        rid = key_to_id.get((r["restaurant_name"], r["restaurant_address"]))
        if rid is None:
            skipped.append(r["restaurant_name"])
            continue
        resolved.append((rid, r["dow"], r["hour"], r["avg_congestion_pct"], r["avg_wait_min"]))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM congestion_stats")
    if resolved:
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO congestion_stats (restaurant_id, dow, hour, avg_congestion_pct, avg_wait_min) VALUES %s",
            resolved,
        )
    conn.commit()
    cur.close()
    conn.close()
    return len(resolved), sorted(set(skipped))


def get_congestion_lookup_for(dow: int, hour: int):
    """{restaurant_id: (avg_congestion_pct, avg_wait_min)} - 지금 요일x시간대 것만 가져옵니다.
    음식점 3,647개 x 요일7 x 시간대14 = 35만행 넘는 테이블 전체를 매번 불러오면 느려서
    (예전엔 그렇게 했다가 추천 1번에 2초 넘게 걸렸음), 지금 필요한 행만 좁혀서 쿼리합니다."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT restaurant_id, avg_congestion_pct, avg_wait_min FROM congestion_stats WHERE dow = %s AND hour = %s",
        (dow, hour),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {r["restaurant_id"]: (r["avg_congestion_pct"], r["avg_wait_min"]) for r in rows}


# ---------- users (간단 로그인) ----------

def create_user(username, password_hash):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (%s, %s, %s)",
        (username, password_hash, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_user(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


# ---------- favorites (즐겨찾기) ----------


def add_favorite(username, restaurant_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO favorites (username, restaurant_id, created_at) VALUES (%s, %s, %s) "
        "ON CONFLICT (username, restaurant_id) DO NOTHING",
        (username, restaurant_id, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    cur.close()
    conn.close()


def remove_favorite(username, restaurant_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM favorites WHERE username = %s AND restaurant_id = %s",
        (username, restaurant_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def list_favorite_ids(username):
    """추천 1번에 음식점 여러 개를 돌 때 건건이 쿼리하지 않기 위해 id 집합을 한 번에 불러옴."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT restaurant_id FROM favorites WHERE username = %s", (username,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {r["restaurant_id"] for r in rows}


def list_favorite_restaurants(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT r.* FROM restaurants r JOIN favorites f ON f.restaurant_id = r.id "
        "WHERE f.username = %s ORDER BY f.created_at DESC",
        (username,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


# ---------- reports (신고 - 카테고리/위치 오류 등) ----------


def add_report(restaurant_id, reporter, reason, detail=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reports (restaurant_id, reporter, reason, detail, status, created_at) "
        "VALUES (%s, %s, %s, %s, 'open', %s)",
        (restaurant_id, reporter, reason, detail, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    cur.close()
    conn.close()


def list_reports(status=None):
    """관리자 페이지용. 음식점 현재 정보(이름/카테고리/주소/좌표)를 같이 묶어서 돌려줘서
    신고 내용과 현재 값을 바로 비교할 수 있게 함."""
    conn = get_conn()
    cur = conn.cursor()
    query = (
        "SELECT rep.id, rep.restaurant_id, rep.reporter, rep.reason, rep.detail, "
        "rep.status, rep.created_at, "
        "r.name AS restaurant_name, r.category AS restaurant_category, "
        "r.address AS restaurant_address, r.lat AS restaurant_lat, r.lng AS restaurant_lng "
        "FROM reports rep JOIN restaurants r ON r.id = rep.restaurant_id"
    )
    params = ()
    if status and status != "all":
        query += " WHERE rep.status = %s"
        params = (status,)
    query += " ORDER BY rep.created_at DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def set_report_status(report_id, status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE reports SET status = %s WHERE id = %s", (status, report_id))
    conn.commit()
    cur.close()
    conn.close()


def update_restaurant(restaurant_id, **fields):
    """관리자가 신고 보고 직접 고칠 때 씀. 전달된 필드만 업데이트."""
    allowed = {"name", "category", "lat", "lng", "address"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return
    conn = get_conn()
    cur = conn.cursor()
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    cur.execute(
        f"UPDATE restaurants SET {set_clause} WHERE id = %s",
        (*updates.values(), restaurant_id),
    )
    conn.commit()
    cur.close()
    conn.close()


# ---------- recommend_logs (마이페이지 통계용) ----------


def add_recommend_log(username, category, feasible_count):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO recommend_logs (username, category, feasible_count, created_at) VALUES (%s, %s, %s, %s)",
        (username, category, feasible_count, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_recommend_stats(username):
    """총 추천받은 횟수 + 가장 많이 고른 카테고리."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM recommend_logs WHERE username = %s", (username,))
    total_count = cur.fetchone()["n"]
    cur.execute(
        "SELECT category, COUNT(*) AS n FROM recommend_logs WHERE username = %s "
        "GROUP BY category ORDER BY n DESC LIMIT 1",
        (username,),
    )
    top = cur.fetchone()
    cur.close()
    conn.close()
    return {
        "total_count": total_count,
        "top_category": top["category"] if top else None,
    }
