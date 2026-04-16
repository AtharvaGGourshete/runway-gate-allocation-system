"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ScheduleTable from "@/components/ScheduleTable";
import dynamic from "next/dynamic";
import KpiBar from "@/components/KpiBar";
import FlightDetailsDrawer from "@/components/FlightDetailsDrawer";
import AiInsightsPanel from "@/components/AiInsightsPanel";
import SurfaceMovementPanel from "@/components/SurfaceMovementPanel";
import ResourceDispatchPanel from "@/components/ResourceDispatchPanel";

const AirportLayout = dynamic(() => import("@/components/AirportLayout"), {
  ssr: false,
});

export default function DashboardPage() {
  const [schedule, setSchedule] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [simulationTime, setSimulationTime] = useState(0);
  const [insights, setInsights] = useState(null);

  const [selectedFlightId, setSelectedFlightId] = useState(null);
  const [flightDetails, setFlightDetails] = useState(null);
  const [flightDetailsLoading, setFlightDetailsLoading] = useState(false);
  const [flightDetailsError, setFlightDetailsError] = useState(null);

  useEffect(() => {
    const fetchSchedule = async () => {
      try {
        const res = await fetch("http://localhost:5000/api/latest-schedule", {
          cache: "no-store",
        });

        const data = await res.json();

        if (data.status === "success") {
          setSchedule(data.schedule);
          setSimulationTime(data.simulation_time);
        }
      } catch (err) {
        console.error("Fetch error:", err);
        setError("Unable to load latest schedule.");
      } finally {
        setLoading(false);
      }
    };

    fetchSchedule();
    const interval = setInterval(fetchSchedule, 1000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchInsights = async () => {
      try {
        const res = await fetch("http://localhost:5000/api/dashboard-insights?window=120", {
          cache: "no-store",
        });

        const data = await res.json();

        if (data.status === "success") {
          setInsights(data);
        }
      } catch (err) {
        console.error("Insights fetch error:", err);
      }
    };

    fetchInsights();
    const interval = setInterval(fetchInsights, 5000);

    return () => clearInterval(interval);
  }, []);

  const handleFlightClick = async (flightId) => {
    setSelectedFlightId(flightId);
    setFlightDetails(null);
    setFlightDetailsError(null);
    setFlightDetailsLoading(true);

    try {
      const res = await fetch(
        `http://localhost:5000/api/flight/${encodeURIComponent(flightId)}/details`,
        { cache: "no-store" }
      );

      const data = await res.json();

      if (data.status === "success") {
        setFlightDetails(data.details);
      } else {
        setFlightDetailsError(data.message || "Unable to load flight details.");
      }
    } catch (err) {
      console.error("Flight details fetch error:", err);
      setFlightDetailsError("Unable to load flight details.");
    } finally {
      setFlightDetailsLoading(false);
    }
  };

  const handleCloseDrawer = () => {
    setSelectedFlightId(null);
    setFlightDetails(null);
    setFlightDetailsError(null);
    setFlightDetailsLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#141414] text-[#f7c576] px-2 md:px-3 lg:px-4 py-8">
      <div className="max-w-[1820px] mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Airport Operations Dashboard</h1>
            <p className="text-sm text-[#f7c576]/70 mt-1">
              Live schedule, surface movement, resources, and AI insights for LSZH.
            </p>
          </div>
          <div className="hidden md:flex items-center gap-2 text-xs">
            <Link
              href="/flights"
              className="px-3 py-1.5 rounded-lg border border-[#2a2a2a] bg-[#1f1f1f] text-[#f7c576] hover:bg-[#252525] transition"
            >
              Flights Center
            </Link>
            <Link
              href="/gse"
              className="px-3 py-1.5 rounded-lg border border-[#2a2a2a] bg-[#1f1f1f] text-[#f7c576] hover:bg-[#252525] transition"
            >
              GSE Center
            </Link>
            <Link
              href="/reports"
              className="px-3 py-1.5 rounded-lg border border-[#2a2a2a] bg-[#1f1f1f] text-[#f7c576] hover:bg-[#252525] transition"
            >
              Reports
            </Link>
            <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="uppercase tracking-widest font-semibold text-[#f7c576]/70">
              Simulation Live
            </span>
          </div>
        </div>

        {loading && (
          <div className="flex justify-center items-center py-20">
            <div className="w-12 h-12 border-4 border-[#f7c576] border-t-transparent rounded-full animate-spin"></div>
          </div>
        )}

        {error && (
          <div className="bg-red-900/40 text-red-200 border border-red-500/60 p-4 rounded-2xl">
            {error}
          </div>
        )}

        {!loading && !error && (
          <div className="space-y-5">
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
              <div className="lg:col-span-3 space-y-4">
                {insights && <KpiBar simulationTime={simulationTime} kpis={insights.kpis} />}
                <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
                  <div className="md:col-span-2">
                    <SurfaceMovementPanel />
                  </div>
                  <div className="md:col-span-3">
                    <ResourceDispatchPanel />
                  </div>
                </div>
              </div>
              <div className="lg:col-span-1">
                <AiInsightsPanel compact />
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
              <div className="lg:col-span-2">
                <ScheduleTable schedule={schedule} onFlightClick={handleFlightClick} />
              </div>
              <div className="lg:col-span-3">
                <AirportLayout schedule={schedule} currentTime={simulationTime} />
              </div>
            </div>
          </div>
        )}
      </div>

      <FlightDetailsDrawer
        isOpen={!!selectedFlightId}
        onClose={handleCloseDrawer}
        details={flightDetails}
        loading={flightDetailsLoading}
        error={flightDetailsError}
      />
    </div>
  );
}






