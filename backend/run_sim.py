from app.simulation.environment import run_simulation
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    try:
        print("Starting simulation...")
        run_simulation()
        print("Simulation complete.")
    except KeyboardInterrupt:
        print("Simulation manually stopped by the user.")