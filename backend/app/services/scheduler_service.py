import json
import os
import time
import traceback

from app.db.mongo import get_db
from app.db.queries import get_committed_schedule, save_schedule_assignments, save_schedule_version
from app.optimization.solver import solve_airport_schedule
from app.simulation.gates_from_geojson import gate_ids, gate_index_to_id
from app.agents.multi_agent_coordinator import coordinator as multi_agent_coordinator

simulation_time = 0

# Feed configuration for Zurich dataset ingestion.
_FEED_BATCH_SIZE = 3
_FEED_WINDOW_MINUTES = 20

_feed_loaded = False
_feed_rows = []
_feed_cursor = 0
_geojson_runways = []


def _data_file_path() -> str:
    # backend/app/services -> backend/data/zurich_flights_100.json
    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "data",
            "zurich_flights_100.json",
        )
    )


def _geojson_path() -> str:
    # backend/app/services -> project_root/frontend/public/lszh_airport.geojson
    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "frontend",
            "public",
            "lszh_airport.geojson",
        )
    )


def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _load_geojson_runways() -> list[str]:
    global _geojson_runways

    if _geojson_runways:
        return _geojson_runways

    path = _geojson_path()
    if not os.path.exists(path):
        _geojson_runways = ["16/34", "10/28", "14/32"]
        return _geojson_runways

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        refs = []
        seen = set()
        for feature in data.get("features", []):
            props = feature.get("properties") or {}
            if props.get("aeroway") != "runway":
                continue
            ref = str(props.get("ref") or props.get("name") or "").strip()
            if not ref or ref.startswith("H"):
                continue
            if ref in seen:
                continue
            seen.add(ref)
            refs.append(ref)

        # Keep deterministic ordering and prioritize runways the solver can use.
        preferred = ["16/34", "10/28", "14/32"]
        ordered = [r for r in preferred if r in refs] + [r for r in refs if r not in preferred]
        _geojson_runways = ordered or ["16/34", "10/28", "14/32"]
        return _geojson_runways
    except Exception as e:
        print(f"Runway GeoJSON load error: {e}")
        _geojson_runways = ["16/34", "10/28", "14/32"]
        return _geojson_runways


def _normalize_feed_row(raw: dict, index: int) -> dict:
    flight_id = (
        raw.get("flight_id")
        or raw.get("id")
        or raw.get("flight_number")
        or raw.get("callsign")
        or f"ZRH{index + 1:03d}"
    )

    scheduled_arrival = _safe_int(
        raw.get("scheduled_arrival", raw.get("arrival_time", raw.get("eta", 0))),
        0,
    )

    gates = gate_ids()
    runways = _load_geojson_runways()

    gate_choice = gates[index % len(gates)] if gates else "G1"
    runway_choice = runways[index % len(runways)] if runways else "16/34"

    return {
        "flight_id": str(flight_id),
        "scheduled_arrival": max(0, scheduled_arrival),
        "max_delay": _safe_int(raw.get("max_delay", 30), 30),
        "landing_duration": _safe_int(raw.get("landing_duration", 5), 5),
        "service_time": _safe_int(raw.get("service_time", 35), 35),
        "max_turnaround": _safe_int(raw.get("max_turnaround", 90), 90),
        "takeoff_duration": _safe_int(raw.get("takeoff_duration", 5), 5),
        "aircraft_type": str(raw.get("aircraft_type", "A320")),
        "status": "arriving",
        # Stored for realism/traceability; optimizer still computes actual assignment.
        "preferred_gate": gate_choice,
        "preferred_runway": runway_choice,
        "assigned_gate": gate_choice,
        "assigned_runway": runway_choice,
    }


def _load_feed_if_needed() -> None:
    global _feed_loaded, _feed_rows, _feed_cursor

    if _feed_loaded:
        return

    _feed_loaded = True
    _feed_rows = []
    _feed_cursor = 0

    path = _data_file_path()
    if not os.path.exists(path):
        print(
            "Flight feed file not found at "
            f"{path}. Scheduler will continue without dataset insertion."
        )
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        if isinstance(payload, dict):
            rows = payload.get("flights", [])
        elif isinstance(payload, list):
            rows = payload
        else:
            rows = []

        normalized = [_normalize_feed_row(r or {}, i) for i, r in enumerate(rows)]
        normalized.sort(key=lambda r: r.get("scheduled_arrival", 0))
        # Smooth bursty arrivals for a more realistic stream into the solver.
        min_gap = 2
        for i in range(1, len(normalized)):
            prev_arr = _safe_int(normalized[i - 1].get("scheduled_arrival", 0), 0)
            this_arr = _safe_int(normalized[i].get("scheduled_arrival", 0), 0)
            normalized[i]["scheduled_arrival"] = max(this_arr, prev_arr + min_gap)
        _feed_rows = normalized
        print(f"Loaded Zurich feed rows: {len(_feed_rows)}")
    except Exception as e:
        print(f"Failed to load Zurich feed: {e}")


def _insert_feed_batch(current_time: int) -> int:
    global _feed_cursor

    _load_feed_if_needed()
    if not _feed_rows:
        return 0

    db = get_db()
    inserted = 0

    while _feed_cursor < len(_feed_rows) and inserted < _FEED_BATCH_SIZE:
        row = _feed_rows[_feed_cursor]
        scheduled_arrival = int(row.get("scheduled_arrival", 0))

        # Rows are sorted by arrival; stop once we are outside the approach window.
        if scheduled_arrival > current_time + _FEED_WINDOW_MINUTES:
            break

        flight_id = row["flight_id"]
        exists = db["flight"].find_one({"flight_id": flight_id}, {"_id": 1})
        if not exists:
            db["flight"].insert_one(row)
            inserted += 1

        _feed_cursor += 1

    return inserted


def _predict_turnaround_minutes(flight: dict, current_time: int) -> int:
    base_service = max(1, _safe_int(flight.get("service_time", 30), 30))
    flight_id = flight.get("flight_id")
    if not flight_id:
        return base_service

    db = get_db()
    tasks = list(
        db["service_task"].find(
            {"flight_id": flight_id},
            {
                "_id": 0,
                "service_type": 1,
                "status": 1,
                "duration_min": 1,
                "start_time": 1,
                "end_time": 1,
                "stage_order": 1,
            },
        )
    )
    if not tasks:
        return base_service

    stage_order = {
        "passenger_bus": 0,
        "cleaning": 1,
        "fueling": 2,
        "catering": 3,
    }
    tasks.sort(
        key=lambda t: int(t.get("stage_order", stage_order.get(t.get("service_type"), 999)))
    )

    scheduled_arrival = _safe_int(flight.get("scheduled_arrival", current_time), current_time)
    landing_duration = max(1, _safe_int(flight.get("landing_duration", 5), 5))
    gate_arrival_anchor = scheduled_arrival + landing_duration

    cursor = max(current_time, gate_arrival_anchor)
    for task in tasks:
        status = str(task.get("status") or "pending")
        duration = max(1, _safe_int(task.get("duration_min", 5), 5))

        if status == "done":
            cursor = max(cursor, _safe_int(task.get("end_time", cursor), cursor))
            continue

        if status in ("scheduled", "active"):
            end_time = task.get("end_time")
            start_time = task.get("start_time")
            if end_time is not None:
                cursor = max(cursor, _safe_int(end_time, cursor))
            elif start_time is not None:
                cursor = max(cursor, _safe_int(start_time, cursor) + duration)
            else:
                cursor += duration
            continue

        # pending/blocked/unset -> remaining sequential work to execute
        cursor += duration

    predicted_total = max(base_service, cursor - gate_arrival_anchor)
    return int(predicted_total)


def _prepare_flights_for_solver(current_time: int) -> list[dict]:
    db = get_db()
    flights = list(
        db["flight"].find(
            {"status": {"$in": ["arriving", "landing", "taxiing"]}},
            {"_id": 0},
        )
    )

    enriched = []
    for flight in flights:
        item = dict(flight)

        # Guard against legacy/string values in DB docs.
        item["scheduled_arrival"] = _safe_int(
            item.get("scheduled_arrival", current_time),
            current_time,
        )
        item["max_delay"] = max(0, _safe_int(item.get("max_delay", 30), 30))
        item["landing_duration"] = max(1, _safe_int(item.get("landing_duration", 5), 5))
        item["takeoff_duration"] = max(1, _safe_int(item.get("takeoff_duration", 5), 5))

        predicted_turnaround = _predict_turnaround_minutes(item, current_time)
        item["service_time"] = predicted_turnaround
        item["max_turnaround"] = max(
            _safe_int(item.get("max_turnaround", predicted_turnaround), predicted_turnaround),
            predicted_turnaround,
        )
        enriched.append(item)

    return enriched


def _normalize_solver_schedule(schedule_rows: list[dict]) -> list[dict]:
    out = []
    for row in schedule_rows:
        item = dict(row)

        gate_index = item.get("gate_index")
        if gate_index is None:
            gate_num = _safe_int(item.get("gate", 1), 1)
            gate_index = max(0, gate_num - 1)

        item["gate_index"] = int(gate_index)
        item["gate"] = gate_index_to_id(int(gate_index) + 1)

        runway = str(item.get("runway") or "").strip()
        if not runway:
            runway_index = _safe_int(item.get("runway_index", 0), 0)
            runway = "16/34" if runway_index == 0 else ("10/28" if runway_index == 1 else "14/32")
        item["runway"] = runway

        out.append(item)

    return out


def cleanup_departed_flights(current_time):
    db = get_db()

    departed_flights = list(
        db["schedule"].find(
            {"takeoff_time": {"$lt": current_time}},
            {
                "_id": 0,
                "flight_id": 1,
                "landing_time": 1,
                "gate_arrival": 1,
                "gate_departure": 1,
                "takeoff_time": 1,
                "gate": 1,
                "gate_index": 1,
                "runway": 1,
                "runway_index": 1,
            },
        )
    )

    for flight in departed_flights:
        db["flight"].update_one(
            {"flight_id": flight["flight_id"]},
            {
                "$set": {
                    "status": "departed",
                    # Preserve realized schedule timings for historical views
                    # after schedule rows are cleaned up.
                    "landing_time": flight.get("landing_time"),
                    "gate_arrival": flight.get("gate_arrival"),
                    "gate_departure": flight.get("gate_departure"),
                    "takeoff_time": flight.get("takeoff_time"),
                    "gate": flight.get("gate"),
                    "gate_index": flight.get("gate_index"),
                    "runway": flight.get("runway"),
                    "runway_index": flight.get("runway_index"),
                }
            },
        )

    db["schedule"].delete_many({"takeoff_time": {"$lt": current_time}})


def run_scheduler(current_time):
    freeze_window = 15
    planning_horizon = 180

    flights = _prepare_flights_for_solver(current_time)
    committed = get_committed_schedule()

    gate_count = max(5, min(20, len(gate_ids()) or 5))

    runway_count = max(2, min(3, len(_load_geojson_runways()) or 2))

    result = solve_airport_schedule(
        R=runway_count,
        G=gate_count,
        flights=flights,
        committed_schedule=committed,
        current_time=current_time,
        planning_horizon=planning_horizon,
        freeze_window=freeze_window,
    )

    if result["status"] != "success":
        return

    normalized_schedule = _normalize_solver_schedule(result["schedule"])
    version = int(time.time())

    save_schedule_version(version, current_time, freeze_window, planning_horizon)
    save_schedule_assignments(normalized_schedule, version, current_time + freeze_window)


def scheduler_loop():
    global simulation_time

    while True:
        try:
            simulation_time += 1  # 1 minute per cycle
            current_time = simulation_time

            inserted = _insert_feed_batch(current_time)
            if inserted:
                print(f"Inserted flights this tick: {inserted}")

            run_scheduler(current_time)
            cleanup_departed_flights(current_time)

            try:
                multi_agent_coordinator.step(current_time=current_time)
            except Exception as e:
                print("Multi-agent step error:", e)

            print("Sim Time:", simulation_time)

        except Exception as e:
            print("Scheduler error:", e)
            traceback.print_exc()

        time.sleep(1)  # 1 second = 1 simulated minute









