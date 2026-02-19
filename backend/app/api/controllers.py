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

dash = Blueprint("health_api", __name__)

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
