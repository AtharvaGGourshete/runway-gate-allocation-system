import React from "react";
import { PlaneTakeoff, Github, Twitter, Linkedin, Mail } from "lucide-react";

const Footer = () => {
  return (
    <footer className="bg-[#0f0f0f] border-t border-white/5 pt-16 pb-8 px-10">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-16">
          {/* Brand Column */}
          <div className="col-span-1 md:col-span-1">
            <div className="flex items-center gap-2 text-2xl font-bold tracking-tighter text-white mb-6">
              <PlaneTakeoff className="text-[#f7c576]" />
              <span>
                Sky<span className="text-[#f7c576]">slot</span>
              </span>
            </div>
            <p className="text-gray-400 text-sm leading-relaxed mb-6">
              Next-generation airport coordination. Leveraging Multi-Agent
              Systems to bridge the gap between tarmac complexity and autonomous
              precision.
            </p>
            <div className="flex gap-4">
              <Github
                className="text-gray-500 hover:text-[#f7c576] cursor-pointer transition-colors"
                size={20}
              />
              <Twitter
                className="text-gray-500 hover:text-[#f7c576] cursor-pointer transition-colors"
                size={20}
              />
              <Linkedin
                className="text-gray-500 hover:text-[#f7c576] cursor-pointer transition-colors"
                size={20}
              />
            </div>
          </div>

          {/* Platform Links */}
          <div>
            <h4 className="text-white font-bold mb-6 uppercase tracking-widest text-xs">
              Platform
            </h4>
            <ul className="space-y-4 text-gray-400 text-sm">
              <li className="hover:text-[#f7c576] cursor-pointer transition-colors">
                Agent Simulation
              </li>
              <li className="hover:text-[#f7c576] cursor-pointer transition-colors">
                Runway Analytics
              </li>
              <li className="hover:text-[#f7c576] cursor-pointer transition-colors">
                Gate Allocation
              </li>
              <li className="hover:text-[#f7c576] cursor-pointer transition-colors">
                Conflict Logs
              </li>
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="text-white font-bold mb-6 uppercase tracking-widest text-xs">
              Resources
            </h4>
            <ul className="space-y-4 text-gray-400 text-sm">
              <li className="hover:text-[#f7c576] cursor-pointer transition-colors">
                Documentation
              </li>
              <li className="hover:text-[#f7c576] cursor-pointer transition-colors">
                MAS Research
              </li>
              <li className="hover:text-[#f7c576] cursor-pointer transition-colors">
                API Reference
              </li>
              <li className="hover:text-[#f7c576] cursor-pointer transition-colors">
                System Status
              </li>
            </ul>
          </div>

          {/* Newsletter / Contact */}
          <div>
            <h4 className="text-white font-bold mb-6 uppercase tracking-widest text-xs">
              Stay Synced
            </h4>
            <p className="text-gray-400 text-xs mb-4">
              Receive system updates and research notes.
            </p>
            <div className="relative">
              <input
                type="email"
                placeholder="ops@airport.com"
                className="w-full bg-[#1c1c1c] border border-white/10 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#f7c576]/50 transition-colors"
              />
              <button className="absolute right-2 top-1 text-[#f7c576] p-1 hover:bg-[#f7c576]/10 rounded-md transition-colors">
                <Mail size={18} />
              </button>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-white/5 flex flex-col md:row items-center justify-between gap-4">
          <div className="flex gap-6 text-[10px] font-mono text-gray-500 uppercase tracking-widest">
            <span>© 2026 Skyslot MAS</span>
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
