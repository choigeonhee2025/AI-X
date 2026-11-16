"""
ML 과제 정의 (5칸)
  예측 대상 (y): 편도 도보 이동 시간 (분)
  입력 특징 (X): 직선거리(m), 시간대(hour, 0-23), 요일(dow, 0=월 ... 6=일), 회원(개인화)
  예측 시점: 학생이 출발 직전, 목적지(음식점)와 본인(member)이 확정된 시점
  과제 유형: 회귀
  평가 지표: MAE(분). 베이스라인 = 고정 평균 보행속도 모델

개인화는 데이터가 쌓이는 정도에 따라 3단계로 전환됩니다 (데이터 없이 바로 "회원별 모델"을
학습하면 과적합되므로, 데이터가 적을 땐 더 단순한 방법으로 내려가는 구조):

  0단계: 아무 실측 데이터도 없음        -> 전체 평균 속도(DEFAULT_SPEED_M_PER_MIN) 고정값
  1단계: 그 사람 기록이 MIN_PERSONAL_TRIPS건 이상 -> 그 사람 평균 속도로 대체 (개인화 베이스라인)
  2단계: 전체 기록이 MIN_TRIPS_FOR_MODEL건 이상   -> distance/hour/dow/member를 특징으로 쓰는
         회귀 모델 (학습 시 등장한 회원마다 다른 예측이 나옴)
"""
import os

import joblib

import db

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "speed_model.pkl")

# 성인 평균 도보 속도의 보수적인 추정값(분당 미터). 실측 데이터가 쌓이기 전까지의 기본값.
DEFAULT_SPEED_M_PER_MIN = 67

MIN_PERSONAL_TRIPS = 3
MIN_TRIPS_FOR_MODEL = 5


def _load_model_bundle():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None


def build_feature_row(distance_m, hour, dow, member, known_members):
    """학습 때와 예측 때 항상 같은 순서로 회원을 원-핫 인코딩합니다."""
    one_hot = [1 if member == m else 0 for m in known_members]
    return [distance_m, hour, dow] + one_hot


def predict_one_way_minutes(distance_m: float, hour: int, dow: int, member: str = None) -> dict:
    """
    편도 이동시간(분)을 예측하고, 어떤 단계(tier)를 썼는지도 같이 돌려줍니다.
    반환: {"minutes": float, "tier": "model" | "personal_avg" | "default"}
    """
    bundle = _load_model_bundle()
    if bundle is not None:
        row = build_feature_row(distance_m, hour, dow, member, bundle["members"])
        pred = bundle["model"].predict([row])[0]
        return {"minutes": max(0.5, float(pred)), "tier": "model"}

    if member:
        personal_speed = db.get_member_average_speed_m_per_min(member, min_trips=MIN_PERSONAL_TRIPS)
        if personal_speed:
            return {"minutes": distance_m / personal_speed, "tier": "personal_avg"}

    return {"minutes": distance_m / DEFAULT_SPEED_M_PER_MIN, "tier": "default"}


def is_using_trained_model() -> bool:
    return os.path.exists(MODEL_PATH)
