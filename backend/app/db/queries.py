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
