"use client"

import { Montserrat } from "next/font/google";
import React, { useEffect, useState } from "react";
import { Activity, Plane, Box, Navigation, Clock } from "lucide-react";

const montserrat = Montserrat({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-montserrat",
});

const Page = () => {
  const [flights, setFlights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState("");

  useEffect(() => {
    const fetchFlights = async () => {
      try {
        const res = await fetch("http://localhost:5000/api/dashboard");
        const data = await res.json();
        
        // REVERSE THE DATA HERE: Latest flight at index 0
        setFlights([...data].reverse());
        
        setLastUpdated(new Date().toLocaleTimeString());
        setLoading(false);
      } catch (error) {
        console.error("Data stream error:", error);
        setLoading(false);
      }
    };

    fetchFlights();
    const interval = setInterval(fetchFlights, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main className={`min-h-screen bg-[#141414] text-white ${montserrat.className}`}>
      <div className="p-10">
        {/* Stats Grid */}
        <div className="flex gap-5 w-full mb-10">
          <div className="bg-[#1c1c1c] p-6 rounded-2xl border border-white/5 hover:border-[#f7c576]/50 transition-all w-full">
            <p className="text-[#f7c576] font-bold text-xs uppercase tracking-widest mb-1">Average Delay</p>
            <p className="text-2xl font-mono">02:14 <span className="text-xs text-gray-500">m/s</span></p>
          </div>
          <div className="bg-[#1c1c1c] p-6 rounded-2xl border border-white/5 hover:border-[#f7c576]/50 transition-all w-full">
            <p className="text-[#f7c576] font-bold text-xs uppercase tracking-widest mb-1">Total Agents</p>
            <p className="text-2xl font-mono">{flights.length}</p>
          </div>
          <div className="bg-[#1c1c1c] p-6 rounded-2xl border border-white/5 hover:border-[#f7c576]/50 transition-all w-full">
            <p className="text-[#f7c576] font-bold text-xs uppercase tracking-widest mb-1">Conflicts Resolved</p>
            <p className="text-2xl font-mono text-green-400">24</p>
          </div>
          <div className="bg-[#1c1c1c] p-6 rounded-2xl border border-white/5 hover:border-[#f7c576]/50 transition-all w-full">
            <p className="text-[#f7c576] font-bold text-xs uppercase tracking-widest mb-1">Gate Utilization</p>
            <p className="text-2xl font-mono">88%</p>
          </div>
        </div>

        {/* Full Tabular Flight Log */}
        <div className="bg-[#1c1c1c] rounded-2xl border border-white/10 overflow-hidden shadow-2xl flex flex-col max-h-[70vh]">
          <div className="p-5 border-b border-white/5 bg-white/2 flex justify-between items-center sticky top-0 z-10 backdrop-blur-md">
            <div>
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Activity className="text-[#f7c576]" size={20} />
                Full System Allocation Logs
              </h2>
              <p className="text-[10px] text-gray-500 font-mono mt-1 flex items-center gap-1">
                <Clock size={10} /> LAST UPDATE: {lastUpdated || "SYNCHRONIZING..."}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">
                Active Flights: {flights.length}
              </span>
              <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
            </div>
          </div>

          <div className="overflow-y-auto">
            <table className="w-full text-left border-collapse">
              <thead className="sticky top-0 bg-[#1c1c1c] z-10 shadow-sm">
                <tr className="border-b border-white/5 text-[11px] font-mono text-gray-500 uppercase tracking-[0.2em]">
                  <th className="p-5 font-medium">Flight ID</th>
                  <th className="p-5 font-medium">Status</th>
                  <th className="p-5 font-medium">Assigned Gate</th>
                  <th className="p-5 font-medium text-right">Runway Vector</th>
                </tr>
              </thead>
              <tbody className="font-mono text-sm">
                {flights.length > 0 ? (
                  flights.map((f) => (
                    <tr key={f.flight_id} className="border-b border-white/5 hover:bg-white/3 transition-colors group">
                      <td className="p-5">
                        <div className="flex items-center gap-3">
                          <Plane size={14} className="text-[#f7c576] opacity-50" />
                          <span className="font-bold tracking-widest text-white">{f.flight_id}</span>
                        </div>
                      </td>
                      <td className="p-5">
                        <span className={`px-3 py-1 rounded-full text-[10px] font-bold border uppercase ${
                          f.status === 'Allocated' || f.status === 'Active'
                          ? 'bg-green-500/10 text-green-400 border-green-500/20' 
                          : 'bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse'
                        }`}>
                          {f.status}
                        </span>
                      </td>
                      <td className="p-5">
                        <div className="flex items-center gap-2 text-gray-300">
                          <Box size={14} className="text-gray-600" />
                          {f.assigned_gate || "PENDING"}
                        </div>
                      </td>
                      <td className="p-5 text-right">
                        <div className="flex items-center justify-end gap-2 text-gray-400 italic">
                          {f.assigned_runway || "N/A"}
                          <Navigation size={14} className="text-gray-700" />
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="p-20 text-center text-gray-600 animate-pulse">
                      {loading ? "REVERSING DATA STREAM..." : "NO ACTIVE FLIGHTS DETECTED"}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          
          <div className="p-3 bg-black/20 text-center border-t border-white/5">
             <span className="text-[10px] text-gray-600 uppercase tracking-widest">
               MAS Engine: Chronological Feed (Newest First)
             </span>
          </div>
        </div>
      </div>
    </main>
  );
};

export default Page;