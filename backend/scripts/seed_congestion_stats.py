"""
backend/data/congestion_stats.csv (scripts/build_congestion_stats.py가 만든 요약본)를
DB(.env의 DATABASE_URL)에 넣습니다. 로컬/Neon 둘 다 DATABASE_URL만 바꿔서 이 스크립트를
돌리면 됩니다.

사용법 (backend/ 에서):
    python scripts/seed_congestion_stats.py
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db  # noqa: E402

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "congestion_stats.csv")


def main():
    db.init_db()
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = [
            {
                "restaurant_name": row["restaurant_name"],
                "dow": int(row["dow"]),
                "hour": int(row["hour"]),
                "avg_congestion_pct": float(row["avg_congestion_pct"]),
                "avg_wait_min": float(row["avg_wait_min"]),
            }
            for row in csv.DictReader(f)
        ]
    saved, skipped = db.replace_congestion_stats(rows)
    print(f"{saved}행 저장 완료.")
    if skipped:
        print(f"이 DB에서 이름을 못 찾아서 건너뜀: {', '.join(skipped)}")


if __name__ == "__main__":
    main()
