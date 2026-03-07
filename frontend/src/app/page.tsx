"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ChatMessage from "./components/ChatMessage";
import QueryInput from "./components/QueryInput";

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

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const EXAMPLE_QUERIES = [
  "What did the Treasurer say about inflation in 2024?",
  "Has the Senate debated nuclear energy recently?",
  "What happened in Question Time on the last sitting day?",
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSubmit = async (query: string) => {
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setIsStreaming(true);

    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", sources: [] },
    ]);

    try {
      const res = await fetch(`${API_BASE}/api/ask/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      if (!res.ok) throw new Error(`API error: ${res.status}`);

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";
      let streamedText = "";
      let sources: Source[] = [];
      let currentEvent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const rawLine of lines) {
          const line = rawLine.replace(/\r$/, "");
          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            const data = line.startsWith("data: ")
              ? line.slice(6)
              : line.slice(5);

            if (currentEvent === "sources") {
              try {
                sources = JSON.parse(data);
              } catch {
                // ignore parse errors
              }
            } else if (currentEvent === "token") {
              streamedText += data;
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant") {
                  last.content = streamedText;
                  last.sources = sources;
                }
                return [...updated];
              });
            }
            currentEvent = "";
          }
        }
      }

      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last.role === "assistant") {
          last.content = streamedText;
          last.sources = sources;
        }
        return [...updated];
      });
    } catch (err) {
      console.error("Stream error:", err);
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last.role === "assistant") {
          last.content = `Sorry, something went wrong connecting to the API. Make sure the backend is running on ${API_BASE}`;
        }
        return [...updated];
      });
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-[#fafafa]">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-stone-200 bg-white px-6 py-3">
        <h1 className="text-lg font-semibold text-stone-800 text-center">
          Hansardy
        </h1>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full px-6">
            <div className="text-center max-w-lg">
              <h2 className="text-xl font-medium text-stone-700 mb-2">
                What would you like to know about Australian Parliament?
              </h2>
              <p className="text-sm text-stone-400 mb-8">
                Search the official Hansard record with AI-powered analysis.
              </p>
              <div className="flex flex-col gap-2">
                {EXAMPLE_QUERIES.map((q) => (
                  <button
                    key={q}
                    onClick={() => handleSubmit(q)}
                    className="text-left text-sm text-stone-600 px-4 py-3 rounded-xl border border-stone-200 hover:bg-white hover:border-stone-300 hover:shadow-sm transition-all duration-150"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="max-w-2xl mx-auto px-6 py-6 space-y-6">
            {messages.map((msg, i) => (
              <ChatMessage
                key={i}
                role={msg.role}
                content={msg.content}
                sources={msg.sources}
              />
            ))}
            {isStreaming &&
              messages[messages.length - 1]?.content === "" && (
                <div className="flex gap-1.5 py-2">
                  <span
                    className="w-1.5 h-1.5 bg-stone-400 rounded-full"
                    style={{ animation: "pulse-dot 1.2s ease-in-out infinite" }}
                  />
                  <span
                    className="w-1.5 h-1.5 bg-stone-400 rounded-full"
                    style={{
                      animation: "pulse-dot 1.2s ease-in-out infinite",
                      animationDelay: "0.2s",
                    }}
                  />
                  <span
                    className="w-1.5 h-1.5 bg-stone-400 rounded-full"
                    style={{
                      animation: "pulse-dot 1.2s ease-in-out infinite",
                      animationDelay: "0.4s",
                    }}
                  />
                </div>
              )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input with gradient fade */}
      <div className="flex-shrink-0 relative">
        <div className="absolute inset-x-0 -top-8 h-8 bg-gradient-to-t from-[#fafafa] to-transparent pointer-events-none" />
        <div className="px-6 py-4 max-w-2xl mx-auto w-full">
          <QueryInput onSubmit={handleSubmit} disabled={isStreaming} />
        </div>
      </div>
    </div>
  );
}
