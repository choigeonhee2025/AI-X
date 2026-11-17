"""
data.go.kr에서 안산시 전체 일반음식점 데이터를 받아와서, 캠퍼스 반경 안에 있는 곳만
걸러 DB에 저장합니다. 안산시 전체가 3만건이 넘고 서버가 느려서(페이지당 10~20초+)
시간이 꽤 걸립니다 — 백그라운드로 돌리는 걸 추천합니다.

사용법 (backend/ 에서):
    python scripts/fetch_real_restaurants.py

중단됐다가 다시 실행하면 이미 받은 페이지부터 다시 받습니다(이어받기 아님,
전체 재수집). DB에 쌓인 기존 "data.go.kr_general_restaurants" 소스 데이터는
시작할 때 한 번 지우고 새로 채웁니다 (수동으로 추가한 manual:* 데이터는 안 건드림).
"""
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db  # noqa: E402
from services.restaurant_api import fetch_page, normalize_item  # noqa: E402

CAMPUS_LAT = 37.2996
CAMPUS_LNG = 126.8350
RADIUS_M = 3000
NUM_OF_ROWS = 100


def haversine_m(lat1, lng1, lat2, lng2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def clear_previous_api_data():
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM restaurants WHERE source = 'data.go.kr_general_restaurants'")
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"기존 data.go.kr 데이터 {deleted}건 삭제")


def main():
    clear_previous_api_data()

    page_no = 1
    total_matched = 0
    total_seen = 0
    total_count = None

    while True:
        start = time.time()
        try:
            items, total_count = fetch_page(page_no, NUM_OF_ROWS)
        except RuntimeError as e:
            print(f"[page {page_no}] 실패, 건너뜀: {e}")
            page_no += 1
            if total_count and (page_no - 1) * NUM_OF_ROWS >= total_count:
                break
            continue

        elapsed = time.time() - start
        if not items:
            print(f"[page {page_no}] 더 이상 데이터 없음, 종료")
            break

        batch = []
        for item in items:
            total_seen += 1
            normalized = normalize_item(item)
            if normalized is None or not normalized["is_active"]:
                continue
            dist = haversine_m(CAMPUS_LAT, CAMPUS_LNG, normalized["lat"], normalized["lng"])
            if dist <= RADIUS_M:
                normalized.pop("is_active")
                batch.append(normalized)

        if batch:
            db.insert_restaurants_batch(batch)
            total_matched += len(batch)

        print(
            f"[page {page_no}/{math.ceil(total_count / NUM_OF_ROWS) if total_count else '?'}] "
            f"{elapsed:.1f}초, 이번 페이지 매칭 {len(batch)}건, 누적 매칭 {total_matched}건, "
            f"누적 조회 {total_seen}/{total_count}건"
        )

        if total_count and page_no * NUM_OF_ROWS >= total_count:
            break
        page_no += 1

    print(f"완료. 캠퍼스 반경 {RADIUS_M}m 안의 영업중 음식점 {total_matched}건 저장됨.")


if __name__ == "__main__":
    main()
