from typing import Any, Dict, List, Tuple

from app.db.mongo import get_db


def get_runway_utilization(current_time: int) -> Dict[str, int]:
    """
    Simple aggregate of how many scheduled operations each runway has overall.
    Kept for backward-compatibility; does not use current_time.
    """
    db = get_db()

    flights = list(db["schedule"].find({}, {"_id": 0, "runway": 1}))

    runway_counts: Dict[str, int] = {}

    for f in flights:
        runway = f.get("runway", "Unknown")
        runway_counts[runway] = runway_counts.get(runway, 0) + 1

    return runway_counts


def get_gate_utilization(current_time: int) -> Dict[str, int]:
    """
    Simple aggregate of how many scheduled operations each gate has overall.
    Kept for backward-compatibility; does not use current_time.
    """
    db = get_db()

    flights = list(db["schedule"].find({}, {"_id": 0, "gate": 1}))

    gate_counts: Dict[str, int] = {}

    for f in flights:
        gate = f.get("gate", "Unknown")
        gate_counts[gate] = gate_counts.get(gate, 0) + 1

    return gate_counts


def get_flight_delay(flight_id: str) -> Dict[str, Any] | str:
    """
    Compute delay for a single flight based on its scheduled_arrival and
    the landing_time from the schedule collection.
    """
    db = get_db()

    flight = db["flight"].find_one(
        {"flight_id": flight_id},
        {"_id": 0, "scheduled_arrival": 1},
    )

    if not flight:
        return "Flight not found"

    scheduled = flight.get("scheduled_arrival")
    if scheduled is None:
        return "Flight has no scheduled_arrival"

    schedule_entry = db["schedule"].find_one(
        {"flight_id": flight_id},
        {"_id": 0, "landing_time": 1},
    )

    if not schedule_entry:
        return "Flight not scheduled yet"

    actual = schedule_entry.get("landing_time")
    if actual is None:
        return "Flight schedule has no landing_time"

    delay = actual - scheduled

    return {
        "scheduled": scheduled,
        "actual": actual,
        "delay": delay,
    }


def _collect_schedule_and_flights() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Helper to load all schedule entries and the corresponding flight docs
    into memory. This keeps aggregation logic in Python and avoids complex
    aggregation pipelines while the dataset is relatively small.
    """
    db = get_db()

    schedule: List[Dict[str, Any]] = list(
        db["schedule"].find(
            {},
            {
                "_id": 0,
                "flight_id": 1,
                "landing_time": 1,
                "takeoff_time": 1,
                "runway": 1,
                "gate": 1,
            },
        )
    )

    flight_ids = {s["flight_id"] for s in schedule if "flight_id" in s}

    flights_cursor = db["flight"].find(
        {"flight_id": {"$in": list(flight_ids)}},
        {
            "_id": 0,
            "flight_id": 1,
            "scheduled_arrival": 1,
            "status": 1,
        },
    )
    flights = {f["flight_id"]: f for f in flights_cursor}

    return schedule, flights


def get_flight_details(flight_id: str) -> Dict[str, Any] | str:
    """
    Return a rich view of a single flight including:
    - Basic flight document
    - Schedule entry
    - Event timeline
    - Simple delay information and breakdown
    """
    db = get_db()

    flight = db["flight"].find_one({"flight_id": flight_id}, {"_id": 0})
    if not flight:
        return "Flight not found"

    schedule_entry = db["schedule"].find_one({"flight_id": flight_id}, {"_id": 0})

    # Events are stored with wall-clock timestamps (seconds since epoch).
    # We sort ascending so the UI can show a chronological timeline.
    events_cursor = (
        db["event"]
        .find({"flight_id": flight_id}, {"_id": 0})
        .sort("timestamp", 1)
    )
    events: List[Dict[str, Any]] = list(events_cursor)

    # Attach a coarse-grained "phase" label based on the event type so the
    # frontend can group them visually without hard-coding this mapping.
    phase_map = {
        "flight_arrived": "arrival",
        "landing_started": "landing",
        "landed": "landing",
        "taxi_started": "taxiing",
        "taxi_completed": "taxiing",
        "parked": "at_gate",
        "pushback_started": "pushback",
        "pushback_completed": "pushback",
        "takeoff_started": "takeoff",
        "takeoff_completed": "takeoff",
    }

    for ev in events:
        ev_type = ev.get("type")
        if ev_type:
            ev["phase"] = phase_map.get(ev_type, "other")

    # Basic delay computation using scheduled_arrival vs landing_time when available.
    scheduled = flight.get("scheduled_arrival")
    landing_time = schedule_entry.get("landing_time") if schedule_entry else None

    delay_minutes: int | None = None
    if scheduled is not None and landing_time is not None:
        delay_minutes = int(landing_time - scheduled)

    # Very simple breakdown: for now we expose the total delay and leave room
    # for future per-phase attribution as the simulation logs become richer.
    delay_info: Dict[str, Any] | None = None
    if delay_minutes is not None:
        delay_info = {
            "scheduled_arrival": scheduled,
            "actual_landing": landing_time,
            "delay_minutes": delay_minutes,
        }

    delay_breakdown: Dict[str, Any] | None = None
    if delay_minutes is not None:
        delay_breakdown = {
            "total_delay_minutes": delay_minutes,
            "segments": [
                {
                    "label": "Arrival to landing",
                    "delay_minutes": delay_minutes,
                }
            ],
        }

    return {
        "flight_id": flight_id,
        "flight": flight,
        "schedule": schedule_entry,
        "events": events,
        "delay": delay_info,
        "delay_breakdown": delay_breakdown,
    }


def get_dashboard_insights(current_time: int, window_minutes: int = 120) -> Dict[str, Any]:
    """
    Compute global KPIs and simple utilization metrics for the dashboard.

    - Uses a historical window [current_time - window_minutes, current_time]
      to compute throughput, delay statistics, and utilization.
    - Also computes simple counts of upcoming arrivals/departures in the
      next window_minutes into the future for quick look-ahead.
    """
    if window_minutes <= 0:
        window_minutes = 60

    history_start = max(0, current_time - window_minutes)
    history_end = current_time
    future_end = current_time + window_minutes

    db = get_db()

    # Active flights: anything not yet departed.
    active_flights_count = db["flight"].count_documents(
        {"status": {"$ne": "departed"}}
    )

    total_flights_count = db["flight"].count_documents({})

    schedule, flights = _collect_schedule_and_flights()

    # Aggregation buckets
    delays: List[int] = []
    runway_counts: Dict[str, int] = {}
    gate_counts: Dict[str, int] = {}

    history_flights_count = 0
    upcoming_arrivals = 0
    upcoming_departures = 0

    for s in schedule:
        landing_time = s.get("landing_time")
        takeoff_time = s.get("takeoff_time")
        flight_id = s.get("flight_id")

        # Historical window: throughput, delay stats, utilization
        if landing_time is not None and history_start <= landing_time <= history_end:
            history_flights_count += 1

            # Delay, if we have scheduled_arrival for this flight
            flight = flights.get(flight_id or "")
            if flight is not None:
                scheduled = flight.get("scheduled_arrival")
                if scheduled is not None:
                    delays.append(landing_time - scheduled)

            # Utilization counts
            runway = s.get("runway", "Unknown")
            gate = s.get("gate", "Unknown")

            runway_counts[runway] = runway_counts.get(runway, 0) + 1
            gate_counts[gate] = gate_counts.get(gate, 0) + 1

        # Future window: upcoming arrivals/departures
        if landing_time is not None and current_time < landing_time <= future_end:
            upcoming_arrivals += 1

        if takeoff_time is not None and current_time < takeoff_time <= future_end:
            upcoming_departures += 1

    # Delay statistics
    avg_delay = sum(delays) / len(delays) if delays else 0.0
    max_delay = max(delays) if delays else 0
    if delays:
        on_time_count = sum(1 for d in delays if d <= 0)
        on_time_percentage = on_time_count / len(delays)
    else:
        on_time_percentage = 1.0

    # Throughput: flights per hour in the historical window
    hours = window_minutes / 60.0
    if hours > 0:
        flights_per_hour = history_flights_count / hours
    else:
        flights_per_hour = 0.0

    kpis: Dict[str, Any] = {
        "active_flights": active_flights_count,
        "total_flights": total_flights_count,
        "avg_delay": avg_delay,
        "max_delay": max_delay,
        "on_time_percentage": on_time_percentage,
        "upcoming_arrivals": upcoming_arrivals,
        "upcoming_departures": upcoming_departures,
        "flights_per_hour": flights_per_hour,
    }

    return {
        "kpis": kpis,
        "runway_utilization": runway_counts,
        "gate_utilization": gate_counts,
    }
