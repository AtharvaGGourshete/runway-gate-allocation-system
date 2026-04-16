"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from "recharts";

const formatTime = (minutes) => {
  const safe = Number(minutes);
  if (!Number.isFinite(safe) || safe < 0) return "--:--";
  const hrs = Math.floor(safe / 60);
  const mins = safe % 60;
  return `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
};

const toEntries = (obj) =>
  Object.entries(obj || {}).sort((a, b) => Number(b[1] || 0) - Number(a[1] || 0));

const CHART_COLORS = ["#f7c576", "#ff9ea6", "#9bc3ff", "#8de7c4", "#e0d28f"];

export default function ReportsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [windowMinutes, setWindowMinutes] = useState(240);

  const fetchSummary = async () => {
    try {
      setError(null);
      const res = await fetch(`http://localhost:5000/api/reports/summary?window=${windowMinutes}`, {
        cache: "no-store",
      });
      const json = await res.json();
      if (!res.ok || json.status !== "success") {
        throw new Error(json.message || "Unable to load report summary");
      }
      setData(json);
    } catch (e) {
      setError(e.message || "Unable to load report summary");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    fetchSummary();
    const id = setInterval(fetchSummary, 12000);
    return () => clearInterval(id);
  }, [windowMinutes]);

  const summary = data?.summary || {};
  const kpis = summary.kpis || {};
  const sla = summary.delay_summary || {};
  const trends = summary.kpi_trends || [];
  const runwayRows = useMemo(() => toEntries(summary.runway_utilization), [summary]);
  const gateRows = useMemo(() => toEntries(summary.gate_utilization), [summary]);
  const runwayChartData = useMemo(
    () => runwayRows.map(([name, operations]) => ({ name, operations: Number(operations || 0) })),
    [runwayRows]
  );
  const gateChartData = useMemo(
    () => gateRows.slice(0, 12).map(([name, operations]) => ({ name, operations: Number(operations || 0) })),
    [gateRows]
  );
  const slaPieData = useMemo(
    () => [
      { name: "On-time (<=0m)", value: Number(sla.on_time_0_min || 0) },
      { name: "<=5m", value: Number(sla.within_5_min || 0) },
      { name: "<=15m", value: Number(sla.within_15_min || 0) },
      { name: ">15m", value: Number(sla.severe_over_15_min || 0) },
    ],
    [sla]
  );

  return (
    <div className="min-h-screen bg-[#141414] text-[#f7c576] px-2 md:px-3 lg:px-4 py-8">
      <div className="max-w-[1820px] mx-auto space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Reporting Module</h1>
            <p className="text-sm text-[#f7c576]/70 mt-1">
              Historical operations summary, utilization, and delay insights.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/dashboard" className="px-4 py-2 text-xs font-semibold rounded-xl border border-[#2a2a2a] bg-[#1f1f1f] hover:bg-[#252525]">
              Dashboard
            </Link>
          </div>
        </div>

        <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl p-4 flex items-center justify-between flex-wrap gap-3">
          <div className="text-sm text-[#f7c576]/80">
            Simulation Time: <span className="font-semibold text-[#f7c576]">{formatTime(data?.simulation_time)}</span>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-[#f7c576]/70">Window</span>
            <select
              value={windowMinutes}
              onChange={(e) => setWindowMinutes(Number(e.target.value))}
              className="rounded-lg bg-[#141414] border border-[#2a2a2a] px-2 py-1 text-xs"
            >
              <option value={120}>120 min</option>
              <option value={240}>240 min</option>
              <option value={360}>360 min</option>
            </select>
            <a
              href={`http://localhost:5000/api/reports/export/csv?kind=schedules&window=${windowMinutes}`}
              className="px-3 py-1 text-xs rounded-lg border border-[#2a2a2a] bg-[#141414] hover:bg-[#202020]"
            >
              Schedules CSV
            </a>
            <a
              href={`http://localhost:5000/api/reports/export/csv?kind=metrics&window=${windowMinutes}`}
              className="px-3 py-1 text-xs rounded-lg border border-[#2a2a2a] bg-[#141414] hover:bg-[#202020]"
            >
              Metrics CSV
            </a>
            <a
              href={`http://localhost:5000/api/reports/export/csv?kind=events&window=${windowMinutes}`}
              className="px-3 py-1 text-xs rounded-lg border border-[#2a2a2a] bg-[#141414] hover:bg-[#202020]"
            >
              Events CSV
            </a>
            <a
              href={`http://localhost:5000/api/reports/export/pdf?kind=summary&window=${windowMinutes}`}
              className="px-3 py-1 text-xs rounded-lg border border-[#2a2a2a] bg-[#141414] hover:bg-[#202020]"
            >
              Summary PDF
            </a>
          </div>
        </div>

        {loading && <div className="text-sm text-[#f7c576]/70">Loading report summary...</div>}
        {error && <div className="text-sm text-red-300">{error}</div>}

        {!loading && !error && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl p-4">
                <div className="text-[11px] uppercase tracking-widest text-[#f7c576]/70">Avg Delay</div>
                <div className="text-2xl font-bold mt-1">{Number(kpis.avg_delay || 0).toFixed(1)} min</div>
              </div>
              <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl p-4">
                <div className="text-[11px] uppercase tracking-widest text-[#f7c576]/70">Max Delay</div>
                <div className="text-2xl font-bold mt-1">{kpis.max_delay || 0} min</div>
              </div>
              <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl p-4">
                <div className="text-[11px] uppercase tracking-widest text-[#f7c576]/70">Throughput</div>
                <div className="text-2xl font-bold mt-1">{Number(kpis.flights_per_hour || 0).toFixed(1)} / hr</div>
              </div>
              <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl p-4">
                <div className="text-[11px] uppercase tracking-widest text-[#f7c576]/70">GSE Utilization</div>
                <div className="text-2xl font-bold mt-1">{summary.resource_snapshot?.utilization_pct || 0}%</div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl p-4">
                <div className="text-[11px] uppercase tracking-widest text-[#f7c576]/70">SLA On-time (0m)</div>
                <div className="text-2xl font-bold mt-1">{Number(sla.on_time_0_min || 0).toFixed(1)}%</div>
              </div>
              <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl p-4">
                <div className="text-[11px] uppercase tracking-widest text-[#f7c576]/70">SLA = 5m</div>
                <div className="text-2xl font-bold mt-1">{Number(sla.within_5_min || 0).toFixed(1)}%</div>
              </div>
              <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl p-4">
                <div className="text-[11px] uppercase tracking-widest text-[#f7c576]/70">SLA = 15m</div>
                <div className="text-2xl font-bold mt-1">{Number(sla.within_15_min || 0).toFixed(1)}%</div>
              </div>
              <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl p-4">
                <div className="text-[11px] uppercase tracking-widest text-[#f7c576]/70">Severe  15m</div>
                <div className="text-2xl font-bold mt-1">{Number(sla.severe_over_15_min || 0).toFixed(1)}%</div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl overflow-hidden">
                <div className="px-4 py-3 border-b border-[#2a2a2a] text-sm font-semibold">Throughput & Delay Trend</div>
                <div className="h-[340px] p-3">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trends}>
                      <CartesianGrid stroke="#2a2a2a" strokeDasharray="3 3" />
                      <XAxis dataKey="time" stroke="#f7c57699" tick={{ fill: "#f7c57699", fontSize: 11 }} />
                      <YAxis yAxisId="left" stroke="#f7c57699" tick={{ fill: "#f7c57699", fontSize: 11 }} />
                      <YAxis yAxisId="right" orientation="right" stroke="#ff9ea699" tick={{ fill: "#ff9ea699", fontSize: 11 }} />
                      <Tooltip contentStyle={{ background: "#1f1f1f", border: "1px solid #2a2a2a", color: "#f7c576" }} />
                      <Legend />
                      <Line yAxisId="left" type="monotone" dataKey="throughput_per_hour" name="Throughput /hr" stroke="#f7c576" strokeWidth={2} dot={false} />
                      <Line yAxisId="right" type="monotone" dataKey="avg_delay" name="Avg Delay (min)" stroke="#ff9ea6" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl overflow-hidden">
                <div className="px-4 py-3 border-b border-[#2a2a2a] text-sm font-semibold">SLA Distribution</div>
                <div className="h-[340px] p-3">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Tooltip contentStyle={{ background: "#1f1f1f", border: "1px solid #2a2a2a", color: "#f7c576" }} />
                      <Legend />
                      <Pie data={slaPieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={95} label>
                        {slaPieData.map((entry, idx) => (
                          <Cell key={`sla-${entry.name}`} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl overflow-hidden">
                <div className="px-4 py-3 border-b border-[#2a2a2a] text-sm font-semibold">Timeline (15-min buckets)</div>
                <div className="h-[320px] p-3">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={summary.timeline || []}>
                      <CartesianGrid stroke="#2a2a2a" strokeDasharray="3 3" />
                      <XAxis dataKey="time" stroke="#f7c57699" tick={{ fill: "#f7c57699", fontSize: 11 }} />
                      <YAxis stroke="#f7c57699" tick={{ fill: "#f7c57699", fontSize: 11 }} />
                      <Tooltip contentStyle={{ background: "#1f1f1f", border: "1px solid #2a2a2a", color: "#f7c576" }} />
                      <Legend />
                      <Bar dataKey="arrivals" fill="#f7c576" />
                      <Bar dataKey="departures" fill="#9bc3ff" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl overflow-hidden">
                <div className="px-4 py-3 border-b border-[#2a2a2a] text-sm font-semibold">Runway Utilization</div>
                <div className="h-[320px] p-3">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={runwayChartData}>
                      <CartesianGrid stroke="#2a2a2a" strokeDasharray="3 3" />
                      <XAxis dataKey="name" stroke="#f7c57699" tick={{ fill: "#f7c57699", fontSize: 11 }} />
                      <YAxis stroke="#f7c57699" tick={{ fill: "#f7c57699", fontSize: 11 }} />
                      <Tooltip contentStyle={{ background: "#1f1f1f", border: "1px solid #2a2a2a", color: "#f7c576" }} />
                      <Bar dataKey="operations" fill="#f7c576" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl overflow-hidden">
                <div className="px-4 py-3 border-b border-[#2a2a2a] text-sm font-semibold">Gate Utilization (Top 12)</div>
                <div className="h-[320px] p-3">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={gateChartData}>
                      <CartesianGrid stroke="#2a2a2a" strokeDasharray="3 3" />
                      <XAxis dataKey="name" stroke="#f7c57699" tick={{ fill: "#f7c57699", fontSize: 11 }} />
                      <YAxis stroke="#f7c57699" tick={{ fill: "#f7c57699", fontSize: 11 }} />
                      <Tooltip contentStyle={{ background: "#1f1f1f", border: "1px solid #2a2a2a", color: "#f7c576" }} />
                      <Bar dataKey="operations" fill="#9bc3ff" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl overflow-hidden">
              <div className="px-4 py-3 border-b border-[#2a2a2a] text-sm font-semibold">Top Delayed Flights</div>
              <div className="max-h-[300px] overflow-auto">
                <table className="w-full text-xs">
                  <thead className="bg-[#232323] text-[#f7c576]/75 uppercase">
                    <tr>
                      <th className="text-left px-3 py-2">Flight</th>
                      <th className="text-left px-3 py-2">Delay</th>
                      <th className="text-left px-3 py-2">Sched Arr</th>
                      <th className="text-left px-3 py-2">Landing</th>
                      <th className="text-left px-3 py-2">Runway</th>
                      <th className="text-left px-3 py-2">Gate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(summary.top_delays || []).map((row) => (
                      <tr key={`${row.flight_id}-${row.landing_time}`} className="border-t border-[#2a2a2a]">
                        <td className="px-3 py-2">{row.flight_id}</td>
                        <td className="px-3 py-2">{row.delay_minutes} min</td>
                        <td className="px-3 py-2">{formatTime(row.scheduled_arrival)}</td>
                        <td className="px-3 py-2">{formatTime(row.landing_time)}</td>
                        <td className="px-3 py-2">{row.runway}</td>
                        <td className="px-3 py-2">{row.gate}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
