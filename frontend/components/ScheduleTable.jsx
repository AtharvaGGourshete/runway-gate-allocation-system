"use client";

import React, { useMemo } from "react";

const formatTime = (minutes) => {
  const safe = Number(minutes);
  if (!Number.isFinite(safe)) return "--:--";
  const hrs = Math.floor(safe / 60);
  const mins = safe % 60;
  return `${hrs.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}`;
};

const landingRunwayLabel = (flight) => {
  const byName = String(flight?.landing_runway || flight?.runway || "").trim();
  if (byName) return byName;

  const idx = Number(flight?.landing_runway_index ?? flight?.runway_index);
  if (idx === 0) return "16/34";
  if (idx === 1) return "10/28";
  if (idx === 2) return "14/32";
  return "--";
};

const takeoffRunwayLabel = (flight) => {
  const byName = String(flight?.takeoff_runway || flight?.runway || "").trim();
  if (byName) return byName;

  const idx = Number(flight?.takeoff_runway_index ?? flight?.runway_index);
  if (idx === 0) return "16/34";
  if (idx === 1) return "10/28";
  if (idx === 2) return "14/32";
  return "--";
};

export default function ScheduleTable({ schedule, onFlightClick }) {
  const visibleRows = useMemo(() => {
    const rows = Array.isArray(schedule) ? [...schedule] : [];
    rows.sort((a, b) => {
      const aArr = Number(a?.landing_time);
      const bArr = Number(b?.landing_time);
      const safeA = Number.isFinite(aArr) ? aArr : Number.MAX_SAFE_INTEGER;
      const safeB = Number.isFinite(bArr) ? bArr : Number.MAX_SAFE_INTEGER;
      return safeA - safeB;
    });
    return rows.slice(0, 5);
  }, [schedule]);

  if (!visibleRows || visibleRows.length === 0) {
    return (
      <div className="text-center py-10 text-[#f7c576]/60 bg-[#1f1f1f] rounded-2xl border border-[#2a2a2a]">
        No scheduled flights available.
      </div>
    );
  }

  const handleRowClick = (flightId) => {
    if (onFlightClick) {
      onFlightClick(flightId);
    }
  };

  return (
    <div className="bg-[#1f1f1f] rounded-2xl border border-[#2a2a2a] shadow-sm h-[560px] flex flex-col overflow-hidden">
      <div className="px-6 py-4 border-b border-[#2a2a2a] bg-[#1b1b1b] text-[#f7c576] flex items-center justify-between">
        <h2 className="text-xl font-semibold">Optimized Flight Schedule</h2>
      </div>

      <div className="overflow-y-auto flex-1">
        <table className="w-full table-fixed text-xs text-left">
          <thead className="bg-[#232323] text-[#f7c576]/75 uppercase text-xs sticky top-0 z-10">
            <tr>
              <th className="px-3 py-2 whitespace-nowrap">Flight</th>
              <th className="px-3 py-2 whitespace-nowrap">Arrival</th>
              <th className="px-3 py-2 whitespace-nowrap">Land RWY</th>
              <th className="px-3 py-2 whitespace-nowrap">Tkof RWY</th>
              <th className="px-3 py-2 whitespace-nowrap">Gate</th>
              <th className="px-3 py-2 whitespace-nowrap">Gate Arr</th>
              <th className="px-3 py-2 whitespace-nowrap">Gate Dep</th>
              <th className="px-3 py-2 whitespace-nowrap">Takeoff</th>
            </tr>
          </thead>

          <tbody className="text-[#f7c576]">
            {visibleRows.map((flight, index) => (
              <tr
                key={`${flight.flight_id}-${index}`}
                className="border-b border-[#2a2a2a] hover:bg-[#242424] transition duration-200 cursor-pointer"
                onClick={() => handleRowClick(flight.flight_id)}
              >
                <td className="px-3 py-3 font-semibold truncate">{flight.flight_id}</td>
                <td className="px-3 py-3 text-[#f7c576]/85 whitespace-nowrap">{formatTime(flight.landing_time)}</td>

                <td className="px-3 py-3">
                  <span className="px-2 py-0.5 text-[11px] font-medium bg-[#3a272a] text-[#ff9ea6] rounded-full border border-[#5a363d] whitespace-nowrap">
                    {landingRunwayLabel(flight)}
                  </span>
                </td>

                <td className="px-3 py-3">
                  <span className="px-2 py-0.5 text-[11px] font-medium bg-[#1f3a29] text-[#97f7bd] rounded-full border border-[#2f5a3f] whitespace-nowrap">
                    {takeoffRunwayLabel(flight)}
                  </span>
                </td>

                <td className="px-3 py-3">
                  <span className="px-2 py-0.5 text-[11px] font-medium bg-[#263244] text-[#9bc3ff] rounded-full border border-[#334661] whitespace-nowrap">
                    {flight.gate}
                  </span>
                </td>

                <td className="px-3 py-3 text-[#f7c576]/85 whitespace-nowrap">{formatTime(flight.gate_arrival)}</td>
                <td className="px-3 py-3 text-[#f7c576]/85 whitespace-nowrap">{formatTime(flight.gate_departure)}</td>
                <td className="px-3 py-3 text-[#f7c576]/85 whitespace-nowrap">{formatTime(flight.takeoff_time)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}


