from flask import Blueprint, jsonify, request
from time import time

import app.services.scheduler_service as scheduler_service
from app.agents.multi_agent_coordinator import coordinator as multi_agent_coordinator
from app.db.mongo import get_db
from app.db.queries import (
    get_active_flights,
    get_all_flights,
    get_committed_schedule,
    save_schedule_assignments,
    save_schedule_version,
)
from app.optimization.solver import solve_airport_schedule
from app.services.analytics_service import get_dashboard_insights, get_flight_details


dash = Blueprint("health_api", __name__)

# Explanation-agent invocation is intentionally disabled for the current phase.
# from app.agents.explanation_agent import build_explanation_agent
# agent = build_explanation_agent()


def _top_bottlenecks(utilization_map, top_n=3):
    if not isinstance(utilization_map, dict):
        return []

    items = [
        (rid, count)
        for rid, count in utilization_map.items()
        if rid not in (None, "Unknown")
    ]
    items.sort(key=lambda x: x[1], reverse=True)

    return [{"id": rid, "operations": int(count)} for rid, count in items[:top_n]]


@dash.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Backend is running"})


@dash.route("/db-check", methods=["GET"])
def db_check():
    try:
        db = get_db()
        db.command("ping")
        collections = db.list_collection_names()

        return jsonify(
            {
                "db_connected": True,
                "database": db.name,
                "collections": collections,
            }
        )

    except Exception as e:
        return jsonify({"db_connected": False, "error": str(e)}), 500


@dash.route("/dashboard")
def all_flights():
    return jsonify(get_all_flights())


def active_flights():
    return jsonify(get_active_flights())


@dash.route("/schedule", methods=["GET"])
def generate_schedule():
    current_time = 10  # example day minute
    freeze_window = 15
    planning_horizon = 180

    flights = get_active_flights()
    committed = get_committed_schedule()

    result = solve_airport_schedule(
        R=3,
        G=5,
        flights=flights,
        committed_schedule=committed,
        current_time=current_time,
        planning_horizon=planning_horizon,
        freeze_window=freeze_window,
    )

    if result["status"] != "success":
        return result

    version = int(time())

    save_schedule_version(version, current_time, freeze_window, planning_horizon)
    save_schedule_assignments(result["schedule"], version, current_time + freeze_window)

    return result


@dash.route("/latest-schedule", methods=["GET"])
def get_latest_schedule():
    db = get_db()
    schedule = list(db["schedule"].find({}, {"_id": 0}))

    # Backfill runway label for older rows that may only have runway_index.
    for row in schedule:
        runway = str(row.get("runway") or "").strip()
        if runway:
            continue
        try:
            idx = int(row.get("runway_index", -1))
        except (TypeError, ValueError):
            idx = -1
        if idx == 0:
            row["runway"] = "16/34"
        elif idx == 1:
            row["runway"] = "10/28"
        elif idx == 2:
            row["runway"] = "14/32"

    return {
        "status": "success",
        "schedule": schedule,
        "simulation_time": scheduler_service.simulation_time,
    }


@dash.route("/dashboard-insights", methods=["GET"])
def dashboard_insights():
    try:
        window = int(request.args.get("window", 120))
    except (TypeError, ValueError):
        window = 120

    current_time = scheduler_service.simulation_time
    insights = get_dashboard_insights(current_time=current_time, window_minutes=window)

    return jsonify(
        {
            "status": "success",
            "simulation_time": current_time,
            "window_minutes": window,
            **insights,
        }
    )


@dash.route("/ai-insights", methods=["POST"])
def ai_insights():
    """
    Explanation agent is temporarily disabled.
    Keep endpoint response shape stable for frontend compatibility.
    """
    payload = request.get_json(silent=True) or {}
    try:
        window = int(payload.get("window", 120))
    except (TypeError, ValueError):
        window = 120

    if window <= 0:
        window = 60

    current_time = scheduler_service.simulation_time
    base_insights = get_dashboard_insights(current_time=current_time, window_minutes=window)

    context = {
        "simulation_time": current_time,
        "window_minutes": window,
        "kpis": base_insights.get("kpis", {}),
        "top_bottlenecks": {
            "runways": _top_bottlenecks(base_insights.get("runway_utilization", {})),
            "gates": _top_bottlenecks(base_insights.get("gate_utilization", {})),
        },
        "recent_events": [],
    }

    return jsonify(
        {
            "status": "success",
            "simulation_time": current_time,
            "window_minutes": window,
            "context": context,
            "answer": "AI explanation is temporarily disabled for this demo phase.",
        }
    )


@dash.route("/ai-query", methods=["POST"])
def ai_query():
    return {
        "error": "AI query is temporarily disabled for this demo phase."
    }, 503


@dash.route("/flight/<flight_id>/details", methods=["GET"])
def flight_details(flight_id: str):
    details = get_flight_details(flight_id)

    if isinstance(details, str):
        return jsonify({"status": "error", "message": details}), 404

    return jsonify({"status": "success", "details": details})


@dash.route("/surface-state", methods=["GET"])
def surface_state():
    db = get_db()
    try:
        window = int(request.args.get("window", 60))
    except (TypeError, ValueError):
        window = 60

    current_time = scheduler_service.simulation_time
    horizon_end = current_time + max(1, window)

    docs = list(
        db["surface_state"].find(
            {"end_time": {"$gte": current_time}, "start_time": {"$lte": horizon_end}},
            {"_id": 0},
        )
    )
    return jsonify(
        {
            "status": "success",
            "simulation_time": current_time,
            "window_minutes": window,
            "surface_state": docs,
        }
    )


@dash.route("/resources", methods=["GET"])
def resources_state():
    db = get_db()
    resources = list(db["resource"].find({}, {"_id": 0}))

    try:
        limit = int(request.args.get("tasks", 100))
    except (TypeError, ValueError):
        limit = 100

    tasks = (
        db["service_task"]
        .find({}, {"_id": 0})
        .sort("window_end", 1)
        .limit(max(1, limit))
    )

    return jsonify(
        {
            "status": "success",
            "simulation_time": scheduler_service.simulation_time,
            "resources": resources,
            "service_tasks": list(tasks),
        }
    )


@dash.route("/multi-agent/step", methods=["POST"])
def multi_agent_step():
    payload = request.get_json(silent=True) or {}
    try:
        t = int(payload.get("time", scheduler_service.simulation_time))
    except (TypeError, ValueError):
        t = scheduler_service.simulation_time

    result = multi_agent_coordinator.step(current_time=t)
    return jsonify(result)


