"""
SQLite 기반 데이터 저장소. trips.json / restaurants.json 플랫파일을 대체합니다.

trips  : 팀원이 /collect에서 직접 측정한 이동시간 기록 (회원 이름 태그 포함)
restaurants : 추천에 쓰는 음식점 목록 (지금은 더미 시드, 추후 공공데이터 API로 교체)
"""
import datetime
import json
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "app.db")
SEED_RESTAURANTS_PATH = os.path.join(BASE_DIR, "data", "restaurants.json")

TEAM_MEMBERS = ["박성현", "윤금초", "이윤환", "최건희"]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member TEXT NOT NULL,
            distance_m REAL NOT NULL,
            duration_min REAL NOT NULL,
            hour INTEGER NOT NULL,
            dow INTEGER NOT NULL,
            recorded_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0]
    if count == 0:
        _seed_restaurants(conn)
    conn.close()


def _seed_restaurants(conn):
    if not os.path.exists(SEED_RESTAURANTS_PATH):
        return
    with open(SEED_RESTAURANTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    now = datetime.datetime.now().isoformat()
    rows = [
        (r["name"], r["category"], r["lat"], r["lng"], r.get("address"), r.get("source", "dummy_sample"), now)
        for r in data["restaurants"]
    ]
    conn.executemany(
        "INSERT INTO restaurants (name, category, lat, lng, address, source, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


# ---------- trips ----------

def add_trip(member, distance_m, duration_min, hour, dow, recorded_at):
    conn = get_conn()
    conn.execute(
        "INSERT INTO trips (member, distance_m, duration_min, hour, dow, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
        (member, distance_m, duration_min, hour, dow, recorded_at),
    )
    conn.commit()
    conn.close()


def trip_count():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM trips").fetchone()[0]
    conn.close()
    return n


def list_trips(limit=50):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM trips ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_training_data():
    """회귀 모델 학습용 (X, y) 리스트. 지금은 member를 특징으로 쓰지 않고 풀링합니다."""
    conn = get_conn()
    rows = conn.execute("SELECT distance_m, hour, dow, duration_min FROM trips").fetchall()
    conn.close()
    X = [[r["distance_m"], r["hour"], r["dow"]] for r in rows]
    y = [r["duration_min"] for r in rows]
    return X, y


def trips_per_member():
    conn = get_conn()
    rows = conn.execute("SELECT member, COUNT(*) as n FROM trips GROUP BY member").fetchall()
    conn.close()
    return {r["member"]: r["n"] for r in rows}


# ---------- restaurants ----------

def list_restaurants(category=None):
    conn = get_conn()
    if category and category != "전체":
        rows = conn.execute("SELECT * FROM restaurants WHERE category = ?", (category,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM restaurants").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_categories():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT category FROM restaurants ORDER BY category").fetchall()
    conn.close()
    return [r["category"] for r in rows]


def restaurant_count():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0]
    conn.close()
    return n


def replace_restaurants(restaurants):
    """공공데이터 API 연동 후 호출할 함수. source, fetched_at은 호출부에서 채워서 넘겨주세요."""
    conn = get_conn()
    conn.execute("DELETE FROM restaurants")
    conn.executemany(
        "INSERT INTO restaurants (name, category, lat, lng, address, source, fetched_at) "
        "VALUES (:name, :category, :lat, :lng, :address, :source, :fetched_at)",
        restaurants,
    )
    conn.commit()
    conn.close()
