# airport_simulator.py
import simpy
import random

class AirportSim:
    def __init__(self, env, num_runways, num_gates):
        self.env = env
        # SimPy Resources represent our physical constraints
        self.runway = simpy.Resource(env, capacity=num_runways)
        # For Gates, we can use a PriorityResource if we want specific assignments
        # But for simplicity, we use a standard Resource matching the count
        self.gates = simpy.Resource(env, capacity=num_gates)
        self.logs = []

    def log(self, message):
        self.logs.append(f"{self.env.now:.2f}: {message}")

def flight_process(env, airport, flight_plan):
    """
    Simulates the lifecycle of ONE flight based on the OR-Tools schedule.
    """
    f_id = flight_plan['flight_id']
    scheduled_land = flight_plan['landing_time']
    scheduled_gate_dur = flight_plan['gate_departure'] - flight_plan['gate_arrival']

    # 1. Wait for the Scheduled Arrival Time
    # If the simulation starts at 0, we wait until the plane appears on radar
    yield env.timeout(scheduled_land)
    airport.log(f"Flight {f_id} arrived in airspace.")

    # 2. Request Runway for Landing
    # We add a small random variance to landing duration (Realism!)
    landing_duration = 10 + random.randint(-2, 5) 
    
    with airport.runway.request() as request:
        yield request
        airport.log(f"Flight {f_id} landing on Runway.")
        yield env.timeout(landing_duration)
        airport.log(f"Flight {f_id} vacated Runway.")

    # 3. Request Gate
    # The plane taxis to the gate.
    taxi_time = 5
    yield env.timeout(taxi_time)

    with airport.gates.request() as request:
        result = yield request | env.timeout(0) # Try to get gate instantly
        
        if request in result:
            airport.log(f"Flight {f_id} parked at Gate.")
            
            # 4. Turnaround (Service)
            # Add chaos: delays in cleaning/fueling?
            actual_service_time = scheduled_gate_dur + random.randint(0, 15)
            yield env.timeout(actual_service_time)
            
            airport.log(f"Flight {f_id} leaving Gate (Turnaround complete).")
        else:
            # This happens if the Schedule was bad OR if previous delays piled up
            airport.log(f"CRITICAL: Flight {f_id} waiting on tarmac! Gate blocked.")
            yield request # Wait until it opens
            airport.log(f"Flight {f_id} finally got a gate.")
            yield env.timeout(scheduled_gate_dur)

def run_simulation(num_runways, num_gates, schedule):
    """
    Main entry point to run SimPy
    """
    env = simpy.Environment()
    airport = AirportSim(env, num_runways, num_gates)

    # Spawn a process for every flight in the schedule
    for flight in schedule:
        env.process(flight_process(env, airport, flight))

    # Run until the last scheduled event + buffer
    last_event = max([f['gate_departure'] for f in schedule]) + 100
    env.run(until=last_event)

    return airport.logs