"use client";

import type { Source } from "../types";

function formatDate(source: Source): string {
  // Try sitting_date first — if it looks valid (e.g., "2024-05-15")
  if (source.sitting_date && /^\d{4}-\d{2}-\d{2}$/.test(source.sitting_date)) {
    const d = new Date(source.sitting_date + "T00:00:00");
    if (!isNaN(d.getTime())) {
      return d.toLocaleDateString("en-AU", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    }
  }
  // Fallback: extract date from source_file (e.g., "2024-05-15.xml")
  if (source.source_file) {
    const match = source.source_file.match(/(\d{4}-\d{2}-\d{2})/);
    if (match) {
      const d = new Date(match[1] + "T00:00:00");
      if (!isNaN(d.getTime())) {
        return d.toLocaleDateString("en-AU", {
          day: "numeric",
          month: "short",
          year: "numeric",
        });
      }
    }
  }
  // Last resort: show raw sitting_date
  return source.sitting_date || "Unknown date";
}

export default function SourceCard({
  source,
  index,
}: {
  source: Source;
  index: number;
}) {
  const displayDate = formatDate(source);

  return (
    <div className="min-w-[200px] max-w-[240px] flex-shrink-0 border border-stone-200 rounded-xl p-3 bg-white hover:border-stone-300 transition-colors">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-teal-50 border border-teal-200 text-teal-700 text-[10px] font-bold flex-shrink-0">
          {index}
        </span>
        <span className="font-medium text-stone-900 text-xs truncate">
          {source.speakers || "Parliamentary Record"}
        </span>
      </div>
      <div className="text-[11px] text-stone-500 leading-snug">
        <span>{source.chamber}</span>
        <span className="mx-1">&middot;</span>
        <span>{displayDate}</span>
      </div>
    </div>
  );
}
