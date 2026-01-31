import simpy
import random
import json
from app.agents.flight_agent import build_flight_agent
from app.db.queries import (
    log_event, save_flight, save_gate, save_runway,
    update_gate_status, update_runway_status
)
from app.db.models.flight import Flight
from app.db.models.gate import Gate
from app.db.models.runway import Runway

# Configuration
NUM_FLIGHTS = 15
GATES = ["G1", "G2", "G3"]
RUNWAYS = ["R1", "R2"]
MAX_LLM_CALLS = 3

# State tracking
gate_status = {g: None for g in GATES}
runway_status = {r: None for r in RUNWAYS}
llm_calls = 0

def deterministic_assign(flight_id):
    """Simple logic to avoid LLM calls when obvious."""
    free_gates = [g for g, v in gate_status.items() if v is None]
    free_runways = [r for r, v in runway_status.items() if v is None]

    if not free_gates or not free_runways:
        return None, None
    if len(free_gates) == 1 and len(free_runways) == 1:
        return free_gates[0], free_runways[0]
    return "AMBIGUOUS", "AMBIGUOUS"

def flight_lifecycle(env, flight_id, agent, api_resource):
    global llm_calls
    yield env.timeout(random.randint(1, 10))

    assigned_gate, assigned_runway = deterministic_assign(flight_id)

    if assigned_gate == "AMBIGUOUS":
        if llm_calls >= MAX_LLM_CALLS:
            # Fallback to first available if limit reached
            free_gates = [g for g, v in gate_status.items() if v is None]
            free_runways = [r for r, v in runway_status.items() if v is None]
            assigned_gate = free_gates[0] if free_gates else None
            assigned_runway = free_runways[0] if free_runways else None
        else:
            with api_resource.request() as req:
                yield req
                llm_calls += 1
                yield env.timeout(5)
                print(f"[SimPy Time: {env.now}] Flight {flight_id} calling model...")

                prompt_text = (
                    f"Assign gate and runway for flight {flight_id}. "
                    f"Available gates: {gate_status}. "
                    f"Available runways: {runway_status}. "
                    "Respond ONLY with JSON."
                )

                try:
                    log_event("agent_invoked", flight_id=flight_id, action="Invoking agent")

                    # UPDATED: AgentExecutor uses 'input' and returns 'output'
                    result = agent.invoke({"input": prompt_text})
                    raw_content = result["output"]

                    # Clean up markdown if Gemini includes it
                    json_str = raw_content.replace("```json", "").replace("```", "").strip()
                    response = json.loads(json_str)

                    assigned_gate = response["assigned_gate"]
                    assigned_runway = response["assigned_runway"]

                    log_event("agent_response", flight_id=flight_id, action=raw_content)
                    print(f"[Agent Success] {flight_id} assigned to {assigned_gate}/{assigned_runway}")

                except Exception as e:
                    log_event("error", flight_id=flight_id, action=str(e))
                    print(f"[LLM Error] {flight_id}: {e}")
                    return

    # Resource allocation and Database logging
    if assigned_gate and assigned_runway:
        gate_status[assigned_gate] = flight_id
        runway_status[assigned_runway] = flight_id

        # Simulating landing and gate occupancy
        yield env.timeout(20)

        # Release resources
        gate_status[assigned_gate] = None
        runway_status[assigned_runway] = None
        print(f"[SimPy Time: {env.now}] Flight {flight_id} released resources.")

def run_simulation():
    env = simpy.Environment()
    api_resource = simpy.Resource(env, capacity=1)
    agent = build_flight_agent()

    for i in range(NUM_FLIGHTS):
        flight_id = f"F{i+1}"
        env.process(flight_lifecycle(env, flight_id, agent, api_resource))

    print("--- Starting Simulation ---")
    env.run(until=500)
    print("--- Simulation Complete ---")

if __name__ == "__main__":
    run_simulation()