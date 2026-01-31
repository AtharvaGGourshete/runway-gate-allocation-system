import { BentoGrid, BentoGridItem } from "@/components/ui/bento-grid";
import {
  Airplay,
  BarChart3,
  Bot,
  CheckCircle2,
  Clock,
  Cpu,
  Network,
  PlaneLanding,
  PlaneTakeoff,
  ShieldAlert,
  Sparkle,
  SparkleIcon,
  Zap,
} from "lucide-react";
import { Montserrat, Poppins } from "next/font/google";
import Image from "next/image";

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"], // Add the weights you need
  variable: "--font-poppins",
});

const montserrat = Montserrat({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"], // Add the weights you need
  variable: "--font-poppins",
});

export default function Home() {
  const items = [
    {
      title: "Eliminating Human Bottlenecks",
      description:
        "Manual allocation relies on voice comms and radio relays. Our agents bypass verbal lag, negotiating runway slots in milliseconds.",
      icon: <Cpu className="text-[#f7c576]" size={24} />,
      className: "md:col-span-2",
    },
    {
      title: "Real-Time Re-Routing",
      description:
        "Manual systems struggle with sudden delays. Our MAS instantly recalculates every gate assignment the moment a flight plan shifts.",
      icon: <Zap className="text-[#f7c576]" size={24} />,
      className: "md:col-span-1",
    },
    {
      title: "Dynamic Gate Mapping",
      description:
        "Shift from static 'first-come' logic to intelligent mapping that minimizes taxi time based on current tarmac congestion.",
      icon: <Network className="text-[#f7c576]" size={24} />,
      className: "md:col-span-1",
    },
    {
      title: "Conflict De-escalation",
      description:
        "Autonomous agents resolve taxiway deadlocks before they happen, removing the mental load from stressed ground controllers.",
      icon: <ShieldAlert className="text-[#f7c576]" size={24} />,
      className: "md:col-span-2",
    },
    {
      title: "Data-Driven Throughput",
      description:
        "Increase airport capacity by 20% by filling 'micro-gaps' in runway schedules that manual controllers often miss.",
      icon: <BarChart3 className="text-[#f7c576]" size={24} />,
      className: "md:col-span-2",
    },
    {
      title: "Zero Manual Overhead",
      description:
        "Automate the repetitive logistics of gate shuffling, allowing ATC to focus solely on high-level safety and emergency management.",
      icon: <Clock className="text-[#f7c576]" size={24} />,
      className: "md:col-span-1",
    },
  ];
  return (
    <>
      <main className="relative h-screen w-full overflow-hidden">
        <Image
          src="/hero-img.png"
          alt="Airport allocation system background"
          fill
          priority
          className="object-cover object-center"
        />
        <section className={`${montserrat.className}`}>
          <div className="relative z-10 flex h-full flex-col">
            <nav className="flex items-center justify-between px-10 py-6 text-white sticky">
              <div className="text-2xl flex gap-2 items-center font-bold tracking-tighter">
                {/* <Image src={"/logo.png"} width={70} height={70} alt="logo"/> */}
                <PlaneTakeoff />
                <span className="text-[#FFDAB9]">Skyslot</span>
              </div>
              <ul className="flex gap-8 font-medium">
                <li className="cursor-pointer hover:text-[#FFDAB9] transition">
                  Home
                </li>
                <li className="cursor-pointer hover:text-[#FFDAB9] transition">
                  Simulation
                </li>
                <li className="cursor-pointer hover:text-[#FFDAB9] transition">
                  Analytics
                </li>
                <li className="cursor-pointer hover:text-[#FFDAB9] transition">
                  Documentation
                </li>
              </ul>
              <button className="bg-[#FFDAB9] text-black px-5 py-2 rounded-3xl transition">
                Launch
              </button>
            </nav>

            <div className="text-center">
              <h1 className="tracking-tighter">
                <span className="text-7xl block ">
                  <span className={`${montserrat.className}`}>
                    Ready to take over
                  </span>
                </span>{" "}
                <span className="text-7xl">
                  <span className={`${montserrat.className}`}>
                    {" "}
                    the{" "}
                    <span className="text-[#f7c576] font-bold">RUNWAYS?</span>
                  </span>
                </span>
              </h1>
              <p className="text-xl text-center font-semibold mt-96 px-60 leading-relaxed text-black">
                <span className="text-[#f7c576]">Aviation</span> is complex.
                Coordination should be{" "}
                <span className="text-[#f7c576]">Autonomous</span>. From tarmac
                to terminal, distributed agents negotiate every second to ensure
                the perfect gate is ready before touchdown.
              </p>
            </div>
          </div>
        </section>
      </main>

      <section
        className={`bg-[#141414] py-24 px-10 min-h-screen ${montserrat.className}`}
      >
        <div className="max-w-7xl mx-auto">
          <div className="mb-16">
            <h2 className="text-7xl font-bold text-white">
              How it <span className="text-[#FFDAB9]">works?</span>
            </h2>
            <p className={`${poppins.className} mt-4 text-xl text-gray-400`}>
              Three simple steps to autonomous coordination.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
            {/* Step 1 */}
            <div className="group relative bg-[#1c1c1c] p-8 rounded-2xl border border-white/5 hover:border-[#f7c576]/50 transition-all">
              <div className="bg-[#f7c576]/10 w-16 h-16 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <PlaneLanding className="text-[#f7c576]" size={32} />
              </div>
              <h3 className="text-2xl font-bold text-white mb-4">
                1. Flight Arrives
              </h3>
              <p
                className={`${poppins.className} text-gray-400 leading-relaxed`}
              >
                Incoming and outgoing flights enter the system as individual
                agents, carrying specific requirements for runways and ground
                time.
              </p>
            </div>

            {/* Step 2 */}
            <div className="group relative bg-[#1c1c1c] p-8 rounded-2xl border border-white/5 hover:border-[#f7c576]/50 transition-all">
              <div className="bg-[#f7c576]/10 w-16 h-16 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <Bot className="text-[#f7c576]" size={32} />
              </div>
              <h3 className="text-2xl font-bold text-white mb-4">
                2. Agents Negotiate
              </h3>
              <p
                className={`${poppins.className} text-gray-400 leading-relaxed`}
              >
                The AI Agent checks available runways and gate logistics,
                negotiating with other agents to find the most efficient slot.
              </p>
            </div>

            {/* Step 3 */}
            <div className="group relative bg-[#1c1c1c] p-8 rounded-2xl border border-white/5 hover:border-[#f7c576]/50 transition-all">
              <div className="bg-[#f7c576]/10 w-16 h-16 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <CheckCircle2 className="text-[#f7c576]" size={32} />
              </div>
              <h3 className="text-2xl font-bold text-white mb-4">
                3. Auto-Assignment
              </h3>
              <p
                className={`${poppins.className} text-gray-400 leading-relaxed`}
              >
                Assignments happen automatically in milliseconds. The system
                optimizes throughput and ensures zero gate conflicts.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-[#141414] py-20 px-10">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-7xl font-bold text-white mb-12 tracking-tighter">
            Why it <span className="text-[#FFDAB9]">matters?</span>
          </h2>

          {/* 2. The Bento Grid UI */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {items.map((item, i) => (
              <div
                key={i}
                className={`
                ${item.className}
                group relative overflow-hidden rounded-3xl border border-white/10 
                bg-[#1c1c1c] p-8 hover:border-[#f7c576]/40 transition-all duration-300
              `}
              >
                {/* Subtle Gradient Glow on Hover */}
                <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-[#f7c576]/5 blur-3xl group-hover:bg-[#f7c576]/10" />

                <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-white/5 border border-white/10 group-hover:border-[#f7c576]/20">
                  {item.icon}
                </div>

                <h3 className="text-xl font-bold text-white mb-2 tracking-tight">
                  {item.title}
                </h3>

                <p className="text-gray-400 text-sm leading-relaxed max-w-70">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
