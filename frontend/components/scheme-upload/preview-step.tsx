"use client";

import { SemesterTable } from "@/components/scheme-upload/semester-table";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { pairSemesters, summarize, type SemesterRows } from "@/lib/schemes";

export function PreviewStep({
  programName,
  schemeYear,
  fileName,
  semesters,
  saving,
  onBack,
  onConfirm,
}: {
  programName: string;
  schemeYear: number;
  fileName: string;
  semesters: SemesterRows[];
  saving: boolean;
  onBack: () => void;
  onConfirm: () => void;
}) {
  // Step 4: exactly what will be stored labs are shown merged the same way the server merges them.
  const paired = pairSemesters(semesters);
  const totals = summarize(paired);
  const mergedLabRows = summarize(semesters).courses - totals.courses;

  const facts: [string, string][] = [
    ["Program", programName],
    ["Scheme year", String(schemeYear)],
    ["Document", fileName],
    ["Courses", String(totals.courses)],
    ["With a lab", String(totals.labs)],
    ["Credit hours", String(totals.creditHours)],
  ];

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-content">Preview before saving</h2>
        <p className="mt-1 text-sm text-content/70">
          Nothing has been saved yet. Confirm to store the document and this course list.
        </p>
      </div>

      <dl className="grid grid-cols-2 gap-4 rounded-xl bg-surface p-4 ring-1 ring-content/15 sm:grid-cols-3">
        {facts.map(([label, value]) => (
          <div key={label} className="min-w-0">
            <dt className="text-xs font-medium uppercase tracking-wide text-content/60">{label}</dt>
            <dd className="mt-1 break-words text-sm font-medium text-content">{value}</dd>
          </div>
        ))}
      </dl>

      {mergedLabRows > 0 && (
        <Alert tone="info">
          {mergedLabRows} separate lab row{mergedLabRows === 1 ? "" : "s"} will be merged into
          {mergedLabRows === 1 ? " its" : " their"} theory course{mergedLabRows === 1 ? "" : "s"}, so{" "}
          {totals.courses} courses will be saved.
        </Alert>
      )}

      <div className="space-y-4">
        {paired.map((semester) => (
          <SemesterTable key={semester.semester} semester={semester} />
        ))}
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
        {saving && (
          <p className="text-center text-xs text-content/60 sm:mr-auto sm:text-left">
            Uploading the document and saving {totals.courses} courses…
          </p>
        )}
        <Button variant="secondary" onClick={onBack} disabled={saving} className="w-full sm:w-auto">
          Back
        </Button>
        <Button onClick={onConfirm} loading={saving} className="w-full sm:w-auto">
          {saving ? "Saving…" : `Confirm and save ${totals.courses} courses`}
        </Button>
      </div>
    </section>
  );
}
