from langchain.tools import tool
import random

GATES = ["G1", "G2", "G3"]
RUNWAYS = ["R1", "R2"]

@tool
def check_gate_availability(flight_id: str) -> str:
    """Returns an available gate for the flight."""
    gate = random.choice(GATES)
    print(f"[Tool] Assigned gate {gate} to {flight_id}")
    return gate

@tool
def suggest_runway(flight_id: str) -> str:
    """Returns a suggested runway for the flight."""
    runway = random.choice(RUNWAYS)
    print(f"[Tool] Assigned runway {runway} to {flight_id}")
    return runway

@tool
def resolve_conflict(flight_id: str) -> str:
    """Resolves resource conflicts for the flight."""
    print(f"[Tool] Conflict resolved for flight {flight_id}")
    return f"Conflict resolved for {flight_id}"
