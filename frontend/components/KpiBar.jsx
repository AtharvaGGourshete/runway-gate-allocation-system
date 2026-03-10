"use client";

import React from "react";

const formatTime = (minutes) => {
  const h = Math.floor(minutes / 60) % 24;
  const m = minutes % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
};

export default function KpiBar({ simulationTime, kpis }) {
  if (!kpis) {
    return null;
  }

  const {
    active_flights,
    total_flights,
    avg_delay,
    max_delay,
    on_time_percentage,
    upcoming_arrivals,
    upcoming_departures,
    flights_per_hour,
  } = kpis;

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl px-4 py-3 flex flex-col justify-between">
        <div className="text-[11px] font-semibold text-[#f7c576]/70 uppercase tracking-widest">
          Simulation Time
        </div>
        <div className="text-2xl font-bold text-[#f7c576] mt-1">
          {formatTime(simulationTime)}
        </div>
        <div className="text-xs text-[#f7c576]/60 mt-1">
          Flights in system:{" "}
          <span className="font-semibold text-[#f7c576]">
            {active_flights ?? 0}
          </span>
        </div>
      </div>

      <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl px-4 py-3 flex flex-col justify-between">
        <div className="text-[11px] font-semibold text-[#f7c576]/70 uppercase tracking-widest">
          Delay & Punctuality
        </div>
        <div className="flex items-baseline gap-3 mt-1">
          <div>
            <div className="text-lg font-semibold text-[#f7c576]">
              {avg_delay?.toFixed ? avg_delay.toFixed(1) : avg_delay || 0}
            </div>
            <div className="text-xs text-[#f7c576]/60">Avg delay (min)</div>
          </div>
          <div>
            <div className="text-sm font-semibold text-[#f7c576]">
              {max_delay ?? 0}
            </div>
            <div className="text-xs text-[#f7c576]/60">Max delay</div>
          </div>
        </div>
        <div className="mt-2">
          <div className="flex items-center justify-between text-xs text-[#f7c576]/60">
            <span>On-time flights</span>
            <span className="font-semibold text-emerald-400">
              {on_time_percentage != null
                ? `${Math.round(on_time_percentage * 100)}%`
                : "—"}
            </span>
          </div>
          <div className="h-1.5 bg-[#2a2a2a] rounded-full overflow-hidden mt-1">
            <div
              className="h-full bg-emerald-400 rounded-full transition-all"
              style={{
                width: `${
                  on_time_percentage != null
                    ? Math.min(100, Math.max(0, on_time_percentage * 100))
                    : 0
                }%`,
              }}
            />
          </div>
        </div>
      </div>

      <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl px-4 py-3 flex flex-col justify-between">
        <div className="text-[11px] font-semibold text-[#f7c576]/70 uppercase tracking-widest">
          Throughput
        </div>
        <div className="text-lg font-semibold text-[#f7c576] mt-1">
          {flights_per_hour?.toFixed
            ? flights_per_hour.toFixed(1)
            : flights_per_hour || 0}{" "}
          / hr
        </div>
        <div className="text-xs text-[#f7c576]/60 mt-1">
          Total flights seen:{" "}
          <span className="font-semibold text-[#f7c576]">
            {total_flights ?? 0}
          </span>
        </div>
      </div>

      <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl px-4 py-3 flex flex-col justify-between">
        <div className="text-[11px] font-semibold text-[#f7c576]/70 uppercase tracking-widest">
          Upcoming Window
        </div>
        <div className="flex items-baseline gap-4 mt-1">
          <div>
            <div className="text-lg font-semibold text-[#f7c576]">
              {upcoming_arrivals ?? 0}
            </div>
            <div className="text-xs text-[#f7c576]/60">Arrivals</div>
          </div>
          <div>
            <div className="text-lg font-semibold text-[#f7c576]">
              {upcoming_departures ?? 0}
            </div>
            <div className="text-xs text-[#f7c576]/60">Departures</div>
          </div>
        </div>
        <div className="text-xs text-[#f7c576]/60 mt-1">
          Upcoming flights total:{" "}
          <span className="font-semibold">
            {(upcoming_arrivals ?? 0) + (upcoming_departures ?? 0)}
          </span>
        </div>
      </div>
    </div>
  );
}

