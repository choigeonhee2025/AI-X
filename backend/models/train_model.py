"""
DB(trips 테이블)에 쌓인 실측 이동 데이터로 회귀 모델을 학습하고 speed_model.pkl로 저장합니다.

사용법 (backend/ 에서):
    python models/train_model.py

평가 지표: MAE(분). 데이터가 MIN_TRIPS_FOR_MODEL보다 적으면 학습하지 않고 종료합니다
(이때는 speed_predictor.py의 고정 속도 베이스라인이 계속 사용됩니다).
"""
import os
import sys

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db  # noqa: E402
from models.speed_predictor import DEFAULT_SPEED_M_PER_MIN, MIN_TRIPS_FOR_MODEL, MODEL_PATH  # noqa: E402


def main():
    X, y = db.get_training_data()
    X, y = np.array(X), np.array(y)
    n = len(y)
    print(f"수집된 실측 이동 기록: {n}건")
    print(f"회원별 기록 수: {db.trips_per_member()}")

    if n < MIN_TRIPS_FOR_MODEL:
        print(
            f"최소 {MIN_TRIPS_FOR_MODEL}건이 필요합니다. "
            f"지금은 고정 속도({DEFAULT_SPEED_M_PER_MIN}m/분) 베이스라인을 계속 사용합니다."
        )
        return

    if n < 10:
        X_train, y_train = X, y
        X_test, y_test = X, y
    else:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, pred)

    baseline_pred = X_test[:, 0] / DEFAULT_SPEED_M_PER_MIN
    baseline_mae = mean_absolute_error(y_test, baseline_pred)

    print(f"모델 MAE: {mae:.2f}분")
    print(f"고정 속도 베이스라인 MAE: {baseline_mae:.2f}분")

    joblib.dump(model, MODEL_PATH)
    print(f"모델 저장 완료: {MODEL_PATH}")

    if mae >= baseline_mae:
        print("주의: 학습 모델이 베이스라인보다 나아지지 않았습니다. 데이터를 더 모으거나 특징을 다시 설계해 보세요.")


if __name__ == "__main__":
    main()
