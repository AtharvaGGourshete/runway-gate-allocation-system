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
    upcoming_arrivals,
    upcoming_departures,
    flights_per_hour,
  } = kpis;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
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
