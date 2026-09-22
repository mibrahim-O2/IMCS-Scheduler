"use client";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import type { TimetableSummary } from "@/lib/timetables";

function formatCreatedAt(value: string): string {
  // Generation timestamps come back as ISO strings; show a short readable date and time.
  return new Date(value).toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export function TimetableList({
  timetables,
  loading,
  onView,
}: {
  timetables: TimetableSummary[];
  loading: boolean;
  onView: (id: number) => void;
}) {
  // Every generated timetable as a stacked card whether it converged, how many
  // sessions it placed, and which divisions it covers, with a button to open the detail.
  if (loading) {
    return (
      <p className="flex items-center gap-2 text-sm text-content/60">
        <Spinner /> Loading generated timetables…
      </p>
    );
  }

  if (timetables.length === 0) {
    return (
      <div className="rounded-xl bg-surface p-8 text-center ring-1 ring-content/15">
        <p className="font-medium text-content">No timetables generated yet</p>
        <p className="mt-1 text-sm text-content/60">Generate one for BSCS Part-I to Part-IV above.</p>
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {timetables.map((timetable) => (
        <li key={timetable.id} className="rounded-xl bg-surface p-4 ring-1 ring-content/15">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0 space-y-1">
              <p className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-content">{timetable.label}</span>
                <span className="rounded-full bg-content/10 px-2 py-0.5 text-xs font-medium text-content">
                  {timetable.status}
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium text-content ${
                    timetable.converged ? "bg-status-available/20" : "bg-status-conflict/20"
                  }`}
                >
                  {timetable.converged ? "Converged" : "Not converged"}
                </span>
              </p>
              <p className="text-sm text-content/70">
                {timetable.session_count} sessions · {timetable.generation_count ?? "?"} generations · created{" "}
                {formatCreatedAt(timetable.created_at)}
              </p>
              <p className="break-words text-xs text-content/60">{timetable.division_labels.join(", ")}</p>
            </div>
            <Button variant="secondary" onClick={() => onView(timetable.id)} className="w-full sm:w-auto">
              View
            </Button>
          </div>
        </li>
      ))}
    </ul>
  );
}
