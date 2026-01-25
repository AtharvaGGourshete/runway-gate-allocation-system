class AirportBlueprint:
    def __init__(self):
        self.gates = {
            "G1": None,
            "G2": None,
            "G3": None,
        }

        self.runways = {
            "R1": None,
            "R2": None,
        }

        self.flight_positions = {}

    def assign_gate(self, flight_id):
        for gate, occupant in self.gates.items():
            if occupant is None:
                self.gates[gate] = flight_id
                self.flight_positions[flight_id] = self.get_gate_coords(gate)
                return gate
        return None

    def assign_runway(self, flight_id):
        for rw, occupant in self.runways.items():
            if occupant is None:
                self.runways[rw] = flight_id
                self.flight_positions[flight_id] = self.get_runway_coords(rw)
                return rw
        return None

    def get_gate_coords(self, gate):
        mapping = {"G1": (10, 50), "G2": (30, 50), "G3": (50, 50)}
        return mapping.get(gate, (0, 0))

    def get_runway_coords(self, runway):
        mapping = {"R1": (20, 10), "R2": (40, 10)}
        return mapping.get(runway, (0, 0))