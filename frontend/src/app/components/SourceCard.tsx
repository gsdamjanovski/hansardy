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
    <div className="border border-gray-200 rounded-lg p-3 text-sm bg-white">
      <div className="flex items-center gap-2 mb-2">
        <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold flex-shrink-0">
          {index}
        </span>
        <span className="font-medium text-gray-900 truncate">
          {source.speakers}
        </span>
      </div>
      <div className="flex gap-2 text-xs text-gray-500 mb-2 flex-wrap">
        <span>{source.chamber}</span>
        <span>·</span>
        <span>{source.sitting_date}</span>
        <span>·</span>
        <span>Parliament {source.parliament_no}</span>
      </div>
      <p className="text-gray-700 text-xs leading-relaxed line-clamp-4">
        {source.text}
      </p>
    </div>
  );
}
