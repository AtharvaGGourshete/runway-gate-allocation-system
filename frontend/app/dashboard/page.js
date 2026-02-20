"use client";

import { useEffect, useState } from "react";
import ScheduleTable from "@/components/ScheduleTable";
import GanttTimeline from "@/components/GanttTimeline";
import dynamic from "next/dynamic";

const AirportLayout = dynamic(
  () => import("@/components/AirportLayout"),
  { ssr: false }
);

export default function DashboardPage() {
  const [schedule, setSchedule] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [simulationTime, setSimulationTime] = useState(0);

  function formatTime(minutes) {
  const h = Math.floor(minutes / 60) % 24;
  const m = minutes % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

useEffect(() => {
  const fetchSchedule = async () => {
    try {
      const res = await fetch(
        "http://localhost:5000/api/latest-schedule",
        { cache: "no-store" }
      );

      const data = await res.json();

      if (data.status === "success") {
        setSchedule(data.schedule);
        setSimulationTime(data.simulation_time);
      }
    } catch (err) {
      console.error("Fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  fetchSchedule(); // first load

  const interval = setInterval(fetchSchedule, 1000); // every 1 second

  return () => clearInterval(interval);

}, []);



  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 mb-8">
          Airport Operations Dashboard
        </h1>

        {loading && (
          <div className="flex justify-center items-center py-20">
            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        )}

        {error && (
          <div className="bg-red-100 text-red-700 p-4 rounded-xl">
            {error}
          </div>
        )}

        <div className="text-lg font-semibold mb-4">
          Simulation Time: {formatTime(simulationTime)}
        </div>

        {!loading && !error && (
          <>
            <ScheduleTable schedule={schedule} />
            <AirportLayout
                schedule={schedule}
                currentTime={simulationTime}
              />
            {/* <GanttTimeline
                schedule={schedule}
                currentTime={0}
              /> */}
          </>
        )}
      </div>
    </div>
  );
}
