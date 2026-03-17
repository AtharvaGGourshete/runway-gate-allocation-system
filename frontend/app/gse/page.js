"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";

const formatTime = (minutes) => {
  const safe = Number(minutes);
  if (!Number.isFinite(safe) || safe < 0) return "--:--";
  const hrs = Math.floor(safe / 60);
  const mins = safe % 60;
  return `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
};

const STAGE_ORDER = ["passenger_bus", "cleaning", "fueling", "catering"];
const STATUS_COLUMNS = ["blocked", "pending", "scheduled", "active", "done"];

const pretty = (value) =>
  String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (m) => m.toUpperCase());

export default function GseTurnaroundPage() {
  const [resources, setResources] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [simulationTime, setSimulationTime] = useState(0);

  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const hasLoadedOnceRef = useRef(false);

  const [resourceType, setResourceType] = useState("all");
  const [resourceStatus, setResourceStatus] = useState("all");
  const [taskStatus, setTaskStatus] = useState("all");
  const [taskStage, setTaskStage] = useState("all");
  const [flightQuery, setFlightQuery] = useState("");

  const [resourceLimit, setResourceLimit] = useState(40);
  const [taskLimit, setTaskLimit] = useState(80);

  useEffect(() => {
    let canceled = false;

    const fetchData = async (background = false) => {
      try {
        if (!canceled && hasLoadedOnceRef.current && background) {
          setIsRefreshing(true);
        } else if (!canceled && !hasLoadedOnceRef.current) {
          setIsInitialLoading(true);
          setError(null);
        }

        const res = await fetch("http://localhost:5000/api/resources?tasks=500", {
          cache: "no-store",
        });
        const json = await res.json();

        if (!res.ok || json.status !== "success") {
          throw new Error(json.message || "Failed to load resources");
        }

        if (canceled) return;

        setResources(Array.isArray(json.resources) ? json.resources : []);
        setTasks(Array.isArray(json.service_tasks) ? json.service_tasks : []);
        setSimulationTime(Number(json.simulation_time || 0));
        setError(null);
        hasLoadedOnceRef.current = true;
      } catch (err) {
        if (canceled) return;
        if (!hasLoadedOnceRef.current) {
          setError(err.message || "Unable to load GSE data.");
        }
      } finally {
        if (!canceled) {
          setIsInitialLoading(false);
          setIsRefreshing(false);
        }
      }
    };

    fetchData(false);
    const interval = setInterval(() => {
      if (typeof document !== "undefined" && document.visibilityState !== "visible") {
        return;
      }
      fetchData(true);
    }, 8000);

    return () => {
      canceled = true;
      clearInterval(interval);
    };
  }, []);

  const resourceTypeOptions = useMemo(() => {
    const set = new Set(resources.map((r) => String(r.resource_type || "")).filter(Boolean));
    return Array.from(set).sort();
  }, [resources]);

  const taskStageOptions = useMemo(() => {
    const set = new Set(tasks.map((t) => String(t.service_type || "")).filter(Boolean));
    const fromOrder = STAGE_ORDER.filter((s) => set.has(s));
    const rest = Array.from(set).filter((s) => !fromOrder.includes(s)).sort();
    return [...fromOrder, ...rest];
  }, [tasks]);

  const filteredResources = useMemo(() => {
    return resources
      .filter((r) => {
        const typeOk = resourceType === "all" || String(r.resource_type) === resourceType;
        const statusOk = resourceStatus === "all" || String(r.status || "").toLowerCase() === resourceStatus;
        return typeOk && statusOk;
      })
      .sort((a, b) => String(a.resource_id || "").localeCompare(String(b.resource_id || "")));
  }, [resources, resourceType, resourceStatus]);

  const filteredTasks = useMemo(() => {
    const q = flightQuery.trim().toLowerCase();
    return tasks
      .filter((t) => {
        const status = String(t.status || "").toLowerCase();
        const stage = String(t.service_type || "");
        const flight = String(t.flight_id || "").toLowerCase();

        const statusOk = taskStatus === "all" || status === taskStatus;
        const stageOk = taskStage === "all" || stage === taskStage;
        const queryOk = !q || flight.includes(q);
        return statusOk && stageOk && queryOk;
      })
      .sort((a, b) => Number(a.window_end || 0) - Number(b.window_end || 0));
  }, [tasks, taskStatus, taskStage, flightQuery]);

  const resourceSummary = useMemo(() => {
    const total = resources.length;
    const busy = resources.filter((r) => String(r.status || "").toLowerCase() === "busy").length;
    const idle = total - busy;
    const utilization = total > 0 ? Math.round((busy / total) * 100) : 0;

    const byType = {};
    for (const r of resources) {
      const type = String(r.resource_type || "unknown");
      const st = String(r.status || "idle").toLowerCase();
      if (!byType[type]) {
        byType[type] = { total: 0, busy: 0, idle: 0 };
      }
      byType[type].total += 1;
      if (st === "busy") byType[type].busy += 1;
      else byType[type].idle += 1;
    }

    return { total, busy, idle, utilization, byType };
  }, [resources]);

  const taskSummary = useMemo(() => {
    const summary = { blocked: 0, pending: 0, scheduled: 0, active: 0, done: 0 };
    for (const t of tasks) {
      const s = String(t.status || "").toLowerCase();
      if (summary[s] != null) summary[s] += 1;
    }
    return summary;
  }, [tasks]);

  const pipeline = useMemo(() => {
    const map = { blocked: [], pending: [], scheduled: [], active: [], done: [] };
    for (const t of filteredTasks) {
      const s = String(t.status || "").toLowerCase();
      if (map[s]) {
        map[s].push(t);
      }
    }
    return map;
  }, [filteredTasks]);

  return (
    <div className="min-h-screen bg-[#141414] text-[#f7c576] px-2 md:px-3 lg:px-4 py-8">
      <div className="max-w-[1820px] mx-auto space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">GSE & Turnaround</h1>
            <p className="text-sm text-[#f7c576]/70 mt-1">
              Fleet visibility, service-stage sequencing, and turnaround execution status.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/dashboard"
              className="px-4 py-2 text-xs font-semibold rounded-xl border border-[#2a2a2a] bg-[#1f1f1f] hover:bg-[#252525]"
            >
              Back to Dashboard
            </Link>
            <Link
              href="/flights"
              className="px-4 py-2 text-xs font-semibold rounded-xl border border-[#2a2a2a] bg-[#1f1f1f] hover:bg-[#252525]"
            >
              Flights Center
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl px-4 py-3">
            <div className="text-[11px] uppercase tracking-widest text-[#f7c576]/70 font-semibold">Simulation Time</div>
            <div className="text-2xl font-bold mt-1">{formatTime(simulationTime)}</div>
          </div>
          <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl px-4 py-3">
            <div className="text-[11px] uppercase tracking-widest text-[#f7c576]/70 font-semibold">Resources</div>
            <div className="text-2xl font-bold mt-1">{resourceSummary.total}</div>
            <div className="text-xs text-[#f7c576]/70 mt-1">Busy {resourceSummary.busy} | Idle {resourceSummary.idle}</div>
          </div>
          <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl px-4 py-3">
            <div className="text-[11px] uppercase tracking-widest text-[#f7c576]/70 font-semibold">Utilization</div>
            <div className="text-2xl font-bold mt-1">{resourceSummary.utilization}%</div>
            <div className="text-xs text-[#f7c576]/70 mt-1">Current fleet busy ratio</div>
          </div>
          <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl px-4 py-3">
            <div className="text-[11px] uppercase tracking-widest text-[#f7c576]/70 font-semibold">Tasks</div>
            <div className="text-sm mt-1 text-[#f7c576]/85">
              Active: <span className="font-semibold">{taskSummary.active}</span> | Scheduled:{" "}
              <span className="font-semibold">{taskSummary.scheduled}</span>
            </div>
            <div className="text-xs text-[#f7c576]/70 mt-1">
              Pending {taskSummary.pending} | Blocked {taskSummary.blocked}
            </div>
          </div>
        </div>

        <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl p-4 grid grid-cols-1 md:grid-cols-6 gap-3">
          <select
            value={resourceType}
            onChange={(e) => setResourceType(e.target.value)}
            className="rounded-xl bg-[#141414] border border-[#2a2a2a] px-3 py-2 text-sm"
          >
            <option value="all">Resource type: All</option>
            {resourceTypeOptions.map((t) => (
              <option key={t} value={t}>{pretty(t)}</option>
            ))}
          </select>

          <select
            value={resourceStatus}
            onChange={(e) => setResourceStatus(e.target.value)}
            className="rounded-xl bg-[#141414] border border-[#2a2a2a] px-3 py-2 text-sm"
          >
            <option value="all">Resource status: All</option>
            <option value="idle">Idle</option>
            <option value="busy">Busy</option>
          </select>

          <select
            value={taskStatus}
            onChange={(e) => setTaskStatus(e.target.value)}
            className="rounded-xl bg-[#141414] border border-[#2a2a2a] px-3 py-2 text-sm"
          >
            <option value="all">Task status: All</option>
            {STATUS_COLUMNS.map((s) => (
              <option key={s} value={s}>{pretty(s)}</option>
            ))}
          </select>

          <select
            value={taskStage}
            onChange={(e) => setTaskStage(e.target.value)}
            className="rounded-xl bg-[#141414] border border-[#2a2a2a] px-3 py-2 text-sm"
          >
            <option value="all">Stage: All</option>
            {taskStageOptions.map((s) => (
              <option key={s} value={s}>{pretty(s)}</option>
            ))}
          </select>

          <input
            value={flightQuery}
            onChange={(e) => setFlightQuery(e.target.value)}
            placeholder="Filter by flight ID..."
            className="rounded-xl bg-[#141414] border border-[#2a2a2a] px-3 py-2 text-sm text-[#f7c576] placeholder:text-[#f7c576]/40 focus:outline-none"
          />

          <div className="text-xs text-[#f7c576]/65 flex items-center justify-end pr-1">
            {isRefreshing ? "Refreshing in background..." : "Auto-refresh every 8s"}
          </div>
        </div>

        {isInitialLoading && (
          <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl px-4 py-8 text-sm text-[#f7c576]/70">
            Loading GSE operations...
          </div>
        )}

        {error && !isInitialLoading && (
          <div className="bg-red-900/40 border border-red-500/60 rounded-2xl px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        )}

        {!isInitialLoading && !error && (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
              <div className="lg:col-span-2 bg-[#1f1f1f] rounded-2xl border border-[#2a2a2a] overflow-hidden h-[540px] flex flex-col">
                <div className="px-4 py-3 border-b border-[#2a2a2a] bg-[#1b1b1b] text-sm font-semibold">
                  Resources ({filteredResources.length})
                </div>
                <div className="overflow-auto flex-1">
                  <table className="w-full text-xs md:text-sm">
                    <thead className="bg-[#232323] text-[#f7c576]/75 uppercase text-xs sticky top-0 z-10">
                      <tr>
                        <th className="text-left px-3 py-2">Resource</th>
                        <th className="text-left px-3 py-2">Type</th>
                        <th className="text-left px-3 py-2">Status</th>
                        <th className="text-left px-3 py-2">Location</th>
                        <th className="text-left px-3 py-2">Available</th>
                      </tr>
                    </thead>
                    <tbody className="text-[#f7c576]">
                      {filteredResources.slice(0, resourceLimit).map((r) => (
                        <tr key={r.resource_id} className="border-t border-[#2a2a2a]">
                          <td className="px-3 py-2 font-semibold">{r.resource_id}</td>
                          <td className="px-3 py-2 text-[#f7c576]/80">{pretty(r.resource_type)}</td>
                          <td className="px-3 py-2">
                            <span className={`px-2 py-0.5 rounded-full text-[11px] border ${String(r.status).toLowerCase() === "busy" ? "bg-[#3a272a] border-[#5a363d] text-[#ff9ea6]" : "bg-[#263244] border-[#334661] text-[#9bc3ff]"}`}>
                              {pretty(r.status)}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-[#f7c576]/80">{r.location_node || "--"}</td>
                          <td className="px-3 py-2 text-[#f7c576]/80">{formatTime(r.available_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="px-3 py-2 border-t border-[#2a2a2a] bg-[#1b1b1b] text-xs flex justify-end">
                  <select
                    value={resourceLimit}
                    onChange={(e) => setResourceLimit(Number(e.target.value))}
                    className="rounded-lg bg-[#141414] border border-[#2a2a2a] px-2 py-1"
                  >
                    <option value={20}>Show 20</option>
                    <option value={40}>Show 40</option>
                    <option value={80}>Show 80</option>
                    <option value={150}>Show 150</option>
                  </select>
                </div>
              </div>

              <div className="lg:col-span-3 bg-[#1f1f1f] rounded-2xl border border-[#2a2a2a] overflow-hidden h-[540px] flex flex-col">
                <div className="px-4 py-3 border-b border-[#2a2a2a] bg-[#1b1b1b] text-sm font-semibold">
                  Service Task Pipeline ({filteredTasks.length})
                </div>
                <div className="grid grid-cols-1 md:grid-cols-5 gap-3 p-3 overflow-auto flex-1">
                  {STATUS_COLUMNS.map((status) => (
                    <div key={status} className="bg-[#191919] border border-[#2a2a2a] rounded-xl min-h-[420px] flex flex-col">
                      <div className="px-3 py-2 border-b border-[#2a2a2a] text-xs uppercase tracking-wider text-[#f7c576]/75 font-semibold flex items-center justify-between">
                        <span>{pretty(status)}</span>
                        <span className="text-[#f7c576]">{pipeline[status].length}</span>
                      </div>
                      <div className="p-2 space-y-2 overflow-y-auto flex-1">
                        {pipeline[status].slice(0, taskLimit).map((t) => (
                          <div key={`${t.flight_id}-${t.service_type}-${t.stage_order}`} className="bg-[#232323] border border-[#353535] rounded-lg p-2 text-xs">
                            <div className="font-semibold text-[#f7c576]">{t.flight_id}</div>
                            <div className="text-[#f7c576]/75 mt-0.5">{pretty(t.service_type)}</div>
                            <div className="text-[#f7c576]/70 mt-0.5">{t.assigned_resource_id || "unassigned"}</div>
                            <div className="text-[#f7c576]/60 mt-1">{t.gate_node || "--"} | {formatTime(t.window_start)} {"->"} {formatTime(t.window_end)}</div>
                          </div>
                        ))}
                        {pipeline[status].length === 0 && (
                          <div className="text-xs text-[#f7c576]/50 px-1 py-1">No tasks</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="px-3 py-2 border-t border-[#2a2a2a] bg-[#1b1b1b] text-xs flex justify-end">
                  <select
                    value={taskLimit}
                    onChange={(e) => setTaskLimit(Number(e.target.value))}
                    className="rounded-lg bg-[#141414] border border-[#2a2a2a] px-2 py-1"
                  >
                    <option value={30}>Show 30/column</option>
                    <option value={60}>Show 60/column</option>
                    <option value={120}>Show 120/column</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="bg-[#1f1f1f] rounded-2xl border border-[#2a2a2a] overflow-hidden">
              <div className="px-4 py-3 border-b border-[#2a2a2a] bg-[#1b1b1b] text-sm font-semibold">
                Fleet Type Utilization
              </div>
              <div className="p-4 grid grid-cols-1 md:grid-cols-4 gap-3">
                {Object.entries(resourceSummary.byType).map(([type, stats]) => {
                  const util = stats.total > 0 ? Math.round((stats.busy / stats.total) * 100) : 0;
                  return (
                    <div key={type} className="bg-[#191919] border border-[#2a2a2a] rounded-xl p-3">
                      <div className="text-xs uppercase tracking-wider text-[#f7c576]/70 font-semibold">{pretty(type)}</div>
                      <div className="text-2xl font-bold mt-1 text-[#f7c576]">{util}%</div>
                      <div className="text-xs text-[#f7c576]/70 mt-1">Busy {stats.busy} / Total {stats.total}</div>
                    </div>
                  );
                })}
                {Object.keys(resourceSummary.byType).length === 0 && (
                  <div className="text-sm text-[#f7c576]/60">No resource data yet.</div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
