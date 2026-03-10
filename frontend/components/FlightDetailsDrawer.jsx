"use client";

import React from "react";

const formatSimTime = (minutes) => {
  if (minutes === null || minutes === undefined) return "—";
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hrs.toString().padStart(2, "0")}:${mins
    .toString()
    .padStart(2, "0")}`;
};

const formatWallClock = (timestamp) => {
  if (!timestamp) return "—";
  const d = new Date(timestamp * 1000);
  return d.toLocaleTimeString();
};

export default function FlightDetailsDrawer({
  isOpen,
  onClose,
  details,
  loading,
  error,
}) {
  const flight = details?.flight;
  const schedule = details?.schedule;
  const events = details?.events || [];
  const delay = details?.delay;
  const breakdown = details?.delay_breakdown;

  return (
    <div
      className={`fixed inset-0 z-40 ${
        isOpen ? "pointer-events-auto" : "pointer-events-none"
      }`}
    >
      <div
        className={`absolute inset-0 bg-black transition-opacity ${
          isOpen ? "opacity-40" : "opacity-0"
        }`}
        onClick={onClose}
      />

      <div
        className={`absolute right-0 top-0 h-full w-full max-w-md bg-white shadow-2xl transform transition-transform duration-300 ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a2a2a] bg-[#1b1b1b]">
          <div>
            <h2 className="text-lg font-semibold text-[#f7c576]">
              Flight details
            </h2>
            {flight?.flight_id && (
              <p className="text-sm text-[#f7c576]/70">
                Flight ID:{" "}
                <span className="font-mono text-[#f7c576]">
                  {flight.flight_id}
                </span>
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-[#f7c576]/60 hover:text-[#f7c576] transition"
          >
            ✕
          </button>
        </div>

        <div className="h-full overflow-y-auto px-6 py-4 space-y-6 bg-[#141414] text-[#f7c576]">
          {loading && (
            <div className="flex justify-center items-center py-10">
              <div className="w-8 h-8 border-4 border-[#f7c576] border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {error && !loading && (
            <div className="bg-red-900/40 text-red-200 border border-red-500/60 px-4 py-3 rounded-xl text-sm">
              {error}
            </div>
          )}

          {!loading && !error && details && (
            <>
              {/* Basic info */}
              <section>
                <h3 className="text-sm font-semibold text-[#f7c576]/80 mb-2">
                  Basic information
                </h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-[#f7c576]/60">Status</p>
                    <p className="font-medium text-[#f7c576]">
                      {flight?.status ?? "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-[#f7c576]/60">Gate</p>
                    <p className="font-medium text-[#f7c576]">
                      {schedule?.gate ?? flight?.assigned_gate ?? "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-[#f7c576]/60">Runway</p>
                    <p className="font-medium text-[#f7c576]">
                      {schedule?.runway ?? flight?.assigned_runway ?? "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-[#f7c576]/60">Scheduled arrival</p>
                    <p className="font-medium text-[#f7c576]">
                      {delay?.scheduled_arrival !== undefined
                        ? formatSimTime(delay.scheduled_arrival)
                        : "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-[#f7c576]/60">Actual landing</p>
                    <p className="font-medium text-[#f7c576]">
                      {delay?.actual_landing !== undefined
                        ? formatSimTime(delay.actual_landing)
                        : "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-[#f7c576]/60">Total delay</p>
                    <p className="font-medium text-[#f7c576]">
                      {delay?.delay_minutes !== undefined
                        ? `${Math.max(delay.delay_minutes, 0)} min`
                        : "—"}
                    </p>
                  </div>
                </div>
              </section>

              {/* Delay breakdown */}
              {breakdown && (
                <section>
                  <h3 className="text-sm font-semibold text-[#f7c576]/80 mb-2">
                    Delay breakdown
                  </h3>
                  <div className="bg-[#1f1f1f] rounded-xl p-3 space-y-2 text-sm border border-[#2a2a2a]">
                    <div className="flex items-center justify-between">
                      <span className="text-[#f7c576]/70">Total delay</span>
                      <span className="font-semibold text-[#f7c576]">
                        {breakdown.total_delay_minutes} min
                      </span>
                    </div>
                    {Array.isArray(breakdown.segments) &&
                      breakdown.segments.map((seg, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between text-xs text-[#f7c576]/70"
                        >
                          <span>{seg.label}</span>
                          <span>{seg.delay_minutes} min</span>
                        </div>
                      ))}
                  </div>
                </section>
              )}

              {/* Timeline */}
              <section>
                <h3 className="text-sm font-semibold text-[#f7c576]/80 mb-2">
                  Event timeline
                </h3>
                {events.length === 0 ? (
                  <p className="text-xs text-[#f7c576]/60">
                    No events recorded yet for this flight.
                  </p>
                ) : (
                  <ol className="relative border-l border-[#2a2a2a] text-sm">
                    {events.map((ev, idx) => (
                      <li key={idx} className="mb-4 ml-4">
                        <div className="absolute w-2 h-2 bg-[#f7c576] rounded-full mt-1.5 -left-1 border border-[#141414]" />
                        <time className="mb-1 text-xs font-medium text-[#f7c576]/60">
                          {formatWallClock(ev.timestamp)}
                        </time>
                        <p className="text-[#f7c576] font-medium">
                          {ev.type}{" "}
                          {ev.phase && (
                            <span className="ml-1 inline-flex items-center rounded-full bg-[#232323] px-2 py-0.5 text-[10px] font-medium text-[#f7c576]/80">
                              {ev.phase}
                            </span>
                          )}
                        </p>
                        {ev.resource && (
                          <p className="text-xs text-[#f7c576]/60">
                            Resource: {ev.resource}
                          </p>
                        )}
                        {ev.action && (
                          <p className="text-xs text-[#f7c576]/70">
                            {ev.action}
                          </p>
                        )}
                      </li>
                    ))}
                  </ol>
                )}
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

