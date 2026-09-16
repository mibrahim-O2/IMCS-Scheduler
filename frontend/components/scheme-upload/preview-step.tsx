"use client";

import { Button } from "@/components/ui/button";
import { countCourses, type SemesterRows } from "@/lib/schemes";

export function PreviewStep({
  programName,
  schemeYear,
  fileName,
  semesters,
  busy,
  onBack,
  onConfirm,
}: {
  programName: string;
  schemeYear: number;
  fileName: string;
  semesters: SemesterRows[];
  busy: boolean;
  onBack: () => void;
  onConfirm: () => void;
}) {
  // Step 4: last look before anything is written. Confirm uploads the file and saves the rows.
  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-content">Preview before saving</h2>
        <p className="mt-1 text-sm text-content/70">
          Nothing has been saved yet. Confirm to store the document and the course list.
        </p>
      </div>

      <dl className="grid grid-cols-1 gap-3 rounded-xl bg-surface p-4 ring-1 ring-content/15 sm:grid-cols-3">
        {[
          ["Program", programName],
          ["Scheme year", String(schemeYear)],
          ["File", fileName],
        ].map(([label, value]) => (
          <div key={label} className="min-w-0">
            <dt className="text-xs font-medium uppercase tracking-wide text-content/60">{label}</dt>
            <dd className="mt-1 break-words text-sm text-content">{value}</dd>
          </div>
        ))}
      </dl>

      {semesters.map((semester) => (
        <div key={semester.semester} className="rounded-xl bg-surface ring-1 ring-content/15">
          <h3 className="px-4 py-3 text-sm font-semibold text-content">
            Semester {semester.semester} · {semester.courses.length} course
            {semester.courses.length === 1 ? "" : "s"}
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[34rem] text-left text-sm">
              <thead className="bg-content/5 text-xs uppercase tracking-wide text-content/60">
                <tr>
                  <th className="px-4 py-2 font-medium">Code</th>
                  <th className="px-4 py-2 font-medium">Name</th>
                  <th className="px-4 py-2 font-medium">Cr.</th>
                  <th className="px-4 py-2 font-medium">Lab</th>
                  <th className="px-4 py-2 font-medium">Marks</th>
                </tr>
              </thead>
              <tbody>
                {semester.courses.map((course, index) => (
                  <tr key={`${course.code}-${index}`} className="border-t border-content/10">
                    <td className="px-4 py-2 font-mono text-xs">{course.code}</td>
                    <td className="px-4 py-2">{course.name}</td>
                    <td className="px-4 py-2">{course.credit_hours ?? "NC"}</td>
                    <td className="px-4 py-2">{course.has_lab ? course.lab_credit_hours ?? "yes" : "—"}</td>
                    <td className="px-4 py-2">
                      {course.min_marks ?? "—"} / {course.max_marks ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onBack} disabled={busy} className="w-full sm:w-auto">
          Back
        </Button>
        <Button onClick={onConfirm} disabled={busy} className="w-full sm:w-auto">
          {busy ? "Saving…" : `Confirm and save ${countCourses(semesters)} courses`}
        </Button>
      </div>
    </section>
  );
}
