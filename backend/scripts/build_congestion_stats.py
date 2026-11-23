"""
팀원이 만들어준 가상 결제/혼잡도 시뮬레이션 데이터(분당 246,960행)를
우리 DB에 쓸 수 있는 작은 요약 테이블로 변환합니다.

원본 CSV는 토스플레이스 API 접근 권한이 없어서 만든 가상 데이터라, 42개 음식점 이름이
data.go.kr에서 받은 실제 상호명과 정확히 일치하지 않는 경우가 많습니다 (지점명 표기 차이,
구내식당류는 일반음식점 등록 자체가 안 돼 있음 등). 그래서 이름이 확실하게 매칭되는
음식점만 골라서 쓰고, 나머지는 건너뜁니다.

사용법 (backend/ 에서):
    python scripts/build_congestion_stats.py "<원본 csv 경로>"

결과: backend/data/congestion_stats.csv (요일×시간대별 평균 혼잡도/대기시간, 매칭된
음식점만, 약 1500행) 을 생성합니다. 이 파일을 커밋해두면 다른 환경에서는 원본 거대
CSV 없이 scripts/seed_congestion_stats.py 로 DB에 바로 넣을 수 있습니다.

restaurant_id가 아니라 restaurant_name(우리 DB에 저장된 그대로의 이름)으로 저장합니다.
로컬/Neon처럼 같은 음식점이라도 SERIAL id가 서로 다른 DB가 여러 개라서, id를 그대로
박아두면 다른 DB에서는 엉뚱한 음식점에 매칭될 수 있기 때문입니다. id는 seed 스크립트가
넣을 때 그 DB에서 이름으로 다시 찾습니다.
"""
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "congestion_stats.csv")

WEEKDAY_KO_TO_NUM = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}

CAMPUS_TOKENS = ["한양대에리카", "한양대 ERICA", "한양대ERICA", "ERICA", "에리카", "안산한양대", "한양대"]


def _core(name: str) -> str:
    s = name.replace(" ", "")
    for t in CAMPUS_TOKENS:
        s = s.replace(t.replace(" ", ""), "")
    return re.sub(r"점$", "", s)


def _has_campus_token(name: str) -> bool:
    s = name.replace(" ", "")
    return any(t.replace(" ", "") in s for t in CAMPUS_TOKENS)


def match_names(sim_names, db_rows):
    """팀원 CSV의 음식점명 -> 우리 DB의 정식 이름(name). 확실한 것만 매칭(느슨하게 겹치면 스킵)."""
    mapping = {}
    for sim_name in sim_names:
        key_core = _core(sim_name)
        key_has_campus = _has_campus_token(sim_name)
        if not key_core:
            continue
        candidates = [
            r
            for r in db_rows
            if _core(r["name"]) == key_core and (_has_campus_token(r["name"]) if key_has_campus else True)
        ]
        if len(candidates) == 1:
            mapping[sim_name] = candidates[0]["name"]
    return mapping


def main():
    if len(sys.argv) < 2:
        sys.exit("사용법: python scripts/build_congestion_stats.py <원본 csv 경로>")
    src_path = sys.argv[1]

    df = pd.read_csv(src_path, encoding="utf-8-sig")
    df["hour"] = df["time"].str.slice(0, 2).astype(int)
    df["dow"] = df["weekday"].map(WEEKDAY_KO_TO_NUM)

    db_rows = db.list_restaurants()
    mapping = match_names(df["restaurant_name"].unique().tolist(), db_rows)
    print(f"이름 매칭: {len(mapping)} / {df['restaurant_name'].nunique()}개 음식점")

    df = df[df["restaurant_name"].isin(mapping)].copy()
    df["db_name"] = df["restaurant_name"].map(mapping)

    agg = (
        df.groupby(["db_name", "dow", "hour"])
        .agg(avg_congestion_pct=("congestion_pct", "mean"), avg_wait_min=("estimated_wait_min", "mean"))
        .reset_index()
        .rename(columns={"db_name": "restaurant_name"})
    )
    agg["avg_congestion_pct"] = agg["avg_congestion_pct"].round(1)
    agg["avg_wait_min"] = agg["avg_wait_min"].round(1)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    agg.to_csv(OUT_PATH, index=False)
    print(f"{len(agg)}행 저장: {OUT_PATH}")


if __name__ == "__main__":
    main()
