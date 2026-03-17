from langchain.tools import tool
from app.simulation.state import gate_status, runway_status
from app.services.analytics_service import (
    get_runway_utilization,
    get_gate_utilization,
    get_flight_delay,
    get_dashboard_insights,
)
import app.services.scheduler_service as scheduler_service
from app.db.mongo import get_db

@tool
def check_gate_availability(flight_id: str) -> str:
    """
    Returns an available gate for the flight.
    """
    for gate, status in gate_status.items():
        if status == "available":
            print(f"[Tool] Assigned gate {gate} to {flight_id}")
            return gate

    raise ValueError("No available gates")

@tool
def suggest_runway(flight_id: str) -> str:
    """
    Returns an available runway for the flight.
    """
    for runway, status in runway_status.items():
        if status == "available":
            print(f"[Tool] Assigned runway {runway} to {flight_id}")
            return runway

    raise ValueError("No available runways")

@tool
def resolve_conflict(flight_id: str) -> str:
    """
    Handles conflicts when no resources are available.
    """
    print(f"[Tool] Conflict detected for {flight_id}")
    return "WAIT"

@tool
def runway_utilization():
    """Returns runway usage statistics."""
    return get_runway_utilization(scheduler_service.simulation_time)


@tool
def gate_utilization():
    """Returns gate usage statistics."""
    return get_gate_utilization(scheduler_service.simulation_time)


@tool
def flight_delay(flight_id: str):
    """Returns delay information for a specific flight ID."""
    return get_flight_delay(flight_id)


@tool
def operations_snapshot(window_minutes: int = 120):
    """Returns KPI snapshot and top runway/gate bottlenecks for the current simulation window."""
    current_time = scheduler_service.simulation_time
    insights = get_dashboard_insights(current_time=current_time, window_minutes=max(1, int(window_minutes)))

    def top_items(items: dict, n: int = 3):
        rows = []
        if not isinstance(items, dict):
            return rows
        for k, v in items.items():
            if k in (None, "Unknown"):
                continue
            try:
                rows.append({"id": k, "operations": int(v)})
            except Exception:
                continue
        rows.sort(key=lambda x: x["operations"], reverse=True)
        return rows[:n]

    return {
        "simulation_time": current_time,
        "window_minutes": max(1, int(window_minutes)),
        "kpis": insights.get("kpis", {}),
        "top_runways": top_items(insights.get("runway_utilization", {})),
        "top_gates": top_items(insights.get("gate_utilization", {})),
    }


@tool
def high_risk_flights(limit: int = 5):
    """Returns flights with lowest delay headroom based on scheduled/max_delay vs planned/actual landing."""
    db = get_db()
    n = max(1, min(20, int(limit)))

    flights = list(
        db["flight"].find(
            {"status": {"$ne": "departed"}},
            {"_id": 0, "flight_id": 1, "scheduled_arrival": 1, "max_delay": 1},
        )
    )
    schedule = list(
        db["schedule"].find(
            {},
            {"_id": 0, "flight_id": 1, "landing_time": 1},
        )
    )
    by_fid = {s.get("flight_id"): s for s in schedule if s.get("flight_id")}

    risk_rows = []
    for f in flights:
        fid = f.get("flight_id")
        if not fid:
            continue
        try:
            arr = int(f.get("scheduled_arrival"))
            max_delay = int(f.get("max_delay", 30))
        except Exception:
            continue
        landing = by_fid.get(fid, {}).get("landing_time")
        if landing is None:
            continue
        try:
            landing = int(landing)
        except Exception:
            continue
        delay = landing - arr
        headroom = max_delay - delay
        risk_rows.append(
            {
                "flight_id": fid,
                "scheduled_arrival": arr,
                "planned_landing": landing,
                "delay_minutes": delay,
                "remaining_headroom": headroom,
            }
        )

    risk_rows.sort(key=lambda x: (x["remaining_headroom"], -x["delay_minutes"], x["flight_id"]))
    return risk_rows[:n]


@tool
def gse_overview():
    """Returns ground resource and task pipeline summary (busy/idle and task states)."""
    db = get_db()
    resources = list(db["resource"].find({}, {"_id": 0, "status": 1}))
    tasks = list(db["service_task"].find({}, {"_id": 0, "status": 1}))

    busy = 0
    idle = 0
    for r in resources:
        status = str(r.get("status", "idle")).lower()
        if status == "busy":
            busy += 1
        else:
            idle += 1

    task_counts = {"blocked": 0, "pending": 0, "scheduled": 0, "active": 0, "done": 0}
    for t in tasks:
        s = str(t.get("status", "")).lower()
        if s in task_counts:
            task_counts[s] += 1

    return {
        "resources_total": len(resources),
        "busy": busy,
        "idle": idle,
        "tasks": task_counts,
    }


@tool
def surface_overview(window_minutes: int = 60):
    """Returns taxi plan summary in the given window (taxi_in/taxi_out and average hold)."""
    db = get_db()
    current_time = scheduler_service.simulation_time
    horizon = current_time + max(1, int(window_minutes))

    docs = list(
        db["surface_state"].find(
            {"end_time": {"$gte": current_time}, "start_time": {"$lte": horizon}},
            {"_id": 0, "mode": 1, "hold_minutes": 1},
        )
    )

    taxi_in = 0
    taxi_out = 0
    holds = []
    for d in docs:
        mode = str(d.get("mode", "")).lower()
        if mode == "taxi_in":
            taxi_in += 1
        elif mode == "taxi_out":
            taxi_out += 1
        try:
            holds.append(int(d.get("hold_minutes", 0)))
        except Exception:
            holds.append(0)

    avg_hold = round((sum(holds) / len(holds)), 2) if holds else 0.0
    return {
        "simulation_time": current_time,
        "window_minutes": max(1, int(window_minutes)),
        "plans_total": len(docs),
        "taxi_in": taxi_in,
        "taxi_out": taxi_out,
        "avg_hold_minutes": avg_hold,
    }
