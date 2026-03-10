from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Tuple


@dataclass(frozen=True)
class GateInfo:
    gate_id: str
    coord: Tuple[float, float]


def _project_root() -> str:
    # backend/app/simulation -> backend -> project root
    here = os.path.abspath(os.path.dirname(__file__))
    backend_dir = os.path.abspath(os.path.join(here, "..", ".."))
    return os.path.abspath(os.path.join(backend_dir, ".."))


def _geojson_path() -> str:
    root = _project_root()
    return os.path.join(root, "frontend", "public", "lszh_airport.geojson")


@lru_cache(maxsize=1)
def load_gates() -> List[GateInfo]:
    """
    Load gate identifiers and coordinates from the LSZH GeoJSON used by the
    frontend map. This keeps gate IDs consistent across backend agents and UI.
    """
    path = _geojson_path()
    if not os.path.exists(path):
        # Fall back to an empty list; callers should handle this gracefully.
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    gates: List[GateInfo] = []

    for feat in features:
        props = feat.get("properties", {}) or {}
        if props.get("aeroway") != "gate":
            continue

        gate_id = props.get("ref") or props.get("name")
        if not gate_id:
            continue

        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates")
        if not coords:
            continue

        # For Points, GeoJSON is [lon, lat]; for other types we pick the first.
        if isinstance(coords[0], (float, int)):
            lon, lat = float(coords[0]), float(coords[1])
        else:
            lon, lat = float(coords[0][0]), float(coords[0][1])

        gates.append(GateInfo(gate_id=str(gate_id), coord=(lon, lat)))

    # Deterministic ordering
    gates.sort(key=lambda g: g.gate_id)
    return gates


def gate_ids() -> List[str]:
    return [g.gate_id for g in load_gates()]


def gate_index_to_id(index: int) -> str:
    """
    Map a 1-based gate index (from the optimizer/schedule) to a concrete gate
    identifier from the GeoJSON file. If out of range, wraps around.
    """
    ids = gate_ids()
    if not ids:
        return "G1"

    if index <= 0:
        index = 1
    # 1-based -> 0-based with wrap-around
    idx = (index - 1) % len(ids)
    return ids[idx]

