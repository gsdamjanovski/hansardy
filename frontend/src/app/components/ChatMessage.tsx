"use client";

import MarkdownRenderer from "./MarkdownRenderer";
import SourcesRow from "./SourcesRow";

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

const QUERY_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  FACTUAL_LOOKUP: { label: "Factual", color: "bg-blue-50 text-blue-700 border-blue-200" },
  TEMPORAL: { label: "Temporal", color: "bg-amber-50 text-amber-700 border-amber-200" },
  THEMATIC: { label: "Thematic", color: "bg-purple-50 text-purple-700 border-purple-200" },
  COMPARISON: { label: "Comparison", color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  SPEAKER_PROFILE: { label: "Speaker", color: "bg-rose-50 text-rose-700 border-rose-200" },
  EXPLORATORY: { label: "Exploratory", color: "bg-stone-50 text-stone-600 border-stone-200" },
};

export default function ChatMessage({
  role,
  content,
  sources,
  queryType,
}: {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  queryType?: string;
}) {
  const isUser = role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed bg-stone-100 text-stone-900">
          {content}
        </div>
      </div>
    );
  }

  const typeInfo = queryType ? QUERY_TYPE_LABELS[queryType] : null;

  return (
    <div className="w-full">
      {typeInfo && (
        <div className="mb-2">
          <span
            className={`inline-block text-[11px] font-medium px-2 py-0.5 rounded-full border ${typeInfo.color}`}
          >
            {typeInfo.label}
          </span>
        </div>
      )}
      {sources && sources.length > 0 && <SourcesRow sources={sources} />}
      <MarkdownRenderer content={content} />
    </div>
  );
}
