"use client";

import React from "react";

const MINUTES_IN_VIEW = 180; // 3 hour window
const PIXELS_PER_MINUTE = 4;

const getLeft = (time, startTime) =>
  (time - startTime) * PIXELS_PER_MINUTE;

const getWidth = (start, end) =>
  (end - start) * PIXELS_PER_MINUTE;

export default function GanttTimeline({ schedule, currentTime = 0 }) {
  if (!schedule || schedule.length === 0) {
    return (
      <div className="text-center py-10 text-gray-500">
        No scheduled flights available.
      </div>
    );
  }

  const gates = [...new Set(schedule.map(f => f.gate))];

  return (
    <div className="bg-white rounded-2xl shadow-lg p-6 overflow-x-auto">

      <h2 className="text-xl font-semibold mb-6">
        Gate Allocation Timeline
      </h2>

      <div
        className="relative border border-gray-200"
        style={{ width: MINUTES_IN_VIEW * PIXELS_PER_MINUTE }}
        >

        {/* 30-Minute Vertical Markers */}
        {Array.from({ length: Math.ceil(MINUTES_IN_VIEW / 30) }).map((_, i) => (
            <div
            key={i}
            className="absolute top-0 bottom-0 border-l border-gray-300"
            style={{ left: i * 30 * PIXELS_PER_MINUTE }}
            >
            <span className="absolute -top-6 text-xs text-gray-500">
                {i * 30}m
            </span>
            </div>
        ))}

        {/* Gate Rows */}
        {gates.map((gate, rowIndex) => (
            <div
            key={gate}
            className="relative border-b h-16"
            >
            <div className="absolute left-0 top-0 w-8 h-full flex items-center font-medium bg-white z-10">
                {gate}
            </div>

            {schedule
                .filter(f => f.gate === gate)
                .map((flight, i) => (
                <div
                    key={i}
                    className="absolute bg-blue-500 text-white text-xs rounded-md px-2 py-1 shadow-md"
                    style={{
                    left: getLeft(flight.gate_arrival, currentTime),
                    width: getWidth(
                        flight.gate_arrival,
                        flight.gate_departure
                    ),
                    top: 20,
                    }}
                >
                    {flight.flight_id}
                </div>
                ))}
            </div>
        ))}
        </div>

    </div>
  );
}
