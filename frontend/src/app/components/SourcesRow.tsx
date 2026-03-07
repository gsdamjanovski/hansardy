"use client";

import SourceCard from "./SourceCard";

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

export default function SourcesRow({ sources }: { sources: Source[] }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="flex gap-2 overflow-x-auto pb-2 mb-4 scrollbar-hide">
      {sources.map((source, i) => (
        <SourceCard key={source.id} source={source} index={i + 1} />
      ))}
    </div>
  );
}
