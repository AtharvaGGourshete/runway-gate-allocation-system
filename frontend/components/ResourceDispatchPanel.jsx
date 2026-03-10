"use client";

import { useEffect, useState } from "react";

export default function ResourceDispatchPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchResources = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch("http://localhost:5000/api/resources?tasks=80", {
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
    const interval = setInterval(fetchResources, 10000);
    return () => clearInterval(interval);
  }, []);

  const resources = (data?.resources || []).slice(0, 6);
  const activeTasks = (data?.service_tasks || [])
    .filter((t) => t.status === "active" || t.status === "scheduled")
    .slice(0, 6);

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-800">GSE Dispatch</h3>
        <button
          onClick={fetchResources}
          className="text-xs font-semibold text-blue-600 hover:text-blue-700"
          disabled={loading}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && <div className="text-xs text-red-600">{error}</div>}

      {!error && (
        <div className="space-y-3">
          <div className="text-[11px] text-gray-500">
            Sim time: {data?.simulation_time ?? "—"}
          </div>

          <div>
            <div className="text-[11px] font-semibold text-gray-600 mb-1">
              Resources
            </div>
            <div className="grid grid-cols-1 gap-1">
              {resources.length === 0 && (
                <div className="text-xs text-gray-500">No resources found.</div>
              )}
              {resources.map((r) => (
                <div
                  key={r.resource_id}
                  className="flex items-center justify-between text-xs bg-gray-50 border border-gray-100 rounded-lg px-2 py-1"
                >
                  <div className="text-gray-800 font-medium">
                    {r.resource_id}{" "}
                    <span className="text-gray-500 font-normal">
                      ({r.resource_type})
                    </span>
                  </div>
                  <div className="text-gray-600">
                    {r.status}
                    {r.status === "busy" && r.available_at != null
                      ? ` → t=${r.available_at}`
                      : ""}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="text-[11px] font-semibold text-gray-600 mb-1">
              Active/Scheduled tasks
            </div>
            <div className="space-y-1">
              {activeTasks.length === 0 && (
                <div className="text-xs text-gray-500">No active tasks yet.</div>
              )}
              {activeTasks.map((t) => (
                <div
                  key={`${t.flight_id}-${t.service_type}`}
                  className="text-xs bg-gray-50 border border-gray-100 rounded-lg px-2 py-1"
                >
                  <div className="flex items-center justify-between">
                    <div className="font-medium text-gray-800">
                      {t.flight_id} — {t.service_type}
                    </div>
                    <div className="text-gray-600">{t.status}</div>
                  </div>
                  <div className="text-[11px] text-gray-600">
                    {t.assigned_resource_id || "unassigned"} @ {t.gate_node}{" "}
                    {t.start_time != null && t.end_time != null
                      ? `(t=${t.start_time}→${t.end_time})`
                      : ""}
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

