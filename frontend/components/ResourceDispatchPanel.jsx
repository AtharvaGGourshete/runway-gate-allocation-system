"use client";

import { useEffect, useMemo, useState } from "react";

export default function ResourceDispatchPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchResources = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch("http://localhost:5000/api/resources?tasks=300", {
        cache: "no-store",
      });
      const json = await res.json();
      if (json.status !== "success") {
        setError(json.message || "Failed to load resources.");
        return;
      }
      setData(json);
    } catch (e) {
      console.error("Resources fetch error:", e);
      setError("Unable to reach backend for resources.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResources();
    const interval = setInterval(fetchResources, 8000);
    return () => clearInterval(interval);
  }, []);

  const resources = data?.resources || [];
  const tasks = data?.service_tasks || [];

  const statusSummary = useMemo(() => {
    const summary = { idle: 0, busy: 0 };
    for (const r of resources) {
      const status = String(r?.status || "idle").toLowerCase();
      if (status === "busy") summary.busy += 1;
      else summary.idle += 1;
    }
    return summary;
  }, [resources]);

  const taskSummary = useMemo(() => {
    const summary = { pending: 0, blocked: 0, scheduled: 0, active: 0, done: 0 };
    for (const t of tasks) {
      const s = String(t?.status || "pending").toLowerCase();
      if (summary[s] != null) summary[s] += 1;
    }
    return summary;
  }, [tasks]);

  const visibleTasks = tasks
    .filter((t) => ["pending", "blocked", "scheduled", "active"].includes(String(t.status)))
    .sort((a, b) => Number(a.window_end || 0) - Number(b.window_end || 0))
    .slice(0, 20);

  return (
    <div className="bg-[#1f1f1f] rounded-2xl shadow-sm border border-[#2a2a2a] p-4 h-[360px] flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-[#f7c576]">GSE Dispatch</h3>
        <button
          onClick={fetchResources}
          className="text-xs font-semibold text-[#f7c576] hover:text-[#ffd28a]"
          disabled={loading}
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error && <div className="text-xs text-red-300">{error}</div>}

      {!error && (
        <div className="space-y-3 flex-1 overflow-y-auto pr-1">
          <div className="text-[11px] text-[#f7c576]/60">
            Sim time: {data?.simulation_time ?? "--"}
          </div>

          <div className="text-[11px] text-[#f7c576]/75 grid grid-cols-2 gap-2">
            <div>
              Total resources: <span className="font-semibold text-[#f7c576]">{resources.length}</span>
            </div>
            <div>
              Busy: <span className="font-semibold text-[#f7c576]">{statusSummary.busy}</span> | Idle:{" "}
              <span className="font-semibold text-[#f7c576]">{statusSummary.idle}</span>
            </div>
            <div>
              Tasks active/scheduled:{" "}
              <span className="font-semibold text-[#f7c576]">{taskSummary.active + taskSummary.scheduled}</span>
            </div>
            <div>
              Pending: <span className="font-semibold text-[#f7c576]">{taskSummary.pending}</span> | Blocked:{" "}
              <span className="font-semibold text-[#f7c576]">{taskSummary.blocked}</span>
            </div>
          </div>

          <div>
            <div className="text-[11px] font-semibold text-[#f7c576]/75 mb-1">Resources</div>
            <div className="max-h-32 overflow-y-auto grid grid-cols-1 gap-1 pr-1">
              {resources.length === 0 && (
                <div className="text-xs text-[#f7c576]/60">No resources found.</div>
              )}
              {resources.map((r) => (
                <div
                  key={r.resource_id}
                  className="flex items-center justify-between text-xs bg-[#232323] border border-[#353535] rounded-lg px-2 py-1"
                >
                  <div className="text-[#f7c576] font-medium">
                    {r.resource_id}{" "}
                    <span className="text-[#f7c576]/60 font-normal">({r.resource_type})</span>
                  </div>
                  <div className="text-[#f7c576]/75">
                    {r.status}
                    {r.status === "busy" && r.available_at != null ? ` -> t=${r.available_at}` : ""}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="text-[11px] font-semibold text-[#f7c576]/75 mb-1">Stage tasks (top 20)</div>
            <div className="max-h-32 overflow-y-auto space-y-1 pr-1">
              {visibleTasks.length === 0 && (
                <div className="text-xs text-[#f7c576]/60">No in-progress tasks yet.</div>
              )}
              {visibleTasks.map((t) => (
                <div
                  key={`${t.flight_id}-${t.service_type}`}
                  className="text-xs bg-[#232323] border border-[#353535] rounded-lg px-2 py-1"
                >
                  <div className="flex items-center justify-between">
                    <div className="font-medium text-[#f7c576]">
                      {t.flight_id} - {t.service_type}
                    </div>
                    <div className="text-[#f7c576]/75">{t.status}</div>
                  </div>
                  <div className="text-[11px] text-[#f7c576]/70">
                    {t.assigned_resource_id || "unassigned"} @ {t.gate_node}{" "}
                    {t.start_time != null && t.end_time != null ? `(t=${t.start_time}->${t.end_time})` : ""}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

