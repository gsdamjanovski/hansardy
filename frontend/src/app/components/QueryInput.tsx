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
    <div className="border border-gray-300 rounded-2xl bg-white flex items-end gap-2 p-3 shadow-sm">
      <textarea
        ref={textareaRef}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        placeholder="Ask about Australian Hansard..."
        rows={1}
        disabled={disabled}
        className="flex-1 resize-none outline-none text-sm text-gray-900 placeholder:text-gray-400 bg-transparent leading-relaxed"
      />
      <button
        onClick={handleSubmit}
        disabled={disabled || !query.trim()}
        className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
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
          <line x1="22" y1="2" x2="11" y2="13" />
          <polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
      </button>
    </div>
  );
}
