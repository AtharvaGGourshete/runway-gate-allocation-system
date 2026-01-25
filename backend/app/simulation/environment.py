import simpy
import random
import time
from app.agents.flight_agent import build_flight_agent
from langchain_core.messages import HumanMessage

def run_simulation():
    env = simpy.Environment()
    # Create a 'Capacity' of 1 for the API to prevent concurrent calls
    api_resource = simpy.Resource(env, capacity=1)
    
    gates = ["G1", "G2", "G3"]
    runways = ["R1", "R2"]
    
    # Build agent ONCE
    agent = build_flight_agent()

    for i in range(15):
        flight_id = f"F{i+1}"
        env.process(flight_lifecycle(env, flight_id, gates, runways, agent, api_resource))
    
    env.run(until=500) # Increased time to allow for spacing

def flight_lifecycle(env, flight_id, gates, runways, agent, api_resource):
    yield env.timeout(random.randint(1, 10))

    with api_resource.request() as req:
        yield req

        # Do NOT block with time.sleep() in SimPy processes; use env.timeout. [web:13]
        yield env.timeout(5)

        print(f"[SimPy Time: {env.now}] Flight {flight_id} calling model...")

        prompt = f"Assign gate/runway to {flight_id}. Gates: {gates}, Runways: {runways}"

        try:
            result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
            print(f"[Agent] Flight {flight_id}: {result['messages'][-1].content}")

            yield env.timeout(20)

        except Exception as e:
            # Generic 429 handling; adjust once you confirm the exact exception class used in your stack. [web:18]
            if "429" in str(e) or "RateLimit" in str(e):
                print(f"[Quota Error] Waiting for reset for {flight_id}...")
                yield env.timeout(60)
            else:
                print(f"[System/AI Error] {e}")
                yield env.timeout(5)