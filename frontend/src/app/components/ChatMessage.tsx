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

export default function ChatMessage({
  role,
  content,
  sources,
}: {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
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

  return (
    <div className="w-full">
      {sources && sources.length > 0 && <SourcesRow sources={sources} />}
      <MarkdownRenderer content={content} />
    </div>
  );
}
