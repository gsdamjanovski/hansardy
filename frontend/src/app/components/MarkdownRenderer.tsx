"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

function processCitations(content: string): string {
  return content.replace(
    /\[(\d+)\]/g,
    '<cite data-ref="$1">[$1]</cite>'
  );
}

const components: Components = {
  p: ({ children }) => (
    <p className="mb-3 last:mb-0 leading-[1.75]">{children}</p>
  ),
  h1: ({ children }) => (
    <h1 className="text-xl font-semibold text-stone-900 mt-6 mb-3">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-lg font-semibold text-stone-900 mt-5 mb-2">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-base font-medium text-stone-900 mt-4 mb-2">
      {children}
    </h3>
  ),
  ul: ({ children }) => (
    <ul className="mb-3 pl-5 list-disc marker:text-stone-400 space-y-1">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-3 pl-5 list-decimal marker:text-stone-400 space-y-1">
      {children}
    </ol>
  ),
  li: ({ children }) => <li className="leading-[1.75]">{children}</li>,
  strong: ({ children }) => (
    <strong className="font-semibold text-stone-900">{children}</strong>
  ),
  em: ({ children }) => <em className="italic">{children}</em>,
  a: ({ href, children }) => (
    <a
      href={href}
      className="text-teal-700 underline underline-offset-2 hover:text-teal-900 transition-colors"
      target="_blank"
      rel="noopener noreferrer"
    >
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-stone-300 pl-4 my-3 text-stone-600 italic">
      {children}
    </blockquote>
  ),
  code: ({ className, children }) => {
    const isBlock = className?.includes("language-");
    if (isBlock) {
      return (
        <code
          className={`block bg-stone-100 rounded-lg p-4 overflow-x-auto font-mono text-[13px] text-stone-800 ${className || ""}`}
        >
          {children}
        </code>
      );
    }
    return (
      <code className="bg-stone-100 text-stone-800 rounded px-1.5 py-0.5 font-mono text-[13px]">
        {children}
      </code>
    );
  },
  pre: ({ children }) => <pre className="mb-3 last:mb-0">{children}</pre>,
  table: ({ children }) => (
    <div className="overflow-x-auto mb-3">
      <table className="min-w-full text-sm border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-stone-100 text-stone-700">{children}</thead>
  ),
  th: ({ children }) => (
    <th className="border border-stone-200 px-3 py-2 text-left font-medium">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border border-stone-200 px-3 py-2">{children}</td>
  ),
  cite: ({ children }) => (
    <span className="inline-flex items-center justify-center text-[11px] font-semibold text-teal-700 bg-teal-50 border border-teal-200 rounded px-1.5 py-0 mx-0.5 align-baseline leading-snug">
      {children}
    </span>
  ),
};

export default function MarkdownRenderer({ content }: { content: string }) {
  const processed = processCitations(content);

  return (
    <div className="text-[15px] text-stone-800">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
        allowedElements={undefined}
        unwrapDisallowed={false}
        skipHtml={false}
      >
        {processed}
      </ReactMarkdown>
    </div>
  );
}
