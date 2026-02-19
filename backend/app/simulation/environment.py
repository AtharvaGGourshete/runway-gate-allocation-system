# app/simulation/environment.py
import simpy
import random
import json
from langchain_core.messages import HumanMessage

# Import the NEW scheduler agent
from app.agents.scheduler_agent import build_scheduler_agent
from app.simulation.state import GATES, RUNWAYS, gate_status, runway_status
from app.db.queries import log_event, save_flight, save_gate, save_runway, update_gate_status, update_runway_status
from app.db.models.flight import Flight
from app.db.models.gate import Gate
from app.db.models.runway import Runway

NUM_FLIGHTS = 15

def safe_parse_json(content):
    if not content: raise ValueError("Empty response")
    raw = content.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

# --- 1. THE EXECUTION PHASE (SimPy) ---
# This function is now "Dumb" but Fast. It just follows orders.
def flight_lifecycle(env, flight_id, assigned_data):
    # Unpack the specific assignment for this flight
    my_gate = assigned_data['assigned_gate']
    my_runway = assigned_data['assigned_runway']
    
    # Simulate Arrival Variance
    yield env.timeout(random.randint(1, 10))
    log_event("flight_arrived", flight_id, action=f"Arrived. Assigned to {my_gate}/{my_runway}")

    print(f"[SimPy Time: {env.now}] {flight_id} requesting {my_runway} -> {my_gate}")

    # 1. Request Runway (The Plan says R1, but is R1 actually free?)
    # Note: In a full SimPy implementation, you'd use simpy.Resource for the runway.
    # For now, we update the status dict to mimic your original code.
    
    if runway_status[my_runway] == "available":
        runway_status[my_runway] = "occupied"
        update_runway_status(my_runway, "occupied")
    else:
        print(f"[Conflict] {flight_id} waiting for {my_runway}...")
        # Simple wait logic
        while runway_status[my_runway] != "available":
            yield env.timeout(1)
        runway_status[my_runway] = "occupied"

    # 2. Taxi and Request Gate
    yield env.timeout(5) # Taxi time
    
    if gate_status[my_gate] == "available":
        gate_status[my_gate] = "occupied"
        update_gate_status(my_gate, "occupied")
    else:
        # The Schedule said Gate 1, but SimPy reality says it's busy.
        # This is where SimPy proves its value (Detecting bottlenecks).
        print(f"[CRITICAL] {flight_id} blocked at {my_gate}!")
        while gate_status[my_gate] != "available":
            yield env.timeout(1)
        gate_status[my_gate] = "occupied"

    # 3. Save to DB
    save_flight(Flight(
        flight_id=flight_id, status="parked", arrival_time=env.now,
        assigned_gate=my_gate, assigned_runway=my_runway, delay=0, position=(0,0)
    ))
    
    log_event("parked", flight_id, action=f"Parked at {my_gate}")
    
    # 4. Turnaround Service
    yield env.timeout(20)

    # 5. Release Resources
    gate_status[my_gate] = "available"
    runway_status[my_runway] = "available"
    update_gate_status(my_gate, "available")
    update_runway_status(my_runway, "available")
    
    print(f"[SimPy Time: {env.now}] {flight_id} departed.")


# --- 2. THE PLANNING PHASE (Agent + OR-Tools) ---
def run_simulation():
    env = simpy.Environment()
    scheduler = build_scheduler_agent()

    print("=== Phase 1: Planning (Agent + Solver) ===")
    
    # Generate Dummy Flight Data
    flight_manifest = [{"id": f"F{i+1}", "type": "A320"} for i in range(NUM_FLIGHTS)]
    
    prompt = (
        f"I have {len(flight_manifest)} flights incoming.\n"
        f"Flights: {json.dumps(flight_manifest)}\n"
        f"Runways: {RUNWAYS}\n"
        f"Gates: {GATES}\n"
        "Generate a conflict-free schedule using the scheduler tool."
    )

    # ONE single API call for all flights (Fast & Cheap)
    try:
        # Pass the prompt string directly to the 'input' key
        result = scheduler.invoke({"input": prompt})
        # Parse the tool output from the agent's final response
        # Note: Depending on Agent verbose output, you might need to parse `result['output']`
        # Assuming the agent returns the JSON schedule in the text:
        schedule_json = safe_parse_json(result['output']) 
        print("=== Schedule Generated Successfully ===")
    except Exception as e:
        print(f"Planning Failed: {e}")
        return

    print("=== Phase 2: Execution (SimPy) ===")
    
    # Spawn SimPy processes based on the Master Schedule
    for f_id, assignment in schedule_json.items():
        env.process(flight_lifecycle(env, f_id, assignment))

    env.run(until=500)
    print("=== Simulation Complete ===")