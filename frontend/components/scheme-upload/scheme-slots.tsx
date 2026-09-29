"use client";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import type { Program, SchemeSummary } from "@/lib/schemes";

const PART_LABELS = ["Part-I", "Part-II", "Part-III", "Part-IV"];

function formatUploadedAt(value: string): string {
  // Upload timestamps come back as ISO strings; show a short readable date.
  return new Date(value).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

// A 4-slot grid (Part-I..Part-IV) per schedulable program. Empty slot: "Upload".
// Filled slot: "View courses" (opens the full-page view in the parent) and "Delete".
export function SchemeSlots({
  programs,
  schemes,
  loading,
  onUpload,
  onRequestDelete,
  onViewCourses,
}: {
  programs: Program[];
  schemes: SchemeSummary[];
  loading: boolean;
  onUpload: (programId: number, part: number) => void;
  onRequestDelete: (scheme: SchemeSummary) => void;
  onViewCourses: (scheme: SchemeSummary) => void;
}) {
  if (loading) {
    return (
      <p className="flex items-center gap-2 text-sm text-content/60">
        <Spinner /> Loading saved schemes…
      </p>
    );
  }

  return (
    <section className="space-y-8">
      {programs.map((program) => {
        // Only this program's active schemes, one per Part slot (at most).
        const byPart = new Map(
          schemes
            .filter((scheme) => scheme.program_id === program.id && scheme.is_active)
            .map((scheme) => [scheme.applies_to_part, scheme]),
        );

        return (
          <div key={program.id}>
            <h2 className="text-lg font-semibold text-content">{program.display_name}</h2>
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {PART_LABELS.map((label, index) => {
                const part = index + 1;
                const scheme = byPart.get(part);

                return (
                  <div key={part} className="rounded-xl bg-surface p-4 ring-1 ring-content/15">
                    <p className="font-semibold text-content">{label}</p>
                    {scheme ? (
                      <>
                        <p className="mt-1 text-sm text-content/70">
                          Scheme year {scheme.scheme_year} · {scheme.course_count} course
                          {scheme.course_count === 1 ? "" : "s"}
                        </p>
                        <p className="text-xs text-content/60">Uploaded {formatUploadedAt(scheme.uploaded_at)}</p>
                        {scheme.file_url && (
                          <a
                            href={scheme.file_url}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-1 inline-flex min-h-8 items-center break-all text-xs font-medium text-primary underline"
                          >
                            {scheme.source_filename ?? "Original document"}
                          </a>
                        )}
                        <div className="mt-3 flex flex-col gap-2">
                          <Button variant="secondary" onClick={() => onViewCourses(scheme)} className="w-full text-xs">
                            View courses
                          </Button>
                          <Button variant="danger" onClick={() => onRequestDelete(scheme)} className="w-full text-xs">
                            Delete
                          </Button>
                        </div>
                      </>
                    ) : (
                      <>
                        <p className="mt-1 text-sm text-content/60">Empty, no scheme uploaded yet</p>
                        <Button onClick={() => onUpload(program.id, part)} className="mt-3 w-full text-xs">
                          Upload
                        </Button>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </section>
  );
}
