import math
import json
import urllib.request
import urllib.parse
from flask import Blueprint, render_template, jsonify, request, abort
from flask_login import login_required, current_user
from app.models.service_task import ServiceTask
from app.models.app_settings import AppSettings

route_bp = Blueprint("route", __name__, url_prefix="/route")


# ─────────────────────────────────────────────────────────────────────────────
# Геокодирование через Яндекс Geocoder API
# ─────────────────────────────────────────────────────────────────────────────

def geocode_address(address: str, api_key: str) -> tuple[float, float] | None:
    """Возвращает (lat, lon) или None если не найдено."""
    if not address or not api_key:
        return None
    try:
        params = urllib.parse.urlencode({
            "apikey": api_key,
            "geocode": address,
            "format": "json",
            "results": 1,
        })
        url = f"https://geocode-maps.yandex.ru/1.x/?{params}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        pos = (data["response"]["GeoObjectCollection"]
               ["featureMember"][0]["GeoObject"]
               ["Point"]["pos"])
        lon, lat = map(float, pos.split())
        return lat, lon
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# TSP — алгоритм ближайшего соседа
# ─────────────────────────────────────────────────────────────────────────────

def haversine(p1: tuple, p2: tuple) -> float:
    """Расстояние между двумя точками (lat, lon) в км."""
    R = 6371.0
    lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def nearest_neighbor_tsp(points: list[dict]) -> list[dict]:
    """
    points: [{"label": str, "address": str, "lat": float, "lon": float, "task_id": int|None}, ...]
    Первый элемент — офис (стартовая точка), он не переставляется.
    Возвращает список в оптимальном порядке объезда.
    """
    if len(points) <= 2:
        return points

    start = points[0]
    rest  = list(points[1:])
    route = [start]

    while rest:
        current = route[-1]
        nearest = min(
            rest,
            key=lambda p: haversine(
                (current["lat"], current["lon"]),
                (p["lat"],       p["lon"])
            )
        )
        route.append(nearest)
        rest.remove(nearest)

    return route


def build_route_stats(route: list[dict]) -> list[dict]:
    """Добавляет расстояние от предыдущей точки к каждой."""
    for i, point in enumerate(route):
        if i == 0:
            point["dist_from_prev"] = 0.0
            point["dist_label"] = "Старт"
        else:
            d = haversine(
                (route[i-1]["lat"], route[i-1]["lon"]),
                (point["lat"],      point["lon"])
            )
            point["dist_from_prev"] = round(d, 1)
            point["dist_label"] = f"{d:.1f} км"
    total = sum(p["dist_from_prev"] for p in route[1:])
    return route, round(total, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Маршрут для группы план-заданий (по дате)
# ─────────────────────────────────────────────────────────────────────────────

@route_bp.route("/build")
@login_required
def build():
    """
    GET /route/build?task_ids=1,2,3,4,5
    Строит маршрут по переданным task_id.
    """
    ids_raw = request.args.get("task_ids", "")
    try:
        task_ids = [int(x) for x in ids_raw.split(",") if x.strip()]
    except ValueError:
        abort(400)

    if not task_ids:
        abort(400)

    tasks = ServiceTask.query.filter(ServiceTask.id.in_(task_ids)).all()
    if not tasks:
        abort(404)

    geo_key    = AppSettings.get("yandex_geo_key")
    maps_key   = AppSettings.get("yandex_maps_key")
    office_addr = AppSettings.get("office_address", "Москва")

    # Геокодируем офис
    office_coords = geocode_address(office_addr, geo_key)

    # Геокодируем все адреса
    points = []
    failed = []

    if office_coords:
        points.append({
            "label":    "Офис",
            "address":  office_addr,
            "lat":      office_coords[0],
            "lon":      office_coords[1],
            "task_id":  None,
            "number":   "🏢",
            "is_office": True,
        })

    for task in tasks:
        addr = task.object_address or task.object_name
        coords = geocode_address(addr, geo_key) if geo_key else None
        if coords:
            points.append({
                "label":    task.object_name,
                "address":  addr,
                "lat":      coords[0],
                "lon":      coords[1],
                "task_id":  task.id,
                "number":   task.number,
                "is_office": False,
            })
        else:
            failed.append({
                "task_id": task.id,
                "number":  task.number,
                "label":   task.object_name,
                "address": addr,
            })

    # Оптимизируем маршрут
    if len(points) >= 2:
        route = nearest_neighbor_tsp(points)
        route, total_km = build_route_stats(route)
    else:
        route = points
        total_km = 0.0

    # Нумеруем точки (кроме офиса)
    stop_num = 0
    for p in route:
        if not p.get("is_office"):
            stop_num += 1
            p["stop_num"] = stop_num
        else:
            p["stop_num"] = 0

    # Яндекс Навигатор deep-link
    # Формат: https://yandex.ru/maps/?rtext=lat,lon~lat,lon&rtt=auto
    waypoints = "~".join(f"{p['lat']},{p['lon']}" for p in route)
    nav_url = f"https://yandex.ru/maps/?rtext={waypoints}&rtt=auto&mode=routes"

    return render_template(
        "service/route.html",
        route=route,
        failed=failed,
        total_km=total_km,
        task_ids=ids_raw,
        maps_key=maps_key,
        office_addr=office_addr,
        nav_url=nav_url,
        has_geo_key=bool(geo_key),
    )


@route_bp.route("/api/route-json")
@login_required
def route_json():
    """JSON с точками маршрута для карты."""
    ids_raw = request.args.get("task_ids", "")
    try:
        task_ids = [int(x) for x in ids_raw.split(",") if x.strip()]
    except ValueError:
        return jsonify({"error": "bad ids"}), 400

    tasks = ServiceTask.query.filter(ServiceTask.id.in_(task_ids)).all()
    geo_key = AppSettings.get("yandex_geo_key")
    office_addr = AppSettings.get("office_address", "Москва")

    office_coords = geocode_address(office_addr, geo_key)
    points = []

    if office_coords:
        points.append({
            "label": "Офис", "address": office_addr,
            "lat": office_coords[0], "lon": office_coords[1],
            "task_id": None, "is_office": True
        })

    for task in tasks:
        addr = task.object_address or task.object_name
        coords = geocode_address(addr, geo_key) if geo_key else None
        if coords:
            points.append({
                "label": task.object_name, "address": addr,
                "lat": coords[0], "lon": coords[1],
                "task_id": task.id, "number": task.number,
                "is_office": False
            })

    if len(points) >= 2:
        route = nearest_neighbor_tsp(points)
        route, total_km = build_route_stats(route)
    else:
        route = points
        total_km = 0.0

    return jsonify({"route": route, "total_km": total_km})