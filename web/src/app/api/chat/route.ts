import Anthropic from "@anthropic-ai/sdk";
import { TOOL_DEFINITIONS, SYSTEM_PROMPT } from "@/lib/tools";
import { callTool } from "@/lib/sharingClient";
import type { ApiMessage } from "@/lib/types";

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

const MODEL = "claude-sonnet-4-5";
const MAX_TOKENS = 4096;
const MAX_TOOL_ROUNDS = 10; // safety limit on agentic loop

function sseEvent(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

export async function POST(req: Request) {
  const { messages }: { messages: ApiMessage[] } = await req.json();

  const stream = new ReadableStream({
    async start(controller) {
      const enc = new TextEncoder();
      const emit = (event: string, data: unknown) => {
        controller.enqueue(enc.encode(sseEvent(event, data)));
      };

      try {
        // Build conversation history for Anthropic API
        type AnthropicMessage = Anthropic.MessageParam;
        const conversation: AnthropicMessage[] = messages.map((m) => ({
          role: m.role,
          content: m.content,
        }));

        // Agentic loop — non-streaming for tool-use turns
        for (let round = 0; round < MAX_TOOL_ROUNDS; round++) {
          const response = await anthropic.messages.create({
            model: MODEL,
            max_tokens: MAX_TOKENS,
            system: SYSTEM_PROMPT,
            tools: TOOL_DEFINITIONS,
            messages: conversation,
          });

          if (response.stop_reason === "tool_use") {
            const toolUseBlocks = response.content.filter(
              (b): b is Anthropic.ToolUseBlock => b.type === "tool_use"
            );

            // Notify the browser which tools are being called
            for (const block of toolUseBlocks) {
              emit("tool_call", { name: block.name, input: block.input });
            }

            // Execute all tools (sequentially to preserve context order)
            const toolResults: Anthropic.ToolResultBlockParam[] = [];
            for (const block of toolUseBlocks) {
              try {
                const result = await callTool(
                  block.name as "list_tables" | "get_schema" | "sample_data" | "query_table",
                  block.input as Record<string, unknown>
                );
                toolResults.push({
                  type: "tool_result",
                  tool_use_id: block.id,
                  content: result,
                });
              } catch (err) {
                toolResults.push({
                  type: "tool_result",
                  tool_use_id: block.id,
                  is_error: true,
                  content: `Error: ${String(err)}`,
                });
              }
            }

            // Append assistant turn + tool results to conversation
            conversation.push({ role: "assistant", content: response.content });
            conversation.push({ role: "user", content: toolResults });

          } else if (response.stop_reason === "end_turn") {
            // Emit text blocks directly — no need for a second API call
            for (const block of response.content) {
              if (block.type === "text") {
                emit("text", { delta: block.text });
              }
            }
            emit("done", {});
            break;
          } else {
            // Unexpected stop reason
            emit("error", { message: `Unexpected stop_reason: ${response.stop_reason}` });
            break;
          }
        }
      } catch (err) {
        emit("error", { message: String(err) });
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
