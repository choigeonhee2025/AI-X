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
