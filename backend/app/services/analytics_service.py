from app.db.mongo import get_db


def get_runway_utilization(current_time):
    db = get_db()

    flights = list(db["schedule"].find({}, {"_id": 0}))

    runway_counts = {}

    for f in flights:
        runway = f.get("runway", "Unknown")
        runway_counts[runway] = runway_counts.get(runway, 0) + 1

    return runway_counts


def get_gate_utilization(current_time):
    db = get_db()

    flights = list(db["schedule"].find({}, {"_id": 0}))

    gate_counts = {}

    for f in flights:
        gate = f.get("gate")
        gate_counts[gate] = gate_counts.get(gate, 0) + 1

    return gate_counts


def get_flight_delay(flight_id):
    db = get_db()

    flight = db["flight"].find_one(
        {"flight_id": flight_id},
        {"_id": 0}
    )

    if not flight:
        return "Flight not found"

    scheduled = flight["scheduled_arrival"]

    schedule_entry = db["schedule"].find_one(
        {"flight_id": flight_id},
        {"_id": 0}
    )

    if not schedule_entry:
        return "Flight not scheduled yet"

    actual = schedule_entry["landing_time"]

    delay = actual - scheduled

    return {
        "scheduled": scheduled,
        "actual": actual,
        "delay": delay
    }