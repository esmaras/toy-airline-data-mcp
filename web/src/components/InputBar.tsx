"use client";

import { useRef, useEffect } from "react";

interface InputBarProps {
  onSend: (text: string) => void;
  isLoading: boolean;
}

export default function InputBar({ onSend, isLoading }: InputBarProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  });

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const text = textareaRef.current?.value.trim();
    if (!text || isLoading) return;
    onSend(text);
    if (textareaRef.current) textareaRef.current.value = "";
  }

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        <textarea
          ref={textareaRef}
          rows={1}
          disabled={isLoading}
          onKeyDown={handleKeyDown}
          placeholder="Ask about schedules, aircraft rotations, fares…"
          className="flex-1 resize-none rounded-xl border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400 min-h-[40px]"
        />
        <button
          onClick={submit}
          disabled={isLoading}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-xl px-4 py-2 text-sm font-medium transition-colors min-h-[40px]"
        >
          {isLoading ? "…" : "Send"}
        </button>
      </div>
      <p className="text-center text-xs text-gray-400 mt-1.5">
        Shift+Enter for new line · Enter to send
      </p>
    </div>
  );
}
