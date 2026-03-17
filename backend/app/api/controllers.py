from flask import Blueprint, jsonify, request
from time import time

import app.services.scheduler_service as scheduler_service
from app.agents.explanation_agent import build_explanation_agent
from app.agents.multi_agent_coordinator import coordinator as multi_agent_coordinator
from app.db.mongo import get_db
from app.db.queries import (
    get_active_flights,
    get_all_flights,
    get_committed_schedule,
    save_schedule_assignments,
    save_schedule_version,
)
from app.optimization.solver import solve_airport_schedule
from app.services.analytics_service import get_dashboard_insights, get_flight_details


dash = Blueprint("health_api", __name__)
_ALLOWED_PRIORITIES = {"normal", "vip", "international_connection", "emergency"}
_EXPLANATION_AGENT = None


def _top_bottlenecks(utilization_map, top_n=3):
    if not isinstance(utilization_map, dict):
        return []

    items = [
        (rid, count)
        for rid, count in utilization_map.items()
        if rid not in (None, "Unknown")
    ]
    items.sort(key=lambda x: x[1], reverse=True)

    return [{"id": rid, "operations": int(count)} for rid, count in items[:top_n]]


def _get_explanation_agent():
    global _EXPLANATION_AGENT
    if _EXPLANATION_AGENT is None:
        _EXPLANATION_AGENT = build_explanation_agent()
    return _EXPLANATION_AGENT


def _normalize_text(value):
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item.strip())
            elif isinstance(item, dict):
                txt = str(item.get("text", "")).strip()
                if txt:
                    parts.append(txt)
        return "\n".join([p for p in parts if p]).strip()
    return str(value or "").strip()


def _extract_agent_answer(result):
    if isinstance(result, str):
        return result.strip()

    if isinstance(result, dict):
        for key in ("output", "answer", "final_output", "result"):
            if key in result:
                text = _normalize_text(result.get(key))
                if text:
                    return text

        messages = result.get("messages")
        if isinstance(messages, list):
            for msg in reversed(messages):
                if isinstance(msg, dict):
                    role = str(msg.get("role", "")).lower()
                    if role in ("assistant", "ai"):
                        text = _normalize_text(msg.get("content"))
                        if text:
                            return text
                else:
                    msg_type = str(getattr(msg, "type", "")).lower()
                    if msg_type in ("ai", "assistant"):
                        text = _normalize_text(getattr(msg, "content", ""))
                        if text:
                            return text
                    cls_name = msg.__class__.__name__.lower()
                    if "ai" in cls_name or "assistant" in cls_name:
                        text = _normalize_text(getattr(msg, "content", ""))
                        if text:
                            return text

    return ""


def _build_ai_prompt(*, context: dict, question: str):
    kpis = context.get("kpis", {}) if isinstance(context, dict) else {}
    runways = context.get("top_bottlenecks", {}).get("runways", [])
    gates = context.get("top_bottlenecks", {}).get("gates", [])
    risk_flights = context.get("risk_flights", [])
    gse = context.get("gse", {})
    surface = context.get("surface", {})

    mode_line = (
        f"User question: {question.strip()}"
        if question and question.strip()
        else "No user question. Generate an automated operations briefing."
    )

    return (
        "You are assisting airport operations for LSZH.\n"
        f"Simulation time: {context.get('simulation_time')}\n"
        f"Window minutes: {context.get('window_minutes')}\n"
        f"KPIs: {kpis}\n"
        f"Top runway bottlenecks: {runways}\n"
        f"Top gate bottlenecks: {gates}\n"
        f"High risk flights: {risk_flights}\n"
        f"GSE summary: {gse}\n"
        f"Surface summary: {surface}\n"
        f"{mode_line}\n\n"
        "Respond in plain text with this exact structure:\n"
        "Overview:\n"
        "- one or two lines\n"
        "Bottlenecks:\n"
        "- bullet points\n"
        "Action:\n"
        "- one actionable recommendation\n"
        "Keep it concise and factual."
    )


def _context_briefing(context: dict, question: str):
    kpis = context.get("kpis", {}) if isinstance(context, dict) else {}
    runways = context.get("top_bottlenecks", {}).get("runways", [])
    gates = context.get("top_bottlenecks", {}).get("gates", [])
    risk_flights = context.get("risk_flights", []) if isinstance(context, dict) else []
    gse = context.get("gse", {}) if isinstance(context, dict) else {}
    surface = context.get("surface", {}) if isinstance(context, dict) else {}

    top_runway = runways[0]["id"] if runways else "N/A"
    top_gate = gates[0]["id"] if gates else "N/A"
    top_runway_ops = runways[0]["operations"] if runways else 0
    top_gate_ops = gates[0]["operations"] if gates else 0

    overview_q = (
        f"- User focus: {question}"
        if question
        else "- System generated briefing for current simulation window."
    )

    q = (question or "").lower()
    gse_busy = gse.get("busy", 0)
    gse_total = gse.get("resources_total", 0)
    gse_active = (gse.get("tasks", {}) or {}).get("active", 0)
    gse_sched = (gse.get("tasks", {}) or {}).get("scheduled", 0)
    taxi_in = surface.get("taxi_in", 0)
    taxi_out = surface.get("taxi_out", 0)
    avg_hold = surface.get("avg_hold_minutes", 0)

    risk_line = "- No high-risk flights detected in current window."
    if risk_flights:
        top = risk_flights[0]
        risk_line = (
            f"- Highest delay-risk flight: {top.get('flight_id')} "
            f"(delay={top.get('delay_minutes', 0)}m, headroom={top.get('remaining_headroom', 0)}m)."
        )

    action_line = (
        "- Monitor top bottleneck runway/gate and prioritize short-turn flights to protect departures."
    )
    if "resource" in q or "gse" in q:
        action_line = "- Rebalance GSE from idle pools to active gates and clear blocked tasks early."
    elif "surface" in q or "taxi" in q:
        action_line = "- Monitor taxi-out queue and use runway flow smoothing to reduce gate-release pressure."
    elif "delay" in q or "risk" in q:
        action_line = "- Prioritize at-risk flights and protect their gate service completion window."
    elif "runway" in q:
        action_line = "- Shift non-urgent movements away from the busiest runway where feasible."
    elif "gate" in q:
        action_line = "- Hold buffer gates near the busiest stand cluster to absorb short-term peaks."

    return (
        "Overview:\n"
        f"- Active flights: {kpis.get('active_flights', 0)}, throughput: "
        f"{round(float(kpis.get('flights_per_hour', 0.0)), 1)}/hr.\n"
        f"- Upcoming: arrivals={kpis.get('upcoming_arrivals', 0)}, "
        f"departures={kpis.get('upcoming_departures', 0)}.\n"
        f"{overview_q}\n"
        "Bottlenecks:\n"
        f"- Runway pressure: {top_runway} ({top_runway_ops} ops in window).\n"
        f"- Gate pressure: {top_gate} ({top_gate_ops} ops in window).\n"
        f"- Avg delay: {round(float(kpis.get('avg_delay', 0.0)), 1)} min, "
        f"max delay: {kpis.get('max_delay', 0)} min.\n"
        f"{risk_line}\n"
        f"- GSE load: busy={gse_busy}/{gse_total}, active+scheduled tasks={gse_active + gse_sched}.\n"
        f"- Surface flow: taxi_in={taxi_in}, taxi_out={taxi_out}, avg hold={avg_hold}m.\n"
        "Action:\n"
        f"{action_line}"
    )


@dash.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Backend is running"})


@dash.route("/db-check", methods=["GET"])
def db_check():
    try:
        db = get_db()
        db.command("ping")
        collections = db.list_collection_names()

        return jsonify(
            {
                "db_connected": True,
                "database": db.name,
                "collections": collections,
            }
        )

    except Exception as e:
        return jsonify({"db_connected": False, "error": str(e)}), 500


@dash.route("/dashboard")
def all_flights():
    return jsonify(get_all_flights())


def active_flights():
    return jsonify(get_active_flights())


@dash.route("/schedule", methods=["GET"])
def generate_schedule():
    current_time = 10  # example day minute
    freeze_window = 15
    planning_horizon = 180

    flights = get_active_flights()
    committed = get_committed_schedule()

    result = solve_airport_schedule(
        R=3,
        G=5,
        flights=flights,
        committed_schedule=committed,
        current_time=current_time,
        planning_horizon=planning_horizon,
        freeze_window=freeze_window,
    )

    if result["status"] != "success":
        return result

    version = int(time())

    save_schedule_version(version, current_time, freeze_window, planning_horizon)
    save_schedule_assignments(result["schedule"], version, current_time + freeze_window)

    return result


@dash.route("/latest-schedule", methods=["GET"])
def get_latest_schedule():
    db = get_db()
    schedule = list(db["schedule"].find({}, {"_id": 0}))

    # Backfill runway label for older rows that may only have runway_index.
    for row in schedule:
        runway = str(row.get("runway") or "").strip()
        if runway:
            continue
        try:
            idx = int(row.get("runway_index", -1))
        except (TypeError, ValueError):
            idx = -1
        if idx == 0:
            row["runway"] = "16/34"
        elif idx == 1:
            row["runway"] = "10/28"
        elif idx == 2:
            row["runway"] = "14/32"

    return {
        "status": "success",
        "schedule": schedule,
        "simulation_time": scheduler_service.simulation_time,
    }


@dash.route("/flights", methods=["GET"])
def list_flights():
    db = get_db()
    current_time = scheduler_service.simulation_time

    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    try:
        limit = max(1, min(200, int(request.args.get("limit", 50))))
    except (TypeError, ValueError):
        limit = 50

    status_filter = str(request.args.get("status", "all")).strip().lower()
    priority_filter = str(request.args.get("priority", "all")).strip().lower()
    search_query = str(request.args.get("q", "")).strip().lower()
    sort_by = str(request.args.get("sort", "scheduled_arrival")).strip()
    sort_order = str(request.args.get("order", "asc")).strip().lower()
    reverse = sort_order == "desc"

    try:
        from_time = int(request.args["from"]) if "from" in request.args else None
    except (TypeError, ValueError):
        from_time = None

    try:
        to_time = int(request.args["to"]) if "to" in request.args else None
    except (TypeError, ValueError):
        to_time = None

    flights_raw = list(db["flight"].find({}, {"_id": 0}))
    schedule_raw = list(db["schedule"].find({}, {"_id": 0}))

    schedule_by_flight = {}
    for row in schedule_raw:
        fid = row.get("flight_id")
        if fid:
            schedule_by_flight[fid] = row

    def runway_label(item):
        runway = str(item.get("runway") or "").strip()
        if runway:
            return runway
        try:
            idx = int(item.get("runway_index", -1))
        except (TypeError, ValueError):
            idx = -1
        if idx == 0:
            return "16/34"
        if idx == 1:
            return "10/28"
        if idx == 2:
            return "14/32"
        return ""

    def safe_operational_time(value):
        try:
            t = int(value)
        except (TypeError, ValueError):
            return None
        # 0 is usually a placeholder/legacy value for "not set yet".
        return t if t > 0 else None

    rows = []
    for flight in flights_raw:
        fid = flight.get("flight_id")
        if not fid:
            continue

        sched = schedule_by_flight.get(fid, {})
        scheduled_arrival = flight.get("scheduled_arrival")
        landing_time = safe_operational_time(
            sched.get("landing_time", flight.get("landing_time"))
        )
        gate = (
            sched.get("gate")
            or flight.get("gate")
            or flight.get("assigned_gate")
        )
        runway = (
            runway_label(sched)
            or str(flight.get("runway") or "").strip()
            or str(flight.get("assigned_runway") or "").strip()
        )
        priority = str(flight.get("priority") or "normal").strip().lower()
        status = str(flight.get("status") or "unknown").strip().lower()

        delay_minutes = None
        if scheduled_arrival is not None and landing_time is not None:
            try:
                delay_minutes = int(landing_time) - int(scheduled_arrival)
            except (TypeError, ValueError):
                delay_minutes = None

        row = {
            "flight_id": fid,
            "status": status,
            "priority": priority if priority in _ALLOWED_PRIORITIES else "normal",
            "aircraft_type": flight.get("aircraft_type", ""),
            "scheduled_arrival": scheduled_arrival,
            "landing_time": landing_time,
            "gate_arrival": safe_operational_time(
                sched.get("gate_arrival", flight.get("gate_arrival"))
            ),
            "gate_departure": safe_operational_time(
                sched.get("gate_departure", flight.get("gate_departure"))
            ),
            "takeoff_time": safe_operational_time(
                sched.get("takeoff_time", flight.get("takeoff_time"))
            ),
            "gate": gate,
            "runway": runway,
            "delay_minutes": delay_minutes,
            "max_delay": flight.get("max_delay"),
        }

        if status_filter != "all" and row["status"] != status_filter:
            continue
        if priority_filter != "all" and row["priority"] != priority_filter:
            continue

        try:
            sched_time = int(row["scheduled_arrival"])
        except (TypeError, ValueError):
            sched_time = None

        if from_time is not None and (sched_time is None or sched_time < from_time):
            continue
        if to_time is not None and (sched_time is None or sched_time > to_time):
            continue

        if search_query:
            searchable = " ".join(
                [
                    str(row.get("flight_id", "")),
                    str(row.get("status", "")),
                    str(row.get("priority", "")),
                    str(row.get("aircraft_type", "")),
                    str(row.get("gate", "")),
                    str(row.get("runway", "")),
                ]
            ).lower()
            if search_query not in searchable:
                continue

        rows.append(row)

    sortable_fields = {
        "flight_id",
        "status",
        "priority",
        "scheduled_arrival",
        "landing_time",
        "delay_minutes",
        "gate",
        "runway",
        "takeoff_time",
    }
    if sort_by not in sortable_fields:
        sort_by = "scheduled_arrival"

    numeric_fields = {"scheduled_arrival", "landing_time", "delay_minutes", "takeoff_time"}

    def sort_key(item):
        value = item.get(sort_by)
        if value is None:
            return (1, 0)
        if sort_by in numeric_fields:
            try:
                return (0, float(value))
            except (TypeError, ValueError):
                return (1, 0)
        return (0, str(value).lower())

    rows.sort(key=sort_key, reverse=reverse)

    total = len(rows)
    start = (page - 1) * limit
    end = start + limit
    paged_rows = rows[start:end]

    return jsonify(
        {
            "status": "success",
            "simulation_time": current_time,
            "page": page,
            "limit": limit,
            "total": total,
            "flights": paged_rows,
        }
    )


@dash.route("/flights/<flight_id>/priority", methods=["PATCH"])
def update_flight_priority(flight_id: str):
    payload = request.get_json(silent=True) or {}
    priority = str(payload.get("priority") or "").strip().lower()

    if priority not in _ALLOWED_PRIORITIES:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"Invalid priority. Allowed: {sorted(_ALLOWED_PRIORITIES)}",
                }
            ),
            400,
        )

    db = get_db()
    result = db["flight"].update_one(
        {"flight_id": flight_id},
        {"$set": {"priority": priority}},
    )

    if result.matched_count == 0:
        return jsonify({"status": "error", "message": "Flight not found"}), 404

    return jsonify(
        {
            "status": "success",
            "flight_id": flight_id,
            "priority": priority,
        }
    )


@dash.route("/dashboard-insights", methods=["GET"])
def dashboard_insights():
    try:
        window = int(request.args.get("window", 120))
    except (TypeError, ValueError):
        window = 120

    current_time = scheduler_service.simulation_time
    insights = get_dashboard_insights(current_time=current_time, window_minutes=window)

    return jsonify(
        {
            "status": "success",
            "simulation_time": current_time,
            "window_minutes": window,
            **insights,
        }
    )


@dash.route("/ai-insights", methods=["POST"])
def ai_insights():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    try:
        window = int(payload.get("window", 120))
    except (TypeError, ValueError):
        window = 120

    if window <= 0:
        window = 60

    current_time = scheduler_service.simulation_time
    base_insights = get_dashboard_insights(current_time=current_time, window_minutes=window)
    db = get_db()

    # Risk flights based on delay headroom.
    flights = list(
        db["flight"].find(
            {"status": {"$ne": "departed"}},
            {"_id": 0, "flight_id": 1, "scheduled_arrival": 1, "max_delay": 1},
        )
    )
    schedule_rows = list(
        db["schedule"].find(
            {},
            {"_id": 0, "flight_id": 1, "landing_time": 1},
        )
    )
    schedule_by_fid = {s.get("flight_id"): s for s in schedule_rows if s.get("flight_id")}
    risk_flights = []
    for f in flights:
        fid = f.get("flight_id")
        if not fid:
            continue
        landing = schedule_by_fid.get(fid, {}).get("landing_time")
        if landing is None:
            continue
        try:
            arr = int(f.get("scheduled_arrival"))
            max_delay = int(f.get("max_delay", 30))
            landing_t = int(landing)
        except (TypeError, ValueError):
            continue
        delay = landing_t - arr
        risk_flights.append(
            {
                "flight_id": fid,
                "delay_minutes": delay,
                "remaining_headroom": max_delay - delay,
            }
        )
    risk_flights.sort(key=lambda x: (x["remaining_headroom"], -x["delay_minutes"], x["flight_id"]))
    risk_flights = risk_flights[:5]

    resources = list(db["resource"].find({}, {"_id": 0, "status": 1}))
    service_tasks = list(db["service_task"].find({}, {"_id": 0, "status": 1}))
    gse_busy = sum(1 for r in resources if str(r.get("status", "")).lower() == "busy")
    task_counts = {"blocked": 0, "pending": 0, "scheduled": 0, "active": 0, "done": 0}
    for t in service_tasks:
        s = str(t.get("status", "")).lower()
        if s in task_counts:
            task_counts[s] += 1

    horizon_end = current_time + max(1, window)
    surface_docs = list(
        db["surface_state"].find(
            {"end_time": {"$gte": current_time}, "start_time": {"$lte": horizon_end}},
            {"_id": 0, "mode": 1, "hold_minutes": 1},
        )
    )
    taxi_in = sum(1 for d in surface_docs if str(d.get("mode", "")).lower() == "taxi_in")
    taxi_out = sum(1 for d in surface_docs if str(d.get("mode", "")).lower() == "taxi_out")
    holds = []
    for d in surface_docs:
        try:
            holds.append(int(d.get("hold_minutes", 0)))
        except (TypeError, ValueError):
            holds.append(0)

    context = {
        "simulation_time": current_time,
        "window_minutes": window,
        "kpis": base_insights.get("kpis", {}),
        "top_bottlenecks": {
            "runways": _top_bottlenecks(base_insights.get("runway_utilization", {})),
            "gates": _top_bottlenecks(base_insights.get("gate_utilization", {})),
        },
        "risk_flights": risk_flights,
        "gse": {
            "resources_total": len(resources),
            "busy": gse_busy,
            "idle": max(0, len(resources) - gse_busy),
            "tasks": task_counts,
        },
        "surface": {
            "plans_total": len(surface_docs),
            "taxi_in": taxi_in,
            "taxi_out": taxi_out,
            "avg_hold_minutes": round((sum(holds) / len(holds)), 2) if holds else 0.0,
        },
        "recent_events": [],
    }

    fallback_answer = _context_briefing(context, question)

    answer = ""
    try:
        agent = _get_explanation_agent()
        prompt = _build_ai_prompt(context=context, question=question)
        raw = agent.invoke({"input": prompt})
        answer = _extract_agent_answer(raw) or fallback_answer
        lower = answer.lower()
        if (
            "i'm sorry" in lower
            or "i cannot" in lower
            or "i can't" in lower
            or "don't have the tool" in lower
            or "do not have the tool" in lower
        ):
            answer = fallback_answer
    except Exception as e:
        print("AI insights error:", e)
        answer = fallback_answer

    return jsonify(
        {
            "status": "success",
            "simulation_time": current_time,
            "window_minutes": window,
            "context": context,
            "answer": answer,
        }
    )


@dash.route("/ai-query", methods=["POST"])
def ai_query():
    payload = request.get_json(silent=True) or {}
    payload["window"] = payload.get("window", 120)
    with dash.test_request_context("/api/ai-insights", method="POST", json=payload):
        return ai_insights()


@dash.route("/flight/<flight_id>/details", methods=["GET"])
def flight_details(flight_id: str):
    details = get_flight_details(flight_id)

    if isinstance(details, str):
        return jsonify({"status": "error", "message": details}), 404

    return jsonify({"status": "success", "details": details})


@dash.route("/surface-state", methods=["GET"])
def surface_state():
    db = get_db()
    try:
        window = int(request.args.get("window", 60))
    except (TypeError, ValueError):
        window = 60

    current_time = scheduler_service.simulation_time
    horizon_end = current_time + max(1, window)

    docs = list(
        db["surface_state"].find(
            {"end_time": {"$gte": current_time}, "start_time": {"$lte": horizon_end}},
            {"_id": 0},
        )
    )
    return jsonify(
        {
            "status": "success",
            "simulation_time": current_time,
            "window_minutes": window,
            "surface_state": docs,
        }
    )


@dash.route("/resources", methods=["GET"])
def resources_state():
    db = get_db()
    resources = list(db["resource"].find({}, {"_id": 0}))

    try:
        limit = int(request.args.get("tasks", 100))
    except (TypeError, ValueError):
        limit = 100

    tasks = (
        db["service_task"]
        .find({}, {"_id": 0})
        .sort("window_end", 1)
        .limit(max(1, limit))
    )

    return jsonify(
        {
            "status": "success",
            "simulation_time": scheduler_service.simulation_time,
            "resources": resources,
            "service_tasks": list(tasks),
        }
    )


@dash.route("/multi-agent/step", methods=["POST"])
def multi_agent_step():
    payload = request.get_json(silent=True) or {}
    try:
        t = int(payload.get("time", scheduler_service.simulation_time))
    except (TypeError, ValueError):
        t = scheduler_service.simulation_time

    result = multi_agent_coordinator.step(current_time=t)
    return jsonify(result)


