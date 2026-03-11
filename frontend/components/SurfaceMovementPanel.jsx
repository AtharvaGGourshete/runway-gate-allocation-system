"use client";

import { useEffect, useState } from "react";

export default function SurfaceMovementPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchSurface = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch("http://localhost:5000/api/surface-state?window=60", {
        cache: "no-store",
      });
      const json = await res.json();
      if (json.status !== "success") {
        setError(json.message || "Failed to load surface state.");
        return;
      }
      setData(json);
    } catch (e) {
      console.error("Surface state fetch error:", e);
      setError("Unable to reach backend for surface state.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSurface();
    const interval = setInterval(fetchSurface, 10000);
    return () => clearInterval(interval);
  }, []);

  const rows = (data?.surface_state || []).slice(0, 8);

  return (
    <div className="bg-[#1f1f1f] rounded-2xl shadow-sm border border-[#2a2a2a] p-4 h-[360px] flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-[#f7c576]">
          Surface Movement
        </h3>
        <button
          onClick={fetchSurface}
          className="text-xs font-semibold text-[#f7c576] hover:text-[#ffd28a]"
          disabled={loading}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && <div className="text-xs text-red-300">{error}</div>}

      {!error && (
        <div className="space-y-2 flex-1 overflow-y-auto pr-1">
          <div className="text-[11px] text-[#f7c576]/60">
            Sim time: {data?.simulation_time ?? "—"}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[#f7c576]/60">
                  <th className="text-left py-1 pr-2 font-medium">Flight</th>
                  <th className="text-left py-1 pr-2 font-medium">Mode</th>
                  <th className="text-left py-1 pr-2 font-medium">From</th>
                  <th className="text-left py-1 pr-2 font-medium">To</th>
                  <th className="text-left py-1 pr-2 font-medium">Hold</th>
                  <th className="text-left py-1 pr-2 font-medium">ETA</th>
                </tr>
              </thead>
              <tbody className="text-[#f7c576]">
                {rows.length === 0 && (
                  <tr>
                    <td className="py-2 text-[#f7c576]/60" colSpan={6}>
                      No active taxi plans yet.
                    </td>
                  </tr>
                )}
                {rows.map((r) => (
                  <tr
                    key={`${r.flight_id}-${r.mode}`}
                    className="border-t border-[#2a2a2a]"
                  >
                    <td className="py-1 pr-2 font-medium">{r.flight_id}</td>
                    <td className="py-1 pr-2 text-[#f7c576]/80">
                      {r.mode}
                    </td>
                    <td className="py-1 pr-2">{r.start_node}</td>
                    <td className="py-1 pr-2">{r.end_node}</td>
                    <td className="py-1 pr-2">{r.hold_minutes ?? 0}m</td>
                    <td className="py-1 pr-2">{r.end_time ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data?.surface_state?.length > rows.length && (
            <div className="text-[11px] text-[#f7c576]/60">
              Showing {rows.length} of {data.surface_state.length}.
            </div>
          )}
        </div>
      )}
    </div>
  );
}



