from flask import Blueprint, jsonify
from app.db.mongo import get_db
from app.db.queries import get_all_flights, get_active_flights
from app.optimization.solver import solve_airport_schedule
from app.db.queries import (
    get_active_flights,
    get_committed_schedule,
    save_schedule_assignments,
    save_schedule_version
)
from time import time
import app.services.scheduler_service as scheduler_service
from flask import request
from app.agents.explanation_agent import build_explanation_agent
from app.agents.multi_agent_coordinator import coordinator as multi_agent_coordinator
from app.services.analytics_service import get_dashboard_insights, get_flight_details

dash = Blueprint("health_api", __name__)
agent = build_explanation_agent()


def _top_bottlenecks(utilization_map, top_n=3):
    """
    Return a small list of the highest-utilization resources from a
    simple {resource_id: count} mapping so prompts stay compact.
    """
    if not isinstance(utilization_map, dict):
        return []

    items = [
        (rid, count)
        for rid, count in utilization_map.items()
        if rid not in (None, "Unknown")
    ]
    items.sort(key=lambda x: x[1], reverse=True)

    return [
        {"id": rid, "operations": int(count)}
        for rid, count in items[:top_n]
    ]

@dash.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "Backend is running"
    })


@dash.route("/db-check", methods=["GET"])
def db_check():
    try:
        db = get_db()

        # Ping the database
        db.command("ping")

        # List collections
        collections = db.list_collection_names()

        return jsonify({
            "db_connected": True,
            "database": db.name,
            "collections": collections
        })

    except Exception as e:
        return jsonify({
            "db_connected": False,
            "error": str(e)
        }), 500

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
        R=2,
        G=5,
        flights=flights,
        committed_schedule=committed,
        current_time=current_time,
        planning_horizon=planning_horizon,
        freeze_window=freeze_window
    )

    if result["status"] != "success":
        return result

    version = int(time())

    save_schedule_version(version, current_time, freeze_window, planning_horizon)

    save_schedule_assignments(
        result["schedule"],
        version,
        current_time + freeze_window
    )

    return result

@dash.route("/latest-schedule", methods=["GET"])
def get_latest_schedule():
    db = get_db()
    schedule = list(db["schedule"].find({}, {"_id": 0}))

    return {
        "status": "success",
        "schedule": schedule,
        "simulation_time": scheduler_service.simulation_time
    }


@dash.route("/dashboard-insights", methods=["GET"])
def dashboard_insights():
    """
    Returns aggregated KPIs and simple utilization metrics for the
    current simulation time window, optimized for the dashboard UI.
    """
    # Allow overriding the window via query param, default to 120 minutes.
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
    Use the explanation_agent to generate concise operational insights based on
    current KPIs, utilization, and a small sample of recent events.

    Expected JSON payload (all fields optional):
    {
        "question": "Why are delays increasing?",
        "window": 120
    }
    """
    payload = request.get_json(silent=True) or {}

    try:
        window = int(payload.get("window", 120))
    except (TypeError, ValueError):
        window = 120

    if window <= 0:
        window = 60

    current_time = scheduler_service.simulation_time
    base_insights = get_dashboard_insights(
        current_time=current_time, window_minutes=window
    )

    db = get_db()

    # Sample a small number of recent events to keep the prompt compact.
    recent_events_cursor = (
        db["event"]
        .find(
            {},
            {
                "_id": 0,
                "flight_id": 1,
                "type": 1,
                "timestamp": 1,
                "details": 1,
            },
        )
        .sort("timestamp", -1)
        .limit(20)
    )
    recent_events = list(recent_events_cursor)

    kpis = base_insights.get("kpis", {})
    runway_utilization = base_insights.get("runway_utilization", {})
    gate_utilization = base_insights.get("gate_utilization", {})

    context = {
        "simulation_time": current_time,
        "window_minutes": window,
        "kpis": kpis,
        "top_bottlenecks": {
            "runways": _top_bottlenecks(runway_utilization),
            "gates": _top_bottlenecks(gate_utilization),
        },
        "recent_events": recent_events,
    }

    user_question = payload.get(
        "question",
        "Provide a brief summary of the current airport operations situation, "
        "highlighting bottlenecks and any notable changes in delays or throughput.",
    )

    prompt = (
        "You are given structured, up-to-date airport operations data.\n"
        "1. First, quickly interpret the KPIs and bottlenecks.\n"
        "2. Then, answer the controller's question.\n"
        "3. Finish with 2–4 concise, actionable recommendations.\n\n"
        f"CONTEXT (JSON):\n{context}\n\n"
        f"QUESTION FROM CONTROLLER:\n{user_question}\n"
    )

    try:
        response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        answer = response["messages"][-1].content

        return jsonify(
            {
                "status": "success",
                "simulation_time": current_time,
                "window_minutes": window,
                "context": context,
                "answer": answer,
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@dash.route("/ai-query", methods=["POST"])
def ai_query():
    data = request.get_json()
    query = data.get("query")

    try:
        response = agent.invoke({"messages": [{"role": "user", "content": query}]})
        return {"response": response["messages"][-1].content}
    except Exception as e:
        return {"error": str(e)}, 500


@dash.route("/flight/<flight_id>/details", methods=["GET"])
def flight_details(flight_id: str):
    """
    Return rich per-flight information including:
    - basic flight document
    - schedule entry
    - event timeline
    - simple delay and delay breakdown
    """
    details = get_flight_details(flight_id)

    if isinstance(details, str):
        # Error string from service
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

    tasks = list(
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
            "service_tasks": tasks,
        }
    )


@dash.route("/multi-agent/step", methods=["POST"])
def multi_agent_step():
    """
    Manual trigger for a coordinator step. Useful for debugging or demoing.
    """
    payload = request.get_json(silent=True) or {}
    try:
        t = int(payload.get("time", scheduler_service.simulation_time))
    except (TypeError, ValueError):
        t = scheduler_service.simulation_time

    result = multi_agent_coordinator.step(current_time=t)
    return jsonify(result)