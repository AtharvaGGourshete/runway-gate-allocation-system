from ortools.sat.python import cp_model


def _coerce_index(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_time(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


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

    horizon_end = int(current_time + planning_horizon)
    freeze_end = int(current_time + freeze_window)

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
        landing_time = _coerce_time(frozen.get("landing_time", -1), -1)
        if landing_time < 0 or landing_time >= freeze_end:
            continue

        runway_index = _coerce_index(frozen.get("runway_index", 0), 0)
        gate_index = frozen.get("gate_index")
        if gate_index is None:
            gate_index = _coerce_index(frozen.get("gate", 1), 1) - 1

        runway_index = max(0, min(R - 1, runway_index))
        gate_index = max(0, min(G - 1, _coerce_index(gate_index, 0)))

        gate_arrival = _coerce_time(frozen.get("gate_arrival", landing_time), landing_time)
        gate_departure = _coerce_time(
            frozen.get("gate_departure", gate_arrival + 1),
            gate_arrival + 1,
        )
        if gate_departure <= gate_arrival:
            gate_departure = gate_arrival + 1

        takeoff_time = _coerce_time(
            frozen.get("takeoff_time", gate_departure),
            gate_departure,
        )

        landing_interval = model.NewIntervalVar(
            landing_time,
            5,
            landing_time + 5,
            f"frozen_landing_{frozen['flight_id']}",
        )
        runway_intervals_per_runway[runway_index].append(landing_interval)

        gate_interval = model.NewIntervalVar(
            gate_arrival,
            gate_departure - gate_arrival,
            gate_departure,
            f"frozen_gate_{frozen['flight_id']}",
        )
        gate_intervals_per_gate[gate_index].append(gate_interval)

        takeoff_interval = model.NewIntervalVar(
            takeoff_time,
            5,
            takeoff_time + 5,
            f"frozen_takeoff_{frozen['flight_id']}",
        )
        runway_intervals_per_runway[runway_index].append(takeoff_interval)

    for i, p in enumerate(flights):
        scheduled_arrival = _coerce_time(p.get("scheduled_arrival", current_time), current_time)
        max_delay = max(0, _coerce_time(p.get("max_delay", 30), 30))
        landing_duration = max(1, _coerce_time(p.get("landing_duration", 5), 5))
        service_time = max(1, _coerce_time(p.get("service_time", 35), 35))
        max_turnaround = max(service_time, _coerce_time(p.get("max_turnaround", service_time), service_time))
        takeoff_duration = max(1, _coerce_time(p.get("takeoff_duration", 5), 5))

        if not (current_time <= scheduled_arrival <= horizon_end):
            continue

        flight_id = p["flight_id"]

        arrival_lb = max(scheduled_arrival, current_time)
        arrival_ub = scheduled_arrival + max_delay

        land_start = model.NewIntVar(arrival_lb, arrival_ub, f"land_{i}")
        land_end = model.NewIntVar(0, horizon_end, f"land_end_{i}")
        model.Add(land_end == land_start + landing_duration)

        delay = model.NewIntVar(0, max_delay, f"delay_{i}")
        model.Add(delay == land_start - scheduled_arrival)
        total_delay.append(delay)

        runway_var = model.NewIntVar(0, R - 1, f"runway_{i}")

        for r in range(R):
            is_on_runway = model.NewBoolVar(f"is_f{i}_r{r}")

            model.Add(runway_var == r).OnlyEnforceIf(is_on_runway)
            model.Add(runway_var != r).OnlyEnforceIf(is_on_runway.Not())

            landing_optional = model.NewOptionalIntervalVar(
                land_start,
                landing_duration,
                land_end,
                is_on_runway,
                f"landing_f{i}_r{r}",
            )

            runway_intervals_per_runway[r].append(landing_optional)

        gate_start = land_end

        gate_duration = model.NewIntVar(
            service_time,
            max_turnaround,
            f"gate_dur_{i}",
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
                f"gate_interval_f{i}_g{g}",
            )

            gate_intervals_per_gate[g].append(optional_interval)

        takeoff_start = gate_end
        takeoff_end = model.NewIntVar(0, horizon_end, f"takeoff_end_{i}")
        model.Add(takeoff_end == takeoff_start + takeoff_duration)

        for r in range(R):
            is_on_runway = model.NewBoolVar(f"is_takeoff_f{i}_r{r}")

            model.Add(runway_var == r).OnlyEnforceIf(is_on_runway)
            model.Add(runway_var != r).OnlyEnforceIf(is_on_runway.Not())

            takeoff_optional = model.NewOptionalIntervalVar(
                takeoff_start,
                takeoff_duration,
                takeoff_end,
                is_on_runway,
                f"takeoff_f{i}_r{r}",
            )

            runway_intervals_per_runway[r].append(takeoff_optional)

        results[i] = {
            "flight_id": flight_id,
            "land_start": land_start,
            "gate_var": gate_var,
            "gate_start": gate_start,
            "gate_end": gate_end,
            "takeoff_start": takeoff_start,
            "takeoff_end": takeoff_end,
            "runway_var": runway_var,
        }

    for r in range(R):
        model.AddNoOverlap(runway_intervals_per_runway[r])

    for g in range(G):
        model.AddNoOverlap(gate_intervals_per_gate[g])

    model.Minimize(sum(total_delay))

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
        gate_index = solver.Value(results[i]["gate_var"])

        schedule.append(
            {
                "flight_id": results[i]["flight_id"],
                "landing_time": solver.Value(results[i]["land_start"]),
                "gate": gate_index + 1,
                "gate_index": gate_index,
                "gate_arrival": solver.Value(results[i]["gate_start"]),
                "gate_departure": solver.Value(results[i]["gate_end"]),
                "takeoff_time": solver.Value(results[i]["takeoff_end"]),
                "runway_index": runway_index,
                "runway": RUNWAY_MAP.get(runway_index, "Unknown"),
            }
        )

    return {"status": "success", "schedule": schedule}


