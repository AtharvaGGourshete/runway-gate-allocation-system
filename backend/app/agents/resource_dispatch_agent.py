from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.db.mongo import get_db
from app.db.queries import log_event
from app.simulation.airport_graph import AirportGraph
from app.simulation.gates_from_geojson import gate_ids, gate_index_to_id


def _gate_node(gate_value: Any) -> str:
    """
    Normalize schedule gate values to real LSZH gate identifiers taken from the
    shared GeoJSON file used by the frontend.
    """
    ids = gate_ids()

    if isinstance(gate_value, str):
        if gate_value in ids:
            return gate_value
        try:
            n = int(gate_value)
            return gate_index_to_id(n)
        except Exception:
            return ids[0] if ids else "G1"

    try:
        n = int(gate_value)
        return gate_index_to_id(n)
    except Exception:
        return ids[0] if ids else "G1"


@dataclass(frozen=True)
class ServiceSpec:
    service_type: str
    resource_type: str
    duration_min: int


DEFAULT_SERVICES: List[ServiceSpec] = [
    ServiceSpec(service_type="cleaning", resource_type="cleaning_team", duration_min=10),
    ServiceSpec(service_type="fueling", resource_type="fuel_truck", duration_min=15),
    ServiceSpec(service_type="catering", resource_type="catering_truck", duration_min=8),
]


DEFAULT_RESOURCES = [
    {"resource_id": "FUEL1", "resource_type": "fuel_truck"},
    {"resource_id": "FUEL2", "resource_type": "fuel_truck"},
    {"resource_id": "CATER1", "resource_type": "catering_truck"},
    {"resource_id": "CLEAN1", "resource_type": "cleaning_team"},
    {"resource_id": "TUG1", "resource_type": "tug"},
    {"resource_id": "BUS1", "resource_type": "bus"},
]


class ResourceDispatchAgent:
    """
    Step-based resource dispatch agent (GSE beyond gates), without SimPy.

    - Creates/updates service tasks for flights at gate
    - Assigns available resources to tasks using a deterministic greedy policy
      (nearest-available + lateness penalty)
    """

    def __init__(self, graph: Optional[AirportGraph] = None):
        self.graph = graph or AirportGraph()

    def _ensure_resources(self, current_time: int) -> int:
        db = get_db()
        created = 0
        for r in DEFAULT_RESOURCES:
            exists = db["resource"].find_one({"resource_id": r["resource_id"]}, {"_id": 1})
            if exists:
                continue
            db["resource"].insert_one(
                {
                    "resource_id": r["resource_id"],
                    "resource_type": r["resource_type"],
                    "status": "idle",
                    "location_node": "DEPOT",
                    "available_at": current_time,
                    "current_task": None,
                }
            )
            created += 1
        return created

    def step(
        self,
        current_time: int,
        window_minutes: int = 60,
        lateness_penalty: float = 5.0,
    ) -> Dict[str, Any]:
        db = get_db()
        horizon_end = current_time + max(1, window_minutes)

        created_resources = self._ensure_resources(current_time)

        # Flights in the system (scheduled) that are at gate now or soon.
        schedule = list(
            db["schedule"].find(
                {
                    "gate_arrival": {"$lte": horizon_end},
                    "gate_departure": {"$gte": current_time},
                },
                {
                    "_id": 0,
                    "flight_id": 1,
                    "gate": 1,
                    "gate_arrival": 1,
                    "gate_departure": 1,
                },
            )
        )

        # Create missing service tasks for flights that are (or will be) at gate.
        created_tasks = 0
        for s in schedule:
            fid = s.get("flight_id")
            if not fid:
                continue
            gate_node = _gate_node(s.get("gate"))
            for spec in DEFAULT_SERVICES:
                key = {"flight_id": fid, "service_type": spec.service_type}
                existing = db["service_task"].find_one(key, {"_id": 1})
                if existing:
                    continue
                db["service_task"].insert_one(
                    {
                        "flight_id": fid,
                        "gate_node": gate_node,
                        "service_type": spec.service_type,
                        "resource_type": spec.resource_type,
                        "duration_min": spec.duration_min,
                        "window_start": int(s.get("gate_arrival") or current_time),
                        "window_end": int(s.get("gate_departure") or horizon_end),
                        "status": "pending",  # pending|scheduled|active|done
                        "assigned_resource_id": None,
                        "start_time": None,
                        "end_time": None,
                        "last_updated_at": current_time,
                    }
                )
                created_tasks += 1

        # Update task statuses as time moves.
        db["service_task"].update_many(
            {"status": "scheduled", "start_time": {"$lte": current_time}},
            {"$set": {"status": "active", "last_updated_at": current_time}},
        )
        db["service_task"].update_many(
            {"status": "active", "end_time": {"$lte": current_time}},
            {"$set": {"status": "done", "last_updated_at": current_time}},
        )

        # Free up resources that finished tasks.
        done_resources = list(
            db["resource"].find(
                {"status": "busy", "available_at": {"$lte": current_time}},
                {"_id": 0, "resource_id": 1},
            )
        )
        for r in done_resources:
            db["resource"].update_one(
                {"resource_id": r["resource_id"]},
                {"$set": {"status": "idle", "current_task": None}},
            )

        # Dispatch: choose assignments for pending tasks whose window includes now.
        pending_tasks = list(
            db["service_task"].find(
                {
                    "status": "pending",
                    "window_start": {"$lte": horizon_end},
                    "window_end": {"$gte": current_time},
                },
                {"_id": 0},
            )
        )

        # Deterministic ordering: earliest window_end first to reduce missed turns.
        pending_tasks.sort(key=lambda t: (t.get("window_end", 0), t.get("flight_id", ""), t.get("service_type", "")))

        assigned = 0
        for task in pending_tasks:
            gate_node = task.get("gate_node") or "G1"
            res_type = task.get("resource_type")
            duration = int(task.get("duration_min") or 5)
            window_end = int(task.get("window_end") or horizon_end)
            window_start = int(task.get("window_start") or current_time)

            # Candidates: idle resources of matching type.
            resources = list(
                db["resource"].find(
                    {"resource_type": res_type, "status": "idle"},
                    {"_id": 0},
                )
            )
            if not resources:
                continue

            best: Optional[Tuple[float, Dict[str, Any], int, int]] = None
            for r in sorted(resources, key=lambda x: x.get("resource_id", "")):
                loc = r.get("location_node") or "DEPOT"
                available_at = int(r.get("available_at") or current_time)

                # Travel time on the same graph (resource drives on apron/taxi routes).
                path = self.graph.shortest_path(loc, gate_node)
                travel = self.graph.path_travel_time(path)

                start_time = max(current_time, available_at, window_start) + travel
                end_time = start_time + duration
                lateness = max(0, end_time - window_end)
                cost = (start_time - current_time) + (lateness_penalty * lateness)

                if best is None or cost < best[0]:
                    best = (cost, r, start_time, end_time)

            if best is None:
                continue

            _, resource_doc, start_time, end_time = best
            resource_id = resource_doc["resource_id"]

            # Commit assignment.
            db["service_task"].update_one(
                {"flight_id": task["flight_id"], "service_type": task["service_type"]},
                {
                    "$set": {
                        "status": "scheduled" if start_time > current_time else "active",
                        "assigned_resource_id": resource_id,
                        "start_time": start_time,
                        "end_time": end_time,
                        "last_updated_at": current_time,
                    }
                },
            )
            db["resource"].update_one(
                {"resource_id": resource_id},
                {
                    "$set": {
                        "status": "busy",
                        "location_node": gate_node,
                        "available_at": end_time,
                        "current_task": {
                            "flight_id": task["flight_id"],
                            "service_type": task["service_type"],
                        },
                    }
                },
            )

            log_event(
                "resource_assigned",
                flight_id=task["flight_id"],
                resource=resource_id,
                action=f"{task['service_type']} at {gate_node} start={start_time} end={end_time}",
            )

            assigned += 1

        return {
            "status": "success",
            "current_time": current_time,
            "created_resources": created_resources,
            "created_tasks": created_tasks,
            "assigned_count": assigned,
        }

