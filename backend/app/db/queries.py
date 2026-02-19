from datetime import datetime
from app.db.models.flight import Flight
from app.db.models.gate import Gate
from app.db.models.runway import Runway
from app.db.models.event import Event
from app.db.models.metrics import Metrics
from app.db.mongo import get_db 

def save_flight(flight: Flight):
    db = get_db()
    db["flight"].insert_one(flight.dict())
    
def save_gate(gate: Gate):
    db = get_db()
    db["gate"].insert_one(gate.dict())

def save_runway(runway: Runway):
    db = get_db()
    db["runway"].insert_one(runway.dict())

def log_event(event_type, flight_id=None, resource=None, action=""):
    db = get_db()
    event = Event(
        timestamp=datetime.utcnow().timestamp(),
        type=event_type,
        flight_id=flight_id,
        resource=resource,
        action=action,
    )
    db["event"].insert_one(event.dict())
    
def save_metrics(metrics: Metrics):
    db = get_db()
    db["metrics"].insert_one(metrics.dict())
    
def update_gate_status(gate_id: str, status: str):
    db = get_db()
    db["gate"].update_one(
        {"gate_id": gate_id},
        {"$set": {"status": status, "occupied_by": None}}
    )

def update_runway_status(runway_id: str, status: str):
    db = get_db()
    db["runway"].update_one(
        {"runway_id": runway_id},
        {"$set": {"status": status, "occupied_by": None}}
    )

def get_all_flights():
    db = get_db()
    flights = list(db["flight"].find({}, {"_id": 0}))
    return flights

def get_active_flights():
    db = get_db()
    return list(
        db["flight"].find(
            {"status": {"$in": ["arriving", "landing", "taxiing"]}},
            {"_id": 0}
        )
    )
def save_schedule_version(version, current_time, freeze_window, planning_horizon):
    db = get_db()
    db["schedule_meta"].insert_one({
        "version": version,
        "run_time": datetime.utcnow().timestamp(),
        "current_time": current_time,
        "freeze_window": freeze_window,
        "planning_horizon": planning_horizon
    })

def save_schedule_assignments(schedule, version, freeze_end):
    db = get_db()

    # Remove old non-frozen future schedule
    db["schedule"].delete_many({"frozen": False})

    for s in schedule:

        is_frozen = s["landing_time"] < freeze_end

        db["schedule"].update_one(
            {"flight_id": s["flight_id"]},
            {
                "$set": {
                    "landing_time": s["landing_time"],
                    "gate": s["gate"],
                    "gate_arrival": s["gate_arrival"],
                    "gate_departure": s["gate_departure"],
                    "takeoff_time": s["takeoff_time"],
                    "frozen": is_frozen,
                    "schedule_version": version,
                    "created_at": datetime.utcnow().timestamp()
                }
            },
            upsert=True
        )

def get_committed_schedule():
    db = get_db()
    return list(
        db["schedule"].find(
            {"frozen": True},
            {"_id": 0}
        )
    )
