/**
 * Types and API call for the Phase 10 function-calling chatbot widget.
 * See docs/PROJECT_ARCHITECTURE.md §8.
 */

import { apiFetch } from "@/lib/api-client";

export type ChatTurn = { role: "user" | "assistant"; text: string };

export function sendChatMessage(message: string, history: ChatTurn[]): Promise<{ answer: string }> {
  // One chat turn: the new question plus every earlier turn this session, so a follow-up
  // question ("and on Wednesday?") still has context.
  return apiFetch<{ answer: string }>("/api/v1/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
}
