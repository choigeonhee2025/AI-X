"""
로컬 PostgreSQL에 수집된 data.go.kr 음식점 데이터를 Neon(배포용 DB)으로 복사합니다.
manual:* 로 추가된 데이터나 Neon 쪽의 다른 데이터는 건드리지 않고,
source='data.go.kr_general_restaurants' 인 행만 Neon에서 지우고 로컬 걸로 새로 채웁니다.

사용법 (backend/ 에서, .env에 DATABASE_URL=로컬, NEON_DATABASE_URL=Neon 둘 다 설정된 상태로):
    python scripts/sync_to_neon.py
"""
import os
import sys

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

SOURCE = "data.go.kr_general_restaurants"
BATCH_SIZE = 500


def main():
    local_url = os.getenv("DATABASE_URL")
    neon_url = os.getenv("NEON_DATABASE_URL")
    if not local_url:
        sys.exit("DATABASE_URL(로컬)이 .env에 없습니다.")
    if not neon_url:
        sys.exit("NEON_DATABASE_URL이 .env에 없습니다.")

    local_conn = psycopg2.connect(local_url, cursor_factory=psycopg2.extras.RealDictCursor)
    local_cur = local_conn.cursor()
    local_cur.execute(
        "SELECT name, category, lat, lng, address, source, fetched_at "
        "FROM restaurants WHERE source = %s",
        (SOURCE,),
    )
    rows = local_cur.fetchall()
    local_cur.close()
    local_conn.close()

    if not rows:
        sys.exit(f"로컬에 source='{SOURCE}' 데이터가 없습니다.")

    print(f"로컬에서 {len(rows)}건 읽음")

    neon_conn = psycopg2.connect(neon_url)
    neon_cur = neon_conn.cursor()

    neon_cur.execute(
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

    neon_cur.execute("DELETE FROM restaurants WHERE source = %s", (SOURCE,))
    deleted = neon_cur.rowcount
    print(f"Neon에서 기존 {SOURCE} 데이터 {deleted}건 삭제")

    values = [
        (r["name"], r["category"], r["lat"], r["lng"], r["address"], r["source"], r["fetched_at"])
        for r in rows
    ]
    for i in range(0, len(values), BATCH_SIZE):
        chunk = values[i : i + BATCH_SIZE]
        psycopg2.extras.execute_values(
            neon_cur,
            "INSERT INTO restaurants (name, category, lat, lng, address, source, fetched_at) VALUES %s",
            chunk,
        )
        neon_conn.commit()
        print(f"  Neon에 {i + len(chunk)}/{len(values)}건 저장")

    neon_cur.close()
    neon_conn.close()
    print(f"완료. Neon에 {len(values)}건 복사됨.")


if __name__ == "__main__":
    main()
