export type MessageRole = "user" | "assistant";

export interface ToolCall {
  name: string;
  input: Record<string, unknown>;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  toolCalls?: ToolCall[];
  isStreaming?: boolean;
}

// Shape of messages sent to /api/chat
export interface ApiMessage {
  role: MessageRole;
  content: string;
}
