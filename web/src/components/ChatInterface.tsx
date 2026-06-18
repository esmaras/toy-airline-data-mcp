"use client";

import { useState, useCallback } from "react";
import MessageList from "./MessageList";
import InputBar from "./InputBar";
import type { Message, ApiMessage, ToolCall } from "@/lib/types";

function uid() {
  return Math.random().toString(36).slice(2);
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(async (text: string) => {
    const userMsg: Message = { id: uid(), role: "user", content: text };
    const assistantId = uid();
    const assistantMsg: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      toolCalls: [],
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsLoading(true);

    // Build history to send to API (exclude the current empty assistant placeholder)
    const history: ApiMessage[] = [...messages, userMsg].map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history }),
      });

      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          if (!part.trim()) continue;

          // Parse SSE: extract event and data lines
          let eventType = "message";
          let dataStr = "";
          for (const line of part.split("\n")) {
            if (line.startsWith("event: ")) eventType = line.slice(7);
            if (line.startsWith("data: ")) dataStr = line.slice(6);
          }
          if (!dataStr) continue;

          const payload = JSON.parse(dataStr);

          if (eventType === "tool_call") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, toolCalls: [...(m.toolCalls ?? []), payload as ToolCall] }
                  : m
              )
            );
          } else if (eventType === "text") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + payload.delta }
                  : m
              )
            );
          } else if (eventType === "done") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, isStreaming: false } : m
              )
            );
          } else if (eventType === "error") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: `Error: ${payload.message}`, isStreaming: false }
                  : m
              )
            );
          }
        }
      }
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: `Failed to get response: ${String(err)}`, isStreaming: false }
            : m
        )
      );
    } finally {
      setIsLoading(false);
    }
  }, [messages]);

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto">
      <MessageList messages={messages} />
      <InputBar onSend={sendMessage} isLoading={isLoading} />
    </div>
  );
}
