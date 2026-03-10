from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.db.mongo import get_db
from app.db.queries import log_event
from app.simulation.airport_graph import AirportGraph
from app.simulation.gates_from_geojson import gate_ids, gate_index_to_id


def _gate_node(gate_value: Any) -> str:
    """
    Normalize a schedule gate value (often an int index) to a concrete gate
    identifier from the LSZH GeoJSON.
    """
    ids = gate_ids()

    if isinstance(gate_value, str):
        # If this exact ID exists in GeoJSON, keep it.
        if gate_value in ids:
            return gate_value
        # Allow simple numeric strings like "1", "2", ...
        try:
            n = int(gate_value)
            return gate_index_to_id(n)
        except Exception:
            # Fallback: first known gate
            return ids[0] if ids else "G1"

    try:
        n = int(gate_value)
        return gate_index_to_id(n)
    except Exception:
        return ids[0] if ids else "G1"


def _runway_node(runway_value: Any, runway_index: Any = None) -> str:
    # Prefer the concrete runway string produced by the solver.
    if isinstance(runway_value, str) and runway_value.strip():
        return runway_value.strip()
    # Fallback to index mapping consistent with optimization/solver.py
    try:
        idx = int(runway_index)
    except Exception:
        idx = 0
    return "16/34" if idx == 0 else "10/28"


@dataclass
class PlannedTaxi:
    flight_id: str
    mode: str  # taxi_in | taxi_out
    start_node: str
    end_node: str
    start_time: int
    path: List[str]
    eta_by_node: List[Dict[str, Any]]
    hold_minutes: int


class SurfaceMovementAgent:
    """
    Step-based surface movement agent:
    - Plans taxi-in (runway -> gate) and taxi-out (gate -> runway)
    - Uses simple A* routing on AirportGraph and a reservation table to avoid
      node conflicts in discrete minutes.

    This agent is deterministic and does not require SimPy.
    """

    def __init__(self, graph: Optional[AirportGraph] = None):
        self.graph = graph or AirportGraph()

    def step(
        self,
        current_time: int,
        window_minutes: int = 45,
        max_start_delay: int = 15,
    ) -> Dict[str, Any]:
        db = get_db()
        horizon_end = current_time + max(1, window_minutes)

        schedule = list(
            db["schedule"].find(
                {
                    "$or": [
                        # Arrivals that are landing or taxiing-in soon
                        {"landing_time": {"$lte": horizon_end}},
                        # Departures that will push and taxi-out soon
                        {"gate_departure": {"$lte": horizon_end}},
                    ]
                },
                {
                    "_id": 0,
                    "flight_id": 1,
                    "landing_time": 1,
                    "gate": 1,
                    "gate_arrival": 1,
                    "gate_departure": 1,
                    "takeoff_time": 1,
                    "runway": 1,
                    "runway_index": 1,
                },
            )
        )

        # Reservation table: time -> set(node_ids) to prevent two aircraft
        # occupying the same node at the same discrete minute.
        reservations: Dict[int, set] = {}

        def reserve(t: int, node_id: str) -> None:
            reservations.setdefault(t, set()).add(node_id)

        def is_reserved(t: int, node_id: str) -> bool:
            return node_id in reservations.get(t, set())

        # Load existing plans so we can reuse reservations for already-planned aircraft.
        existing = list(
            db["surface_state"].find(
                {"end_time": {"$gte": current_time}},
                {"_id": 0, "flight_id": 1, "eta_by_node": 1},
            )
        )
        for doc in existing:
            for step in doc.get("eta_by_node", []) or []:
                t = step.get("t")
                n = step.get("node")
                if isinstance(t, int) and isinstance(n, str):
                    reserve(t, n)

        # Build candidate taxi legs (taxi-in & taxi-out).
        candidates: List[Tuple[int, str, Dict[str, Any]]] = []
        for s in schedule:
            fid = s.get("flight_id")
            if not fid:
                continue

            landing_time = s.get("landing_time")
            gate_arrival = s.get("gate_arrival")
            gate_departure = s.get("gate_departure")
            takeoff_time = s.get("takeoff_time")

            runway_node = _runway_node(s.get("runway"), s.get("runway_index"))
            gate_node = _gate_node(s.get("gate"))

            # Taxi-in: landing_time -> gate_arrival
            if isinstance(landing_time, int) and isinstance(gate_arrival, int):
                if landing_time <= horizon_end and gate_arrival >= current_time:
                    start = max(current_time, landing_time)
                    candidates.append((start, "taxi_in", {**s, "start_node": runway_node, "end_node": gate_node}))

            # Taxi-out: gate_departure -> takeoff_time
            if isinstance(gate_departure, int) and isinstance(takeoff_time, int):
                if gate_departure <= horizon_end and takeoff_time >= current_time:
                    start = max(current_time, gate_departure)
                    candidates.append((start, "taxi_out", {**s, "start_node": gate_node, "end_node": runway_node}))

        # Plan in chronological order (simple priority).
        candidates.sort(key=lambda x: (x[0], x[1], x[2].get("flight_id", "")))

        planned: List[PlannedTaxi] = []
        upserts = 0

        for start_time, mode, s in candidates:
            fid = s["flight_id"]
            start_node = s["start_node"]
            end_node = s["end_node"]

            if not (self.graph.has_node(start_node) and self.graph.has_node(end_node)):
                continue

            # Avoid replanning if we already have an active plan of same mode.
            existing_doc = db["surface_state"].find_one(
                {"flight_id": fid, "mode": mode, "end_time": {"$gte": current_time}},
                {"_id": 1},
            )
            if existing_doc:
                continue

            base_path = self.graph.shortest_path(start_node, end_node)
            if not base_path:
                continue

            # Try delaying start to avoid conflicts at nodes.
            chosen: Optional[PlannedTaxi] = None
            for delay in range(0, max_start_delay + 1):
                t = start_time + delay
                eta_by_node: List[Dict[str, Any]] = []

                # Reserve the start node at the start minute.
                if is_reserved(t, base_path[0]):
                    continue
                eta_by_node.append({"t": t, "node": base_path[0]})

                ok = True
                cur_t = t
                for a, b in zip(base_path, base_path[1:]):
                    cur_t += self.graph.edge_travel_time(a, b)
                    if is_reserved(cur_t, b):
                        ok = False
                        break
                    eta_by_node.append({"t": cur_t, "node": b})

                if not ok:
                    continue

                chosen = PlannedTaxi(
                    flight_id=fid,
                    mode=mode,
                    start_node=start_node,
                    end_node=end_node,
                    start_time=t,
                    path=base_path,
                    eta_by_node=eta_by_node,
                    hold_minutes=delay,
                )
                break

            if chosen is None:
                # Couldn't find a conflict-free window quickly; skip for now.
                continue

            # Commit reservations.
            for step in chosen.eta_by_node:
                reserve(step["t"], step["node"])

            end_time = chosen.eta_by_node[-1]["t"]
            db["surface_state"].update_one(
                {"flight_id": fid, "mode": mode},
                {
                    "$set": {
                        "flight_id": fid,
                        "mode": mode,
                        "start_node": chosen.start_node,
                        "end_node": chosen.end_node,
                        "start_time": chosen.start_time,
                        "end_time": end_time,
                        "path": chosen.path,
                        "eta_by_node": chosen.eta_by_node,
                        "hold_minutes": chosen.hold_minutes,
                        "last_planned_at": current_time,
                    }
                },
                upsert=True,
            )
            upserts += 1

            log_event(
                "taxi_plan_created",
                flight_id=fid,
                resource="surface",
                action=f"{mode} {chosen.start_node}->{chosen.end_node} start={chosen.start_time} hold={chosen.hold_minutes}",
            )

            planned.append(chosen)

        return {
            "status": "success",
            "current_time": current_time,
            "planned_count": len(planned),
            "upserts": upserts,
        }

