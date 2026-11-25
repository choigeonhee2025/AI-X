"""
팀원이 만들어준 가상 결제/혼잡도 시뮬레이션 데이터를 우리 DB에 쓸 수 있는 작은 요약
테이블로 변환합니다.

2026-11-25 기준: 팀원이 이번엔 우리가 보내준 음식점 DB 전체(엑셀/CSV, restaurants.id
그대로)를 기준으로 시뮬레이션을 돌려서, **3,647개 음식점 전부**에 대해
restaurant_id로 바로 매칭되는 데이터를 줬습니다 (예전 42개짜리 + 이름 퍼지매칭 방식은
이제 안 씀 - 그 코드는 지움).

사용법 (backend/ 에서):
    python scripts/build_congestion_stats.py <원본 csv 경로 또는 폴더> [<csv2> ...]

폴더를 주면 그 안의 *.csv를 전부(part1~4 등) 읽어서 합칩니다.

결과: backend/data/congestion_stats.csv (요일×시간대별 평균 혼잡도/대기시간)을 생성.
restaurant_id가 아니라 (restaurant_name, restaurant_address) 조합으로 저장합니다 -
로컬/Neon처럼 같은 음식점도 SERIAL id가 다른 DB가 여러 개라서, id를 그대로 박아두면
다른 DB에서는 엉뚱한 음식점에 매칭될 수 있기 때문입니다. 이름만 쓰면 안 되는 이유는
실제로 이름이 완전히 같은 음식점이 3,647개 중 65쌍(지점 여러 개 등) 있어서 주소까지
같이 써야 거의 다 구분됩니다 (그래도 주소까지 같은 진짜 중복 1건은 남는데, 영향 적어서
무시함). restaurant_id -> (name, address) 변환은 이 스크립트를 실행하는 DB 기준으로 하고,
실제 넣을 때는 scripts/seed_congestion_stats.py가 그 조합으로 다시 찾습니다.
"""
import glob
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "congestion_stats.csv")

WEEKDAY_KO_TO_NUM = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}


def _resolve_input_paths(args):
    paths = []
    for arg in args:
        if os.path.isdir(arg):
            paths.extend(sorted(glob.glob(os.path.join(arg, "*.csv"))))
        else:
            paths.append(arg)
    return paths


def main():
    if len(sys.argv) < 2:
        sys.exit("사용법: python scripts/build_congestion_stats.py <csv 경로 또는 폴더> [...]")
    paths = _resolve_input_paths(sys.argv[1:])
    if not paths:
        sys.exit("csv 파일을 찾지 못했습니다.")

    id_to_name = {r["id"]: r["name"] for r in db.list_restaurants()}
    id_to_address = {r["id"]: r["address"] for r in db.list_restaurants()}

    parts = []
    total_rows = 0
    for path in paths:
        df = pd.read_csv(
            path,
            usecols=["time", "weekday", "restaurant_id", "congestion_pct", "estimated_wait_min"],
            dtype={"restaurant_id": "int64", "congestion_pct": "int32", "estimated_wait_min": "int32"},
        )
        total_rows += len(df)
        df["hour"] = df["time"].str.slice(0, 2).astype("int16")
        df["dow"] = df["weekday"].map(WEEKDAY_KO_TO_NUM).astype("int16")
        df["restaurant_name"] = df["restaurant_id"].map(id_to_name)
        df["restaurant_address"] = df["restaurant_id"].map(id_to_address)
        unmatched = df["restaurant_name"].isna().sum()
        if unmatched:
            print(f"  {os.path.basename(path)}: DB에 없는 restaurant_id {unmatched}행 건너뜀")
        df = df.dropna(subset=["restaurant_name"])
        parts.append(
            df[["restaurant_name", "restaurant_address", "dow", "hour", "congestion_pct", "estimated_wait_min"]]
        )
        print(f"읽음: {path} ({len(df):,}행)")

    full = pd.concat(parts, ignore_index=True)
    print(f"전체 {total_rows:,}행 중 매칭된 {len(full):,}행, 음식점 {full['restaurant_name'].nunique():,}개")

    agg = (
        full.groupby(["restaurant_name", "restaurant_address", "dow", "hour"])
        .agg(avg_congestion_pct=("congestion_pct", "mean"), avg_wait_min=("estimated_wait_min", "mean"))
        .reset_index()
    )
    agg["avg_congestion_pct"] = agg["avg_congestion_pct"].round(1)
    agg["avg_wait_min"] = agg["avg_wait_min"].round(1)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    agg.to_csv(OUT_PATH, index=False)
    print(f"{len(agg):,}행 저장: {OUT_PATH}")


if __name__ == "__main__":
    main()
