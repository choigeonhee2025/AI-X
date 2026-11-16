import datetime
import json
import os

from flask import Flask, jsonify, request, send_from_directory

from models.speed_predictor import TRIPS_PATH, is_using_trained_model, trip_count
from services.recommend import recommend
from services.restaurant_service import haversine_m, list_categories, load_restaurants

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/collect")
def collect_page():
    return send_from_directory(STATIC_DIR, "collect.html")


@app.route("/api/restaurants")
def api_restaurants():
    restaurants, campus_center = load_restaurants()
    return jsonify(
        {
            "campus_center": campus_center,
            "categories": ["전체"] + list_categories(),
            "count": len(restaurants),
        }
    )


@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    payload = request.get_json(force=True)
    try:
        break_minutes = float(payload["break_minutes"])
        meal_minutes = float(payload["meal_minutes"])
        category = payload.get("category", "전체")
        user_lat = float(payload["lat"])
        user_lng = float(payload["lng"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "break_minutes, meal_minutes, lat, lng가 필요합니다."}), 400

    feasible, infeasible = recommend(break_minutes, meal_minutes, category, user_lat, user_lng)
    return jsonify(
        {
            "feasible": feasible,
            "infeasible": infeasible,
            "using_trained_model": is_using_trained_model(),
            "trip_count": trip_count(),
        }
    )


@app.route("/api/trips", methods=["POST"])
def api_add_trip():
    payload = request.get_json(force=True)
    try:
        start_lat = float(payload["start_lat"])
        start_lng = float(payload["start_lng"])
        end_lat = float(payload["end_lat"])
        end_lng = float(payload["end_lng"])
        start_ts = float(payload["start_ts"])  # epoch ms
        end_ts = float(payload["end_ts"])  # epoch ms
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "start_lat, start_lng, end_lat, end_lng, start_ts, end_ts가 필요합니다."}), 400

    distance_m = haversine_m(start_lat, start_lng, end_lat, end_lng)
    duration_min = (end_ts - start_ts) / 1000 / 60
    if duration_min <= 0:
        return jsonify({"error": "end_ts가 start_ts보다 이후여야 합니다."}), 400

    start_dt = datetime.datetime.fromtimestamp(start_ts / 1000)

    trip = {
        "distance_m": round(distance_m, 1),
        "duration_min": round(duration_min, 2),
        "hour": start_dt.hour,
        "dow": start_dt.weekday(),
        "recorded_at": start_dt.isoformat(),
    }

    trips = []
    if os.path.exists(TRIPS_PATH):
        with open(TRIPS_PATH, "r", encoding="utf-8") as f:
            trips = json.load(f)
    trips.append(trip)
    with open(TRIPS_PATH, "w", encoding="utf-8") as f:
        json.dump(trips, f, ensure_ascii=False, indent=2)

    return jsonify({"saved": trip, "trip_count": len(trips)})


@app.route("/api/trips/count")
def api_trip_count():
    return jsonify({"trip_count": trip_count(), "using_trained_model": is_using_trained_model()})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
