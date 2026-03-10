from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from app.simulation.gates_from_geojson import load_gates


Coord = Tuple[float, float]


@dataclass(frozen=True)
class Node:
    id: str
    coord: Coord


class AirportGraph:
    """
    Lightweight airport surface graph for taxi routing.

    Notes:
    - This is intentionally simple and deterministic (no SimPy, no external deps).
    - Coordinates are approximate; gate IDs are taken directly from the LSZH
      GeoJSON used by the frontend, so naming and cardinality stay consistent.
    """

    def __init__(self, taxi_speed_units_per_min: float = 8.0):
        self.taxi_speed_units_per_min = max(0.1, taxi_speed_units_per_min)

        self.nodes: Dict[str, Node] = {}

        # Runways (keep simple abstract positions)
        self.nodes["16/34"] = Node("16/34", (0.0, 0.0))
        self.nodes["10/28"] = Node("10/28", (40.0, 0.0))

        # Surface junctions / apron / depot (abstract layout)
        self.nodes["APRON"] = Node("APRON", (20.0, 20.0))
        self.nodes["DEPOT"] = Node("DEPOT", (10.0, 25.0))
        self.nodes["EXIT_16"] = Node("EXIT_16", (5.0, 10.0))
        self.nodes["EXIT_10"] = Node("EXIT_10", (35.0, 10.0))

        # Gates: project real gates from GeoJSON into a simple line near the apron.
        gates = load_gates()
        if not gates:
            # Fallback: small synthetic set if GeoJSON is missing
            gate_ids = ["G1", "G2", "G3"]
        else:
            gate_ids = [g.gate_id for g in gates]

        x0 = 0.0
        step = 8.0 if len(gate_ids) > 1 else 0.0
        for i, gid in enumerate(gate_ids):
            self.nodes[gid] = Node(gid, (x0 + i * step, 40.0))

        # Undirected edges between nodes (taxiways)
        self.adj: Dict[str, List[str]] = {nid: [] for nid in self.nodes}
        self._connect("16/34", "EXIT_16")
        self._connect("10/28", "EXIT_10")
        self._connect("EXIT_16", "APRON")
        self._connect("EXIT_10", "APRON")
        self._connect("DEPOT", "APRON")
        for gid in gate_ids:
            self._connect("APRON", gid)

    def _connect(self, a: str, b: str) -> None:
        self.adj[a].append(b)
        self.adj[b].append(a)

    def has_node(self, node_id: str) -> bool:
        return node_id in self.nodes

    def coord(self, node_id: str) -> Coord:
        return self.nodes[node_id].coord

    def distance(self, a: str, b: str) -> float:
        ax, ay = self.coord(a)
        bx, by = self.coord(b)
        return math.hypot(ax - bx, ay - by)

    def edge_travel_time(self, a: str, b: str) -> int:
        # At least 1 minute per edge to keep discrete simulation stable.
        dist = self.distance(a, b)
        return max(1, int(math.ceil(dist / self.taxi_speed_units_per_min)))

    def shortest_path(self, start: str, goal: str) -> List[str]:
        """
        Deterministic A* on the taxiway graph.
        Returns list of node IDs including start and goal.
        """
        if start == goal:
            return [start]
        if start not in self.nodes or goal not in self.nodes:
            return []

        open_set = {start}
        came_from: Dict[str, str] = {}

        g_score: Dict[str, float] = {nid: float("inf") for nid in self.nodes}
        g_score[start] = 0.0

        f_score: Dict[str, float] = {nid: float("inf") for nid in self.nodes}
        f_score[start] = self.distance(start, goal)

        def lowest_f() -> Optional[str]:
            best = None
            best_val = float("inf")
            for nid in open_set:
                val = f_score.get(nid, float("inf"))
                if val < best_val:
                    best, best_val = nid, val
            return best

        while open_set:
            current = lowest_f()
            if current is None:
                break
            if current == goal:
                return self._reconstruct_path(came_from, current)

            open_set.remove(current)
            for nb in sorted(self.adj.get(current, [])):
                tentative = g_score[current] + self.edge_travel_time(current, nb)
                if tentative < g_score[nb]:
                    came_from[nb] = current
                    g_score[nb] = tentative
                    f_score[nb] = tentative + self.distance(nb, goal)
                    open_set.add(nb)

        return []

    def _reconstruct_path(self, came_from: Dict[str, str], current: str) -> List[str]:
        out = [current]
        while current in came_from:
            current = came_from[current]
            out.append(current)
        out.reverse()
        return out

    def path_travel_time(self, path: List[str]) -> int:
        if not path:
            return 0
        total = 0
        for a, b in zip(path, path[1:]):
            total += self.edge_travel_time(a, b)
        return total

