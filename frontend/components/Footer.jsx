import React from "react";
import { PlaneTakeoff, Github, Twitter, Linkedin, Mail } from "lucide-react";

const Footer = () => {
  return (
    <footer className="bg-[#0f0f0f] border-t border-white/5 pt-16 pb-8 px-10">
      <div className="max-w-7xl mx-auto">
        <div className="mb-16">
          {/* Brand Column */}
          <div className="col-span-1 md:col-span-1">
            <div className="flex items-center justify-center gap-2 text-2xl font-bold tracking-tighter text-white mb-6">
              <PlaneTakeoff className="text-[#f7c576]" />
              <span>
                Sky<span className="text-[#f7c576]">slot</span>
              </span>
            </div>
            <p className="text-gray-400 text-sm leading-relaxed mb-6 text-center">
              Next-generation airport coordination. Leveraging Multi-Agent
              Systems to bridge the gap between tarmac complexity and autonomous
              precision.
            </p>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-white/5 flex flex-col md:row items-center justify-between gap-4">
          <div className="flex gap-6 text-[10px] font-mono text-gray-500 uppercase tracking-widest">
            <span>© 2026 Skyslot</span>
          </div>
          <div className="text-[10px] text-gray-600">
            Designed for Autonomous Aviation Excellence
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
