import type { ReactNode } from "react";

type Tone = "success" | "error" | "warning" | "info";

const TONE_CLASSES: Record<Tone, string> = {
  success: "bg-status-available/15 ring-status-available/40",
  error: "bg-status-conflict/15 ring-status-conflict/40",
  warning: "bg-status-busy/15 ring-status-busy/40",
  info: "bg-primary/10 ring-primary/30",
};

export function Alert({
  tone,
  children,
  action,
  onDismiss,
}: {
  tone: Tone;
  children: ReactNode;
  action?: ReactNode;
  onDismiss?: () => void;
}) {
  // Inline message banner. Errors are announced to screen readers immediately;
  // everything else is announced politely.
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={`flex flex-wrap items-center gap-3 rounded-lg px-3 py-2 text-sm text-content ring-1 ${TONE_CLASSES[tone]}`}
    >
      <div className="min-w-0 flex-1 break-words">{children}</div>
      {action}
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss message"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-lg leading-none text-content/60 hover:bg-content/10 hover:text-content"
        >
          ×
        </button>
      )}
    </div>
  );
}
