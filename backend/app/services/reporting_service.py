from __future__ import annotations

import csv
import io
import time
from typing import Any, Dict, List, Tuple

from app.db.mongo import get_db
from app.services.analytics_service import get_dashboard_insights


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _bucket_label(minute_value: int) -> str:
    minute_value = max(0, _to_int(minute_value, 0))
    hh = minute_value // 60
    mm = minute_value % 60
    return f"{hh:02d}:{mm:02d}"


def _build_delay_summary(delay_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(delay_rows)
    if total == 0:
        return {
            "total_flights": 0,
            "on_time_0_min": 0.0,
            "within_5_min": 0.0,
            "within_15_min": 0.0,
            "severe_over_15_min": 0.0,
        }

    delays = [_to_int(r.get("delay_minutes", 0), 0) for r in delay_rows]
    on_time_0 = sum(1 for d in delays if d <= 0)
    within_5 = sum(1 for d in delays if d <= 5)
    within_15 = sum(1 for d in delays if d <= 15)
    severe = sum(1 for d in delays if d > 15)

    return {
        "total_flights": total,
        "on_time_0_min": round((on_time_0 / total) * 100, 2),
        "within_5_min": round((within_5 / total) * 100, 2),
        "within_15_min": round((within_15 / total) * 100, 2),
        "severe_over_15_min": round((severe / total) * 100, 2),
    }


def _build_kpi_trends(
    *, delay_rows: List[Dict[str, Any]], bucket_map: Dict[int, Dict[str, int]], window_minutes: int
) -> List[Dict[str, Any]]:
    # throughput per bucket, average delay by landing bucket
    delay_by_bucket: Dict[int, List[int]] = {}
    bucket_size = 15
    for r in delay_rows:
        landing = _to_int(r.get("landing_time"), -1)
        if landing < 0:
            continue
        bucket = landing - (landing % bucket_size)
        delay_by_bucket.setdefault(bucket, []).append(_to_int(r.get("delay_minutes", 0), 0))

    trends = []
    hours_per_bucket = bucket_size / 60.0
    for bucket in sorted(bucket_map.keys()):
        arrivals = _to_int(bucket_map[bucket].get("arrivals", 0), 0)
        departures = _to_int(bucket_map[bucket].get("departures", 0), 0)
        avg_delay = 0.0
        vals = delay_by_bucket.get(bucket, [])
        if vals:
            avg_delay = round(sum(vals) / len(vals), 2)
        throughput = round((arrivals + departures) / hours_per_bucket, 2)
        trends.append(
            {
                "time": _bucket_label(bucket),
                "arrivals": arrivals,
                "departures": departures,
                "avg_delay": avg_delay,
                "throughput_per_hour": throughput,
            }
        )
    # Keep only recent trend points sized by window.
    max_points = max(4, min(40, window_minutes // 15 + 1))
    return trends[-max_points:]


def get_reporting_summary(*, current_time: int, window_minutes: int = 240) -> Dict[str, Any]:
    if window_minutes <= 0:
        window_minutes = 240

    db = get_db()
    start_time = max(0, current_time - window_minutes)
    insights = get_dashboard_insights(current_time=current_time, window_minutes=window_minutes)

    schedule = list(
        db["schedule"].find(
            {
                "$or": [
                    {"landing_time": {"$gte": start_time, "$lte": current_time}},
                    {"takeoff_time": {"$gte": start_time, "$lte": current_time}},
                ]
            },
            {"_id": 0, "flight_id": 1, "landing_time": 1, "takeoff_time": 1, "runway": 1, "gate": 1},
        )
    )
    flights = list(
        db["flight"].find(
            {},
            {"_id": 0, "flight_id": 1, "scheduled_arrival": 1, "status": 1, "aircraft_type": 1},
        )
    )
    by_fid = {f.get("flight_id"): f for f in flights if f.get("flight_id")}

    runway_counts: Dict[str, int] = {}
    gate_counts: Dict[str, int] = {}
    delay_rows: List[Dict[str, Any]] = []

    bucket_size = 15
    bucket_map: Dict[int, Dict[str, int]] = {}
    for t in range(start_time - (start_time % bucket_size), current_time + bucket_size, bucket_size):
        bucket_map[t] = {"arrivals": 0, "departures": 0}

    for row in schedule:
        runway = str(row.get("runway") or "Unknown")
        gate = str(row.get("gate") or "Unknown")
        runway_counts[runway] = runway_counts.get(runway, 0) + 1
        gate_counts[gate] = gate_counts.get(gate, 0) + 1

        landing = row.get("landing_time")
        takeoff = row.get("takeoff_time")

        if isinstance(landing, int) and start_time <= landing <= current_time:
            bucket = landing - (landing % bucket_size)
            bucket_map.setdefault(bucket, {"arrivals": 0, "departures": 0})
            bucket_map[bucket]["arrivals"] += 1

            fid = row.get("flight_id")
            f = by_fid.get(fid or "")
            if f:
                try:
                    sched_arr = int(f.get("scheduled_arrival"))
                    delay = int(landing) - sched_arr
                    delay_rows.append(
                        {
                            "flight_id": fid,
                            "scheduled_arrival": sched_arr,
                            "landing_time": int(landing),
                            "delay_minutes": delay,
                            "runway": runway,
                            "gate": gate,
                        }
                    )
                except (TypeError, ValueError):
                    pass

        if isinstance(takeoff, int) and start_time <= takeoff <= current_time:
            bucket = takeoff - (takeoff % bucket_size)
            bucket_map.setdefault(bucket, {"arrivals": 0, "departures": 0})
            bucket_map[bucket]["departures"] += 1

    timeline = []
    for bucket in sorted(bucket_map.keys()):
        if bucket < start_time or bucket > current_time:
            continue
        timeline.append(
            {
                "time": _bucket_label(bucket),
                "arrivals": bucket_map[bucket]["arrivals"],
                "departures": bucket_map[bucket]["departures"],
            }
        )

    delay_rows.sort(key=lambda x: x["delay_minutes"], reverse=True)

    resources = list(db["resource"].find({}, {"_id": 0, "status": 1}))
    busy = sum(1 for r in resources if str(r.get("status", "")).lower() == "busy")
    idle = max(0, len(resources) - busy)
    utilization_pct = round((busy / len(resources)) * 100, 2) if resources else 0.0

    delay_summary = _build_delay_summary(delay_rows)
    kpi_trends = _build_kpi_trends(
        delay_rows=delay_rows,
        bucket_map=bucket_map,
        window_minutes=window_minutes,
    )

    return {
        "window_minutes": window_minutes,
        "from_time": start_time,
        "to_time": current_time,
        "kpis": insights.get("kpis", {}),
        "timeline": timeline,
        "kpi_trends": kpi_trends,
        "delay_summary": delay_summary,
        "runway_utilization": runway_counts,
        "gate_utilization": gate_counts,
        "top_delays": delay_rows[:10],
        "resource_snapshot": {
            "total": len(resources),
            "busy": busy,
            "idle": idle,
            "utilization_pct": utilization_pct,
        },
    }


def _schedule_export_rows(*, current_time: int, window_minutes: int) -> Tuple[List[str], List[List[Any]]]:
    db = get_db()
    start_time = max(0, current_time - window_minutes)
    rows = list(
        db["schedule"].find(
            {
                "$or": [
                    {"landing_time": {"$gte": start_time, "$lte": current_time}},
                    {"takeoff_time": {"$gte": start_time, "$lte": current_time}},
                ]
            },
            {"_id": 0},
        )
    )
    headers = [
        "flight_id",
        "runway",
        "gate",
        "landing_time",
        "gate_arrival",
        "gate_departure",
        "takeoff_time",
        "frozen",
        "schedule_version",
    ]
    out = []
    for r in rows:
        out.append([r.get(h, "") for h in headers])
    return headers, out


def _metrics_export_rows(*, current_time: int, window_minutes: int) -> Tuple[List[str], List[List[Any]]]:
    summary = get_reporting_summary(current_time=current_time, window_minutes=window_minutes)
    k = summary.get("kpis", {})
    d = summary.get("delay_summary", {})
    r = summary.get("resource_snapshot", {})
    headers = ["metric", "value"]
    rows = [
        ["simulation_time", current_time],
        ["window_minutes", window_minutes],
        ["active_flights", k.get("active_flights", 0)],
        ["total_flights", k.get("total_flights", 0)],
        ["avg_delay_min", round(_to_float(k.get("avg_delay", 0.0), 0.0), 2)],
        ["max_delay_min", _to_int(k.get("max_delay", 0), 0)],
        ["throughput_per_hour", round(_to_float(k.get("flights_per_hour", 0.0), 0.0), 2)],
        ["on_time_pct_0min", d.get("on_time_0_min", 0.0)],
        ["sla_within_5min_pct", d.get("within_5_min", 0.0)],
        ["sla_within_15min_pct", d.get("within_15_min", 0.0)],
        ["severe_delay_over_15min_pct", d.get("severe_over_15_min", 0.0)],
        ["gse_utilization_pct", r.get("utilization_pct", 0.0)],
    ]
    return headers, rows


def _events_export_rows(*, window_minutes: int) -> Tuple[List[str], List[List[Any]]]:
    db = get_db()
    # Events are wall-clock timestamps (epoch seconds), so we export recent real-time window.
    now_epoch = time.time()
    from_epoch = now_epoch - (max(1, window_minutes) * 60)
    docs = list(
        db["event"].find(
            {"timestamp": {"$gte": from_epoch}},
            {"_id": 0},
        ).sort("timestamp", -1)
    )
    headers = ["timestamp", "type", "flight_id", "resource", "action"]
    rows = [[d.get("timestamp", ""), d.get("type", ""), d.get("flight_id", ""), d.get("resource", ""), d.get("action", "")] for d in docs]
    return headers, rows


def get_report_export_rows(*, kind: str, current_time: int, window_minutes: int = 240) -> Tuple[List[str], List[List[Any]]]:
    k = str(kind or "").strip().lower()
    if k == "schedules":
        return _schedule_export_rows(current_time=current_time, window_minutes=window_minutes)
    if k == "events":
        return _events_export_rows(window_minutes=window_minutes)
    return _metrics_export_rows(current_time=current_time, window_minutes=window_minutes)


def csv_bytes_from_rows(headers: List[str], rows: List[List[Any]]) -> bytes:
    sio = io.StringIO()
    writer = csv.writer(sio)
    writer.writerow(headers)
    for r in rows:
        writer.writerow(r)
    return sio.getvalue().encode("utf-8")


def _render_summary_lines(summary: Dict[str, Any], current_time: int) -> List[str]:
    k = summary.get("kpis", {})
    d = summary.get("delay_summary", {})
    r = summary.get("resource_snapshot", {})
    lines = [
        "SkySlot Operational Report",
        f"Simulation Time: {_bucket_label(current_time)}",
        f"Window: {summary.get('window_minutes', 0)} minutes",
        "",
        "KPIs",
        f"- Active flights: {k.get('active_flights', 0)}",
        f"- Throughput: {round(_to_float(k.get('flights_per_hour', 0.0), 0.0), 2)} / hr",
        f"- Avg delay: {round(_to_float(k.get('avg_delay', 0.0), 0.0), 2)} min",
        f"- Max delay: {_to_int(k.get('max_delay', 0), 0)} min",
        "",
        "SLA / Delay Summary",
        f"- On-time (<=0 min): {d.get('on_time_0_min', 0.0)}%",
        f"- Within 5 min: {d.get('within_5_min', 0.0)}%",
        f"- Within 15 min: {d.get('within_15_min', 0.0)}%",
        f"- Severe delays (>15 min): {d.get('severe_over_15_min', 0.0)}%",
        "",
        "Resource Snapshot",
        f"- Busy: {r.get('busy', 0)}/{r.get('total', 0)}",
        f"- Utilization: {r.get('utilization_pct', 0.0)}%",
    ]
    return lines


def _pdf_escape(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_from_lines(lines: List[str]) -> bytes:
    # Minimal single-font PDF generator.
    page_w, page_h = 595, 842
    left, start_y, line_h = 45, 800, 14
    max_lines = int((start_y - 50) / line_h)
    pages = [lines[i:i + max_lines] for i in range(0, len(lines), max_lines)] or [[]]

    objs: List[str] = []
    objs.append("<< /Type /Catalog /Pages 2 0 R >>")

    kids = []
    page_ids = []
    content_ids = []
    obj_id = 3
    for _ in pages:
        page_ids.append(obj_id)
        content_ids.append(obj_id + 1)
        kids.append(f"{obj_id} 0 R")
        obj_id += 2
    objs.append(f"<< /Type /Pages /Count {len(pages)} /Kids [{' '.join(kids)}] >>")

    for i, page_lines in enumerate(pages):
        page_obj = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_w} {page_h}] "
            f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> "
            f"/Contents {content_ids[i]} 0 R >>"
        )
        objs.append(page_obj)

        stream_lines = ["BT", "/F1 11 Tf", f"{left} {start_y} Td"]
        first = True
        for ln in page_lines:
            if not first:
                stream_lines.append(f"0 -{line_h} Td")
            first = False
            stream_lines.append(f"({_pdf_escape(ln)}) Tj")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines)
        content_obj = f"<< /Length {len(stream.encode('latin-1', errors='ignore'))} >>\nstream\n{stream}\nendstream"
        objs.append(content_obj)

    pdf_chunks = ["%PDF-1.4\n"]
    offsets = [0]
    for idx, obj in enumerate(objs, start=1):
        offsets.append(sum(len(x.encode("latin-1", errors="ignore")) for x in pdf_chunks))
        pdf_chunks.append(f"{idx} 0 obj\n{obj}\nendobj\n")

    xref_pos = sum(len(x.encode("latin-1", errors="ignore")) for x in pdf_chunks)
    count = len(objs) + 1
    pdf_chunks.append(f"xref\n0 {count}\n")
    pdf_chunks.append("0000000000 65535 f \n")
    for i in range(1, count):
        pdf_chunks.append(f"{offsets[i]:010d} 00000 n \n")
    pdf_chunks.append(f"trailer\n<< /Size {count} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n")
    return "".join(pdf_chunks).encode("latin-1", errors="ignore")


def pdf_bytes_for_export(*, kind: str, current_time: int, window_minutes: int = 240) -> bytes:
    k = str(kind or "").strip().lower()
    if k == "summary":
        summary = get_reporting_summary(current_time=current_time, window_minutes=window_minutes)
        lines = _render_summary_lines(summary, current_time)
        return _pdf_from_lines(lines)

    headers, rows = get_report_export_rows(kind=k, current_time=current_time, window_minutes=window_minutes)
    title = f"SkySlot {k.title()} Export"
    lines = [title, f"Simulation Time: {_bucket_label(current_time)}", f"Window: {window_minutes} minutes", ""]
    lines.append(" | ".join(headers))
    lines.append("-" * min(120, max(30, len(" | ".join(headers)))))
    for r in rows[:400]:
        lines.append(" | ".join([str(x) for x in r]))
    return _pdf_from_lines(lines)

