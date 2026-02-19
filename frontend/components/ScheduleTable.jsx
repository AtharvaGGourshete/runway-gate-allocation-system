"use client";

import React from "react";

const formatTime = (minutes) => {
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hrs.toString().padStart(2, "0")}:${mins
    .toString()
    .padStart(2, "0")}`;
};

export default function ScheduleTable({ schedule }) {
  if (!schedule || schedule.length === 0) {
    return (
      <div className="text-center py-10 text-gray-500">
        No scheduled flights available.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
      <div className="px-6 py-4 border-b bg-gray-900 text-white">
        <h2 className="text-xl font-semibold">Optimized Flight Schedule</h2>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm text-left">
          <thead className="bg-gray-100 text-gray-700 uppercase text-xs">
            <tr>
              <th className="px-6 py-3">Flight</th>
              <th className="px-6 py-3">Landing</th>
              <th className="px-6 py-3">Gate</th>
              <th className="px-6 py-3">Gate Arrival</th>
              <th className="px-6 py-3">Gate Departure</th>
              <th className="px-6 py-3">Takeoff</th>
            </tr>
          </thead>

          <tbody>
            {schedule.map((flight, index) => (
              <tr
                key={index}
                className="border-b hover:bg-gray-50 transition duration-200"
              >
                <td className="px-6 py-4 font-semibold text-gray-800">
                  {flight.flight_id}
                </td>

                <td className="px-6 py-4">
                  {formatTime(flight.landing_time)}
                </td>

                <td className="px-6 py-4">
                  <span className="px-3 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
                    {flight.gate}
                  </span>
                </td>

                <td className="px-6 py-4">
                  {formatTime(flight.gate_arrival)}
                </td>

                <td className="px-6 py-4">
                  {formatTime(flight.gate_departure)}
                </td>

                <td className="px-6 py-4">
                  {formatTime(flight.takeoff_time)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
