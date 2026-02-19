import random
from datetime import datetime
from app.db.mongo import get_db

AIRCRAFT_TYPES = ["A320", "B737", "A321"]

def generate_random_flight(current_time):

    flight_id = f"SIM{random.randint(1000,9999)}"

    flight = {
        "flight_id": flight_id,
        "scheduled_arrival": current_time + random.randint(5, 60),
        "max_delay": 30,
        "landing_duration": 5,
        "service_time": random.randint(30, 60),
        "max_turnaround": 90,
        "takeoff_duration": 5,
        "aircraft_type": random.choice(AIRCRAFT_TYPES),
        "status": "arriving"
    }

    db = get_db()
    db["flight"].insert_one(flight)

    print("Generated Flight:", flight_id)
