"use client";

import ReactMarkdown from "react-markdown";
import type { Message, ToolCall } from "@/lib/types";

function ToolBadge({ toolCall }: { toolCall: ToolCall }) {
  const labels: Record<string, string> = {
    list_tables: "Listing tables",
    get_schema: `Getting schema: ${(toolCall.input as { table_name?: string }).table_name ?? ""}`,
    sample_data: `Sampling: ${(toolCall.input as { table_name?: string }).table_name ?? ""}`,
    query_table: "Running query",
  };
  return (
    <span className="inline-flex items-center gap-1.5 bg-blue-50 border border-blue-200 text-blue-700 text-xs px-2 py-1 rounded-full">
      <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
      {labels[toolCall.name] ?? toolCall.name}
    </span>
  );
}

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div className={`max-w-[75%] ${isUser ? "order-2" : "order-1"}`}>
        {/* Tool call badges (shown while assistant is working) */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {message.toolCalls.map((tc, i) => (
              <ToolBadge key={i} toolCall={tc} />
            ))}
          </div>
        )}

        {/* Message bubble */}
        {message.content && (
          <div
            className={
              isUser
                ? "bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm"
                : "bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm shadow-sm"
            }
          >
            {isUser ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : (
              <div className="prose prose-sm max-w-none prose-pre:bg-gray-100 prose-pre:text-xs prose-table:text-xs">
                <ReactMarkdown>{message.content}</ReactMarkdown>
                {message.isStreaming && (
                  <span className="inline-block w-1.5 h-4 bg-gray-400 animate-pulse ml-0.5 align-middle" />
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
