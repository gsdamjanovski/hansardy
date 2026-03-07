"use client";

interface Source {
  id: string;
  text: string;
  chamber: string;
  sitting_date: string;
  speakers: string;
  parliament_no: number;
  source_file: string;
  score: number;
}

export default function SourceCard({
  source,
  index,
}: {
  source: Source;
  index: number;
}) {
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
        <span>{source.sitting_date}</span>
      </div>
    </div>
  );
}
