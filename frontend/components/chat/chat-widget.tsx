"use client";

import { MessageCircle, Send, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { errorMessage } from "@/lib/api-client";
import { sendChatMessage, type ChatTurn } from "@/lib/chat";

// A floating chat button on every page (Phase 10): opens a small panel for asking real,
// function-called questions about the current schedule. History lives only in this
// component's state no persistence across a reload, which the task doesn't ask for.
export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Keeps the newest message in view as the conversation grows.
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, open]);

  async function handleSend() {
    // Sends the typed question, appends the real answer (or a readable error) to the thread.
    const text = draft.trim();
    if (!text || sending) return;
    setDraft("");
    setError(null);
    const nextTurns: ChatTurn[] = [...turns, { role: "user", text }];
    setTurns(nextTurns);
    setSending(true);
    try {
      const { answer } = await sendChatMessage(text, turns);
      setTurns([...nextTurns, { role: "assistant", text: answer }]);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 sm:bottom-6 sm:right-6">
      {open && (
        <div className="mb-3 flex h-[28rem] w-[calc(100vw-2rem)] max-w-sm flex-col overflow-hidden rounded-2xl bg-card shadow-lg ring-1 ring-content/10">
          <div className="flex items-center justify-between border-b border-content/10 px-4 py-3">
            <p className="text-sm font-semibold text-content">Ask about the schedule</p>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
              className="flex h-9 w-9 items-center justify-center rounded-md text-content/60 hover:bg-content/10 hover:text-content"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
            {turns.length === 0 && (
              <p className="text-sm text-content/60">
                Try &quot;who&apos;s teaching right now?&quot; or &quot;is Lab A free on Tuesday at 10am?&quot;
              </p>
            )}
            {turns.map((turn, index) => (
              <div
                key={index}
                className={`max-w-[85%] break-words rounded-xl px-3 py-2 text-sm ${
                  turn.role === "user"
                    ? "ml-auto bg-primary text-white"
                    : "bg-surface text-content ring-1 ring-content/10"
                }`}
              >
                {turn.text}
              </div>
            ))}
            {sending && <p className="text-sm text-content/60">Thinking…</p>}
            {error && <p className="text-sm text-status-conflict">{error}</p>}
          </div>

          <div className="flex items-center gap-2 border-t border-content/10 p-3">
            <input
              type="text"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void handleSend();
              }}
              placeholder="Ask a question…"
              className="min-h-11 w-full flex-1 rounded-lg bg-surface px-3 py-2 text-sm text-content ring-1 ring-content/20 focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <button
              type="button"
              onClick={() => void handleSend()}
              disabled={sending || !draft.trim()}
              aria-label="Send"
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label={open ? "Close chat" : "Open chat"}
        className="flex h-14 w-14 items-center justify-center rounded-full bg-primary text-white shadow-lg hover:bg-primary/90"
      >
        {open ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
      </button>
    </div>
  );
}
