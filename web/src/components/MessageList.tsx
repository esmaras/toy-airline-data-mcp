"use client";

import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import type { Message } from "@/lib/types";

export default function MessageList({ messages }: { messages: Message[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-1">
      {messages.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-2">
          <p className="text-lg font-medium">Ask about Southwest Airlines data</p>
          <p className="text-sm">Try: "What tables are available?" or "Show me 5 flights from oag_may"</p>
        </div>
      )}
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
