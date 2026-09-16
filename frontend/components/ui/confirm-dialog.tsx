"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";

// Blocking confirmation before a destructive action. It sits at the bottom of the
// screen on phones (thumb reach) and centred on larger screens.
export function ConfirmDialog({
  title,
  message,
  confirmLabel,
  busyLabel = "Working…",
  busy = false,
  onConfirm,
  onCancel,
}: {
  title: string;
  message: string;
  confirmLabel: string;
  busyLabel?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  useEffect(() => {
    // Escape closes the dialog, unless the action is already running.
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape" && !busy) onCancel();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [busy, onCancel]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-4 sm:items-center"
    >
      <div className="w-full max-w-md rounded-xl bg-card p-6 shadow-lg">
        <h2 id="confirm-dialog-title" className="text-lg font-semibold text-content">
          {title}
        </h2>
        <p className="mt-2 text-sm text-content/70">{message}</p>
        <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button variant="secondary" onClick={onCancel} disabled={busy} className="w-full sm:w-auto">
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm} loading={busy} className="w-full sm:w-auto">
            {busy ? busyLabel : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
