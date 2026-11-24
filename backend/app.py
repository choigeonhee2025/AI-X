import datetime
import os
from functools import wraps

from flask import Flask, jsonify, redirect, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

import db
from models.speed_predictor import is_using_trained_model
from services.kakao_directions import get_walking_route
from services.kakao_local import search_place
from services.recommend import recommend
from services.restaurant_service import haversine_m, list_categories

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
app.secret_key = os.getenv("SECRET_KEY", "dev-only-insecure-secret-change-me")

ADMIN_USERNAMES = {u.strip() for u in os.getenv("ADMIN_USERNAMES", "").split(",") if u.strip()}

db.init_db()


def login_required_page(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("username"):
            return redirect("/login")
        return view(*args, **kwargs)

    return wrapped


def login_required_api(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("username"):
            return jsonify({"error": "로그인이 필요합니다."}), 401
        return view(*args, **kwargs)

    return wrapped


def admin_required_page(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("username"):
            return redirect("/login")
        if session["username"] not in ADMIN_USERNAMES:
            return "관리자만 접근할 수 있습니다.", 403
        return view(*args, **kwargs)

    return wrapped


def admin_required_api(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("username"):
            return jsonify({"error": "로그인이 필요합니다."}), 401
        if session["username"] not in ADMIN_USERNAMES:
            return jsonify({"error": "관리자만 접근할 수 있습니다."}), 403
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
@login_required_page
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/collect")
@login_required_page
def collect_page():
    return send_from_directory(STATIC_DIR, "collect.html")


@app.route("/restaurants")
@login_required_page
def restaurants_page():
    return send_from_directory(STATIC_DIR, "restaurants.html")


@app.route("/admin")
@admin_required_page
def admin_page():
    return send_from_directory(STATIC_DIR, "admin.html")


@app.route("/login")
def login_page():
    if session.get("username"):
        return redirect("/")
    return send_from_directory(STATIC_DIR, "login.html")


@app.route("/api/signup", methods=["POST"])
def api_signup():
    payload = request.get_json(force=True)
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))

    if not username or not password:
        return jsonify({"error": "이름과 비밀번호를 모두 입력해주세요."}), 400
    if len(password) < 4:
        return jsonify({"error": "비밀번호는 4자 이상으로 해주세요."}), 400
    if db.get_user(username):
        return jsonify({"error": "이미 있는 이름이에요. 다른 이름을 써주세요."}), 400

    db.create_user(username, generate_password_hash(password))
    session["username"] = username
    return jsonify({"username": username})


@app.route("/api/login", methods=["POST"])
def api_login():
    payload = request.get_json(force=True)
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))

    user = db.get_user(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "이름 또는 비밀번호가 맞지 않아요."}), 401

    session["username"] = username
    return jsonify({"username": username})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("username", None)
    return jsonify({"ok": True})


@app.route("/api/me")
def api_me():
    return jsonify({"username": session.get("username")})


@app.route("/api/restaurants")
def api_restaurants():
    return jsonify({"categories": list_categories(), "count": db.restaurant_count()})


@app.route("/api/restaurants/list")
@login_required_api
def api_restaurants_list():
    return jsonify({"restaurants": db.list_restaurants()})


@app.route("/api/restaurants", methods=["POST"])
@login_required_api
def api_restaurants_add():
    payload = request.get_json(force=True)
    try:
        name = str(payload["name"]).strip()
        category = str(payload["category"]).strip()
        lat = float(payload["lat"])
        lng = float(payload["lng"])
        address = (payload.get("address") or "").strip() or None
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "name, category, lat, lng가 필요합니다."}), 400

    if not name or not category:
        return jsonify({"error": "이름과 카테고리를 입력해주세요."}), 400

    new_id = db.add_restaurant(name, category, lat, lng, address, session["username"])
    return jsonify({"id": new_id})


@app.route("/api/restaurants/<int:restaurant_id>", methods=["DELETE"])
@login_required_api
def api_restaurants_delete(restaurant_id):
    db.delete_restaurant(restaurant_id)
    return jsonify({"ok": True})


@app.route("/api/restaurants/dummy", methods=["DELETE"])
@login_required_api
def api_restaurants_delete_dummy():
    deleted = db.delete_dummy_restaurants()
    return jsonify({"deleted": deleted})


@app.route("/api/favorites")
@login_required_api
def api_favorites_list():
    return jsonify({"favorites": db.list_favorite_restaurants(session["username"])})


@app.route("/api/favorites/<int:restaurant_id>", methods=["POST"])
@login_required_api
def api_favorites_add(restaurant_id):
    db.add_favorite(session["username"], restaurant_id)
    return jsonify({"ok": True})


@app.route("/api/favorites/<int:restaurant_id>", methods=["DELETE"])
@login_required_api
def api_favorites_remove(restaurant_id):
    db.remove_favorite(session["username"], restaurant_id)
    return jsonify({"ok": True})


REPORT_REASONS = {
    "category": "카테고리 오류",
    "location": "위치 오류",
    "closed": "폐업/없어짐",
    "duplicate": "중복 등록",
    "other": "기타",
}


@app.route("/api/reports", methods=["POST"])
@login_required_api
def api_reports_add():
    payload = request.get_json(force=True)
    try:
        restaurant_id = int(payload["restaurant_id"])
        reason = payload["reason"]
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "restaurant_id, reason이 필요합니다."}), 400
    if reason not in REPORT_REASONS:
        return jsonify({"error": f"reason은 {list(REPORT_REASONS)} 중 하나여야 합니다."}), 400

    detail = (payload.get("detail") or "").strip()[:500] or None
    db.add_report(restaurant_id, session["username"], reason, detail)
    return jsonify({"ok": True})


@app.route("/api/admin/reports")
@admin_required_api
def api_admin_reports_list():
    status = request.args.get("status", "open")
    reports = db.list_reports(status)
    for r in reports:
        r["reason_label"] = REPORT_REASONS.get(r["reason"], r["reason"])
    return jsonify({"reports": reports})


@app.route("/api/admin/reports/<int:report_id>/status", methods=["POST"])
@admin_required_api
def api_admin_reports_status(report_id):
    payload = request.get_json(force=True)
    status = payload.get("status")
    if status not in ("open", "resolved", "dismissed"):
        return jsonify({"error": "status는 open/resolved/dismissed 중 하나여야 합니다."}), 400
    db.set_report_status(report_id, status)
    return jsonify({"ok": True})


@app.route("/api/admin/restaurants/<int:restaurant_id>", methods=["POST"])
@admin_required_api
def api_admin_restaurants_update(restaurant_id):
    payload = request.get_json(force=True)
    fields = {k: payload.get(k) for k in ("name", "category", "address")}
    if payload.get("lat") not in (None, ""):
        fields["lat"] = float(payload["lat"])
    if payload.get("lng") not in (None, ""):
        fields["lng"] = float(payload["lng"])
    db.update_restaurant(restaurant_id, **fields)
    return jsonify({"ok": True})


@app.route("/api/recommend", methods=["POST"])
@login_required_api
def api_recommend():
    payload = request.get_json(force=True)
    try:
        break_minutes = float(payload["break_minutes"])
        meal_minutes = float(payload["meal_minutes"])
        category = payload.get("category", "전체")
        user_lat = float(payload["lat"])
        user_lng = float(payload["lng"])
        dest_lat = float(payload["dest_lat"]) if payload.get("dest_lat") not in (None, "") else None
        dest_lng = float(payload["dest_lng"]) if payload.get("dest_lng") not in (None, "") else None
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "break_minutes, meal_minutes, lat, lng가 필요합니다."}), 400

    member = session["username"]
    feasible, infeasible, tier_used = recommend(
        break_minutes, meal_minutes, category, user_lat, user_lng, member, dest_lat, dest_lng
    )
    db.add_recommend_log(member, category, len(feasible))
    return jsonify(
        {
            "feasible": feasible,
            "infeasible": infeasible,
            "using_trained_model": is_using_trained_model(),
            "trip_count": db.trip_count(),
            "personalization_tier": tier_used,
            "member": member,
        }
    )


@app.route("/api/config")
def api_config():
    """카카오맵 JavaScript 키처럼 프론트에 필요하지만 .env에 보관 중인 값을 내려줍니다.
    (JS 키는 도메인 제한이 걸리는 키라 노출돼도 되는 키입니다 - REST 키와는 다름)"""
    return jsonify({"kakao_js_key": os.getenv("KAKAO_JS_KEY", "")})


@app.route("/api/directions", methods=["POST"])
@login_required_api
def api_directions():
    payload = request.get_json(force=True)
    try:
        origin_lat = float(payload["origin_lat"])
        origin_lng = float(payload["origin_lng"])
        dest_lat = float(payload["dest_lat"])
        dest_lng = float(payload["dest_lng"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "origin_lat, origin_lng, dest_lat, dest_lng가 필요합니다."}), 400

    try:
        route = get_walking_route(origin_lat, origin_lng, dest_lat, dest_lng)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502
    return jsonify(route)


@app.route("/api/search-place")
@login_required_api
def api_search_place():
    query = (request.args.get("q") or "").strip()
    if not query:
        return jsonify({"places": []})
    try:
        places = search_place(query)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502
    return jsonify({"places": places})


@app.route("/mypage")
@login_required_page
def mypage_page():
    return send_from_directory(STATIC_DIR, "mypage.html")


@app.route("/api/mypage")
@login_required_api
def api_mypage():
    username = session["username"]
    stats = db.get_recommend_stats(username)
    return jsonify(
        {
            "username": username,
            "recommend_count": stats["total_count"],
            "top_category": stats["top_category"],
            "trip_count": db.trips_per_member().get(username, 0),
            "favorite_count": len(db.list_favorite_restaurants(username)),
            "using_trained_model": is_using_trained_model(),
        }
    )


@app.route("/api/trips", methods=["POST"])
@login_required_api
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
        return (
            jsonify({"error": "start_lat, start_lng, end_lat, end_lng, start_ts, end_ts가 필요합니다."}),
            400,
        )

    member = session["username"]
    distance_m = haversine_m(start_lat, start_lng, end_lat, end_lng)
    duration_min = (end_ts - start_ts) / 1000 / 60
    if duration_min <= 0:
        return jsonify({"error": "end_ts가 start_ts보다 이후여야 합니다."}), 400

    start_dt = datetime.datetime.fromtimestamp(start_ts / 1000)

    trip = {
        "member": member,
        "distance_m": round(distance_m, 1),
        "duration_min": round(duration_min, 2),
        "hour": start_dt.hour,
        "dow": start_dt.weekday(),
        "recorded_at": start_dt.isoformat(),
    }
    db.add_trip(**trip)

    return jsonify({"saved": trip, "trip_count": db.trip_count()})


@app.route("/api/trips/count")
@login_required_api
def api_trip_count():
    return jsonify(
        {
            "trip_count": db.trip_count(),
            "using_trained_model": is_using_trained_model(),
            "per_member": db.trips_per_member(),
        }
    )


@app.route("/api/trips/recent")
@login_required_api
def api_trips_recent():
    return jsonify({"trips": db.list_trips(limit=20)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
