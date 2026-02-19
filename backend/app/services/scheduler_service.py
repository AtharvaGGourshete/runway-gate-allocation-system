import threading
import time
import random

from app.simulation.flight_generator import generate_random_flight
from app.db.queries import (
    get_active_flights,
    get_committed_schedule,
    save_schedule_assignments,
    save_schedule_version,
)
from app.optimization.solver import solve_airport_schedule
from app.db.mongo import get_db

simulation_time = 0

def cleanup_departed_flights(current_time):

    db = get_db()

    # Find flights whose takeoff_time has passed
    departed_flights = list(
        db["schedule"].find(
            {"takeoff_time": {"$lt": current_time}},
            {"flight_id": 1}
        )
    )

    for flight in departed_flights:

        # Mark flight as departed
        db["flight"].update_one(
            {"flight_id": flight["flight_id"]},
            {"$set": {"status": "departed"}}
        )

    # Remove old schedule entries
    db["schedule"].delete_many(
        {"takeoff_time": {"$lt": current_time}}
    )


def run_scheduler(current_time):

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
        return

    version = int(time.time())

    save_schedule_version(version, current_time, freeze_window, planning_horizon)

    save_schedule_assignments(
        result["schedule"],
        version,
        current_time + freeze_window
    )


def scheduler_loop():

    global simulation_time

    while True:
        try:
            simulation_time += 1  # 1 minute per cycle

            current_time = simulation_time

            db = get_db()

            # cap active flights
            active_count = db["flight"].count_documents(
                {"status": {"$ne": "departed"}}
            )

            if active_count < 50:
                generate_random_flight(current_time)

            run_scheduler(current_time)

            cleanup_departed_flights(current_time)

            print("Sim Time:", simulation_time)

        except Exception as e:
            print("Scheduler error:", e)

        time.sleep(1)  # 1 second = 1 simulated minute
