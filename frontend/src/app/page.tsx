"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ChatMessage from "./components/ChatMessage";
import QueryInput from "./components/QueryInput";
import SourceCard from "./components/SourceCard";

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

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeSources, setActiveSources] = useState<Source[]>([]);
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
    setActiveSources([]);

    // Add empty assistant message to stream into
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

        for (const line of lines) {
          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            const data = line.slice(5);

            if (currentEvent === "sources") {
              try {
                sources = JSON.parse(data);
                setActiveSources(sources);
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

      // Final update
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
    <div className="flex h-screen bg-gray-50">
      {/* Main chat panel */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex-shrink-0 border-b border-gray-200 bg-white px-6 py-4">
          <h1 className="text-xl font-semibold text-gray-900">Hansardy</h1>
          <p className="text-sm text-gray-500">
            Search and query Australian Hansard transcripts
          </p>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-md">
                <h2 className="text-lg font-medium text-gray-700 mb-2">
                  Ask anything about Australian parliament
                </h2>
                <p className="text-sm text-gray-500 mb-6">
                  Hansardy searches the official Hansard record and provides
                  answers with citations.
                </p>
                <div className="flex flex-col gap-2 text-sm text-gray-500">
                  <button
                    onClick={() =>
                      handleSubmit(
                        "What did the Treasurer say about inflation in 2024?"
                      )
                    }
                    className="text-left px-4 py-2 rounded-lg border border-gray-200 hover:bg-white hover:border-gray-300 transition-colors"
                  >
                    &ldquo;What did the Treasurer say about inflation in
                    2024?&rdquo;
                  </button>
                  <button
                    onClick={() =>
                      handleSubmit(
                        "Has the Senate debated nuclear energy recently?"
                      )
                    }
                    className="text-left px-4 py-2 rounded-lg border border-gray-200 hover:bg-white hover:border-gray-300 transition-colors"
                  >
                    &ldquo;Has the Senate debated nuclear energy
                    recently?&rdquo;
                  </button>
                  <button
                    onClick={() =>
                      handleSubmit(
                        "What happened in Question Time on the last sitting day?"
                      )
                    }
                    className="text-left px-4 py-2 rounded-lg border border-gray-200 hover:bg-white hover:border-gray-300 transition-colors"
                  >
                    &ldquo;What happened in Question Time on the last sitting
                    day?&rdquo;
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-4">
              {messages.map((msg, i) => (
                <ChatMessage key={i} role={msg.role} content={msg.content} />
              ))}
              {isStreaming &&
                messages[messages.length - 1]?.content === "" && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-2xl px-4 py-3">
                      <div className="flex gap-1">
                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                        <span
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                          style={{ animationDelay: "0.1s" }}
                        />
                        <span
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                          style={{ animationDelay: "0.2s" }}
                        />
                      </div>
                    </div>
                  </div>
                )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="flex-shrink-0 px-6 py-4 max-w-3xl mx-auto w-full">
          <QueryInput onSubmit={handleSubmit} disabled={isStreaming} />
        </div>
      </div>

      {/* Sources sidebar */}
      <div className="w-80 flex-shrink-0 border-l border-gray-200 bg-white overflow-y-auto hidden lg:block">
        <div className="px-4 py-4 border-b border-gray-200">
          <h2 className="text-sm font-semibold text-gray-700">Sources</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {activeSources.length > 0
              ? `${activeSources.length} Hansard passages retrieved`
              : "Sources will appear here"}
          </p>
        </div>
        <div className="p-4 space-y-3">
          {activeSources.map((source, i) => (
            <SourceCard key={source.id} source={source} index={i + 1} />
          ))}
        </div>
      </div>
    </div>
  );
}
