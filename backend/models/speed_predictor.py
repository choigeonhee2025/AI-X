"""
ML 과제 정의 (5칸)
  예측 대상 (y): 편도 도보 이동 시간 (분)
  입력 특징 (X): 직선거리(m), 시간대(hour, 0-23), 요일(dow, 0=월 ... 6=일)
  예측 시점: 학생이 출발 직전, 목적지(음식점)가 확정된 시점
  과제 유형: 회귀
  평가 지표: MAE(분). 베이스라인 = 고정 평균 보행속도 모델

DB(backend/data/app.db)의 trips 테이블에 쌓인 실측 데이터가 적을 때는 고정 속도
(DEFAULT_SPEED_M_PER_MIN)로 예측하고, 충분히 쌓이면(MIN_TRIPS_FOR_MODEL) 학습된
회귀 모델로 전환합니다.
"""
import os

import joblib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "speed_model.pkl")

# 성인 평균 도보 속도의 보수적인 추정값(분당 미터). 실측 데이터가 쌓이기 전까지의 기본값이며,
# 팀 실측으로 반드시 교체/검증해야 합니다.
DEFAULT_SPEED_M_PER_MIN = 67

MIN_TRIPS_FOR_MODEL = 5


def _load_model():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None


def predict_one_way_minutes(distance_m: float, hour: int, dow: int) -> float:
    """편도 이동시간(분)을 예측합니다."""
    model = _load_model()
    if model is not None:
        pred = model.predict([[distance_m, hour, dow]])[0]
        return max(0.5, float(pred))
    return distance_m / DEFAULT_SPEED_M_PER_MIN


def is_using_trained_model() -> bool:
    return os.path.exists(MODEL_PATH)
