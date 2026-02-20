from ortools.sat.python import cp_model


def solve_airport_schedule(
    R,
    G,
    flights,
    committed_schedule,
    current_time,
    planning_horizon=180,
    freeze_window=15,
):

    model = cp_model.CpModel()

    horizon_end = current_time + planning_horizon
    freeze_end = current_time + freeze_window

    # Zurich runway names
    RUNWAY_MAP = {
        0: "16/34",
        1: "10/28",
        2: "14/32",
    }

    gate_intervals_per_gate = [[] for _ in range(G)]
    runway_intervals_per_runway = [[] for _ in range(R)]

    total_delay = []
    results = {}

    # Add frozen flights
    for frozen in committed_schedule:
        if frozen["landing_time"] < freeze_end:

            runway_index = frozen.get("runway_index", 0)
            gate_index = frozen["gate"] - 1

            # Landing
            landing_interval = model.NewIntervalVar(
                frozen["landing_time"],
                5,
                frozen["landing_time"] + 5,
                f"frozen_landing_{frozen['flight_id']}"
            )

            runway_intervals_per_runway[runway_index].append(
                landing_interval
            )

            # Gate
            gate_interval = model.NewIntervalVar(
                frozen["gate_arrival"],
                frozen["gate_departure"] - frozen["gate_arrival"],
                frozen["gate_departure"],
                f"frozen_gate_{frozen['flight_id']}"
            )

            gate_intervals_per_gate[gate_index].append(
                gate_interval
            )

            # Takeoff
            takeoff_interval = model.NewIntervalVar(
                frozen["takeoff_time"],
                5,
                frozen["takeoff_time"] + 5,
                f"frozen_takeoff_{frozen['flight_id']}"
            )

            runway_intervals_per_runway[runway_index].append(
                takeoff_interval
            )

    # Add flights inside planning horizon
    for i, p in enumerate(flights):

        if not (current_time <= p["scheduled_arrival"] <= horizon_end):
            continue

        flight_id = p["flight_id"]

        arrival_lb = max(p["scheduled_arrival"], current_time)
        arrival_ub = p["scheduled_arrival"] + p["max_delay"]

        # Landing
        land_start = model.NewIntVar(arrival_lb, arrival_ub, f"land_{i}")
        land_end = model.NewIntVar(0, horizon_end, f"land_end_{i}")
        model.Add(land_end == land_start + p["landing_duration"])

        delay = model.NewIntVar(0, p["max_delay"], f"delay_{i}")
        model.Add(delay == land_start - p["scheduled_arrival"])
        total_delay.append(delay)

        runway_var = model.NewIntVar(0, R - 1, f"runway_{i}")

        for r in range(R):

            is_on_runway = model.NewBoolVar(f"is_f{i}_r{r}")

            model.Add(runway_var == r).OnlyEnforceIf(is_on_runway)
            model.Add(runway_var != r).OnlyEnforceIf(is_on_runway.Not())

            landing_optional = model.NewOptionalIntervalVar(
                land_start,
                p["landing_duration"],
                land_end,
                is_on_runway,
                f"landing_f{i}_r{r}"
            )

            runway_intervals_per_runway[r].append(landing_optional)

        # Gate
        gate_start = land_end

        gate_duration = model.NewIntVar(
            p["service_time"],
            p["max_turnaround"],
            f"gate_dur_{i}"
        )

        gate_end = model.NewIntVar(0, horizon_end, f"gate_end_{i}")
        model.Add(gate_end == gate_start + gate_duration)

        gate_var = model.NewIntVar(0, G - 1, f"gate_{i}")

        for g in range(G):

            is_assigned = model.NewBoolVar(f"is_f{i}_g{g}")

            model.Add(gate_var == g).OnlyEnforceIf(is_assigned)
            model.Add(gate_var != g).OnlyEnforceIf(is_assigned.Not())

            optional_interval = model.NewOptionalIntervalVar(
                gate_start,
                gate_duration,
                gate_end,
                is_assigned,
                f"gate_interval_f{i}_g{g}"
            )

            gate_intervals_per_gate[g].append(optional_interval)

        # Takeoff
        takeoff_start = gate_end
        takeoff_end = model.NewIntVar(0, horizon_end, f"takeoff_end_{i}")
        model.Add(takeoff_end == takeoff_start + p["takeoff_duration"])

        for r in range(R):

            is_on_runway = model.NewBoolVar(f"is_takeoff_f{i}_r{r}")

            model.Add(runway_var == r).OnlyEnforceIf(is_on_runway)
            model.Add(runway_var != r).OnlyEnforceIf(is_on_runway.Not())

            takeoff_optional = model.NewOptionalIntervalVar(
                takeoff_start,
                p["takeoff_duration"],
                takeoff_end,
                is_on_runway,
                f"takeoff_f{i}_r{r}"
            )

            runway_intervals_per_runway[r].append(takeoff_optional)

        results[i] = {
            "flight_id": flight_id,
            "land_start": land_start,
            "gate_var": gate_var,
            "gate_start": gate_start,
            "gate_end": gate_end,
            "takeoff_start": takeoff_start,
            "runway_var": runway_var,
        }

    # NoOverlap per runway

    for r in range(R):
        model.AddNoOverlap(runway_intervals_per_runway[r])
    # NoOverlap per gate

    for g in range(G):
        model.AddNoOverlap(gate_intervals_per_gate[g])

    model.Minimize(sum(total_delay))

    # Deterministic Solver using fixed random seed and single thread using CP-SAT parameters
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 42
    solver.parameters.max_time_in_seconds = 20

    status = solver.Solve(model)

    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return {"status": "failure"}

    schedule = []

    for i in results:
        runway_index = solver.Value(results[i]["runway_var"])

        schedule.append({
            "flight_id": results[i]["flight_id"],
            "landing_time": solver.Value(results[i]["land_start"]),
            "gate": solver.Value(results[i]["gate_var"]) + 1,
            "gate_arrival": solver.Value(results[i]["gate_start"]),
            "gate_departure": solver.Value(results[i]["gate_end"]),
            "takeoff_time": solver.Value(results[i]["takeoff_start"]),
            "runway_index": runway_index,
            "runway": RUNWAY_MAP.get(runway_index, "Unknown"),
        })

    return {"status": "success", "schedule": schedule}
