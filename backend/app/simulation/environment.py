import simpy
import random
import json
from langchain_core.messages import HumanMessage

from app.agents.flight_agent import build_flight_agent
from app.simulation.state import gate_status, runway_status
from app.db.queries import (
    log_event,
    save_flight,
    save_gate,
    save_runway,
    update_gate_status,
    update_runway_status,
)
from app.db.models.flight import Flight
from app.db.models.gate import Gate
from app.db.models.runway import Runway

NUM_FLIGHTS = 15

def safe_parse_json(result):
    last_msg = result["messages"][-1]

    if not last_msg.content:
        raise ValueError("Empty LLM response")

    raw = last_msg.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    return json.loads(raw)

def flight_lifecycle(env, flight_id, agent, api_resource):
    yield env.timeout(random.randint(1, 10))
    log_event("flight_arrived", flight_id, action="Flight arrived")

    with api_resource.request() as req:
        yield req
        yield env.timeout(5)

        print(f"[SimPy Time: {env.now}] Flight {flight_id} calling model...")

        prompt = (
            f"Flight {flight_id} has arrived.\n"
            "Use tools to find an available gate and runway.\n"
            "Return only JSON."
        )

        try:
            log_event("agent_invoked", flight_id, action="Invoking LLM")

            result = agent.invoke({
                "messages": [HumanMessage(content=prompt)]
            })

            response = safe_parse_json(result)
            assigned_gate = response["assigned_gate"]
            assigned_runway = response["assigned_runway"]

            print(f"[Agent] {flight_id} → {assigned_gate}/{assigned_runway}")
            log_event(
                "agent_response",
                flight_id,
                action=f"{assigned_gate}/{assigned_runway}"
            )

        except Exception as e:
            print(f"[LLM Error] {flight_id}: {e}")
            log_event("error", flight_id, action=str(e))
            return

    # Validate allocation
    if gate_status[assigned_gate] != "available" or runway_status[assigned_runway] != "available":
        log_event(
            "invalid_assignment",
            flight_id,
            action=f"{assigned_gate}/{assigned_runway} unavailable"
        )
        print(f"[Invalid Assignment] {flight_id}")
        return

    # Allocate
    gate_status[assigned_gate] = "occupied"
    runway_status[assigned_runway] = "occupied"

    save_flight(Flight(
        flight_id=flight_id,
        status="arrived",
        arrival_time=env.now,
        assigned_gate=assigned_gate,
        assigned_runway=assigned_runway,
        delay=0,
        position=(random.randint(0, 10), random.randint(0, 10))
    ))

    save_gate(Gate(
        gate_id=assigned_gate,
        occupied_by=flight_id,
        status="occupied"
    ))

    save_runway(Runway(
        runway_id=assigned_runway,
        occupied_by=flight_id,
        status="occupied"
    ))

    log_event(
        "resource_allocated",
        flight_id,
        action=f"{assigned_gate}/{assigned_runway}"
    )

    yield env.timeout(20)

    # Release
    gate_status[assigned_gate] = "available"
    runway_status[assigned_runway] = "available"

    update_gate_status(assigned_gate, "available")
    update_runway_status(assigned_runway, "available")

    log_event(
        "resource_released",
        flight_id,
        action=f"{assigned_gate}/{assigned_runway}"
    )

    print(f"[SimPy Time: {env.now}] Flight {flight_id} released resources")

def run_simulation():
    env = simpy.Environment()
    api_resource = simpy.Resource(env, capacity=1)
    agent = build_flight_agent()

    print("=== Starting Simulation ===")

    for i in range(NUM_FLIGHTS):
        env.process(
            flight_lifecycle(env, f"F{i+1}", agent, api_resource)
        )

    env.run(until=500)
    print("=== Simulation Complete ===")
