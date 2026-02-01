from langchain.tools import tool
from app.simulation.state import gate_status, runway_status

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
