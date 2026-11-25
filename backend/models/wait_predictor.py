"""
음식점 예상 대기시간 예측. models/train_wait_model.py가 학습한 모델을 불러와 씁니다.

speed_predictor.py와 같은 단계별 구조:
  0단계: 음식점이 모델에 없음(이름 매칭 안 됨) -> 대기시간 0
  1단계: 매칭은 됐는데 모델 파일이 아직 없음  -> 요일x시간대 평균(congestion_stats 테이블)
  2단계: 학습된 모델 있음                    -> 분단위 회귀 예측(더 정확함, train_wait_model.py 참고)
"""
import os

import joblib

import db

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wait_model.pkl")

_model_cache = {"mtime": None, "bundle": None}
_congestion_cache = {"key": None, "lookup": None}
_name_to_id_cache = {"loaded_at": None, "map": None}

NAME_TO_ID_TTL_SEC = 60


def _load_wait_bundle():
    if not os.path.exists(MODEL_PATH):
        return None
    mtime = os.path.getmtime(MODEL_PATH)
    if _model_cache["bundle"] is None or _model_cache["mtime"] != mtime:
        _model_cache["bundle"] = joblib.load(MODEL_PATH)
        _model_cache["mtime"] = mtime
    return _model_cache["bundle"]


def _get_congestion_lookup(dow, hour):
    """(dow, hour) 조합당 한 번만 DB에서 읽고 캐싱 - 음식점 3,647개짜리 요일x시간대 테이블
    전체를 매 추천마다 불러오면 느려서, 지금 이 시각에 필요한 부분만(그리고 같은 시각 안의
    다음 요청부터는 캐시로) 가져옵니다."""
    key = (dow, hour)
    if _congestion_cache["key"] != key:
        _congestion_cache["lookup"] = db.get_congestion_lookup_for(dow, hour)
        _congestion_cache["key"] = key
    return _congestion_cache["lookup"]


def _get_name_to_id():
    import time

    now = time.time()
    if _name_to_id_cache["map"] is None or now - _name_to_id_cache["loaded_at"] > NAME_TO_ID_TTL_SEC:
        _name_to_id_cache["map"] = {r["name"]: r["id"] for r in db.list_restaurants()}
        _name_to_id_cache["loaded_at"] = now
    return _name_to_id_cache["map"]


def predict_wait_batch(restaurant_names, dow: int, hour: int, minute: int = 0):
    """음식점 이름 리스트 -> (예상 대기시간(분) 리스트, 혼잡도%(알 수 있으면) 리스트) 를 한 번에 계산.
    추천 1번에 음식점 수백~수천 개를 돌 때 건건이 쿼리/모델 호출하지 않기 위해 배치로 처리."""
    bundle = _load_wait_bundle()
    congestion_lookup = _get_congestion_lookup(dow, hour)  # {restaurant_id: (pct, wait)}
    name_to_id = _get_name_to_id()

    minute_of_day = hour * 60 + minute
    known_names = set(bundle["restaurant_names"]) if bundle else set()

    rows_for_model = []
    model_idx = []
    waits = [0.0] * len(restaurant_names)
    pcts = [None] * len(restaurant_names)

    for i, name in enumerate(restaurant_names):
        if name in known_names:
            rows_for_model.append({"restaurant_name": name, "dow": dow, "minute_of_day": minute_of_day})
            model_idx.append(i)
            continue
        rid = name_to_id.get(name)
        pct, wait = congestion_lookup.get(rid, (None, 0))
        waits[i] = wait
        pcts[i] = pct

    if rows_for_model:
        import pandas as pd

        preds = bundle["model"].predict(pd.DataFrame(rows_for_model))
        for i, pred in zip(model_idx, preds):
            waits[i] = max(0.0, round(float(pred), 1))
            rid = name_to_id.get(restaurant_names[i])
            pct, _ = congestion_lookup.get(rid, (None, None))
            pcts[i] = pct

    return waits, pcts


def is_using_trained_wait_model() -> bool:
    return os.path.exists(MODEL_PATH)
