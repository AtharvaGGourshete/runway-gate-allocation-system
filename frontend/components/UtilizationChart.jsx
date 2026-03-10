"use client";

import React from "react";

export default function UtilizationChart({ title, data }) {
  if (!data || Object.keys(data).length === 0) {
    return null;
  }

  const entries = Object.entries(data);
  const maxValue = Math.max(...entries.map(([, value]) => value || 0));

  return (
    <div className="bg-[#1f1f1f] border border-[#2a2a2a] rounded-2xl p-4">
      <h3 className="text-sm font-semibold text-[#f7c576] mb-3">{title}</h3>
      <div className="space-y-3">
        {entries.map(([label, value]) => {
          const safeValue = value || 0;
          const percentage =
            maxValue > 0 ? Math.round((safeValue / maxValue) * 100) : 0;

          return (
            <div key={label}>
              <div className="flex items-center justify-between text-xs text-[#f7c576]/70 mb-1">
                <span className="truncate max-w-[60%]">{label}</span>
                <span className="font-medium text-[#f7c576]">
                  {safeValue}
                </span>
              </div>
              <div className="h-2 bg-[#2a2a2a] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${percentage}%` }}
                  // Gradient-like feel using arbitrary tailwind via inline style color
                  // while preserving theme tint.
                  // eslint-disable-next-line react/no-unknown-property
                  data-theme-bar
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

