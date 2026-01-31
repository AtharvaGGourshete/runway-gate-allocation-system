import simpy
import random
import json
from langchain_core.messages import HumanMessage

from app.agents.flight_agent import build_flight_agent
from app.db.queries import (
    log_event, save_flight, save_gate, save_runway,
    update_gate_status, update_runway_status
)
from app.db.models.flight import Flight
from app.db.models.gate import Gate
from app.db.models.runway import Runway

NUM_FLIGHTS = 15
GATES = ["G1", "G2", "G3"]
RUNWAYS = ["R1", "R2"]

gate_status = {g: "available" for g in GATES}
runway_status = {r: "available" for r in RUNWAYS}

def flight_lifecycle(env, flight_id, agent, api_resource):
    # Random arrival time
    yield env.timeout(random.randint(1, 10))

    log_event("flight_arrived", flight_id=flight_id, action="Flight arrived")

    with api_resource.request() as req:
        yield req

        yield env.timeout(5)
        print(f"[SimPy Time: {env.now}] Flight {flight_id} calling model...")

        prompt = (
            f"You are an airport scheduling agent.\n"
            f"Current gate status: {gate_status}\n"
            f"Current runway status: {runway_status}\n"
            f"Assign ONE available gate and ONE available runway to flight {flight_id}.\n"
            f"Respond ONLY in JSON:\n"
            f'{{"assigned_gate": "G1", "assigned_runway": "R1"}}'
        )

        try:
            log_event("agent_invoked", flight_id=flight_id, action="Invoking LLM")

            result = agent.invoke({
                "messages": [HumanMessage(content=prompt)]
            })

            raw = result["messages"][-1].content
            raw = raw.replace("```json", "").replace("```", "").strip()

            response = json.loads(raw)
            assigned_gate = response["assigned_gate"]
            assigned_runway = response["assigned_runway"]

            log_event("agent_response", flight_id=flight_id, action=raw)
            print(f"[Agent] {flight_id} → {assigned_gate}/{assigned_runway}")

        except Exception as e:
            log_event("error", flight_id=flight_id, action=str(e))
            print(f"[LLM Error] {flight_id}: {e}")
            return

    if gate_status.get(assigned_gate) != "available" or runway_status.get(assigned_runway) != "available":
        log_event(
            "invalid_assignment",
            flight_id=flight_id,
            action=f"Gate {assigned_gate} or Runway {assigned_runway} unavailable"
        )
        print(f"[Invalid Assignment] {flight_id}")
        return
    
    gate_status[assigned_gate] = "occupied"
    runway_status[assigned_runway] = "occupied"

    # Save Flight
    flight = Flight(
        flight_id=flight_id,
        status="arrived",
        arrival_time=env.now,
        assigned_gate=assigned_gate,
        assigned_runway=assigned_runway,
        delay=0,
        position=(random.randint(0, 10), random.randint(0, 10))
    )
    save_flight(flight)

    # Save Gate
    save_gate(Gate(
        gate_id=assigned_gate,
        occupied_by=flight_id,
        status="occupied"
    ))

    # Save Runway
    save_runway(Runway(
        runway_id=assigned_runway,
        occupied_by=flight_id,
        status="occupied"
    ))

    log_event(
        "resource_allocated",
        flight_id=flight_id,
        action=f"Gate {assigned_gate}, Runway {assigned_runway}"
    )

    yield env.timeout(20)
    gate_status[assigned_gate] = "available"
    runway_status[assigned_runway] = "available"

    update_gate_status(assigned_gate, "available")
    update_runway_status(assigned_runway, "available")

    log_event(
        "resource_released",
        flight_id=flight_id,
        action=f"Gate {assigned_gate} and Runway {assigned_runway} released"
    )

    print(f"[SimPy Time: {env.now}] Flight {flight_id} released resources")

def run_simulation():
    env = simpy.Environment()

    # 🔒 Hard throttle: only ONE LLM call globally
    api_resource = simpy.Resource(env, capacity=1)

    agent = build_flight_agent()

    for i in range(NUM_FLIGHTS):
        flight_id = f"F{i+1}"
        env.process(flight_lifecycle(env, flight_id, agent, api_resource))

    print("=== Starting Simulation ===")
    env.run(until=500)
    print("=== Simulation Complete ===")


if __name__ == "__main__":
    run_simulation()
