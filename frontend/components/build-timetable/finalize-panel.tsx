"use client";

import { DivisionScheduleTable } from "@/components/timetables/division-schedule";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { exportUrl, type FinalizeResult } from "@/lib/build-timetable";
import type { TimetableDetail } from "@/lib/timetables";

// Step 10: locks the list in, runs the real GA, and shows what came out reuses the same
// division-schedule table the /timetables browse page uses, so a result looks identical
// whichever way it was generated.
export function FinalizePanel({
  assignmentCount,
  locked,
  finalizing,
  result,
  detail,
  onFinalize,
}: {
  assignmentCount: number;
  locked: boolean;
  finalizing: boolean;
  result: FinalizeResult | null;
  detail: TimetableDetail | null;
  onFinalize: () => void;
}) {
  return (
    <section className="space-y-4 rounded-xl bg-card p-4 shadow-sm ring-1 ring-content/10 sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-content">10. Finalize and generate</h2>
          <p className="mt-1 text-sm text-content/70">
            {locked
              ? "This division's assignments are locked. Finalizing again runs a fresh generation from the same list."
              : "Locks the list above and runs the real GA for this division."}
          </p>
        </div>
        <Button onClick={onFinalize} loading={finalizing} disabled={assignmentCount === 0} className="w-full sm:w-auto">
          {locked ? "Regenerate" : "Finalize"}
        </Button>
      </div>

      {result && (
        <Alert tone={result.converged ? "success" : "warning"}>
          {result.converged
            ? `Converged in ${result.generation_count} generations, ${result.session_count} sessions placed in ${result.wall_seconds.toFixed(2)}s.`
            : `Did not fully converge (${result.stagnated ? "stalled" : "hit the generation cap"}) ${result.conflict_list.length} conflict(s) remain. Review below before trusting this result.`}
          {" "}
          <a href={exportUrl(result.timetable_id)} className="font-medium text-primary underline">
            Download Word file
          </a>
        </Alert>
      )}

      {result && result.conflict_list.length > 0 && (
        <Alert tone="warning">
          <ul className="list-disc space-y-1 pl-5">
            {result.conflict_list.slice(0, 10).map((line, index) => (
              <li key={index}>{line}</li>
            ))}
          </ul>
        </Alert>
      )}

      {detail?.divisions.map((schedule) => (
        <DivisionScheduleTable key={schedule.division_id} schedule={schedule} />
      ))}
    </section>
  );
}
