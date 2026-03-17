"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import FlightDetailsDrawer from "@/components/FlightDetailsDrawer";

const formatTime = (minutes) => {
  const safe = Number(minutes);
  if (!Number.isFinite(safe)) return "--:--";
  const hrs = Math.floor(safe / 60);
  const mins = safe % 60;
  return `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
};

const formatOperationalTime = (minutes) => {
  const safe = Number(minutes);
  if (!Number.isFinite(safe) || safe <= 0) return "--:--";
  const hrs = Math.floor(safe / 60);
  const mins = safe % 60;
  return `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
};

const PRIORITY_OPTIONS = [
  { value: "normal", label: "Normal" },
  { value: "vip", label: "VIP" },
  { value: "international_connection", label: "Intl Conn" },
  { value: "emergency", label: "Emergency" },
];

export default function FlightsControlCenterPage() {
  const [flights, setFlights] = useState([]);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const hasLoadedOnceRef = useRef(false);

  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [total, setTotal] = useState(0);
  const [simulationTime, setSimulationTime] = useState(0);

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [priority, setPriority] = useState("all");
  const [sortBy, setSortBy] = useState("scheduled_arrival");
  const [order, setOrder] = useState("asc");

  const [selectedFlightId, setSelectedFlightId] = useState(null);
  const [flightDetails, setFlightDetails] = useState(null);
  const [flightDetailsLoading, setFlightDetailsLoading] = useState(false);
  const [flightDetailsError, setFlightDetailsError] = useState(null);

  const [updatingPriorityId, setUpdatingPriorityId] = useState(null);

  useEffect(() => {
    setPage(1);
  }, [search, status, priority, sortBy, order, limit]);

  useEffect(() => {
    let canceled = false;

    const fetchFlights = async (background = false) => {
      try {
        if (!canceled && hasLoadedOnceRef.current && background) {
          setIsRefreshing(true);
        } else if (!canceled && !hasLoadedOnceRef.current) {
          setIsInitialLoading(true);
          setError(null);
        }

        const params = new URLSearchParams({
          page: String(page),
          limit: String(limit),
          status,
          priority,
          sort: sortBy,
          order,
        });

        if (search.trim()) {
          params.set("q", search.trim());
        }

        const res = await fetch(`http://localhost:5000/api/flights?${params.toString()}`, {
          cache: "no-store",
        });

        const data = await res.json();
        if (!res.ok || data.status !== "success") {
          throw new Error(data.message || "Unable to load flights");
        }

        if (canceled) return;
        setFlights(Array.isArray(data.flights) ? data.flights : []);
        setTotal(Number(data.total || 0));
        setSimulationTime(Number(data.simulation_time || 0));
        setError(null);
        hasLoadedOnceRef.current = true;
      } catch (err) {
        if (canceled) return;
        if (!hasLoadedOnceRef.current) {
          setError(err.message || "Unable to load flights.");
        }
      } finally {
        if (!canceled) {
          setIsInitialLoading(false);
          setIsRefreshing(false);
        }
      }
    };

    fetchFlights(false);
    const interval = setInterval(() => {
      if (typeof document !== "undefined" && document.visibilityState !== "visible") {
        return;
      }
      fetchFlights(true);
    }, 8000);

    return () => {
      canceled = true;
      clearInterval(interval);
    };
  }, [page, limit, search, status, priority, sortBy, order]);

  const pageCount = Math.max(1, Math.ceil(total / Math.max(1, limit)));

  const statusCountsOnPage = useMemo(() => {
    const summary = { arriving: 0, departed: 0, other: 0 };
    for (const f of flights) {
      const s = String(f?.status || "").toLowerCase();
      if (s === "arriving") summary.arriving += 1;
      else if (s === "departed") summary.departed += 1;
      else summary.other += 1;
    }
    return summary;
  }, [flights]);

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

  const updatePriority = async (flightId, nextPriority) => {
    setUpdatingPriorityId(flightId);
    try {
      const res = await fetch(
        `http://localhost:5000/api/flights/${encodeURIComponent(flightId)}/priority`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ priority: nextPriority }),
        }
      );
      const data = await res.json();
      if (!res.ok || data.status !== "success") {
        throw new Error(data.message || "Priority update failed");
      }

      setFlights((prev) =>
        prev.map((f) => (f.flight_id === flightId ? { ...f, priority: nextPriority } : f))
      );
    } catch (err) {
      setError(err.message || "Unable to update priority.");
    } finally {
      setUpdatingPriorityId(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#141414] text-[#f7c576] px-2 md:px-3 lg:px-4 py-8">
      <div className="max-w-[1820px] mx-auto space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Flights Control Center</h1>
            <p className="text-sm text-[#f7c576]/70 mt-1">
              Full flight operations view with live filters, priority controls, and deep timelines.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/dashboard"
              className="px-4 py-2 text-xs font-semibold rounded-xl border border-[#2a2a2a] bg-[#1f1f1f] hover:bg-[#252525]"
            >
              Back to Dashboard
            </Link>
            <Link
              href="/gse"
              className="px-4 py-2 text-xs font-semibold rounded-xl border border-[#2a2a2a] bg-[#1f1f1f] hover:bg-[#252525]"
            >
              GSE Center
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl px-4 py-3">
            <div className="text-[11px] uppercase tracking-widest text-[#f7c576]/70 font-semibold">Simulation Time</div>
            <div className="text-2xl font-bold mt-1">{formatTime(simulationTime)}</div>
          </div>
          <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl px-4 py-3">
            <div className="text-[11px] uppercase tracking-widest text-[#f7c576]/70 font-semibold">Total Matching Flights</div>
            <div className="text-2xl font-bold mt-1">{total}</div>
          </div>
          <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl px-4 py-3">
            <div className="text-[11px] uppercase tracking-widest text-[#f7c576]/70 font-semibold">On This Page</div>
            <div className="text-sm mt-1 text-[#f7c576]/85">
              Arriving: <span className="font-semibold">{statusCountsOnPage.arriving}</span> | Departed:{" "}
              <span className="font-semibold">{statusCountsOnPage.departed}</span>
            </div>
          </div>
          <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl px-4 py-3">
            <div className="text-[11px] uppercase tracking-widest text-[#f7c576]/70 font-semibold">Page</div>
            <div className="text-2xl font-bold mt-1">{page} / {pageCount}</div>
          </div>
        </div>

        <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl p-4 grid grid-cols-1 md:grid-cols-6 gap-3">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search flight, gate, runway, aircraft..."
            className="md:col-span-2 rounded-xl bg-[#141414] border border-[#2a2a2a] px-3 py-2 text-sm text-[#f7c576] placeholder:text-[#f7c576]/40 focus:outline-none"
          />

          {/* <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded-xl bg-[#141414] border border-[#2a2a2a] px-3 py-2 text-sm"
          >
            <option value="all">All status</option>
            <option value="arriving">Arriving</option>
            <option value="landing">Landing</option>
            <option value="taxiing">Taxiing</option>
            <option value="departed">Departed</option>
          </select>

          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="rounded-xl bg-[#141414] border border-[#2a2a2a] px-3 py-2 text-sm"
          >
            <option value="all">All priority</option>
            {PRIORITY_OPTIONS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select> */}

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="rounded-xl bg-[#141414] border border-[#2a2a2a] px-3 py-2 text-sm"
          >
            <option value="scheduled_arrival">Sort: Scheduled arrival</option>
            <option value="landing_time">Sort: Landing time</option>
            <option value="takeoff_time">Sort: Takeoff time</option>
            <option value="delay_minutes">Sort: Delay</option>
            <option value="flight_id">Sort: Flight ID</option>
          </select>

          <div className="flex gap-2">
            <select
              value={order}
              onChange={(e) => setOrder(e.target.value)}
              className="flex-1 rounded-xl bg-[#141414] border border-[#2a2a2a] px-3 py-2 text-sm"
            >
              <option value="asc">Asc</option>
              <option value="desc">Desc</option>
            </select>
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="flex-1 rounded-xl bg-[#141414] border border-[#2a2a2a] px-3 py-2 text-sm"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={30}>30</option>
              <option value={50}>50</option>
            </select>
          </div>
        </div>

        <div className="bg-[#1f1f1f] rounded-2xl border border-[#2a2a2a] overflow-hidden">
          <div className="px-4 py-3 border-b border-[#2a2a2a] bg-[#1b1b1b] text-sm font-semibold">
            Live flights
          </div>

          <div className="px-4 py-2 border-b border-[#2a2a2a] bg-[#1b1b1b] text-[11px] text-[#f7c576]/65">
            {isRefreshing ? "Refreshing in background..." : "Auto-refresh every 8s"}
          </div>

          {isInitialLoading && (
            <div className="px-4 py-6 text-sm text-[#f7c576]/70">Loading flights...</div>
          )}
          {error && !isInitialLoading && flights.length === 0 && (
            <div className="px-4 py-6 text-sm text-red-300">{error}</div>
          )}
          {error && !isInitialLoading && flights.length > 0 && (
            <div className="px-4 py-2 text-xs text-red-300 border-b border-[#2a2a2a]">
              Latest refresh failed; showing last successful data.
            </div>
          )}

          {!isInitialLoading && (
            <div className="overflow-auto">
              <table className="w-full text-xs md:text-sm">
                <thead className="bg-[#232323] text-[#f7c576]/75 uppercase">
                  <tr>
                    <th className="text-left px-3 py-2">Flight</th>
                    <th className="text-left px-3 py-2">Status</th>
                    {/* <th className="text-left px-3 py-2">Priority</th> */}
                    <th className="text-left px-3 py-2">Sched Arr</th>
                    <th className="text-left px-3 py-2">Landing</th>
                    <th className="text-left px-3 py-2">Runway</th>
                    <th className="text-left px-3 py-2">Gate</th>
                    <th className="text-left px-3 py-2">Delay</th>
                    <th className="text-left px-3 py-2">Takeoff</th>
                  </tr>
                </thead>
                <tbody className="text-[#f7c576]">
                  {flights.length === 0 && (
                    <tr>
                      <td className="px-3 py-4 text-[#f7c576]/60" colSpan={9}>
                        No flights match the selected filters.
                      </td>
                    </tr>
                  )}
                  {flights.map((f) => (
                    <tr
                      key={f.flight_id}
                      className="border-t border-[#2a2a2a] hover:bg-[#242424] cursor-pointer"
                      onClick={() => handleFlightClick(f.flight_id)}
                    >
                      <td className="px-3 py-3 font-semibold">{f.flight_id}</td>
                      <td className="px-3 py-3 text-[#f7c576]/85">{f.status || "--"}</td>
                      {/* <td className="px-3 py-3">
                        <select
                          value={f.priority || "normal"}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) => {
                            e.stopPropagation();
                            updatePriority(f.flight_id, e.target.value);
                          }}
                          disabled={updatingPriorityId === f.flight_id}
                          className="rounded-lg bg-[#141414] border border-[#2a2a2a] px-2 py-1 text-xs"
                        >
                          {PRIORITY_OPTIONS.map((p) => (
                            <option key={p.value} value={p.value}>{p.label}</option>
                          ))}
                        </select>
                      </td> */}
                      <td className="px-3 py-3 text-[#f7c576]/85">{formatTime(f.scheduled_arrival)}</td>
                      <td className="px-3 py-3 text-[#f7c576]/85">{formatOperationalTime(f.landing_time)}</td>
                      <td className="px-3 py-3">{f.runway || "--"}</td>
                      <td className="px-3 py-3">{f.gate || "--"}</td>
                      <td className="px-3 py-3 text-[#f7c576]/85">
                        {f.delay_minutes == null ? "--" : `${Math.max(0, Number(f.delay_minutes))}m`}
                      </td>
                      <td className="px-3 py-3 text-[#f7c576]/85">{formatOperationalTime(f.takeoff_time)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="px-4 py-3 border-t border-[#2a2a2a] bg-[#1b1b1b] flex items-center justify-between text-xs">
            <div className="text-[#f7c576]/70">Showing {flights.length} of {total} flights</div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="px-3 py-1 rounded-lg border border-[#2a2a2a] bg-[#141414] disabled:opacity-40"
              >
                Prev
              </button>
              <button
                onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
                disabled={page >= pageCount}
                className="px-3 py-1 rounded-lg border border-[#2a2a2a] bg-[#141414] disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </div>
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

