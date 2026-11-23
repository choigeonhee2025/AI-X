"""
팀원이 만든 가상 결제/혼잡도 데이터로 '예상 대기시간' 회귀 모델을 학습합니다.
(팀원이 공유해준 노트북의 RandomForest 설계 - restaurant_id/weekday/minute_of_day 특징,
baseline으로 전체 평균(global mean) 비교 - 를 그대로 가져와서 우리 프로젝트에 맞게 다듬음.)

예측 대상(y): 예상 대기시간(분)
입력 특징(X): 음식점, 요일, 분단위 시각(minute_of_day = hour*60+minute)
베이스라인: 전체 평균(global mean) 고정값
평가: MAE/RMSE/R2, 전체 영업시간 vs 점심시간(12~13시)만

데이터가 딱 1주일(월~일) 뿐이라, 팀원 노트북의 "날짜로 통째로 자르기" 방식(학습 11/2~11/6,
검증 11/6~11/7, 테스트 11/7~11/9)을 그대로 쓰면 학습에는 평일(월~목)만, 테스트에는 주말만
들어가서 모델이 주말 패턴을 한 번도 못 보고 평가받는 문제가 있었습니다(실제로 그렇게
해보니 베이스라인보다 한참 나쁘게 나옴). 그래서 하루 안에서 시각(분)을 60/20/20으로
섞어서 모든 요일이 학습/검증/테스트에 고르게 들어가도록 분할 방식만 바꿨습니다
(팀원 노트북의 "요일마다 학습/검증/테스트를 균등하게 나눈다"는 취지는 그대로 유지).

음식점 이름은 data.go.kr 실제 상호명과 표기가 달라서, scripts/build_congestion_stats.py와
같은 규칙으로 확실히 매칭되는 것만 골라서 씁니다 (현재 15개).

사용법 (backend/ 에서):
    python models/train_wait_model.py "<원본 CSV 경로>"
"""
import os
import re
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db  # noqa: E402

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wait_model.pkl")
TARGET = "estimated_wait_min"
FEATURES = ["restaurant_name", "dow", "minute_of_day"]

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
    """scripts/build_congestion_stats.py와 동일한 규칙. 확실한 것만 매칭."""
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


def build_pipeline():
    encode = ColumnTransformer(
        [("categories", OneHotEncoder(handle_unknown="ignore"), ["restaurant_name", "dow"])],
        remainder="passthrough",
    )
    return make_pipeline(
        encode,
        RandomForestRegressor(n_estimators=200, max_depth=12, min_samples_leaf=5, random_state=42, n_jobs=-1),
    )


def evaluate(model, rows, label, is_baseline=False):
    actual = rows[TARGET]
    predicted = model.predict(np.zeros((len(rows), 1))) if is_baseline else model.predict(rows[FEATURES])
    return {
        "model": "글로벌 평균(베이스라인)" if is_baseline else "RandomForest",
        "구간": label,
        "MAE": round(mean_absolute_error(actual, predicted), 3),
        "RMSE": round(np.sqrt(mean_squared_error(actual, predicted)), 3),
        "R2": round(r2_score(actual, predicted), 3) if actual.nunique() > 1 else float("nan"),
        "표본수": len(rows),
    }


def main():
    if len(sys.argv) < 2:
        sys.exit("사용법: python models/train_wait_model.py <원본 csv 경로>")
    src_path = sys.argv[1]

    df = pd.read_csv(src_path, encoding="utf-8-sig")
    df["dow"] = df["weekday"].map(WEEKDAY_KO_TO_NUM)
    df["minute_of_day"] = df["time"].str.slice(0, 2).astype(int) * 60 + df["time"].str.slice(3, 5).astype(int)
    df["date_time"] = pd.to_datetime(df["date"] + " " + df["time"])

    db_rows = db.list_restaurants()
    mapping = match_names(df["restaurant_name"].unique().tolist(), db_rows)
    print(f"이름 매칭: {len(mapping)} / {df['restaurant_name'].nunique()}개 음식점")
    df = df[df["restaurant_name"].isin(mapping)].copy()
    df["restaurant_name"] = df["restaurant_name"].map(mapping)

    # 하루 안에서 분 단위로 60/20/20 섞어서 모든 요일이 세 분할에 고르게 들어가게 함
    # (날짜로 통째로 자르면 이 데이터는 7일뿐이라 학습=평일, 테스트=주말로 쪼개지는 문제가 있었음)
    bucket = df["minute_of_day"] % 5
    train = df[bucket.isin([0, 1, 2])]
    validation = df[bucket == 3]
    test = df[bucket == 4]
    print(f"학습 {len(train):,}행 / 검증 {len(validation):,}행 / 테스트 {len(test):,}행")
    assert train["dow"].nunique() == 7 and test["dow"].nunique() == 7, "분할에 모든 요일이 들어가지 않음"

    baseline = DummyRegressor(strategy="mean")
    baseline.fit(np.zeros((len(train), 1)), train[TARGET])

    model = build_pipeline()
    model.fit(train[FEATURES], train[TARGET])

    lunch_test = test[test["date_time"].dt.hour.eq(12)]
    rows = [
        evaluate(baseline, test, "전체 영업시간", is_baseline=True),
        evaluate(baseline, lunch_test, "점심(12~13시)", is_baseline=True),
        evaluate(model, test, "전체 영업시간"),
        evaluate(model, lunch_test, "점심(12~13시)"),
    ]
    print(pd.DataFrame(rows).to_string(index=False))

    known_names = sorted(df["restaurant_name"].unique().tolist())
    joblib.dump({"model": model, "restaurant_names": known_names}, MODEL_PATH, compress=3)
    print(f"모델 저장: {MODEL_PATH}")


if __name__ == "__main__":
    main()
