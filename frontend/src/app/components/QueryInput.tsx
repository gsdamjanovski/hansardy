"use client";

import { useState, useRef, KeyboardEvent } from "react";

export default function QueryInput({
  onSubmit,
  disabled,
}: {
  onSubmit: (query: string) => void;
  disabled: boolean;
}) {
  const [query, setQuery] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    const trimmed = query.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setQuery("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 160) + "px";
    }
  };

  return (
    <div className="border border-stone-200 rounded-2xl bg-white flex items-end gap-2 p-3 shadow-sm focus-within:ring-2 focus-within:ring-teal-500/20 focus-within:border-stone-300 transition-all duration-200">
      <textarea
        ref={textareaRef}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        placeholder="Ask about Australian Parliament..."
        rows={1}
        disabled={disabled}
        className="flex-1 resize-none outline-none text-[15px] text-stone-900 placeholder:text-stone-400 bg-transparent leading-relaxed"
      />
      <button
        onClick={handleSubmit}
        disabled={disabled || !query.trim()}
        className="flex-shrink-0 w-8 h-8 rounded-full bg-teal-600 text-white flex items-center justify-center hover:bg-teal-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <line x1="12" y1="19" x2="12" y2="5" />
          <polyline points="5 12 12 5 19 12" />
        </svg>
      </button>
    </div>
  );
}
